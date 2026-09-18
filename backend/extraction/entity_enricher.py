"""
Entity Enricher
================

WHY THIS MATTERS:
    The old pipeline stored only {text, label, start, end} per entity.
    The knowledge graph had no frequency data, no aliases, no document
    provenance, and no context sentences.  This made it impossible to
    rank entities by importance or to trace where an entity came from.

HOW IT WORKS:
    For every normalized entity:
      - Count all occurrences (canonical name + every alias) in the document.
      - Record first_occurrence and last_occurrence char offsets.
      - Extract up to 3 context sentences containing the entity.
      - Attach document_id for cross-document tracking.
      - Compute an importance score: log(frequency) * confidence.

IMPROVEMENT OVER OLD CODE:
    Old: {text, label, start, end}  — flat, no provenance
    New: full enriched record ready for the knowledge graph node schema
"""

import re
from datetime import datetime, timezone
from math import log1p
from typing import Any, Dict, List, Optional


class EntityEnricher:
    """
    Stage 6 of the extraction pipeline.

    Takes normalized entities and attaches frequency, document provenance,
    context sentences, and importance scores.
    """

    # Max context sentences stored per entity
    MAX_CONTEXT_SENTENCES = 3

    # Compiled sentence boundary pattern (reused across calls)
    _SENT_BOUNDARY = re.compile(r"(?<=[.!?])\s+")

    def enrich(
        self,
        entities: List[Dict[str, Any]],
        text: str,
        doc_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Enrich every entity with document-level statistics.

        Args:
            entities : Normalized entity list from EntityNormalizer.
            text     : The preprocessed document text.
            doc_id   : Optional document identifier.

        Returns:
            Enriched entity list with full metadata.
        """
        text_lower = text.lower()
        sentences = self._split_sentences(text)
        now = datetime.now(timezone.utc).isoformat()

        enriched = []
        for ent in entities:
            enriched.append(
                self._enrich_one(ent, text, text_lower, sentences, doc_id, now)
            )
        return enriched

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _enrich_one(
        self,
        ent: Dict[str, Any],
        text: str,
        text_lower: str,
        sentences: List[str],
        doc_id: Optional[str],
        timestamp: str,
    ) -> Dict[str, Any]:
        canonical = ent.get("canonical_name", ent.get("text", ""))
        aliases   = ent.get("aliases", [])
        confidence = float(ent.get("confidence", 1.0))

        # --- Collect all search terms (canonical + aliases) ---
        search_terms = {canonical.lower()} | {a.lower() for a in aliases}

        # --- Find all char offsets ---
        offsets: List[int] = []
        for term in search_terms:
            if not term:
                continue
            start = 0
            while True:
                pos = text_lower.find(term, start)
                if pos == -1:
                    break
                offsets.append(pos)
                start = pos + 1

        offsets = sorted(set(offsets))
        frequency = max(len(offsets), ent.get("frequency", 1))

        # --- Context sentences ---
        context: List[str] = []
        canonical_lower = canonical.lower()
        for sent in sentences:
            if canonical_lower in sent.lower() or any(
                a in sent.lower() for a in search_terms
            ):
                context.append(sent.strip()[:300])
                if len(context) >= self.MAX_CONTEXT_SENTENCES:
                    break

        # --- Importance score ---
        importance = round(log1p(frequency) * confidence, 4)

        return {
            **ent,
            "frequency":       frequency,
            "document_count":  1,
            "document_ids":    [doc_id] if doc_id else [],
            "first_occurrence": offsets[0] if offsets else ent.get("start", 0),
            "last_occurrence":  offsets[-1] if offsets else ent.get("end", 0),
            "context_sentences": context,
            "importance_score":  importance,
            "enriched_at":       timestamp,
        }

    def _split_sentences(self, text: str) -> List[str]:
        """Fast regex sentence splitter — avoids a second spaCy pass."""
        parts = self._SENT_BOUNDARY.split(text)
        return [p.strip() for p in parts if len(p.strip()) > 10]
