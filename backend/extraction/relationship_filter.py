"""
Relationship Filter
====================

WHY THIS MATTERS:
    The old pipeline created duplicate relationship records every time a
    document was processed (no deduplication).  It also never removed
    self-loops, empty triples, or weak/meaningless predicates.  This bloated
    the graph with noise that degraded retrieval quality.

HOW IT WORKS:
    1. Reject incomplete triples (empty subject, predicate, or object).
    2. Reject self-loops (subject text == object text after normalization).
    3. Reject very weak predicates (single-character or in WEAK_PREDS set).
    4. Reject triples below MIN_CONFIDENCE threshold.
    5. Deduplicate: triples with the same (subject_key, predicate, object_key)
       are collapsed into one — the confidence and weight are kept from the
       highest-scoring instance.  An occurrence_count field is incremented.
    6. Sort final list: by confidence descending (best triples first).

IMPROVEMENT OVER OLD CODE:
    Old: unlimited duplicates, no quality gate, relationships[:50] hard cap
    New: deduplicated, quality-gated, ranked — no arbitrary cap
"""

import re
from typing import Any, Dict, List, Set


# Predicates too generic to add graph value
WEAK_PREDICATES: Set[str] = {
    "BE", "HAVE", "DO", "SAY", "GO", "COME", "GET", "MAKE",
    "TAKE", "GIVE", "KNOW", "THINK", "SEE", "LOOK", "FEEL",
    "SEEM", "APPEAR", "REMAIN", "BECOME", "EXIST", "OCCUR",
    "HAPPEN", "RELATE", "INVOLVE",
}

# Min confidence to keep a relationship
MIN_CONFIDENCE = 0.55


class RelationshipFilter:
    """
    Stage 8 of the extraction pipeline.

    Cleans, deduplicates, and ranks relationship triples.
    """

    def filter(
        self, relationships: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Apply all filter and deduplication rules.

        Args:
            relationships: Raw output from RelationshipExtractor.extract().

        Returns:
            Cleaned, deduplicated, ranked list of relationship dicts.
        """
        # Step 1: Basic validity checks
        valid = [r for r in relationships if self._is_valid(r)]

        # Step 2: Deduplicate — merge same (subject, predicate, object) triples
        deduped = self._deduplicate(valid)

        # Step 3: Sort by confidence descending
        deduped.sort(key=lambda r: r.get("confidence", 0), reverse=True)

        return deduped

    # ------------------------------------------------------------------
    # Validity gate
    # ------------------------------------------------------------------

    def _is_valid(self, rel: Dict[str, Any]) -> bool:
        subj = (rel.get("subject") or "").strip()
        pred = (rel.get("predicate") or "").strip()
        obj  = (rel.get("object") or "").strip()

        # Must have all three components
        if not subj or not pred or not obj:
            return False

        # Self-loop check
        if self._normalize_key(subj) == self._normalize_key(obj):
            return False

        # Weak predicate check
        if pred.upper() in WEAK_PREDICATES:
            return False

        # Single-character predicate
        if len(pred) < 2:
            return False

        # Confidence threshold
        if float(rel.get("confidence", 0)) < MIN_CONFIDENCE:
            return False

        # Subject and object must have ≥ 2 alphabetic characters
        if sum(c.isalpha() for c in subj) < 2:
            return False
        if sum(c.isalpha() for c in obj) < 2:
            return False

        return True

    # ------------------------------------------------------------------
    # Deduplication
    # ------------------------------------------------------------------

    def _deduplicate(
        self, relationships: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Merge triples with the same canonical (subject, predicate, object) key.

        When merging:
          - Keep the instance with the highest confidence as primary.
          - Sum occurrence_count.
          - Accumulate distinct sentences (up to 3).
        """
        # Map: triple_key → merged record
        merged: Dict[str, Dict[str, Any]] = {}

        for rel in relationships:
            key = self._triple_key(rel)
            if key not in merged:
                record = dict(rel)
                record["occurrence_count"] = 1
                record["all_sentences"] = [rel.get("sentence", "")]
                merged[key] = record
            else:
                existing = merged[key]
                existing["occurrence_count"] = existing.get("occurrence_count", 1) + 1

                # Keep higher confidence
                if rel.get("confidence", 0) > existing.get("confidence", 0):
                    # Update confidence and primary sentence but keep counts
                    count = existing["occurrence_count"]
                    sentences = existing["all_sentences"]
                    existing.update(rel)
                    existing["occurrence_count"] = count
                    existing["all_sentences"] = sentences

                # Accumulate sentences
                new_sent = rel.get("sentence", "")
                if new_sent and new_sent not in existing["all_sentences"]:
                    if len(existing["all_sentences"]) < 3:
                        existing["all_sentences"].append(new_sent)

                # Boost confidence slightly for corroborated triples
                corroboration_boost = min(0.05, 0.01 * existing["occurrence_count"])
                existing["confidence"] = min(
                    1.0, existing["confidence"] + corroboration_boost
                )

        return list(merged.values())

    # ------------------------------------------------------------------
    # Key helpers
    # ------------------------------------------------------------------

    def _triple_key(self, rel: Dict[str, Any]) -> str:
        """Produce a canonical key for (subject, predicate, object)."""
        s = self._normalize_key(rel.get("subject", ""))
        p = rel.get("predicate", "").upper().strip()
        o = self._normalize_key(rel.get("object", ""))
        return f"{s}|{p}|{o}"

    def _normalize_key(self, text: str) -> str:
        """Lowercase, strip punctuation, collapse whitespace."""
        key = text.lower()
        key = re.sub(r"[^\w\s]", "", key)
        key = re.sub(r"\s+", " ", key).strip()
        return key
