"""
Stage 11: Dependency Parser
=============================

PURPOSE:
    Use spaCy dependency parsing to extract Subject-Predicate-Object
    triples from sentences.

    Instead of simple heuristics, uses the full dependency tree:
    - nsubj/nsubjpass → VERB → dobj/dative/attr paths
    - Expands single tokens to complete noun phrases
    - Handles passive voice, conjunctions, prepositional phrases
    - Computes dependency distance for confidence scoring

STRATEGY:
    1. Parse sentence with spaCy dependency parser
    2. Identify all verb-anchored clauses
    3. For each verb, find subject via nsubj/nsubjpass link
    4. Find object via dobj/dative/attr/prep links
    5. Expand to full noun chunks
    6. Handle conjunctions (compound subjects/objects)
    7. Handle passive voice (swap subject/object)
    8. Compute confidence based on dependency quality

CONFIDENCE SIGNALS:
    - Clear nsubj → verb → dobj path: high (0.85-0.95)
    - Passive voice: medium (0.75)
    - Conjunction expansion: medium (0.70)
    - Prepositional object: medium (0.70)
    - Long dependency distance: slight penalty
"""

import re
from typing import Any, Dict, List, Optional, Set, Tuple


class DependencyParser:
    """
    Stage 11 of the extraction pipeline.

    Extracts semantic triples using dependency parse trees.
    """

    # Subject dependency labels
    _SUBJECT_DEPS = {"nsubj", "nsubjpass", "csubj", "csubjpass", "agent"}

    # Object dependency labels
    _OBJECT_DEPS = {"dobj", "dative", "attr", "oprd", "acomp", "xcomp"}

    # Prepositional object markers
    _PREP_OBJECTS = {"pobj", "pcomp"}

    # Weak verbs (too generic for graph edges)
    _WEAK_VERBS: Set[str] = {
        "be", "have", "do", "say", "know", "think", "seem",
        "appear", "become", "remain", "go", "come", "get",
        "give", "take", "make", "see", "look", "feel",
        "use", "use", "use", "based", "include", "contain",
        "consist", "involve", "follow", "show", "note",
        "describe", "present", "discuss", "provide", "refer",
    }

    def __init__(self, ner_pipeline):
        """
        Args:
            ner_pipeline: HybridNER instance (provides get_docs/s).
        """
        self.ner = ner_pipeline

    def parse(
        self, text: str,
        sentences: List[Dict[str, Any]],
        entity_index: Dict[str, str],
    ) -> List[Dict[str, Any]]:
        """
        Extract SPO triples from text using dependency parsing.

        Args:
            text: Preprocessed text
            sentences: List of sentence dicts from SentenceSegmenter
            entity_index: Map of entity_name.lower() → canonical_name

        Returns:
            List of extracted triple dicts
        """
        triples = []
        docs = self.ner.get_docs(text)

        for doc in docs:
            for sent in doc.sents:
                # Extract triples from this sentence
                sent_triples = self._parse_sentence(sent, entity_index)
                triples.extend(sent_triples)

        return triples

    def _parse_sentence(
        self, sent, entity_index: Dict[str, str]
    ) -> List[Dict[str, Any]]:
        """Extract all triples from a single sentence."""
        triples = []

        # Find all verb-anchored clauses
        for token in sent:
            if token.pos_ != "VERB":
                continue

            verb_lemma = token.lemma_.lower()

            # Skip weak verbs (too generic)
            if verb_lemma in self._WEAK_VERBS:
                continue

            is_passive = token.dep_ == "nsubjpass" or any(
                c.dep_ == "nsubjpass" for c in token.children
            )

            # Find subjects
            subjects = self._find_children(token, self._SUBJECT_DEPS, sent)
            # Find objects
            objects = self._find_children(token, self._OBJECT_DEPS, sent)

            # Also find prepositional objects
            for child in token.children:
                if child.dep_ == "prep" or child.dep_ == "agent":
                    prep_objects = self._find_children(
                        child, self._PREP_OBJECTS, sent
                    )
                    objects.extend(prep_objects)

            if not subjects or not objects:
                continue

            # Handle passive voice: swap roles
            if is_passive:
                subjects, objects = objects, subjects

            # Create triples for each subject-object pair
            for subj_text in subjects:
                for obj_text in objects:
                    if not subj_text or not obj_text:
                        continue
                    if subj_text.lower() == obj_text.lower():
                        continue

                    # Look up canonical entity names
                    s_name = self._lookup_entity(subj_text, entity_index)
                    o_name = self._lookup_entity(obj_text, entity_index)

                    # Compute confidence
                    confidence = self._compute_confidence(
                        token, is_passive, s_name, o_name
                    )

                    triples.append({
                        "subject": s_name,
                        "predicate": verb_lemma,
                        "object": o_name,
                        "confidence": confidence,
                        "extraction_method": "dependency_path",
                        "multi_hop": False,
                        "dependency_distance": abs(token.i - (
                            self._find_closest_token(subjects, objects, token, sent)
                        )),
                    })

            # Handle verb conjunctions
            for conj in token.conjuncts:
                if conj.pos_ != "VERB":
                    continue
                conj_lemma = conj.lemma_.lower()
                if conj_lemma in self._WEAK_VERBS:
                    continue

                conj_subjects = self._find_children(conj, self._SUBJECT_DEPS, sent)
                conj_objects = self._find_children(conj, self._OBJECT_DEPS, sent)

                if not conj_subjects:
                    conj_subjects = subjects
                if not conj_objects:
                    conj_objects = objects

                for cs in conj_subjects:
                    for co in conj_objects:
                        if cs and co and cs.lower() != co.lower():
                            sn = self._lookup_entity(cs, entity_index)
                            on = self._lookup_entity(co, entity_index)
                            triples.append({
                                "subject": sn,
                                "predicate": conj_lemma,
                                "object": on,
                                "confidence": 0.70,
                                "extraction_method": "dependency_conjunction",
                                "multi_hop": False,
                                "dependency_distance": abs(conj.i - (
                                    self._find_closest_token(
                                        [cs], [co], conj, sent
                                    )
                                )),
                            })

        return triples

    def _find_children(
        self, token, dep_types: Set[str], sent
    ) -> List[str]:
        """Find tokens with matching dependency labels and expand to noun chunks."""
        spans = []

        for child in token.children:
            if child.dep_ not in dep_types:
                continue

            chunk = self._expand_to_chunk(child, sent)
            if chunk:
                spans.append(chunk)

                # Handle conjunctions in subject/object
                for conj in child.conjuncts:
                    conj_chunk = self._expand_to_chunk(conj, sent)
                    if conj_chunk:
                        spans.append(conj_chunk)

        return spans

    def _expand_to_chunk(self, token, sent) -> Optional[str]:
        """
        Expand a token to its full noun chunk or named entity span.
        """
        # Try noun chunk expansion
        for chunk in sent.noun_chunks:
            if chunk.root == token:
                text = chunk.text.strip()
                # Remove leading articles
                text = re.sub(r"^(the|a|an)\s+", "", text, flags=re.IGNORECASE)
                text = re.sub(r"'s$", "", text).strip()
                return text if len(text) > 1 else None

            # Check if token is within a larger noun chunk
            if chunk.root.i >= token.i and chunk.start <= token.i < chunk.end:
                text = chunk.text.strip()
                if len(text) > 1:
                    return text

        # Fallback: use token's subtree
        subtree = " ".join(
            t.text for t in token.subtree
            if t.dep_ not in {"det", "punct", "cc"}
        ).strip()
        return subtree if len(subtree) > 1 else token.text

    def _lookup_entity(
        self, text: str, entity_index: Dict[str, str]
    ) -> str:
        """Look up canonical entity name."""
        lower = text.lower().strip()
        return entity_index.get(lower, text)

    def _compute_confidence(
        self, verb_token, is_passive: bool,
        s_name: str, o_name: str,
    ) -> float:
        """Compute confidence score for a triple."""
        confidence = 0.85  # Base

        # Passive voice penalty
        if is_passive:
            confidence -= 0.10

        # Boost if both sides are known entities
        s_is_known = s_name.isupper() or len(s_name.split()) > 1
        o_is_known = o_name.isupper() or len(o_name.split()) > 1

        if s_is_known and o_is_known:
            confidence += 0.10
        elif s_is_known or o_is_known:
            confidence += 0.05

        # Clear dependency path bonus
        if verb_token.dep_ == "ROOT":
            confidence += 0.05

        return min(0.95, max(0.60, confidence))

    def _find_closest_token(
        self, subjects, objects, verb_token, sent
    ) -> int:
        """Find the closest subject or object token index to the verb."""
        all_text = subjects + objects
        closest = verb_token.i

        for token in sent:
            if token.text in all_text:
                dist = abs(token.i - verb_token.i)
                if dist < abs(closest - verb_token.i):
                    closest = token.i

        return closest

    def can_extract(self, text: str) -> bool:
        """Check if dependency parsing can be performed (text has verbs)."""
        doc = self.ner.get_doc(text[:5000])
        return any(t.pos_ == "VERB" for t in doc)

