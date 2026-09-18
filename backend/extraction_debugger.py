"""
Extraction Debugger
====================

PURPOSE:
    Saves the complete extraction results for every processed document into
    human-readable JSON files under backend/debug_extractions/.

    This module is PURELY for manual inspection and validation.
    It has absolutely NO effect on the GraphRAG pipeline, knowledge graph,
    vector store, retrieval, or any API.

    All methods are wrapped in try/except so a debugger failure can never
    break the upload workflow.

OUTPUT FILES:
    debug_extractions/<docname>_extraction.json  — per-document full result
    debug_extractions/latest_extraction.json     — always the most recent
    debug_extractions/extraction_summary.json    — running totals across docs
    debug_extractions/graph_preview.json         — nodes + edges for viz tools

USAGE:
    Called once from DocumentProcessor.process_document() after the pipeline
    completes. Requires no extra dependencies beyond the stdlib.
"""

import hashlib
import json
import os
import re
from datetime import datetime, timezone
from typing import Any, Dict, List


# ---------------------------------------------------------------------------
# Directory
# ---------------------------------------------------------------------------
DEBUG_DIR = os.path.join(os.path.dirname(__file__), "debug_extractions")
SUMMARY_FILE      = os.path.join(DEBUG_DIR, "extraction_summary.json")
LATEST_FILE       = os.path.join(DEBUG_DIR, "latest_extraction.json")
GRAPH_PREVIEW_FILE = os.path.join(DEBUG_DIR, "graph_preview.json")


class ExtractionDebugger:
    """
    Saves extraction debug artifacts after every successful document processing.
    """

    def __init__(self):
        try:
            os.makedirs(DEBUG_DIR, exist_ok=True)
        except Exception as exc:
            print(f"[WARN] Could not create debug_extractions directory: {exc}")

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------

    def save(
        self,
        filename: str,
        document_id: str,
        processing_time_seconds: float,
        text_length: int,
        chunks_created: int,
        entities: List[Dict[str, Any]],
        relationships: List[Dict[str, Any]],
        stats: Dict[str, int] = None,
        neo4j_node_count: int = 0,
        neo4j_relationship_count: int = 0,
    ) -> None:
        """
        Save all debug files for one processed document.
        """
        try:
            if stats is None:
                stats = {}

            processed_at = datetime.now(timezone.utc).isoformat()

            # ── Build the main extraction document ──────────────────────
            extraction_doc = self._build_extraction_doc(
                filename=filename,
                document_id=document_id,
                processed_at=processed_at,
                processing_time_seconds=processing_time_seconds,
                text_length=text_length,
                chunks_created=chunks_created,
                entities=entities,
                relationships=relationships,
                stats=stats,
                neo4j_node_count=neo4j_node_count,
                neo4j_relationship_count=neo4j_relationship_count,
            )


            # ── Write per-document file ─────────────────────────────────
            doc_filename = self._safe_filename(filename) + "_extraction.json"
            doc_path = os.path.join(DEBUG_DIR, doc_filename)
            self._write_json(doc_path, extraction_doc)

            # ── Write latest_extraction.json ────────────────────────────
            self._write_json(LATEST_FILE, extraction_doc)

            # ── Update extraction_summary.json ──────────────────────────
            self._update_summary(
                filename=filename,
                processed_at=processed_at,
                entity_count=len(entities),
                relationship_count=len(relationships),
            )

            # ── Update graph_preview.json ───────────────────────────────
            self._update_graph_preview(entities, relationships)

            # ── Print confirmation ──────────────────────────────────────
            print(f"\nExtraction JSON saved:   {doc_path}")
            print(f"Graph Preview saved:     {GRAPH_PREVIEW_FILE}")
            print(f"Summary updated:         {SUMMARY_FILE}\n")

        except Exception as exc:
            # Never crash the upload flow
            print(f"[WARN] ExtractionDebugger.save() failed: {exc}")

    # ------------------------------------------------------------------
    # Build extraction document
    # ------------------------------------------------------------------

    def _build_extraction_doc(
        self,
        filename: str,
        document_id: str,
        processed_at: str,
        processing_time_seconds: float,
        text_length: int,
        chunks_created: int,
        entities: List[Dict],
        relationships: List[Dict],
        stats: Dict[str, int],
        neo4j_node_count: int = 0,
        neo4j_relationship_count: int = 0,
    ) -> Dict[str, Any]:

        return {
            "document": {
                "filename":                filename,
                "document_id":             document_id,
                "processed_at":            processed_at,
                "processing_time_seconds": round(processing_time_seconds, 2),
                "text_length":             text_length,
                "chunks_created":          chunks_created,
            },

            "statistics": {
                "entities_before_filtering":     stats.get("entities_before_filtering", 0),
                "entities_after_filtering":      stats.get("entities_after_filtering", 0),
                "entities_after_normalization":  stats.get("entities_after_normalization", 0),
                "relationships_before_filtering": stats.get("relationships_before_filtering", 0),
                "relationships_after_filtering": stats.get("relationships_after_filtering", 0),
                "neo4j_node_count":              neo4j_node_count,
                "neo4j_relationship_count":      neo4j_relationship_count,
            },

            "entities":      [self._format_entity(e, filename) for e in entities],
            "relationships": [self._format_relationship(r, filename) for r in relationships],
        }


    # ------------------------------------------------------------------
    # Entity / relationship formatters
    # ------------------------------------------------------------------

    def _format_entity(self, ent: Dict[str, Any], filename: str) -> Dict[str, Any]:
        canonical = ent.get("canonical_name") or ent.get("text", "")
        entity_id = hashlib.md5(
            f"{canonical.lower()}_{ent.get('label', '')}".encode()
        ).hexdigest()

        return {
            "id":              entity_id,
            "text":            ent.get("text", canonical),
            "normalized_text": canonical,
            "label":           ent.get("label", "ENTITY"),
            "confidence":      round(float(ent.get("confidence", 0.0)), 4),
            "frequency":       ent.get("frequency", 1),
            "document_count":  ent.get("document_count", 1),
            "importance_score": round(float(ent.get("importance_score", 0.0)), 4),
            "aliases":         ent.get("aliases", []),
            "first_occurrence": ent.get("first_occurrence", 0),
            "last_occurrence":  ent.get("last_occurrence", 0),
            "context_sentences": ent.get("context_sentences", []),
        }

    def _format_relationship(self, rel: Dict[str, Any], filename: str) -> Dict[str, Any]:
        return {
            "subject":              rel.get("subject", ""),
            "subject_label":        rel.get("subject_type", rel.get("subject_label", "ENTITY")),
            "predicate":            rel.get("predicate_raw", rel.get("predicate", "")),
            "normalized_predicate": rel.get("predicate", ""),
            "object":               rel.get("object", ""),
            "object_label":         rel.get("object_type", rel.get("object_label", "ENTITY")),
            "confidence":           round(float(rel.get("confidence", 0.0)), 4),
            "occurrence_count":     rel.get("occurrence_count", 1),
            "sentence":             rel.get("sentence", ""),
            "extraction_method":    rel.get("extraction_method", ""),
            "multi_hop":            rel.get("multi_hop", False),
            "document":             filename,
        }

    # ------------------------------------------------------------------
    # Summary file
    # ------------------------------------------------------------------

    def _update_summary(
        self,
        filename: str,
        processed_at: str,
        entity_count: int,
        relationship_count: int,
    ) -> None:
        """
        Update the running extraction_summary.json with accumulated totals.
        """
        # Load existing summary or start fresh
        if os.path.exists(SUMMARY_FILE):
            try:
                with open(SUMMARY_FILE, "r", encoding="utf-8") as fh:
                    summary = json.load(fh)
            except Exception:
                summary = {}
        else:
            summary = {}

        total_docs  = summary.get("total_documents_processed", 0) + 1
        total_ents  = summary.get("total_entities", 0) + entity_count
        total_rels  = summary.get("total_relationships", 0) + relationship_count

        updated = {
            "total_documents_processed":        total_docs,
            "total_entities":                   total_ents,
            "total_relationships":              total_rels,
            "average_entities_per_document":    round(total_ents / total_docs, 2),
            "average_relationships_per_document": round(total_rels / total_docs, 2),
            "last_processed_document":          filename,
            "last_updated":                     processed_at,
        }

        self._write_json(SUMMARY_FILE, updated)

    # ------------------------------------------------------------------
    # Graph preview file
    # ------------------------------------------------------------------

    def _update_graph_preview(
        self,
        entities: List[Dict[str, Any]],
        relationships: List[Dict[str, Any]],
    ) -> None:
        """
        Update graph_preview.json with the nodes and edges inserted into
        the Knowledge Graph during this processing run.

        Merges with any previously stored nodes/edges so the preview
        accumulates across documents.
        """
        # Load existing preview
        if os.path.exists(GRAPH_PREVIEW_FILE):
            try:
                with open(GRAPH_PREVIEW_FILE, "r", encoding="utf-8") as fh:
                    preview = json.load(fh)
            except Exception:
                preview = {"nodes": [], "edges": []}
        else:
            preview = {"nodes": [], "edges": []}

        # Index existing nodes by id for dedup
        existing_node_ids = {n["id"] for n in preview.get("nodes", [])}
        existing_edge_keys = {
            f"{e['source']}|{e['relationship']}|{e['target']}"
            for e in preview.get("edges", [])
        }

        # Add new nodes
        for ent in entities:
            canonical = ent.get("canonical_name") or ent.get("text", "")
            node_id = hashlib.md5(
                f"{canonical.lower()}_{ent.get('label', '')}".encode()
            ).hexdigest()
            if node_id not in existing_node_ids:
                preview["nodes"].append({
                    "id":         node_id,
                    "label":      canonical,
                    "type":       ent.get("label", "ENTITY"),
                    "confidence": round(float(ent.get("confidence", 0.0)), 4),
                    "frequency":  ent.get("frequency", 1),
                })
                existing_node_ids.add(node_id)

        # Add new edges
        for rel in relationships:
            subj = rel.get("subject", "")
            pred = rel.get("predicate", "")
            obj  = rel.get("object", "")

            subj_id = hashlib.md5(
                f"{subj.lower()}_{rel.get('subject_type', '')}".encode()
            ).hexdigest()
            obj_id = hashlib.md5(
                f"{obj.lower()}_{rel.get('object_type', '')}".encode()
            ).hexdigest()

            edge_key = f"{subj_id}|{pred}|{obj_id}"
            if edge_key not in existing_edge_keys:
                preview["edges"].append({
                    "source":       subj_id,
                    "source_label": subj,
                    "target":       obj_id,
                    "target_label": obj,
                    "relationship": pred,
                    "confidence":   round(float(rel.get("confidence", 0.0)), 4),
                })
                existing_edge_keys.add(edge_key)

        self._write_json(GRAPH_PREVIEW_FILE, preview)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _safe_filename(self, filename: str) -> str:
        """
        Convert a document filename to a safe debug filename stem.
        e.g. "CDSS Project Extensions.pdf" → "CDSS_Project_Extensions"
        """
        stem = os.path.splitext(filename)[0]           # strip extension
        stem = re.sub(r"[^\w\s\-]", "", stem)          # remove special chars
        stem = re.sub(r"[\s]+", "_", stem.strip())     # spaces → underscores
        return stem or "document"

    def _write_json(self, path: str, data: Any) -> None:
        """Write data to a JSON file with pretty-printing."""
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=2, ensure_ascii=False, default=str)
