"""
Stage 8: Entity Normalizer
============================

PURPOSE:
    Generate canonical entity names and unique entity_ids for graph storage.

    Every entity receives:
    - entity_id: MD5 hash of (canonical_name, entity_type) for dedup
    - canonical_name: Preferred display name
    - original_name: The text as it appeared in source
    - entity_type: Standardized type label
    - aliases: All surface forms found in text
"""

import hashlib
import re
from typing import Any, Dict, List


class EntityNormalizer:
    """
    Stage 8 of the extraction pipeline.

    Produces normalized entities ready for dedup and graph storage.
    """

    # Common corporate suffixes to strip for ORG entities
    _ORG_SUFFIX = re.compile(
        r"\s+(Inc\.?|Corp\.?|Corporation|LLC|L\.L\.C\.|"
        r"Ltd\.?|Limited|PLC|GmbH|Co\.?|Company|"
        r"Group|Holdings|Technologies|Systems|Solutions)\s*$",
        re.IGNORECASE,
    )

    # Leading articles to strip
    _LEADING_ARTICLE = re.compile(r"^(The|A|An)\s+", re.IGNORECASE)

    # Possessives
    _POSSESSIVE = re.compile(r"'s$|s'$")

    # Well-known entity mappings (abbreviation → canonical)
    KNOWN_ENTITIES: Dict[str, str] = {
        "ai": "Artificial Intelligence",
        "a.i.": "Artificial Intelligence",
        "ml": "Machine Learning",
        "m.l.": "Machine Learning",
        "nlp": "Natural Language Processing",
        "n.l.p.": "Natural Language Processing",
        "llm": "Large Language Model",
        "llms": "Large Language Model",
        "rag": "Retrieval-Augmented Generation",
        "graphrag": "GraphRAG",
        "openai": "OpenAI",
        "open ai": "OpenAI",
        "openai inc": "OpenAI",
        "openai inc.": "OpenAI",
        "google inc": "Google",
        "google inc.": "Google",
        "microsoft corp": "Microsoft",
        "microsoft corp.": "Microsoft",
        "meta platforms": "Meta",
        "meta platforms inc": "Meta",
        "amazon web services": "AWS",
        "apache software foundation": "Apache",
        "ibm": "IBM",
        "ibm corp": "IBM",
    }

    def normalize(self, entities: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Normalize all entities with canonical names and IDs.

        Args:
            entities: Validated entities from EntityValidator.

        Returns:
            Entities with added: entity_id, canonical_name,
            original_name, entity_type, aliases.
        """
        normalized = []

        for ent in entities:
            normalized.append(self._normalize_one(ent))

        return normalized

    def _normalize_one(self, ent: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize a single entity record."""
        text = ent.get("text", "").strip()
        label = ent.get("label", "MISC")
        canonical = self._compute_canonical(text, label)

        # Generate entity_id
        entity_id = self._generate_entity_id(canonical, label)

        # Build aliases
        aliases = self._build_aliases(text, canonical)

        return {
            "entity_id": entity_id,
            "canonical_name": canonical,
            "original_name": text,
            "entity_type": label,
            "aliases": aliases,
            "confidence": float(ent.get("confidence", 0.85)),
            "frequency": 1,
            "document_count": 1,
            "source": ent.get("source", "pipeline"),
            "label": label,
            "text": canonical,
        }

    def _compute_canonical(self, text: str, label: str) -> str:
        """
        Compute the canonical display name for an entity.

        Rules:
        - Check known entity mappings first
        - Strip possessives
        - Strip leading articles
        - Strip corporate suffixes for ORG entities
        - Preserve original casing for proper nouns
        """
        text = text.strip()
        text_lower = text.lower().strip()

        # Check known entity mappings
        if text_lower in self.KNOWN_ENTITIES:
            return self.KNOWN_ENTITIES[text_lower]

        # Strip possessives
        text = self._POSSESSIVE.sub("", text).strip()

        # Strip leading articles
        text = self._LEADING_ARTICLE.sub("", text).strip()

        # For ORG entities, strip corporate suffixes
        if label == "ORG":
            cleaned = self._ORG_SUFFIX.sub("", text).strip()
            if cleaned and len(cleaned) > 3:
                # Check if cleaned version is in known entities
                cleaned_lower = cleaned.lower()
                if cleaned_lower in self.KNOWN_ENTITIES:
                    return self.KNOWN_ENTITIES[cleaned_lower]
                return cleaned

        # Normalize internal whitespace
        text = re.sub(r"\s+", " ", text).strip()

        # If it's a short ALL-CAPS token, keep as-is (abbreviation)
        if text.isupper() and len(text) <= 6:
            return text

        return text

    def _generate_entity_id(self, canonical: str, entity_type: str) -> str:
        """
        Generate a deterministic entity_id.

        Uses MD5 hash of (canonical_name, entity_type) so the same
        entity gets the same ID across documents.
        """
        key = f"{canonical.lower().strip()}_{entity_type.upper()}"
        return hashlib.md5(key.encode()).hexdigest()

    def _build_aliases(self, original: str, canonical: str) -> List[str]:
        """Build a list of aliases for an entity."""
        aliases = set()

        # Original text is always an alias
        if original != canonical:
            aliases.add(original)

        # Lowercase variant
        if original.lower() != original:
            aliases.add(original.lower())

        # Canonical lowercase
        if canonical.lower() != canonical:
            aliases.add(canonical.lower())

        return sorted(a for a in aliases if a)

    def get_entity_id(self, canonical_name: str, entity_type: str = "ENTITY") -> str:
        """Public helper to compute entity_id from canonical name."""
        return self._generate_entity_id(canonical_name, entity_type)

