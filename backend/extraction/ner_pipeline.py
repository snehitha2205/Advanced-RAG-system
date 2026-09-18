"""
NER Pipeline
=============

WHY THIS MATTERS:
    The old pipeline used spaCy's smallest model (en_core_web_sm, ~12 MB).
    That model has poor NER accuracy, especially for company names, products,
    and domain-specific terms.  It routinely mislabels and misses entities.

HOW IT WORKS (CPU-optimised):
    Primary model: spaCy en_core_web_lg
      - Word-vector-based, ~700 MB, significantly more accurate than _sm.
      - Falls back to en_core_web_md → en_core_web_sm if not installed.
      - Processes text in batched chunks (nlp.pipe) for throughput.
      - Assigns a base confidence of 0.85 (well-tested model for ORG/PERSON/GPE).

    Optional secondary model: HuggingFace dslim/bert-base-NER
      - 4-class CoNLL NER (PER, ORG, LOC, MISC), ~400 MB.
      - Enabled only when USE_HUGGINGFACE_NER=True in config (default: False).
      - Runs on CPU with torch; adds ~2-5s per chunk but improves recall.
      - Ensemble: if both models agree on span+label → confidence boosted.
        If only HF detects a span → added with HF confidence.

    Text chunking:
      - Documents are split into ≤ 10,000 character chunks at paragraph
        boundaries to avoid spaCy's max_length limit and keep memory low.

IMPROVEMENT OVER OLD CODE:
    Old: en_core_web_sm, no confidence, no chunking, hard cap at 100 entities
    New: en_core_web_lg ensemble, confidence scores, unlimited entities,
         proper chunking at paragraph boundaries
"""

import os
import re
from typing import Any, Dict, List, Optional, Tuple


# spaCy label → human-friendly label (standardise HF 4-class to spaCy labels)
_HF_TO_SPACY: Dict[str, str] = {
    "PER":  "PERSON",
    "ORG":  "ORG",
    "LOC":  "GPE",
    "MISC": "MISC",
}

# Base confidence assigned to spaCy lg predictions
_SPACY_BASE_CONFIDENCE = 0.85
# Confidence boost when both models agree
_ENSEMBLE_BOOST        = 0.10
# Max characters per chunk sent to spaCy
_CHUNK_MAX_CHARS       = 10_000


class NERPipeline:
    """
    Stage 3 of the extraction pipeline.

    Usage::

        ner = NERPipeline(use_huggingface=False)   # CPU-friendly default
        entities = ner.extract(text)               # returns List[Dict]
    """

    def __init__(self, use_huggingface: bool = False):
        """
        Args:
            use_huggingface: If True, also run dslim/bert-base-NER.
                             Increases accuracy but adds ~2-5 s/chunk on CPU.
        """
        self.nlp = self._load_spacy()
        self.hf_ner: Optional[Any] = None
        self.use_huggingface = use_huggingface

        if use_huggingface:
            self.hf_ner = self._load_huggingface()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def extract(self, text: str) -> List[Dict[str, Any]]:
        """
        Extract named entities from text.

        Args:
            text: Preprocessed document text.

        Returns:
            List of entity dicts with keys:
                text, label, start, end, confidence, source
        """
        chunks, offsets = self._split_chunks(text)
        all_entities: List[Dict[str, Any]] = []

        for chunk, offset in zip(chunks, offsets):
            spacy_ents = self._extract_spacy(chunk, offset)
            if self.hf_ner:
                hf_ents = self._extract_huggingface(chunk, offset)
                merged  = self._merge_predictions(spacy_ents, hf_ents)
            else:
                merged = spacy_ents
            all_entities.extend(merged)

        return all_entities

    def get_doc(self, text: str):
        """Return a spaCy Doc for the first chunk (used by RelationshipExtractor)."""
        # Limit to first chunk for dependency parsing
        chunk = text[:_CHUNK_MAX_CHARS]
        return self.nlp(chunk)

    def get_docs(self, text: str):
        """Return list of spaCy Docs, one per chunk (for relationship extraction)."""
        chunks, _ = self._split_chunks(text)
        return list(self.nlp.pipe(chunks))

    # ------------------------------------------------------------------
    # Model loading
    # ------------------------------------------------------------------

    def _load_spacy(self):
        """Load the best available spaCy model, with download fallback."""
        import spacy

        preferred = ["en_core_web_lg", "en_core_web_md", "en_core_web_sm"]
        for model_name in preferred:
            try:
                nlp = spacy.load(model_name, disable=["textcat"])
                print(f"[OK] NERPipeline: loaded spaCy model '{model_name}'")
                return nlp
            except OSError:
                continue

        # Last resort: download en_core_web_sm
        print("[WARN]  Downloading en_core_web_sm (en_core_web_lg recommended)...")
        os.system("python -m spacy download en_core_web_sm")
        import spacy
        return spacy.load("en_core_web_sm")

    def _load_huggingface(self) -> Optional[Any]:
        """Load dslim/bert-base-NER with CPU-only settings."""
        try:
            from transformers import pipeline
            ner = pipeline(
                "ner",
                model="dslim/bert-base-NER",
                aggregation_strategy="max",
                device=-1,          # Force CPU
            )
            print("[OK] NERPipeline: HuggingFace dslim/bert-base-NER loaded (CPU)")
            return ner
        except Exception as exc:
            print(f"[WARN]  HuggingFace NER unavailable ({exc}). Using spaCy only.")
            return None

    # ------------------------------------------------------------------
    # Chunking
    # ------------------------------------------------------------------

    def _split_chunks(self, text: str) -> Tuple[List[str], List[int]]:
        """
        Split text into ≤ _CHUNK_MAX_CHARS chunks at paragraph boundaries.
        Returns (chunks, char_offsets).
        """
        if len(text) <= _CHUNK_MAX_CHARS:
            return [text], [0]

        paragraphs = re.split(r"\n{2,}", text)
        chunks: List[str] = []
        offsets: List[int] = []
        current = ""
        current_offset = 0
        global_offset = 0

        for para in paragraphs:
            if len(current) + len(para) + 2 <= _CHUNK_MAX_CHARS:
                if current:
                    current += "\n\n"
                current += para
            else:
                if current:
                    chunks.append(current)
                    offsets.append(current_offset)
                current = para
                current_offset = global_offset

            global_offset += len(para) + 2  # +2 for "\n\n"

        if current:
            chunks.append(current)
            offsets.append(current_offset)

        return chunks, offsets

    # ------------------------------------------------------------------
    # spaCy extraction
    # ------------------------------------------------------------------

    def _extract_spacy(
        self, text: str, offset: int = 0
    ) -> List[Dict[str, Any]]:
        doc = self.nlp(text)
        entities = []
        for ent in doc.ents:
            span_text = ent.text.strip()
            if not span_text:
                continue
            entities.append({
                "text":       span_text,
                "label":      ent.label_,
                "start":      ent.start_char + offset,
                "end":        ent.end_char   + offset,
                "confidence": _SPACY_BASE_CONFIDENCE,
                "source":     "spacy",
            })
        return entities

    # ------------------------------------------------------------------
    # HuggingFace extraction
    # ------------------------------------------------------------------

    def _extract_huggingface(
        self, text: str, offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Run HuggingFace NER on text chunks ≤ 512 tokens."""
        if not self.hf_ner:
            return []

        # HF models have a 512-token limit; sub-chunk by sentence
        sub_chunks = self._hf_sub_chunks(text)
        entities: List[Dict[str, Any]] = []
        sub_offset = offset

        for sub in sub_chunks:
            try:
                results = self.hf_ner(sub)
                for r in (results or []):
                    label = _HF_TO_SPACY.get(r.get("entity_group", ""), "MISC")
                    span  = r.get("word", "").strip()
                    score = float(r.get("score", 0.7))
                    if span:
                        entities.append({
                            "text":       span,
                            "label":      label,
                            "start":      r.get("start", 0) + sub_offset,
                            "end":        r.get("end",   0) + sub_offset,
                            "confidence": round(score, 4),
                            "source":     "huggingface",
                        })
            except Exception as exc:
                print(f"[WARN]  HF NER chunk failed: {exc}")
            sub_offset += len(sub)

        return entities

    def _hf_sub_chunks(self, text: str, max_chars: int = 400) -> List[str]:
        """Split into sentence-bounded sub-chunks safe for BERT (≤512 tokens)."""
        sentences = re.split(r"(?<=[.!?])\s+", text)
        subs: List[str] = []
        current = ""
        for sent in sentences:
            if len(current) + len(sent) <= max_chars:
                current += (" " if current else "") + sent
            else:
                if current:
                    subs.append(current)
                current = sent
        if current:
            subs.append(current)
        return subs

    # ------------------------------------------------------------------
    # Ensemble merge
    # ------------------------------------------------------------------

    def _merge_predictions(
        self,
        spacy_ents: List[Dict[str, Any]],
        hf_ents:    List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """
        Merge spaCy and HuggingFace predictions.

        Rules:
          1. For every HF entity: if a spaCy entity with the same
             normalised text exists → boost spaCy confidence and keep
             spaCy's span (char offsets are more reliable).
          2. If HF detects an entity not seen by spaCy → add it with
             HF confidence (if ≥ 0.70).
          3. Return deduplicated list sorted by start offset.
        """
        merged = list(spacy_ents)
        spacy_texts = {e["text"].lower() for e in spacy_ents}

        for hf_ent in hf_ents:
            hf_text_lower = hf_ent["text"].lower()
            matched = False

            for sp_ent in merged:
                if sp_ent["text"].lower() == hf_text_lower:
                    # Both agree → boost confidence, mark as ensemble
                    sp_ent["confidence"] = min(
                        1.0,
                        sp_ent["confidence"] + _ENSEMBLE_BOOST,
                    )
                    sp_ent["source"] = "ensemble"
                    # Prefer more specific label
                    if hf_ent["label"] != "MISC" and sp_ent["label"] == "MISC":
                        sp_ent["label"] = hf_ent["label"]
                    matched = True
                    break

            if not matched and hf_ent["confidence"] >= 0.70:
                # HF found something spaCy missed
                hf_ent["source"] = "huggingface_only"
                merged.append(hf_ent)

        # Sort by start offset
        merged.sort(key=lambda e: e.get("start", 0))
        return merged
