"""
Stage 7: Entity Validator
==========================

PURPOSE:
    Remove low-quality, invalid, or noisy entities before normalization.

REJECTS:
    - Entire headings (too generic)
    - Entire sentences or paragraphs
    - Generic phrases ("the system", "the process")
    - Very long noun phrases (configurable max token length)
    - Workflow descriptions
    - Repeated titles
    - Boilerplate text
    - Pronouns (he, she, it, they, this, that)
    - Entities below confidence threshold
    - Entities exceeding max token length

PRESERVES:
    - Named entities with specific, meaningful labels
    - Technical terms
    - Short, high-confidence spans
"""

import re
from typing import Any, Dict, List, Set


class EntityValidator:
    """
    Stage 7 of the extraction pipeline.

    Validates and filters entity spans, removing low-quality candidates.
    """

    # Generic/boilerplate phrases to reject
    _GENERIC_PHRASES: Set[str] = {
        "the system", "the process", "the method", "the approach",
        "the model", "the framework", "the platform", "the solution",
        "the technology", "the application", "the algorithm", "the tool",
        "the data", "the result", "the study", "the research",
        "the paper", "the document", "the section", "the chapter",
        "the figure", "the table", "the equation", "the formula",
        "the following", "the above", "the below", "the previous",
        "the next", "the first", "the second", "the last",
        "the proposed", "the developed", "the existing", "the current",
        "the new", "the novel", "the main", "the key", "the important",
        "the overall", "the general", "the specific", "the particular",
        "based on", "focuses on", "consists of", "involves the",
        "section", "chapter", "figure", "table", "equation",
    }

    # Heading-like patterns
    _HEADING_PATTERN = re.compile(
        r"^(?:Abstract|Introduction|Background|Related\s+Work|"
        r"Methodology|Approach|Experiments|Results|Discussion|"
        r"Conclusion|References|Acknowledgments|Appendix|"
        r"Overview|Summary|Future\s+Work|Contributions|"
        r"Limitations|Implementation|Evaluation|Setup|"
        r"Dataset|Experimental\s+Setup|Analysis)$",
        re.IGNORECASE,
    )

    # Workflow/process descriptions
    _WORKFLOW_WORDS: Set[str] = {
        "firstly", "secondly", "thirdly", "finally",
        "thereafter", "thereafter", "subsequently", "consequently",
        "furthermore", "moreover", "additionally", "nevertheless",
        "notably", "specifically", "particularly", "especially",
        "accordingly", "conversely", "alternatively", "similarly",
        "otherwise", "therefore", "hence", "thus", "then",
    }

    # Labels that are always allowed (specific entity types)
    _ALWAYS_ACCEPT_LABELS: Set[str] = {
        "PERSON", "ORG", "GPE", "LOC", "FAC", "PRODUCT",
        "EVENT", "WORK_OF_ART", "LAW", "LANGUAGE", "NORP",
        "SYSTEM", "MODEL", "FRAMEWORK", "DATABASE", "COMPONENT",
        "METRIC", "TECHNOLOGY", "PUBLICATION",
    }

    # Labels that are numeric/temporal and generally not entities
    _NUMERIC_LABELS: Set[str] = {"CARDINAL", "ORDINAL", "QUANTITY", "PERCENT"}
    _TEMPORAL_LABELS: Set[str] = {"DATE", "TIME"}
    _MONEY_LABELS: Set[str] = {"MONEY"}

    def __init__(self, min_confidence: float = 0.60, max_token_length: int = 15):
        """
        Args:
            min_confidence: Minimum confidence to accept an entity
            max_token_length: Maximum words allowed in entity text
        """
        self.min_confidence = min_confidence
        self.max_token_length = max_token_length

    def validate(
        self, entities: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Validate and filter entity list.

        Returns:
            Tuple of (valid_entities, rejection_log).
        """
        valid = []
        rejected = []

        for ent in entities:
            reason = self._check_rejection(ent)
            if reason:
                rejected.append({"entity": ent, "reason": reason})
            else:
                valid.append(ent)

        return valid

    def _check_rejection(self, ent: Dict[str, Any]) -> str:
        """
        Check if entity should be rejected. Returns reason string or "".
        """
        text = ent.get("text", "").strip()
        label = ent.get("label", "MISC")
        confidence = float(ent.get("confidence", 0))

        if not text:
            return "empty_text"

        # Confidence gate
        if confidence < self.min_confidence:
            return f"low_confidence_{confidence}"

        # Length gates
        if len(text) < 2:
            return "too_short"

        words = text.split()
        if len(words) > self.max_token_length:
            return f"too_many_tokens_{len(words)}"

        # Check for heading patterns
        if self._HEADING_PATTERN.match(text):
            return "heading"

        # Check for generic phrases
        text_lower = text.lower().strip()
        if text_lower in self._GENERIC_PHRASES:
            return "generic_phrase"

        # Check for workflow/process words
        if text_lower in self._WORKFLOW_WORDS:
            return "workflow_word"

        # Check for single generic words
        if len(words) == 1:
            # Pronouns
            if text_lower in {
                "i", "me", "my", "we", "us", "our",
                "you", "your", "he", "him", "his",
                "she", "her", "hers", "it", "its",
                "they", "them", "their", "this", "that",
                "these", "those", "who", "whom", "which",
                "there", "here", "where", "when",
            }:
                return "pronoun"

            # Very short generic words (unless they are known labels)
            if len(text) <= 3 and label not in self._ALWAYS_ACCEPT_LABELS:
                # Check if it's an abbreviation
                if not text.isupper():
                    return "short_generic"

        # Numeric labels rejection
        if label in self._NUMERIC_LABELS:
            return "numeric_label"

        # Temporal labels (unless they're proper nouns)
        if label in self._TEMPORAL_LABELS:
            if not any(c.isupper() for c in text):
                return "temporal_label"

        # Check for sentences (multiple verbs or long clauses)
        verb_indicators = sum(
            1 for w in words
            if w.lower() in {
                "is", "are", "was", "were", "be", "been",
                "has", "have", "had", "do", "does", "did",
                "will", "would", "could", "should", "may", "might",
                "uses", "uses", "uses", "based", "using", "used",
                "shown", "shows", "showing", "given", "gives",
            }
        )
        if verb_indicators >= 2 and label not in self._ALWAYS_ACCEPT_LABELS:
            return "sentence_fragment"

        # Check for pure numbers/spaces/punctuation (no meaningful words)
        alpha_count = sum(1 for c in text if c.isalpha())
        if alpha_count < 2:
            return "no_alphabetic"

        return ""  # Entity is valid

    def get_statistics(self, valid: List[Dict], rejected: List[Dict]) -> Dict:
        """Return validation statistics."""
        return {
            "total_candidates": len(valid) + len(rejected),
            "valid": len(valid),
            "rejected": len(rejected),
            "rejection_breakdown": self._count_reasons(rejected),
            "average_confidence": (
                round(sum(e.get("confidence", 0) for e in valid) / len(valid), 4)
                if valid
                else 0
            ),
        }

    def _count_reasons(self, rejected: List[Dict]) -> Dict[str, int]:
        """Count rejection reasons for debugging."""
        counts: Dict[str, int] = {}
        for item in rejected:
            reason = item.get("reason", "unknown")
            counts[reason] = counts.get(reason, 0) + 1
        return counts

