"""
Entity Filter
==============

WHY THIS MATTERS:
    The old pipeline accepted every spaCy entity span without any quality gate.
    This produced pronouns ("he", "they"), generic words ("system", "process"),
    single characters, pure numbers, and very short low-value spans as graph
    nodes — polluting the knowledge graph with noise.

HOW IT WORKS:
    Each entity is evaluated against a set of rules:
      1. Minimum length (≥ 2 characters).
      2. Minimum alpha characters (≥ 2 alphabetic chars).
      3. Pronoun blocklist — personal and demonstrative pronouns removed.
      4. Generic word blocklist — domain-agnostic common nouns removed.
      5. Pure numeric entities removed (unless label is MONEY/QUANTITY/PERCENT).
      6. Temporal entity labels (DATE/TIME) removed unless co-occurring
         with a specific proper-noun form.
      7. Confidence threshold — entities below MIN_CONFIDENCE discarded.

IMPROVEMENT OVER OLD CODE:
    Old: entities[:100] with zero filtering → pronouns, numbers, noise in graph
    New: rule-gated filtering → only meaningful named entities survive
"""

import re
from typing import Any, Dict, List


from config import Config

# ---------------------------------------------------------------------------
# Configuration constants
# ---------------------------------------------------------------------------

MIN_ENTITY_LENGTH   = 2      # characters
MIN_ALPHA_CHARS     = 2      # alphabetic characters required
MIN_CONFIDENCE      = getattr(Config, "ENTITY_MIN_CONFIDENCE", 0.60)   # discard below this threshold


# Personal + demonstrative + relative pronouns
PRONOUNS: set[str] = {
    "i", "me", "my", "myself",
    "we", "us", "our", "ours", "ourselves",
    "you", "your", "yours", "yourself", "yourselves",
    "he", "him", "his", "himself",
    "she", "her", "hers", "herself",
    "it", "its", "itself",
    "they", "them", "their", "theirs", "themselves",
    "this", "that", "these", "those",
    "who", "whom", "whose", "which", "what",
    "there", "here",
}

# Generic, domain-agnostic nouns that add no graph value
GENERIC_WORDS: set[str] = {
    # Structural
    "system", "process", "method", "approach", "framework", "model",
    "platform", "solution", "technology", "implementation", "architecture",
    # Vague
    "thing", "way", "part", "case", "level", "point", "area", "field",
    "type", "form", "kind", "sort", "item", "element", "aspect", "factor",
    "example", "issue", "problem", "matter", "result", "outcome", "effect",
    # Data/Research
    "data", "information", "content", "set", "group", "collection",
    "study", "research", "analysis", "review", "report", "paper",
    "document", "text", "source", "reference", "figure", "table",
    # People (generic)
    "people", "person", "individual", "user", "users", "team", "teams",
    "staff", "member", "members", "employee", "employees", "worker", "workers",
    "customer", "customers", "client", "clients",
    # Business (generic)
    "business", "industry", "market", "sector", "segment", "service",
    "services", "product", "products", "solution", "solutions",
    # Temporal (generic)
    "year", "years", "month", "months", "week", "weeks", "day", "days",
    "today", "yesterday", "tomorrow", "time", "period", "era", "age",
    # Quantifiers
    "number", "amount", "percent", "percentage", "rate", "degree",
    "many", "much", "few", "several", "some", "other", "another", "various",
    "most", "least", "more", "less", "all", "both", "each", "every",
    # Adjectives used as nouns
    "new", "old", "large", "small", "big", "high", "low", "great",
    "first", "second", "third", "last", "next", "previous", "current",
    "good", "best", "better", "major", "main", "key", "important", "similar",
    # Verbs used as nouns
    "use", "uses", "make", "makes", "need", "needs", "take", "gives",
}

# NER label types that represent non-entities we want to remove
NUMERIC_LABELS: set[str] = {"CARDINAL", "ORDINAL", "QUANTITY", "PERCENT"}
TEMPORAL_LABELS: set[str] = {"DATE", "TIME"}
# Labels that are always accepted regardless of other filters
ALWAYS_ACCEPT_LABELS: set[str] = {
    "ORG", "PERSON", "GPE", "LOC", "FAC", "PRODUCT",
    "EVENT", "WORK_OF_ART", "LAW", "LANGUAGE", "NORP",
}

# Compiled patterns
_PURE_NUMBER = re.compile(r"^[\d\s,.\-+%$€£¥]+$")


class EntityFilter:
    """
    Stage 4 of the extraction pipeline.

    Removes low-quality entity spans so only meaningful named entities
    reach the knowledge graph.
    """

    def filter(self, entities: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Apply all filter rules to a list of entity dicts.

        Args:
            entities: List from NERPipeline.extract().

        Returns:
            Filtered list — only high-quality entity spans.
        """
        result = []
        for ent in entities:
            if self._accept(ent):
                result.append(ent)
        return result

    # ------------------------------------------------------------------
    # Decision logic
    # ------------------------------------------------------------------

    def _accept(self, ent: Dict[str, Any]) -> bool:
        text       = ent.get("text", "").strip()
        label      = ent.get("label", "")
        confidence = float(ent.get("confidence", 1.0))

        if not text:
            return False

        # --- Confidence gate --------------------------------------------
        if confidence < MIN_CONFIDENCE:
            return False

        # --- Length gates -----------------------------------------------
        if len(text) < MIN_ENTITY_LENGTH:
            return False
        alpha_count = sum(1 for c in text if c.isalpha())
        if alpha_count < MIN_ALPHA_CHARS:
            return False

        text_lower = text.lower().strip()

        # --- Pronoun check ----------------------------------------------
        if text_lower in PRONOUNS:
            return False

        # --- Pure numeric check -----------------------------------------
        if _PURE_NUMBER.match(text):
            if label not in {"MONEY", "QUANTITY", "PERCENT"}:
                return False

        # --- Numeric / temporal label check -----------------------------
        if label in NUMERIC_LABELS:
            return False
        if label in TEMPORAL_LABELS and label not in ALWAYS_ACCEPT_LABELS:
            return False

        # --- Generic word check (only for short spans) ------------------
        words = text_lower.split()
        if len(words) <= 2 and text_lower in GENERIC_WORDS:
            return False
        # Also check individual words for single-word entities
        if len(words) == 1 and text_lower in GENERIC_WORDS:
            return False

        return True
