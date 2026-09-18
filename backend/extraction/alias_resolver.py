"""
Stage 9: Alias Resolver
=========================

PURPOSE:
    Resolve entity aliases to their canonical form.
    Many entities appear in text with multiple surface forms:
        "Open AI" → "OpenAI"
        "Artificial Intelligence" → "AI" (and vice versa)
        "Neo4j AuraDB" → "Neo4j Aura"
        "Graph RAG" → "GraphRAG"

    Uses both a known mapping dictionary and pattern-based rules.

STRATEGY:
    1. Dictionary-based resolution (known abbreviation ↔ full form pairs)
    2. Pattern-based resolution (spacing normalization, hyphen variants)
    3. Graph-aware: searches Neo4j for existing canonical entries via
       the knowledge graph's entity index
    4. Preserves all aliases for future lookup
"""

import re
from typing import Any, Dict, List, Set


class AliasResolver:
    """
    Stage 9 of the extraction pipeline.

    Resolves entity aliases to canonical forms.
    """

    # Abbreviation ↔ Full form mappings
    ABBREVIATION_MAP: Dict[str, str] = {
        # AI/ML
        "ai": "Artificial Intelligence",
        "a i": "Artificial Intelligence",
        # ML
        "ml": "Machine Learning",
        "m l": "Machine Learning",
        # NLP
        "nlp": "Natural Language Processing",
        "n l p": "Natural Language Processing",
        # LLM
        "llm": "Large Language Model",
        "llms": "Large Language Model",
        # RAG
        "rag": "Retrieval-Augmented Generation",
        "r a g": "Retrieval-Augmented Generation",
        # Common tech
        "ui": "User Interface",
        "ux": "User Experience",
        "api": "API",
        "a p i": "API",
        "sdk": "Software Development Kit",
        "s d k": "Software Development Kit",
        "db": "Database",
        "sql": "SQL",
        "nosql": "NoSQL",
    }

    # Spacing/hyphen variants to normalize
    SPACING_VARIANTS: List[tuple] = [
        # Remove spaces in known compounds
        (r"\bGraph\s+RAG\b", "GraphRAG"),
        (r"\bLang\s*Chain\b", "LangChain"),
        (r"\bLlama\s*Index\b", "LlamaIndex"),
        (r"\bNeo4j\s+Aura\b", "Neo4j Aura"),
        (r"\bHugging\s+Face\b", "HuggingFace"),
        (r"\bOpen\s+AI\b", "OpenAI"),
        (r"\bChroma\s*DB\b", "ChromaDB"),
        (r"\bGraph\s+DB\b", "Graph Database"),
        (r"\bVector\s+DB\b", "Vector Database"),
        (r"\bKnowledge\s+Graph\b", "Knowledge Graph"),
        (r"\bLarge\s+Language\s+Model\b", "Large Language Model"),
        (r"\bNatural\s+Language\s+Processing\b", "Natural Language Processing"),
        (r"\bMachine\s+Learning\b", "Machine Learning"),
        (r"\bDeep\s+Learning\b", "Deep Learning"),
        (r"\bArtificial\s+Intelligence\b", "Artificial Intelligence"),
        (r"\bCritic\s+Agent\b", "Critic Agent"),
        (r"\bMulti.?hop\s+Reasoning\b", "Multi-hop Reasoning"),
        (r"\bVector\s+Search\b", "Vector Search"),
        (r"\bSemantic\s+Search\b", "Semantic Search"),
        (r"\bSimilarity\s+Search\b", "Similarity Search"),
        (r"\bHybrid\s+Search\b", "Hybrid Search"),
        (r"\bEntity\s+Resolution\b", "Entity Resolution"),
        (r"\bRelation.?ship\s+Extraction\b", "Relationship Extraction"),
        (r"\bNamed\s+Entity\s+Recognition\b", "Named Entity Recognition"),
        (r"\bDependency\s+Pars(?:ing|er)\b", "Dependency Parsing"),
        (r"\bCoreference\s+Resolution\b", "Coreference Resolution"),
    ]

    # Hyphen/dash normalization
    _HYPHEN_VARIANTS = re.compile(r"[-–—]")

    def resolve(
        self, entities: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Resolve aliases for all entities.

        Args:
            entities: Normalized entities from EntityNormalizer.

        Returns:
            Entities with canonical names and aliases updated.
        """
        resolved = []

        for ent in entities:
            resolved.append(self._resolve_one(ent))

        return resolved

    def _resolve_one(self, ent: Dict[str, Any]) -> Dict[str, Any]:
        """Resolve aliases for a single entity."""
        text = ent.get("text", ent.get("canonical_name", "")).strip()
        canonical = ent.get("canonical_name", text)
        aliases = set(ent.get("aliases", []))

        # 1. Check abbreviation map
        text_lower = text.lower().strip()
        if text_lower in self.ABBREVIATION_MAP:
            full_form = self.ABBREVIATION_MAP[text_lower]
            if text != full_form:
                aliases.add(text)
                canonical = full_form

        # 2. Check abbreviation map in reverse (full form → abbreviation)
        for abbr, full in self.ABBREVIATION_MAP.items():
            if text_lower == full.lower():
                aliases.add(abbr)
                # Keep canonical as full form (more descriptive)
                break

        # 3. Apply spacing/hyphen normalization
        for pattern, normalized in self.SPACING_VARIANTS:
            if re.search(pattern, text, re.IGNORECASE):
                if text != normalized:
                    aliases.add(text)
                    canonical = normalized
                break

        # 4. Normalize hyphens/dashes
        normalized_hyphens = self._HYPHEN_VARIANTS.sub("-", canonical)
        if normalized_hyphens != canonical:
            aliases.add(canonical)
            canonical = normalized_hyphens

        # 5. Add lowercase variants to aliases
        if canonical.lower() != canonical:
            aliases.add(canonical.lower())
        if text.lower() != text and text.lower() != canonical.lower():
            aliases.add(text.lower())

        # Update entity
        ent["canonical_name"] = canonical
        ent["aliases"] = sorted(a for a in aliases if a and a != canonical)
        ent["text"] = canonical

        return ent

    def resolve_text(self, text: str) -> str:
        """
        Resolve aliases in a text string (used for query expansion).

        Example:
            "uses AI for Graph RAG" → "uses Artificial Intelligence for GraphRAG"
        """
        result = text

        # Apply spacing variants
        for pattern, normalized in self.SPACING_VARIANTS:
            result = re.sub(pattern, normalized, result, flags=re.IGNORECASE)

        # Apply abbreviation map
        for abbr, full in sorted(
            self.ABBREVIATION_MAP.items(), key=lambda x: -len(x[0])
        ):
            result = re.sub(
                r"\b" + re.escape(abbr) + r"\b",
                full,
                result,
                flags=re.IGNORECASE,
            )

        return result

