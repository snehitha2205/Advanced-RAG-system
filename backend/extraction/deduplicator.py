"""
Stage 10: Deduplicator
========================

PURPOSE:
    Final aggressive deduplication of entities before graph storage.

    Uses multiple strategies:
    1. Exact match on entity_id (from entity_normalizer)
    2. Fuzzy match on canonical_name (configurable threshold)
    3. Alias intersection (if two entities share aliases, they're the same)
    4. Compound entity preservation (never split "Knowledge Graph")

STATISTICS TRACKED:
    - Total candidates before dedup
    - Entities after exact dedup
    - Entities after fuzzy dedup
    - Duplicate merge rate
"""

import hashlib
from difflib import SequenceMatcher
from typing import Any, Dict, List, Set, Tuple


class Deduplicator:
    """
    Stage 10 of the extraction pipeline.

    Aggressive entity deduplication with fuzzy matching.
    """

    # Fuzzy match threshold (0.0 - 1.0)
    FUZZY_THRESHOLD = 0.92

    def deduplicate(
        self, entities: List[Dict[str, Any]]
    ) -> Tuple[List[Dict[str, Any]], Dict[str, int]]:
        """
        Deduplicate entities using exact and fuzzy matching.

        Args:
            entities: Entities from AliasResolver.

        Returns:
            Tuple of (deduplicated_entities, statistics).
        """
        stats = {
            "input_count": len(entities),
            "exact_dedup_count": 0,
            "fuzzy_dedup_count": 0,
            "output_count": 0,
            "duplicate_merge_rate": 0.0,
        }

        if not entities:
            return [], stats

        # 1. Exact dedup on entity_id
        exact_deduped, exact_merged = self._exact_dedup(entities)
        stats["exact_dedup_count"] = exact_merged

        # 2. Fuzzy dedup on canonical_name
        fuzzy_deduped, fuzzy_merged = self._fuzzy_dedup(exact_deduped)
        stats["fuzzy_dedup_count"] = fuzzy_merged

        # 3. Final sort
        fuzzy_deduped.sort(
            key=lambda e: (e.get("frequency", 1), e.get("confidence", 0)),
            reverse=True,
        )

        stats["output_count"] = len(fuzzy_deduped)
        if stats["input_count"] > 0:
            stats["duplicate_merge_rate"] = round(
                (stats["input_count"] - stats["output_count"])
                / stats["input_count"]
                * 100,
                2,
            )

        return fuzzy_deduped, stats

    def _exact_dedup(
        self, entities: List[Dict[str, Any]]
    ) -> Tuple[List[Dict[str, Any]], int]:
        """
        Deduplicate by entity_id (exact match).
        """
        merged: Dict[str, Dict[str, Any]] = {}
        merge_count = 0

        for ent in entities:
            eid = ent.get("entity_id", "")
            if not eid:
                # Generate entity_id if missing
                canonical = ent.get("canonical_name", ent.get("text", ""))
                entity_type = ent.get("entity_type", ent.get("label", "ENTITY"))
                eid = hashlib.md5(
                    f"{canonical.lower()}_{entity_type}".encode()
                ).hexdigest()
                ent["entity_id"] = eid

            if eid in merged:
                # Merge: accumulate frequency, keep higher confidence
                existing = merged[eid]
                existing["frequency"] = existing.get("frequency", 1) + ent.get("frequency", 1)

                # Keep higher confidence
                if ent.get("confidence", 0) > existing.get("confidence", 0):
                    existing["confidence"] = ent["confidence"]

                # Merge aliases
                existing_aliases = set(existing.get("aliases", []))
                existing_aliases.update(ent.get("aliases", []))
                existing_aliases.add(ent.get("original_name", ""))
                existing_aliases.discard(existing["canonical_name"])
                existing["aliases"] = sorted(a for a in existing_aliases if a)

                # Merge sources
                existing_sources = existing.get("source", "").split(",")
                new_sources = ent.get("source", "").split(",")
                combined = list(set(existing_sources + new_sources))
                existing["source"] = ",".join(sorted(combined))

                merge_count += 1
            else:
                merged[eid] = dict(ent)

        return list(merged.values()), merge_count

    def _fuzzy_dedup(
        self, entities: List[Dict[str, Any]]
    ) -> Tuple[List[Dict[str, Any]], int]:
        """
        Deduplicate by fuzzy matching on canonical_name.

        Also checks alias overlap as a secondary signal.
        """
        if len(entities) <= 1:
            return entities, 0

        # Sort by length descending (prefer longer, more specific names)
        sorted_ents = sorted(
            entities,
            key=lambda e: (
                e.get("frequency", 1),
                len(e.get("canonical_name", "")),
            ),
            reverse=True,
        )

        keep: List[Dict[str, Any]] = []
        merge_count = 0

        for ent in sorted_ents:
            name = ent.get("canonical_name", "").lower()
            name_set = set(name.split())
            aliases = set(a.lower() for a in ent.get("aliases", []))

            found_match = False
            for existing in keep:
                existing_name = existing.get("canonical_name", "").lower()

                # Skip if entity types are completely different
                if ent.get("entity_type") != existing.get("entity_type"):
                    continue

                # Check alias overlap
                existing_aliases = set(
                    a.lower() for a in existing.get("aliases", [])
                )
                shared_aliases = aliases & existing_aliases

                if shared_aliases:
                    # Strong signal: same aliases → same entity
                    found_match = True
                else:
                    # Fuzzy match on name
                    ratio = SequenceMatcher(None, name, existing_name).ratio()
                    if ratio >= self.FUZZY_THRESHOLD:
                        found_match = True

                if found_match:
                    # Merge into existing
                    existing["frequency"] = (
                        existing.get("frequency", 1) + ent.get("frequency", 1)
                    )
                    if ent.get("confidence", 0) > existing.get("confidence", 0):
                        existing["confidence"] = ent["confidence"]

                    existing_aliases.update(aliases)
                    existing_aliases.discard(existing["canonical_name"].lower())
                    existing["aliases"] = sorted(
                        a for a in existing_aliases if a
                    )
                    merge_count += 1
                    break

            if not found_match:
                keep.append(ent)

        return keep, merge_count

