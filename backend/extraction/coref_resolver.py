"""
Stage 3: Coreference Resolution
=================================

PURPOSE:
    Resolve pronouns and ambiguous references to their antecedents.

    Example:
        "OpenAI developed ChatGPT. It was released in 2022."
        → "OpenAI developed ChatGPT. OpenAI released ChatGPT in 2022."

    Uses a hybrid approach:
    1. If `coreferee` spaCy extension is installed, use neural coref.
    2. Otherwise, use enhanced heuristic rules.

DESIGN DECISIONS:
    - CPU-friendly heuristic fallback
    - No external heavy dependencies required
    - Gender-aware pronoun resolution
    - Company/organization references ("The company" → last ORG)
    - Role references ("The CEO" → last PERSON)
"""

import re
from typing import Any, Dict, List, Optional


class CoreferenceResolver:
    """
    Stage 3 of the extraction pipeline.

    Resolves pronouns to their most likely antecedents.
    """

    # Pronoun categories
    _MALE_PRONOUNS = {"he", "him", "his", "himself"}
    _FEMALE_PRONOUNS = {"she", "her", "hers", "herself"}
    _NEUTRAL_PRONOUNS = {"it", "its", "itself"}
    _PLURAL_PRONOUNS = {"they", "them", "their", "theirs", "themselves"}
    _DEMONSTRATIVES = {"this", "that", "these", "those"}
    _ALL_PRONOUNS = (
        _MALE_PRONOUNS
        | _FEMALE_PRONOUNS
        | _NEUTRAL_PRONOUNS
        | _PLURAL_PRONOUNS
        | _DEMONSTRATIVES
    )

    # Role references that point to a person
    _ROLE_PATTERN = re.compile(
        r"\b[Tt]he\s+(CEO|CTO|CFO|COO|founder|co-founder|cofounder|"
        r"president|chairman|chairwoman|director|executive|officer|"
        r"manager|leader|head|chief|researcher|scientist|author|"
        r"creator|developer|engineer|inventor)\b"
    )

    # Organization references
    _ORG_REF_PATTERN = re.compile(
        r"\b[Tt]he\s+(company|organization|firm|startup|corporation|"
        r"group|enterprise|conglomerate|institution|agency|bureau|"
        r"authority|team|department|division|lab|laboratory|"
        r"platform|system|model|framework)\b"
    )

    def __init__(self, nlp=None):
        self.nlp = nlp
        self._has_coreferee = self._check_coreferee(nlp)

    def _check_coreferee(self, nlp) -> bool:
        try:
            import coreferee  # noqa: F401

            return nlp is not None and nlp.has_pipe("coreferee")
        except ImportError:
            return False

    def resolve(
        self,
        text: str,
        entities: Optional[List[Dict[str, Any]]] = None,
    ) -> str:
        """
        Resolve pronouns in text.

        Args:
            text: Cleaned text from SentenceSegmenter.
            entities: Optional pre-extracted entities for antecedent seeding.

        Returns:
            Text with pronouns resolved where possible.
        """
        if self._has_coreferee and self.nlp:
            return self._resolve_with_coreferee(text)
        return self._resolve_heuristic(text, entities or [])

    def _resolve_with_coreferee(self, text: str) -> str:
        """Use coreferee for neural coreference resolution."""
        try:
            doc = self.nlp(text[:100_000])
            resolved = []
            for token in doc:
                coref = token._.coref_chains.resolve(token)
                if coref:
                    resolved.append(" ".join(t.text for t in coref))
                else:
                    resolved.append(token.text_with_ws)
            return "".join(resolved)
        except Exception as e:
            print(f"[WARN] coreferee failed: {e}. Using heuristic fallback.")
            return self._resolve_heuristic(text, [])

    def _resolve_heuristic(
        self, text: str, entities: List[Dict[str, Any]]
    ) -> str:
        """Paragraph-level heuristic pronoun resolution."""
        paragraphs = re.split(r"\n{2,}", text)

        # Seed antecedents from entities
        last_person = self._seed_antecedent(entities, "PERSON")
        last_org = self._seed_antecedent(entities, "ORG")
        last_product = self._seed_antecedent(entities, "PRODUCT")
        last_concept = self._seed_antecedent(entities, "CONCEPT")

        resolved_paras = []
        for para in paragraphs:
            resolved, last_person, last_org, last_product, last_concept = (
                self._resolve_paragraph(
                    para, last_person, last_org, last_product, last_concept
                )
            )
            resolved_paras.append(resolved)

        return "\n\n".join(resolved_paras)

    def _seed_antecedent(
        self, entities: List[Dict], label: str
    ) -> Optional[str]:
        """Find best candidate entity for a label type."""
        candidates = [e for e in entities if e.get("label") == label]
        if not candidates:
            return None
        best = max(
            candidates,
            key=lambda e: (
                e.get("importance_score", 0)
                if "importance_score" in e
                else e.get("confidence", 0)
            ),
        )
        return best.get("canonical_name") or best.get("text")

    def _resolve_paragraph(
        self,
        para: str,
        last_person: Optional[str],
        last_org: Optional[str],
        last_product: Optional[str],
        last_concept: Optional[str],
    ):
        """Process one paragraph, tracking antecedents."""
        sentences = re.split(r"(?<=[.!?])\s+", para)
        resolved = []

        for sent in sentences:
            # Update antecedents from named entities in sentence
            last_person, last_org, last_product, last_concept = (
                self._update_antecedents(
                    sent, last_person, last_org, last_product, last_concept
                )
            )

            # Replace role references
            if last_person:
                sent = self._ROLE_PATTERN.sub(last_person, sent)

            # Replace org references
            if last_org:
                sent = self._ORG_REF_PATTERN.sub(last_org, sent)

            # Replace pronouns
            sent = self._replace_pronouns(
                sent, last_person, last_org, last_product, last_concept
            )

            resolved.append(sent)

        return (
            " ".join(resolved),
            last_person,
            last_org,
            last_product,
            last_concept,
        )

    def _update_antecedents(
        self,
        sent: str,
        last_person: Optional[str],
        last_org: Optional[str],
        last_product: Optional[str],
        last_concept: Optional[str],
    ):
        """Scan sentence for proper nouns to update antecedents."""
        # Find capitalized multi-word phrases (likely named entities)
        named = re.findall(r"\b[A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)*\b", sent)

        for name in named:
            name = name.strip()
            if len(name) <= 3:
                continue

            # Update product for technical/capitalized terms
            if self._is_technical_term(name):
                last_product = name
                continue

            # Multi-word names are likely people
            if " " in name:
                last_person = name
            else:
                # Single capitalized word - could be org
                last_org = name

        return last_person, last_org, last_product, last_concept

    def _is_technical_term(self, text: str) -> bool:
        """Check if text looks like a technical term/product."""
        tech_indicators = [
            "GraphRAG",
            "Neo4j",
            "ChromaDB",
            "Gemini",
            "GPT",
            "LLM",
            "RAG",
            "API",
            "BERT",
            "spaCy",
            "Cypher",
        ]
        return any(ti in text for ti in tech_indicators)

    def _replace_pronouns(
        self,
        sent: str,
        last_person: Optional[str],
        last_org: Optional[str],
        last_product: Optional[str],
        last_concept: Optional[str],
    ) -> str:
        """Replace pronoun tokens with their antecedents."""
        words = sent.split()
        resolved = []

        for word in words:
            clean = word.lower().strip(".,;:!?\"'()[]{}")

            if clean not in self._ALL_PRONOUNS:
                resolved.append(word)
                continue

            replacement = self._get_replacement(
                clean, last_person, last_org, last_product, last_concept
            )

            if replacement:
                # Preserve capitalization and punctuation
                prefix = "".join(c for c in word if not c.isalpha())
                suffix = "".join(c for c in reversed(word) if not c.isalpha())
                suffix = suffix[::-1]
                resolved.append(f"{prefix}{replacement}{suffix}")
            else:
                resolved.append(word)

        return " ".join(resolved)

    def _get_replacement(
        self,
        pronoun: str,
        last_person: Optional[str],
        last_org: Optional[str],
        last_product: Optional[str],
        last_concept: Optional[str],
    ) -> Optional[str]:
        """Determine the correct antecedent for a pronoun."""
        if pronoun in self._MALE_PRONOUNS | self._FEMALE_PRONOUNS:
            return last_person

        if pronoun in self._NEUTRAL_PRONOUNS:
            return last_product or last_org or last_concept

        if pronoun in self._PLURAL_PRONOUNS:
            return last_org or last_concept

        if pronoun in self._DEMONSTRATIVES:
            return last_concept or last_product

        return None

