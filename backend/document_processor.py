"""
Document Processor — Orchestrates the 14-Stage Enterprise Extraction Pipeline
===============================================================================

ARCHITECTURE OVERVIEW:
    Raw Document
        ↓
    [Stage 1]   TextCleaner              — Remove headers, footers, page numbers, OCR artifacts
    [Stage 2]   SentenceSegmenter        — Split into sentences with provenance tracking
    [Stage 3]   CorefResolver            — Resolve pronouns (OpenAI → ChatGPT example)
    [Stage 4]   HybridNER                — Ensemble: spaCy lg + optional transformer + rules
    [Stage 5]   TechnicalEntityDetector  — Rule-based detection of AI/technical terms
    [Stage 6]   EntityFusion             — Merge predictions from all NER sources
    [Stage 7]   EntityValidator          — Reject headings, boilerplate, long phrases, pronouns
    [Stage 8]   EntityNormalizer         — Canonical names, entity_id generation
    [Stage 9]   AliasResolver            — Resolve aliases (Open AI → OpenAI)
    [Stage 10]  Deduplicator             — Aggressive fuzzy dedup of entities
    [Stage 11]  DependencyParser         — Dependency tree SPO extraction
    [Stage 12]  RelationshipExtractor    — Full relationship extraction
    [Stage 13]  RelationshipValidator    — Confidence scoring, validation
    [Stage 14]  PredicateNormalizer      — Semantic predicate normalization
        ↓
    Neo4j Aura (Permanent Knowledge Graph)
        ↓
    Continue (vector store, etc.)

DESIGN PRINCIPLES:
    - Every stage is independently testable and replaceable
    - All stages preserve provenance (source document, sentence, chunk_id)
    - No extraction logic changed — only storage layer upgraded
    - Pure Cypher for Neo4j (no APOC dependencies)
    - CPU-optimized with configurable transformer usage
"""

import os
import uuid
from typing import Any, Dict, List

import PyPDF2
import re

from config import Config

# ---------------------------------------------------------------------------
# Extraction pipeline imports (14 stages + metrics + debug)
# ---------------------------------------------------------------------------
from extraction.text_cleaner import TextCleaner
from extraction.sentence_segmenter import SentenceSegmenter
from extraction.coref_resolver import CoreferenceResolver
from extraction.hybrid_ner import HybridNER
from extraction.technical_entity_detector import TechnicalEntityDetector
from extraction.entity_fusion import EntityFusion
from extraction.entity_validator import EntityValidator
from extraction.entity_normalizer import EntityNormalizer
from extraction.alias_resolver import AliasResolver
from extraction.deduplicator import Deduplicator
from extraction.dependency_parser import DependencyParser
from extraction.relationship_extractor import RelationshipExtractor
from extraction.relationship_validator import RelationshipValidator
from extraction.predicate_normalizer import PredicateNormalizer
from extraction.extraction_metrics import ExtractionMetrics
from extraction.debug_manager import DebugManager


class DocumentProcessor:
    """
    Processes uploaded documents through the full 14-stage extraction pipeline.

    Public API is UNCHANGED:
        process_document(file_path, filename) -> Dict
        extract_entities_and_relationships(text, doc_id) -> Dict
        chunk_document(text, metadata) -> List
        extract_text_from_pdf(file_path) -> str
        extract_text_from_txt(file_path) -> str
    """

    def __init__(self):
        self.chunk_size = Config.CHUNK_SIZE
        self.chunk_overlap = Config.CHUNK_OVERLAP
        use_hf = getattr(Config, "USE_HUGGINGFACE_NER", False)

        print("=" * 60)
        print("🔧 INITIALIZING 14-STAGE ENTERPRISE EXTRACTION PIPELINE")
        print("=" * 60)

        # --- Stage 1: Text Cleaner ---
        self.text_cleaner = TextCleaner()
        print("  [1/14] TextCleaner — Ready")

        # --- Stage 2: Sentence Segmenter ---
        self.sentence_segmenter = SentenceSegmenter()
        print("  [2/14] SentenceSegmenter — Ready")

        # --- Stage 4: Hybrid NER (loads spaCy model) ---
        self.ner_pipeline = HybridNER(use_transformer=use_hf)
        print(f"  [4/14] HybridNER — spaCy + {'Transformer' if use_hf else 'Rules only'} — Ready")

        # --- Stage 3: Coreference Resolver (uses same spaCy nlp object) ---
        self.coref_resolver = CoreferenceResolver(nlp=self.ner_pipeline.nlp)
        print("  [3/14] CoreferenceResolver — Ready")

        # --- Stage 5: Technical Entity Detector ---
        self.technical_detector = TechnicalEntityDetector()
        print("  [5/14] TechnicalEntityDetector — Ready")

        # --- Stage 6: Entity Fusion ---
        self.entity_fusion = EntityFusion()
        print("  [6/14] EntityFusion — Ready")

        # --- Stage 7: Entity Validator ---
        min_conf = getattr(Config, "ENTITY_MIN_CONFIDENCE", 0.60)
        self.entity_validator = EntityValidator(min_confidence=min_conf)
        print(f"  [7/14] EntityValidator (min_conf={min_conf}) — Ready")

        # --- Stage 8: Entity Normalizer ---
        self.entity_normalizer = EntityNormalizer()
        print("  [8/14] EntityNormalizer — Ready")

        # --- Stage 9: Alias Resolver ---
        self.alias_resolver = AliasResolver()
        print("  [9/14] AliasResolver — Ready")

        # --- Stage 10: Deduplicator ---
        self.deduplicator = Deduplicator()
        print("  [10/14] Deduplicator — Ready")

        # --- Stage 11: Dependency Parser (uses spaCy) ---
        self.dependency_parser = DependencyParser(self.ner_pipeline)
        print("  [11/14] DependencyParser — Ready")

        # --- Stage 12: Relationship Extractor ---
        self.rel_extractor = RelationshipExtractor(self.ner_pipeline)
        print("  [12/14] RelationshipExtractor — Ready")

        # --- Stage 13: Relationship Validator ---
        rel_min_conf = getattr(Config, "REL_MIN_CONFIDENCE", 0.55)
        self.rel_validator = RelationshipValidator(min_confidence=rel_min_conf)
        print(f"  [13/14] RelationshipValidator (min_conf={rel_min_conf}) — Ready")

        # --- Stage 14: Predicate Normalizer ---
        self.predicate_normalizer = PredicateNormalizer()
        print("  [14/14] PredicateNormalizer — Ready")

        # --- Metrics & Debug ---
        self.metrics = ExtractionMetrics()
        self.debug_manager = DebugManager()

        print("=" * 60)
        print("✅ 14-STAGE PIPELINE READY")
        print("=" * 60)

    # ------------------------------------------------------------------
    # Text extraction (unchanged public API)
    # ------------------------------------------------------------------

    def extract_text_from_pdf(self, file_path: str) -> str:
        """Extract text from a PDF file using PyPDF2."""
        text = ""
        try:
            with open(file_path, "rb") as fh:
                reader = PyPDF2.PdfReader(fh)
                for page in reader.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
        except Exception as exc:
            raise Exception(f"Error extracting PDF text: {exc}") from exc
        return text

    def extract_text_from_txt(self, file_path: str) -> str:
        """Extract text from a TXT file, trying common encodings."""
        for encoding in ("utf-8", "latin-1", "cp1252"):
            try:
                with open(file_path, "r", encoding=encoding) as fh:
                    return fh.read()
            except UnicodeDecodeError:
                continue
        raise Exception("Could not decode text file with common encodings.")

    # ------------------------------------------------------------------
    # Chunking (unchanged public API)
    # ------------------------------------------------------------------

    def split_text_into_chunks(self, text: str) -> List[str]:
        """Split text into overlapping sentence-aligned chunks."""
        chunks: List[str] = []
        text = re.sub(r"\s+", " ", text).strip()
        sentences = re.split(r"(?<=[.!?])\s+", text)

        current_chunk = ""
        for sentence in sentences:
            if len(current_chunk) + len(sentence) <= self.chunk_size:
                current_chunk += (" " if current_chunk else "") + sentence
            else:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                overlap_text = (
                    current_chunk[-self.chunk_overlap:]
                    if len(current_chunk) > self.chunk_overlap
                    else current_chunk
                )
                current_chunk = overlap_text + " " + sentence

        if current_chunk:
            chunks.append(current_chunk.strip())
        if not chunks and text:
            chunks = [text]
        return chunks

    def chunk_document(
        self, text: str, metadata: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Split document text into chunks with metadata attached."""
        chunks = self.split_text_into_chunks(text)
        chunked_docs = []
        for i, chunk in enumerate(chunks):
            if len(chunk.strip()) > 50:
                chunked_docs.append({
                    "text": chunk.strip(),
                    "metadata": {
                        **metadata,
                        "chunk_index": i,
                        "chunk_id": f"{metadata.get('document_id', 'doc')}_chunk_{i}",
                        "char_start": -1,
                        "char_end": -1,
                    },
                })
        return chunked_docs

    # ------------------------------------------------------------------
    # 14-STAGE EXTRACTION PIPELINE
    # ------------------------------------------------------------------

    def extract_entities_and_relationships(
        self, text: str, doc_id: str = None
    ) -> Dict[str, List]:
        """
        Run the full 14-stage extraction pipeline on document text.

        Returns a dict with:
            - entities: Final deduplicated, alias-resolved entities
            - relationships: Validated, predicate-normalized relationships
            - metrics: Extraction metrics report
        """
        self.metrics.reset()

        # ==================================================================
        # PHASE 1: TEXT PREPARATION (Stages 1-3)
        # ==================================================================

        # Stage 1: Text Cleaner
        self.metrics.start_stage("text_cleaner")
        print("  [1/14] Cleaning text...")
        clean_text, clean_log = self.text_cleaner.clean(text)
        chars_removed = clean_log.get("chars_removed_total", 0)
        self.metrics.end_stage("text_cleaner", f"Removed {chars_removed} chars")

        # Stage 2: Sentence Segmenter
        self.metrics.start_stage("sentence_segmenter")
        print("  [2/14] Segmenting sentences...")
        sentences = self.sentence_segmenter.segment(clean_text)
        self.metrics.end_stage("sentence_segmenter", f"{len(sentences)} sentences")

        # Stage 3: Coreference Resolution
        self.metrics.start_stage("coref_resolver")
        print("  [3/14] Resolving coreferences...")
        resolved_text = self.coref_resolver.resolve(clean_text)
        self.metrics.end_stage("coref_resolver")

        # ==================================================================
        # PHASE 2: ENTITY EXTRACTION (Stages 4-10)
        # ==================================================================

        # Stage 4: Hybrid NER (spaCy + optional transformer + rules)
        self.metrics.start_stage("hybrid_ner")
        print("  [4/14] Running Hybrid NER pipeline...")
        spacy_entities = self.ner_pipeline.extract(resolved_text)
        print(f"         spaCy entities: {len(spacy_entities)}")

        # Stage 5: Technical Entity Detector
        self.metrics.start_stage("technical_detector")
        print("  [5/14] Detecting technical entities...")
        tech_entities = self.technical_detector.detect(resolved_text, spacy_entities)
        print(f"         Technical entities: {len(tech_entities)}")

        # Save raw entities for debugging
        all_raw = spacy_entities + tech_entities
        self.debug_manager.save_raw_entities(all_raw, doc_id or "latest")

        self.metrics.end_stage("technical_detector")

        # Stage 6: Entity Fusion (merge all NER sources)
        self.metrics.start_stage("entity_fusion")
        print("  [6/14] Fusing entity predictions...")
        fused_entities = self.entity_fusion.fuse(
            spacy_entities, [], tech_entities  # transformer empty for now
        )
        print(f"         After fusion: {len(fused_entities)} entities")
        self.metrics.end_stage("entity_fusion", f"{len(fused_entities)} entities")

        # Stage 7: Entity Validation
        self.metrics.start_stage("entity_validator")
        print("  [7/14] Validating entities...")
        validated_entities = self.entity_validator.validate(fused_entities)
        print(f"         After validation: {len(validated_entities)} entities")
        self.debug_manager.save_filtered_entities(validated_entities, doc_id or "latest")
        self.metrics.end_stage("entity_validator", f"{len(validated_entities)} valid")

        # Stage 8: Entity Normalization
        self.metrics.start_stage("entity_normalizer")
        print("  [8/14] Normalizing entities...")
        normalized_entities = self.entity_normalizer.normalize(validated_entities)
        print(f"         After normalization: {len(normalized_entities)} entities")

        # Stage 9: Alias Resolution
        self.metrics.start_stage("alias_resolver")
        print("  [9/14] Resolving aliases...")
        resolved_entities = self.alias_resolver.resolve(normalized_entities)
        self.debug_manager.save_canonical_entities(resolved_entities, doc_id or "latest")
        self.metrics.end_stage("alias_resolver", f"{len(resolved_entities)} resolved")

        # Stage 10: Deduplication
        self.metrics.start_stage("deduplicator")
        print("  [10/14] Deduplicating entities...")
        final_entities, dedup_stats = self.deduplicator.deduplicate(resolved_entities)
        print(f"          Before dedup: {dedup_stats['input_count']}")
        print(f"          After dedup:  {dedup_stats['output_count']}")
        print(f"          Merge rate:   {dedup_stats['duplicate_merge_rate']}%")
        self.debug_manager.save_deduplicated_entities(final_entities, dedup_stats, doc_id or "latest")
        self.metrics.end_stage("deduplicator", f"{dedup_stats['output_count']} final")

        # Record entity metrics
        avg_entity_conf = (
            round(sum(e.get("confidence", 0.85) for e in final_entities) / len(final_entities), 4)
            if final_entities else 0.0
        )
        self.metrics.record_entity_metrics(
            raw_count=len(all_raw),
            filtered_count=len(validated_entities),
            rejected_count=len(fused_entities) - len(validated_entities),
            rejection_breakdown={},
            canonical_count=len(resolved_entities),
            stored_count=len(final_entities),
            duplicate_merge_rate=dedup_stats.get("duplicate_merge_rate", 0.0),
            average_confidence=avg_entity_conf,
        )

        # ==================================================================
        # PHASE 3: RELATIONSHIP EXTRACTION (Stages 11-14)
        # ==================================================================

        # Build entity index for relationship extraction
        entity_index = {}
        for ent in final_entities:
            name = ent.get("canonical_name", ent.get("text", "")).lower()
            entity_index[name] = ent.get("canonical_name", name)
            for alias in ent.get("aliases", []):
                if alias:
                    entity_index[alias.lower()] = ent.get("canonical_name", name)

        # Stage 11: Dependency Parsing
        self.metrics.start_stage("dependency_parser")
        print("  [11/14] Parsing dependency trees...")

        # Stage 12: Relationship Extraction (includes dependency parsing)
        self.metrics.start_stage("relationship_extractor")
        print("  [12/14] Extracting relationships...")
        raw_relationships = self.rel_extractor.extract(
            resolved_text, final_entities, sentences, doc_id=doc_id
        )
        print(f"          Raw relationships: {len(raw_relationships)}")
        self.debug_manager.save_raw_relationships(raw_relationships, doc_id or "latest")
        self.metrics.end_stage("relationship_extractor", f"{len(raw_relationships)} raw")

        # Stage 13: Relationship Validation
        self.metrics.start_stage("relationship_validator")
        print("  [13/14] Validating relationships...")
        validated_rels = self.rel_validator.validate(raw_relationships)
        print(f"          After validation: {len(validated_rels)} relationships")
        self.debug_manager.save_validated_relationships(validated_rels, doc_id or "latest")
        self.metrics.end_stage("relationship_validator", f"{len(validated_rels)} valid")

        # Stage 14: Predicate Normalization
        self.metrics.start_stage("predicate_normalizer")
        print("  [14/14] Normalizing predicates...")
        final_relationships = self.predicate_normalizer.normalize(validated_rels)
        self.debug_manager.save_normalized_relationships(final_relationships, doc_id or "latest")
        self.metrics.end_stage("predicate_normalizer", f"{len(final_relationships)} normalized")

        # Record relationship metrics
        avg_rel_conf = (
            round(sum(r.get("confidence", 0.65) for r in final_relationships) / len(final_relationships), 4)
            if final_relationships else 0.0
        )
        self.metrics.record_relationship_metrics(
            raw_count=len(raw_relationships),
            validated_count=len(validated_rels),
            stored_count=len(final_relationships),
            average_confidence=avg_rel_conf,
            by_method=self.rel_validator.get_statistics(final_relationships).get("by_method", {}),
        )

        # Finalize metrics
        self.metrics.finalize()
        self.debug_manager.save_metrics(self.metrics.get_report(), doc_id or "latest")

        print(f"\n{'='*60}")
        print(f"✅ PIPELINE COMPLETE: {len(final_entities)} entities | {len(final_relationships)} relationships")
        print(f"   Total time: {self.metrics.metrics['total_processing_time_seconds']}s")
        print(f"{'='*60}\n")

        return {
            "entities": final_entities,
            "relationships": final_relationships,
            "metrics": self.metrics.get_report(),
        }

    # ------------------------------------------------------------------
    # Top-level document processor (unchanged public API)
    # ------------------------------------------------------------------

    def process_document(
        self, file_path: str, filename: str
    ) -> Dict[str, Any]:
        """
        Process an uploaded document end-to-end.

        Returns the same dict structure as before:
            document_id, filename, chunks, entities,
            relationships, total_chunks, text_length
        """
        # --- Extract raw text ---
        if filename.lower().endswith(".pdf"):
            text = self.extract_text_from_pdf(file_path)
        elif filename.lower().endswith(".txt"):
            text = self.extract_text_from_txt(file_path)
        else:
            raise ValueError(f"Unsupported file format: {filename}")

        if not text or len(text.strip()) < 100:
            raise ValueError("Document contains insufficient text.")

        doc_id = str(uuid.uuid4())

        print(f"[DOC] Processing '{filename}' (doc_id={doc_id[:8]}...)")

        # --- Run 14-stage extraction pipeline ---
        print("🔬 Running 14-Stage Enterprise Extraction Pipeline...")
        extracted = self.extract_entities_and_relationships(text, doc_id=doc_id)

        # --- Chunk document for vector store ---
        print("[CUT] Chunking document...")
        chunks = self.chunk_document(text, {
            "document_id": doc_id,
            "filename": filename,
            "source": file_path,
            "total_length": len(text),
        })

        print(
            f"[OK] Done: {len(chunks)} chunks | "
            f"{len(extracted['entities'])} entities | "
            f"{len(extracted['relationships'])} relationships"
        )

        return {
            "document_id": doc_id,
            "filename": filename,
            "chunks": chunks,
            "entities": extracted["entities"],
            "relationships": extracted["relationships"],
            "total_chunks": len(chunks),
            "text_length": len(text),
            "metrics": extracted.get("metrics", {}),
        }

