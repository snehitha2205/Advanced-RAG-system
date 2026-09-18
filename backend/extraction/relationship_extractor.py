"""
Stage 12: Relationship Extractor
==================================

PURPOSE:
    Extract high-quality semantic relationships from text using multiple
    complementary strategies:

    1. DEPENDENCY PATH — Shortest dependency path between entities in a sentence.
       Uses spaCy dependency tree to find the connecting verb and relationship path.
       This is the primary and most accurate method.

    2. VERB PHRASE + NOUN CHUNK — For sentences with clear verb phrases linking
       entity pairs. Falls back when dependency paths are unclear.

    3. ENTITY CO-OCCURRENCE — When two entities appear in the same sentence
       and no clear dependency path exists, use the dominant verb.

    4. CROSS-SENTENCE — Sliding window of 2 consecutive sentences.
       Entity at end of sentence N → entity at start of sentence N+1.

    CONFIDENCE SCORING:
    - Dependency path: 0.85-0.95 (shortest path with clear verb)
    - Verb phrase: 0.70-0.80
    - Entity co-occurrence: 0.60-0.70
    - Cross-sentence: 0.50-0.60

    Every relationship includes:
    - subject, predicate, object
    - confidence
    - supporting sentence(s)
    - source document (doc_id)
    - chunk id
    - extraction method
"""

import re
from typing import Any, Dict, List, Optional


class RelationshipExtractor:
    """
    Stage 12 of the extraction pipeline.

    Combines multiple strategies for comprehensive relationship extraction.
    """

    def __init__(self, ner_pipeline):
        """
        Args:
            ner_pipeline: HybridNER instance (provides get_docs/s).
        """
        self.ner = ner_pipeline

    def extract(
        self,
        text: str,
        entities: List[Dict[str, Any]],
        sentences: List[Dict[str, Any]],
        doc_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Extract relationships using all strategies.

        Args:
            text: Preprocessed text.
            entities: Final deduplicated entity list.
            sentences: Sentence list from SentenceSegmenter.
            doc_id: Document identifier for provenance.

        Returns:
            List of relationship dicts.
        """
        # Build entity lookup index
        entity_index = self._build_entity_index(entities)

        # Build entity span index for overlap detection
        span_index = self._build_span_index(entities)

        relationships = []

        # Strategy 1: Dependency path extraction
        print("    [12a] Extracting dependency path relationships...")
        dep_rels = self._extract_dependency_paths(text, entity_index, doc_id)
        relationships.extend(dep_rels)

        # Strategy 2: Entity pair co-occurrence
        print("    [12b] Extracting entity-pair relationships...")
        pair_rels = self._extract_entity_pairs(
            text, entity_index, span_index, doc_id
        )
        relationships.extend(pair_rels)

        # Strategy 3: Cross-sentence relationships
        print("    [12c] Extracting cross-sentence relationships...")
        cross_rels = self._extract_cross_sentence(
            text, entity_index, span_index, doc_id
        )
        relationships.extend(cross_rels)

        return relationships

    def _build_entity_index(
        self, entities: List[Dict[str, Any]]
    ) -> Dict[str, Dict[str, Any]]:
        """Build index: lowercase text → entity record."""
        index = {}
        for ent in entities:
            name = ent.get("canonical_name", ent.get("text", "")).lower()
            index[name] = ent
            for alias in ent.get("aliases", []):
                if alias:
                    index[alias.lower()] = ent
        return index

    def _build_span_index(
        self, entities: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Build span index for overlap detection."""
        spans = []
        for ent in entities:
            name = ent.get("canonical_name", ent.get("text", ""))
            spans.append({
                "text": name,
                "text_lower": name.lower(),
                "entity": ent,
            })
            for alias in ent.get("aliases", []):
                if alias:
                    spans.append({
                        "text": alias,
                        "text_lower": alias.lower(),
                        "entity": ent,
                    })
        # Sort by length descending for longest-match
        spans.sort(key=lambda s: -len(s["text"]))
        return spans

    # ------------------------------------------------------------------
    # Strategy 1: Dependency path extraction
    # ------------------------------------------------------------------

    def _extract_dependency_paths(
        self, text: str,
        entity_index: Dict[str, Dict[str, Any]],
        doc_id: Optional[str],
    ) -> List[Dict[str, Any]]:
        """Extract relationships using dependency parsing."""
        relationships = []
        docs = self.ner.get_docs(text)

        for doc in docs:
            for sent in doc.sents:
                sent_text = sent.text

                # Find all named entities in this sentence
                sent_entities = []
                for ent in sent.ents:
                    if ent.label_ in {
                        "PERSON", "ORG", "GPE", "LOC", "FAC",
                        "PRODUCT", "EVENT", "WORK_OF_ART", "NORP",
                        "SYSTEM", "MODEL", "FRAMEWORK", "DATABASE",
                        "COMPONENT", "CONCEPT", "TECHNOLOGY",
                    }:
                        sent_entities.append(ent)

                if len(sent_entities) < 2:
                    continue

                # For each entity pair, find the shortest dependency path
                for i in range(len(sent_entities)):
                    for j in range(i + 1, len(sent_entities)):
                        e1 = sent_entities[i]
                        e2 = sent_entities[j]

                        path = self._find_dependency_path(e1, e2, sent)
                        if path:
                            rel = self._path_to_relationship(
                                e1, e2, path, sent_text, entity_index, doc_id
                            )
                            if rel:
                                relationships.append(rel)

        return relationships

    def _find_dependency_path(self, e1, e2, sent) -> Optional[List]:
        """
        Find the shortest dependency path between two entities.

        Uses spaCy's token.head chain to find connecting paths.
        """
        # Get root tokens for each entity
        e1_root = e1.root
        e2_root = e2.root

        # Build path from e1 to root
        path1 = []
        t = e1_root
        while t.head != t:
            path1.append(t)
            t = t.head
        path1.append(t)  # Include root

        # Build path from e2 to root
        path2 = []
        t = e2_root
        while t.head != t:
            path2.append(t)
            t = t.head
        path2.append(t)

        # Find common ancestor
        ancestors1 = {t.i: t for t in path1}
        for t in path2:
            if t.i in ancestors1:
                # Path: e1 → ... → common → ... → e2
                path1_to_common = []
                for p in path1:
                    path1_to_common.append(p)
                    if p.i == t.i:
                        break

                path2_to_common = []
                for p in path2:
                    path2_to_common.append(p)
                    if p.i == t.i:
                        break

                # Combine paths (excluding common once)
                combined = path1_to_common[:-1] + path2_to_common[::-1]
                return combined

        return None

    def _path_to_relationship(
        self, e1, e2, path, sent_text: str,
        entity_index: Dict[str, Dict[str, Any]],
        doc_id: Optional[str],
    ) -> Optional[Dict[str, Any]]:
        """Convert a dependency path to a relationship."""
        # Find the main verb in the path
        verb = None
        for token in path:
            if token.pos_ == "VERB":
                verb = token
                break

        if not verb:
            # Use the closest verb outside the path
            for token in e1.root.subtree:
                if token.pos_ == "VERB":
                    verb = token
                    break

        if not verb:
            return None

        verb_lemma = verb.lemma_.lower()
        predicate = verb_lemma

        # Get canonical entity names
        s_name, s_type = self._lookup_entity_full(e1.text, entity_index)
        o_name, o_type = self._lookup_entity_full(e2.text, entity_index)

        if s_name.lower() == o_name.lower():
            return None

        # Compute confidence based on path quality
        confidence = self._path_confidence(path, verb, e1, e2)

        return {
            "subject": s_name,
            "subject_type": s_type,
            "predicate": predicate,
            "predicate_raw": verb_lemma,
            "object": o_name,
            "object_type": o_type,
            "confidence": confidence,
            "sentence": sent_text[:300],
            "source_documents": [doc_id] if doc_id else [],
            "extraction_method": "dependency_path",
            "multi_hop": False,
        }

    def _path_confidence(self, path, verb, e1, e2) -> float:
        """Compute confidence for a dependency path."""
        confidence = 0.85  # Base

        # Verb in path
        if verb in path:
            confidence += 0.05

        # Short path = higher confidence
        if len(path) <= 3:
            confidence += 0.05
        elif len(path) > 6:
            confidence -= 0.10

        # Both entities are specific types
        if e1.label_ in {"PERSON", "ORG", "SYSTEM", "MODEL"}:
            confidence += 0.03
        if e2.label_ in {"PERSON", "ORG", "SYSTEM", "MODEL"}:
            confidence += 0.03

        return min(0.95, max(0.60, confidence))

    # ------------------------------------------------------------------
    # Strategy 2: Entity pair co-occurrence
    # ------------------------------------------------------------------

    def _extract_entity_pairs(
        self, text: str,
        entity_index: Dict[str, Dict[str, Any]],
        span_index: List[Dict[str, Any]],
        doc_id: Optional[str],
    ) -> List[Dict[str, Any]]:
        """Extract relationships from entity co-occurrence in sentences."""
        relationships = []
        docs = self.ner.get_docs(text)

        for doc in docs:
            for sent in doc.sents:
                # Find entities in sentence using span index
                found_entities = self._find_entities_in_text(
                    sent.text, span_index
                )

                if len(found_entities) < 2:
                    continue

                # Find dominant verb in sentence
                verb = None
                for token in sent:
                    if token.pos_ == "VERB" and token.lemma_.lower() not in {
                        "be", "have", "do", "say", "know", "think",
                    }:
                        verb = token
                        break

                if not verb:
                    continue

                predicate = verb.lemma_.lower()

                # Create relationships for entity pairs
                for i in range(len(found_entities)):
                    for j in range(i + 1, len(found_entities)):
                        e1 = found_entities[i]
                        e2 = found_entities[j]

                        # Get canonical names with proper fallbacks
                        e1_canonical = e1.get("canonical_name", e1.get("text", e1.get("name", "")))
                        e2_canonical = e2.get("canonical_name", e2.get("text", e2.get("name", "")))
                        
                        if not e1_canonical or not e2_canonical:
                            continue
                            
                        if e1_canonical.lower() == e2_canonical.lower():
                            continue

                        # Get entity types with fallbacks
                        e1_type = e1.get("entity_type", e1.get("type", "ENTITY"))
                        e2_type = e2.get("entity_type", e2.get("type", "ENTITY"))

                        relationships.append({
                            "subject": e1_canonical,
                            "subject_type": e1_type,
                            "predicate": predicate,
                            "predicate_raw": predicate,
                            "object": e2_canonical,
                            "object_type": e2_type,
                            "confidence": 0.65,
                            "sentence": sent.text[:300],
                            "source_documents": [doc_id] if doc_id else [],
                            "extraction_method": "entity_pair",
                            "multi_hop": False,
                        })

        return relationships

    # ------------------------------------------------------------------
    # Strategy 3: Cross-sentence relationships
    # ------------------------------------------------------------------

    def _extract_cross_sentence(
        self, text: str,
        entity_index: Dict[str, Dict[str, Any]],
        span_index: List[Dict[str, Any]],
        doc_id: Optional[str],
    ) -> List[Dict[str, Any]]:
        """Extract relationships across adjacent sentences."""
        relationships = []
        docs = self.ner.get_docs(text)

        for doc in docs:
            sents = list(doc.sents)

            for i in range(len(sents) - 1):
                sent1 = sents[i]
                sent2 = sents[i + 1]

                # Find entities in each sentence
                ents1 = self._find_entities_in_text(sent1.text, span_index)
                ents2 = self._find_entities_in_text(sent2.text, span_index)

                if not ents1 or not ents2:
                    continue

                # Take last entity of sent1 and first entity of sent2
                e1 = ents1[-1]
                e2 = ents2[0]

                # Get canonical names with proper fallbacks
                e1_canonical = e1.get("canonical_name", e1.get("text", e1.get("name", "")))
                e2_canonical = e2.get("canonical_name", e2.get("text", e2.get("name", "")))
                
                if not e1_canonical or not e2_canonical:
                    continue
                    
                if e1_canonical.lower() == e2_canonical.lower():
                    continue

                # Get entity types with fallbacks
                e1_type = e1.get("entity_type", e1.get("type", "ENTITY"))
                e2_type = e2.get("entity_type", e2.get("type", "ENTITY"))

                # Find connecting verb in either sentence
                verb = None
                for token in list(sent1) + list(sent2):
                    if token.pos_ == "VERB" and token.lemma_.lower() not in {
                        "be", "have", "do", "say", "know",
                    }:
                        verb = token
                        break

                if not verb:
                    continue

                relationships.append({
                    "subject": e1_canonical,
                    "subject_type": e1_type,
                    "predicate": verb.lemma_.lower(),
                    "predicate_raw": verb.lemma_.lower(),
                    "object": e2_canonical,
                    "object_type": e2_type,
                    "confidence": 0.55,
                    "sentence": f"{sent1.text[:200]} {sent2.text[:200]}",
                    "source_documents": [doc_id] if doc_id else [],
                    "extraction_method": "cross_sentence",
                    "multi_hop": True,
                })

        return relationships

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _find_entities_in_text(
        self, text: str, span_index: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Find entities in text using span index (longest match first)."""
        found = []
        text_lower = text.lower()
        covered = set()

        for span in span_index:
            lower = span["text_lower"]
            if lower not in covered and lower in text_lower:
                found.append(span["entity"])
                covered.add(lower)

        return found

    def _lookup_entity_full(
        self, text: str,
        entity_index: Dict[str, Dict[str, Any]],
    ) -> tuple:
        """Look up entity returning (canonical_name, entity_type)."""
        lower = text.lower().strip()
        if lower in entity_index:
            ent = entity_index[lower]
            return (
                ent.get("canonical_name", text),
                ent.get("entity_type", ent.get("label", "ENTITY")),
            )
        return text, "ENTITY"