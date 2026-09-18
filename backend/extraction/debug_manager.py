"""
Debug Manager
===============

PURPOSE:
    Generate per-stage debug JSON files for every document processing run.

    Outputs (under debug_extractions/):
    - <docname>_extraction.json  — Full pipeline result
    - raw_entities.json          — Before any filtering
    - filtered_entities.json     — After EntityValidator
    - canonical_entities.json    — After normalization + alias resolution
    - deduplicated_entities.json — After dedup
    - raw_relationships.json     — Before filtering
    - validated_relationships.json — After RelationshipValidator
    - normalized_relationships.json — After PredicateNormalizer
    - pipeline_metrics.json      — Extraction metrics report
    - latest_extraction.json     — Always the most recent

    This module is purely for debugging and inspection.
    Has NO effect on the pipeline behavior.
"""

import json
import os
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Directory
# ---------------------------------------------------------------------------
DEBUG_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "debug_extractions")


class DebugManager:
    """
    Saves per-stage debug artifacts for extraction pipeline inspection.
    """

    def __init__(self):
        try:
            os.makedirs(DEBUG_DIR, exist_ok=True)
        except Exception as exc:
            print(f"[WARN] Could not create {DEBUG_DIR}: {exc}")

    # ------------------------------------------------------------------
    # Per-stage save methods
    # ------------------------------------------------------------------

    def save_raw_entities(
        self, entities: List[Dict[str, Any]], filename: str
    ):
        """Save entities before any filtering."""
        self._save(f"raw_entities_{filename}", {
            "stage": "extraction.raw_entities",
            "count": len(entities),
            "entities": entities,
            "timestamp": self._now(),
        })

    def save_filtered_entities(
        self, entities: List[Dict[str, Any]], filename: str
    ):
        """Save entities after EntityValidator."""
        self._save(f"filtered_entities_{filename}", {
            "stage": "extraction.filtered_entities",
            "count": len(entities),
            "entities": entities,
            "timestamp": self._now(),
        })

    def save_canonical_entities(
        self, entities: List[Dict[str, Any]], filename: str
    ):
        """Save entities after normalization + alias resolution."""
        self._save(f"canonical_entities_{filename}", {
            "stage": "extraction.canonical_entities",
            "count": len(entities),
            "entities": entities,
            "timestamp": self._now(),
        })

    def save_deduplicated_entities(
        self, entities: List[Dict[str, Any]], stats: Dict[str, int], filename: str
    ):
        """Save entities after dedup."""
        self._save(f"deduplicated_entities_{filename}", {
            "stage": "extraction.deduplicated_entities",
            "count": len(entities),
            "dedup_stats": stats,
            "entities": entities,
            "timestamp": self._now(),
        })

    def save_raw_relationships(
        self, relationships: List[Dict[str, Any]], filename: str
    ):
        """Save relationships before filtering."""
        self._save(f"raw_relationships_{filename}", {
            "stage": "extraction.raw_relationships",
            "count": len(relationships),
            "relationships": relationships,
            "timestamp": self._now(),
        })

    def save_validated_relationships(
        self, relationships: List[Dict[str, Any]], filename: str
    ):
        """Save relationships after RelationshipValidator."""
        self._save(f"validated_relationships_{filename}", {
            "stage": "extraction.validated_relationships",
            "count": len(relationships),
            "relationships": relationships,
            "timestamp": self._now(),
        })

    def save_normalized_relationships(
        self, relationships: List[Dict[str, Any]], filename: str
    ):
        """Save relationships after PredicateNormalizer."""
        self._save(f"normalized_relationships_{filename}", {
            "stage": "extraction.normalized_relationships",
            "count": len(relationships),
            "relationships": relationships,
            "timestamp": self._now(),
        })

    def save_metrics(self, metrics: Dict[str, Any], filename: str):
        """Save extraction metrics."""
        self._save(f"pipeline_metrics_{filename}", {
            "stage": "extraction.metrics",
            "metrics": metrics,
            "timestamp": self._now(),
        })

    # ------------------------------------------------------------------
    # Helper
    # ------------------------------------------------------------------

    def _save(self, name: str, data: Dict[str, Any]):
        """Save data to a JSON file."""
        try:
            # Sanitize filename
            safe_name = re.sub(r"[^\w\-_]", "_", name)
            safe_name = re.sub(r"_+", "_", safe_name).strip("_")
            path = os.path.join(DEBUG_DIR, f"{safe_name}.json")
            with open(path, "w", encoding="utf-8") as fh:
                json.dump(data, fh, indent=2, ensure_ascii=False, default=str)
        except Exception as exc:
            print(f"[WARN] DebugManager._save('{name}') failed: {exc}")

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()
