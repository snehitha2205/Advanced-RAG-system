"""
Stage 6: Entity Fusion
=======================

PURPOSE:
    Combine entity predictions from all NER sources:
    - spaCy entities
    - Transformer entities
    - Technical dictionary entities
    - Paper title entities
    - CamelCase entities

    Merges duplicates, resolves aliases, and chooses the
    highest-confidence version of each entity.

STRATEGY:
    1. Group entities by normalized text (lowercase, stripped)
    2. Within each group:
       - Keep the longest text as canonical
       - Keep the highest confidence score
       - Prefer more specific labels over MISC
       - Prefer technical_dictionary source (has curated labels)
       - Accumulate all aliases
       - Mark as "ensemble" if multiple sources agree
    3. Resolve overlapping spans by preferring longer spans

EXAMPLE:
    "Open AI" (spaCy, 0.85) + "OpenAI" (tech_dict, 0.95)
    → "OpenAI" (confidence 0.95, label ORG, aliases: ["Open AI"])
"""

from typing import Any, Dict, List, Set, Tuple
from difflib import SequenceMatcher


class EntityFusion:
    """
    Stage 6 of the extraction pipeline.

    Merges entity predictions from multiple NER sources.
    """

    # Source priority (higher = more trusted for labels)
    SOURCE_PRIORITY = {
        "technical_dictionary": 10,
        "paper_title": 9,
        "ensemble": 8,
        "spacy": 7,
        "transformer": 6,
        "camelcase": 5,
        "tech_word": 5,
        "version_detector": 4,
    }

    # Label priority for conflict resolution
    LABEL_PRIORITY = {
        "PERSON": 10,
        "ORG": 10,
        "SYSTEM": 9,
        "MODEL": 9,
        "FRAMEWORK": 9,
        "DATABASE": 9,
        "GPE": 9,
        "LOC": 8,
        "PRODUCT": 8,
        "COMPONENT": 8,
        "CONCEPT": 7,
        "METRIC": 7,
        "TECHNOLOGY": 7,
        "LANGUAGE": 6,
        "PUBLICATION": 6,
        "VERSION": 5,
        "EVENT": 5,
        "MISC": 1,
    }

    # Fuzzy matching threshold
    FUZZY_THRESHOLD = 0.88

    def fuse(
        self,
        spacy_entities: List[Dict[str, Any]],
        transformer_entities: List[Dict[str, Any]],
        technical_entities: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """
        Fuse all entity sources into one deduplicated list.

        Args:
            spacy_entities: From HybridNER.spacy
            transformer_entities: From HybridNER.transformer (may be empty)
            technical_entities: From TechnicalEntityDetector

        Returns:
            Fused, deduplicated list of entity dicts.
        """
        # 1. Combine all sources
        all_entities = []
        all_entities.extend(spacy_entities)
        all_entities.extend(transformer_entities)
        all_entities.extend(technical_entities)

        if not all_entities:
            return []

        # 2. Resolve overlapping spans
        all_entities = self._resolve_overlaps(all_entities)

        # 3. Group by normalized key
        groups = self._group_entities(all_entities)

        # 4. Fuzzy merge remaining ungrouped
        groups = self._fuzzy_merge(groups)

        # 5. Collapse each group into single entity
        fused = [self._collapse_group(g) for g in groups.values()]

        # 6. Sort by confidence descending
        fused.sort(key=lambda e: e.get("confidence", 0), reverse=True)

        return fused

    def _resolve_overlaps(
        self, entities: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Resolve overlapping spans by keeping longer spans."""
        if not entities:
            return []

        # Sort by start, then by length descending
        sorted_ents = sorted(
            entities,
            key=lambda e: (e.get("start", 0), -(e.get("end", 0) - e.get("start", 0))),
        )

        resolved = []
        for ent in sorted_ents:
            start, end = ent.get("start", 0), ent.get("end", 0)
            is_overlapped = False

            for i, existing in enumerate(resolved):
                es, ee = existing.get("start", 0), existing.get("end", 0)
                # Check if this entity is contained within an existing one
                if es <= start and end <= ee:
                    is_overlapped = True
                    # Merge if the contained entity has higher confidence
                    if ent.get("confidence", 0) > existing.get("confidence", 0):
                        resolved[i] = ent
                    break
                # Check if existing is contained within this new one
                if start <= es and ee <= end:
                    resolved[i] = ent
                    is_overlapped = True
                    break

            if not is_overlapped:
                resolved.append(ent)

        return resolved

    def _group_entities(
        self, entities: List[Dict[str, Any]]
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Group entities by normalized text key."""
        groups: Dict[str, List[Dict[str, Any]]] = {}

        for ent in entities:
            text = ent.get("text", "").strip()
            key = self._normalize_key(text)
            if key:
                groups.setdefault(key, []).append(ent)

        return groups

    def _fuzzy_merge(
        self, groups: Dict[str, List[Dict[str, Any]]]
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Fuzzy merge groups with similar keys."""
        keys = list(groups.keys())
        merged: Dict[str, str] = {}  # child → parent

        for i in range(len(keys)):
            for j in range(i + 1, len(keys)):
                ki, kj = keys[i], keys[j]
                if ki in merged or kj in merged:
                    continue

                ratio = SequenceMatcher(None, ki, kj).ratio()
                if ratio >= self.FUZZY_THRESHOLD:
                    # Merge into the longer key (more specific)
                    parent = ki if len(ki) >= len(kj) else kj
                    child = kj if parent == ki else ki
                    merged[child] = parent

        # Apply merges
        result: Dict[str, List[Dict[str, Any]]] = {}
        for key, ents in groups.items():
            target = merged.get(key, key)
            result.setdefault(target, []).extend(ents)

        return result

    def _collapse_group(
        self, group: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Merge a group of entity records into one authoritative record."""
        if len(group) == 1:
            return dict(group[0])

        # Sort by source priority, then confidence
        def sort_key(e: Dict) -> Tuple[int, float]:
            source = e.get("source", "")
            priority = self.SOURCE_PRIORITY.get(source, 0)
            return (-priority, -e.get("confidence", 0))

        sorted_group = sorted(group, key=sort_key)

        # Primary is the highest-ranked
        primary = dict(sorted_group[0])

        # Collect all texts
        all_texts: List[str] = []
        for e in sorted_group:
            t = e.get("text", "").strip()
            if t and t not in all_texts:
                all_texts.append(t)

        # Choose longest text as canonical
        primary["canonical_name"] = max(all_texts, key=len) if all_texts else primary.get("text", "")

        # Accumulate aliases (everything except canonical name)
        aliases: Set[str] = set()
        for t in all_texts:
            if t.lower() != primary["canonical_name"].lower():
                aliases.add(t)
        # Also add lowercase variants
        for t in all_texts:
            aliases.add(t.lower())
        primary["aliases"] = sorted(aliases)

        # Highest confidence
        primary["confidence"] = max(e.get("confidence", 0) for e in group)

        # Best label by priority
        def label_score(lbl: str) -> int:
            return self.LABEL_PRIORITY.get(lbl, 1)

        best_label = max(
            (e.get("label", "MISC") for e in group),
            key=label_score,
        )
        primary["label"] = best_label

        # Mark as fused
        primary["source"] = "fused"
        primary["fusion_count"] = len(group)

        return primary

    def _normalize_key(self, text: str) -> str:
        """Create a normalized merge key from entity text."""
        import re

        key = text.lower().strip()
        # Remove punctuation
        key = re.sub(r"[^\w\s]", "", key)
        # Collapse whitespace
        key = re.sub(r"\s+", " ", key).strip()
        return key

