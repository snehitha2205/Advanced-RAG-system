"""
Stage 13: Relationship Validator
==================================

PURPOSE:
    Validate and score extracted relationships to ensure only high-quality
    triples enter the knowledge graph.

    SCORING DIMENSIONS:
    1. NER confidence of subject entity
    2. NER confidence of object entity
    3. Dependency quality (clear path, distance)
    4. Entity types (PERSON ↔ ORG more meaningful than MISC ↔ MISC)
    5. Predicate specificity (domain-specific > generic verbs)
    6. Sentence completeness (is the triple syntactically complete?)
    7. Dependency distance (shorter paths = higher confidence)

    REJECTS:
    - Incomplete triples (missing subject, predicate, or object)
    - Self-loops (subject == object)
    - Low-confidence triples below configurable threshold
    - Triples with generic predicates on generic entities
"""

import re
from typing import Any, Dict, List, Set


class RelationshipValidator:
    """
    Stage 13 of the extraction pipeline.

    Scores and validates relationships before graph storage.
    """

    # Generic predicates that add little value
    _GENERIC_PREDICATES: Set[str] = {
        "be", "have", "do", "say", "know", "think", "see",
        "get", "make", "take", "go", "come", "look", "feel",
        "seem", "appear", "become", "remain", "call",
        "note", "show", "find", "use", "include", "follow",
        "describe", "present", "discuss", "provide", "refer",
        "contain", "consist", "involve", "based",
    }

    # Domain-specific predicates (high value)
    _DOMAIN_PREDICATES: Set[str] = {
        "develop", "implement", "deploy", "architect", "design",
        "build", "create", "train", "evaluate", "optimize",
        "integrate", "configure", "query", "retrieve", "store",
        "process", "analyze", "extract", "transform", "load",
        "generate", "parse", "encode", "embed", "index",
        "search", "rank", "rerank", "filter", "classify",
        "cluster", "predict", "recommend", "summarize",
        "translate", "generate", "compose", "synthesize",
        "enhance", "improve", "outperform", "surpass",
        "leverage", "utilize", "employ", "adapt", "fine-tune",
        "pretrain", "initialize", "regularize", "normalize",
        "standardize", "validate", "verify", "test",
        "communicate", "connect", "link", "bridge",
        "map", "transform", "convert", "serialize",
        "depend", "rely", "base", "found", "ground",
        "specialize", "generalize", "extend", "support",
        "enable", "allow", "facilitate", "produce",
        "outline", "propose", "introduce", "define",
        "address", "solve", "resolve", "overcome",
        "achieve", "demonstrate", "illustrate", "highlight",
    }

    def __init__(self, min_confidence: float = 0.55):
        self.min_confidence = min_confidence

    def validate(
        self, relationships: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Validate and score all relationships.

        Args:
            relationships: Raw relationships from RelationshipExtractor.

        Returns:
            Validated relationships with refined confidence scores.
        """
        validated = []

        for rel in relationships:
            rel = self._validate_one(rel)
            if rel:
                validated.append(rel)

        # Sort by confidence descending
        validated.sort(key=lambda r: r.get("confidence", 0), reverse=True)

        return validated

    def _validate_one(
        self, rel: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Validate a single relationship. Returns None if rejected.
        """
        subject = rel.get("subject", "").strip()
        predicate = rel.get("predicate", "").strip()
        obj = rel.get("object", "").strip()
        confidence = float(rel.get("confidence", 0.65))

        # Check completeness
        if not subject or not predicate or not obj:
            return None

        # Check self-loops
        if subject.lower() == obj.lower():
            return None

        # Check for generic predicates
        predicate_lower = predicate.lower()
        is_generic = predicate_lower in self._GENERIC_PREDICATES
        is_domain = predicate_lower in self._DOMAIN_PREDICATES

        # Refine confidence
        confidence = self._refine_confidence(rel, is_generic, is_domain)

        # Apply threshold
        if confidence < self.min_confidence:
            return None

        # Reject if generic predicate links two generic entities
        if is_generic and self._are_entities_generic(rel):
            return None

        # Update confidence
        rel["confidence"] = round(confidence, 4)

        # Normalize predicate
        rel["predicate"] = predicate_lower

        return rel

    def _refine_confidence(
        self, rel: Dict[str, Any], is_generic: bool, is_domain: bool
    ) -> float:
        """
        Refine confidence score using multiple signals.
        """
        confidence = float(rel.get("confidence", 0.65))

        # Domain predicate bonus
        if is_domain:
            confidence += 0.15

        # Generic predicate penalty
        if is_generic:
            confidence -= 0.15

        # Entity type bonuses
        s_type = rel.get("subject_type", "ENTITY").upper()
        o_type = rel.get("object_type", "ENTITY").upper()

        specific_types = {
            "PERSON", "ORG", "GPE", "SYSTEM", "MODEL",
            "FRAMEWORK", "DATABASE", "PRODUCT", "TECHNOLOGY",
        }

        if s_type in specific_types:
            confidence += 0.05
        if o_type in specific_types:
            confidence += 0.05
        if s_type in specific_types and o_type in specific_types:
            confidence += 0.05  # Both specific

        # Extraction method adjustments
        method = rel.get("extraction_method", "")
        if method == "dependency_path":
            confidence += 0.05
        elif method == "cross_sentence":
            confidence -= 0.10

        # Supporting sentence length (sentence completeness)
        sent = rel.get("sentence", "")
        if len(sent) > 50:
            confidence += 0.03

        # Penalize very long dependency distance
        dep_dist = rel.get("dependency_distance", 0)
        if dep_dist > 10:
            confidence -= 0.05

        return max(0.0, min(0.99, confidence))

    def _are_entities_generic(self, rel: Dict[str, Any]) -> bool:
        """Check if both entities are generic (not specific named entities)."""
        s_type = rel.get("subject_type", "ENTITY").upper()
        o_type = rel.get("object_type", "ENTITY").upper()

        generic_types = {"ENTITY", "MISC", "CONCEPT", "VERSION", "LANGUAGE"}

        return s_type in generic_types and o_type in generic_types

    def get_statistics(
        self, relationships: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Return validation statistics."""
        if not relationships:
            return {
                "total": 0,
                "average_confidence": 0.0,
                "by_method": {},
                "by_type": {},
            }

        return {
            "total": len(relationships),
            "average_confidence": round(
                sum(r.get("confidence", 0) for r in relationships)
                / len(relationships),
                4,
            ),
            "by_method": self._count_by_method(relationships),
            "by_type": self._count_by_type(relationships),
        }

    def _count_by_method(self, rels: List[Dict]) -> Dict[str, int]:
        counts = {}
        for r in rels:
            m = r.get("extraction_method", "unknown")
            counts[m] = counts.get(m, 0) + 1
        return counts

    def _count_by_type(self, rels: List[Dict]) -> Dict[str, int]:
        counts = {}
        for r in rels:
            key = f"{r.get('subject_type', '?')}→{r.get('object_type', '?')}"
            counts[key] = counts.get(key, 0) + 1
        return counts
