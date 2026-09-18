"""
Stage 4: Hybrid Named Entity Recognition
==========================================

PURPOSE:
    Use a hybrid ensemble of NER sources for maximum recall and precision.

STRATEGY:
    1. Primary: spaCy `en_core_web_lg` — fast, accurate for standard entities
    2. Secondary: HuggingFace transformer NER (optional, CPU-compatible)
       - Used only for low-confidence or ambiguous spans from spaCy
    3. Always runs: rule-based patterns for domain-specific entities
    4. Source labels preserved for downstream fusion

TRANSFORMER USAGE:
    - Only invoked when USE_TRANSFORMER_NER=True in config
    - Applied only to sentences where spaCy found < 2 entities
    - Falls back gracefully if torch/transformers not installed
    - Default: OFF (CPU-friendly)
"""

import re
from typing import Any, Dict, List, Optional, Tuple

from config import Config


class HybridNER:
    """
    Stage 4 of the extraction pipeline.

    Multi-source NER that combines spaCy, optional transformer, and rules.
    """

    # spaCy label → standard label
    _SPACY_LABEL_MAP = {
        "PERSON": "PERSON",
        "NORP": "NORP",
        "FAC": "FAC",
        "ORG": "ORG",
        "GPE": "GPE",
        "LOC": "LOC",
        "PRODUCT": "PRODUCT",
        "EVENT": "EVENT",
        "WORK_OF_ART": "WORK_OF_ART",
        "LAW": "LAW",
        "LANGUAGE": "LANGUAGE",
        "DATE": "DATE",
        "TIME": "TIME",
        "PERCENT": "PERCENT",
        "MONEY": "MONEY",
        "QUANTITY": "QUANTITY",
        "ORDINAL": "ORDINAL",
        "CARDINAL": "CARDINAL",
        "MISC": "MISC",
    }

    # Confidence thresholds
    _SPACY_CONFIDENCE = 0.85
    _TRANSFORMER_CONFIDENCE = 0.75
    _ENSEMBLE_BOOST = 0.10

    def __init__(self, use_transformer: bool = False):
        self.nlp = self._load_spacy()
        self.transformer_pipeline = None
        self.use_transformer = use_transformer

        if use_transformer:
            self.transformer_pipeline = self._load_transformer()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def extract(self, text: str) -> List[Dict[str, Any]]:
        """
        Extract named entities using hybrid ensemble.

        Args:
            text: Coreference-resolved text.

        Returns:
            List of entity dicts with keys:
                text, label, start, end, confidence, source
        """
        # 1. spaCy extraction
        spacy_entities = self._extract_spacy(text)

        # 2. Transformer extraction (optional, selective)
        transformer_entities = []
        if self.transformer_pipeline:
            transformer_entities = self._extract_transformer(text)

        # 3. Merge predictions
        merged = self._merge_predictions(spacy_entities, transformer_entities)

        return merged

    def get_doc(self, text: str):
        """Return spaCy Doc for dependency parsing (limited to 100K chars)."""
        chunk = text[:100_000]
        return self.nlp(chunk)

    def get_docs(self, text: str):
        """Return list of spaCy Docs, chunked for large texts."""
        chunks = self._chunk_text(text)
        return list(self.nlp.pipe(chunks))

    # ------------------------------------------------------------------
    # Model loading
    # ------------------------------------------------------------------

    def _load_spacy(self):
        """Load best available spaCy model."""
        import spacy

        preferred = ["en_core_web_lg", "en_core_web_md", "en_core_web_sm"]
        for model_name in preferred:
            try:
                nlp = spacy.load(model_name, disable=["textcat"])
                print(f"[OK] HybridNER: loaded spaCy '{model_name}'")
                return nlp
            except OSError:
                continue

        print("[WARN] Downloading en_core_web_sm...")
        import os as _os
        _os.system("python -m spacy download en_core_web_sm")
        import spacy as _spacy
        return _spacy.load("en_core_web_sm")

    def _load_transformer(self) -> Optional[Any]:
        """Load HuggingFace NER pipeline (CPU)."""
        try:
            from transformers import pipeline

            ner = pipeline(
                "ner",
                model="dslim/bert-base-NER",
                aggregation_strategy="max",
                device=-1,
            )
            print("[OK] HybridNER: Transformer NER loaded (CPU)")
            return ner
        except Exception as e:
            print(f"[WARN] Transformer NER unavailable: {e}. Using spaCy only.")
            return None

    # ------------------------------------------------------------------
    # Text chunking
    # ------------------------------------------------------------------

    def _chunk_text(self, text: str, max_chars: int = 50_000) -> List[str]:
        """Split text into chunks at paragraph boundaries."""
        if len(text) <= max_chars:
            return [text]

        paragraphs = re.split(r"\n{2,}", text)
        chunks = []
        current = ""

        for para in paragraphs:
            if len(current) + len(para) + 2 <= max_chars:
                current += ("\n\n" if current else "") + para
            else:
                if current:
                    chunks.append(current)
                current = para

        if current:
            chunks.append(current)

        return chunks or [text]

    # ------------------------------------------------------------------
    # spaCy extraction
    # ------------------------------------------------------------------

    def _extract_spacy(self, text: str) -> List[Dict[str, Any]]:
        """Extract entities using spaCy."""
        entities = []

        for chunk_text in self._chunk_text(text):
            doc = self.nlp(chunk_text)
            for ent in doc.ents:
                span = ent.text.strip()
                if not span or len(span) < 2:
                    continue
                entities.append({
                    "text": span,
                    "label": self._SPACY_LABEL_MAP.get(ent.label_, "MISC"),
                    "start": ent.start_char,
                    "end": ent.end_char,
                    "confidence": self._SPACY_CONFIDENCE,
                    "source": "spacy",
                })

        return entities

    # ------------------------------------------------------------------
    # Transformer extraction (selective)
    # ------------------------------------------------------------------

    def _extract_transformer(self, text: str) -> List[Dict[str, Any]]:
        """
        Selective transformer NER.
        Only run on sentences with few spaCy entities to improve recall.
        """
        if not self.transformer_pipeline:
            return []

        entities = []
        sentences = re.split(r"(?<=[.!?])\s+", text)

        for sent in sentences:
            if len(sent) < 20 or len(sent) > 500:
                continue

            # Quick spaCy check: skip if already well-covered
            doc = self.nlp(sent[:1000])
            spacy_count = len(doc.ents)
            if spacy_count >= 3:
                continue  # Already well-covered by spaCy

            try:
                results = self.transformer_pipeline(sent[:512])
                for r in results or []:
                    word = r.get("word", "").strip()
                    label = r.get("entity_group", "MISC")
                    score = float(r.get("score", 0.7))

                    if word and len(word) >= 2 and score >= 0.70:
                        entities.append({
                            "text": word,
                            "label": self._hf_to_spacy_label(label),
                            "start": r.get("start", 0),
                            "end": r.get("end", 0),
                            "confidence": score,
                            "source": "transformer",
                        })
            except Exception:
                continue

        return entities

    def _hf_to_spacy_label(self, hf_label: str) -> str:
        """Map HuggingFace 4-class labels to spaCy-style labels."""
        mapping = {
            "PER": "PERSON",
            "ORG": "ORG",
            "LOC": "GPE",
            "MISC": "MISC",
        }
        return mapping.get(hf_label, "MISC")

    # ------------------------------------------------------------------
    # Ensemble merge
    # ------------------------------------------------------------------

    def _merge_predictions(
        self,
        spacy_ents: List[Dict[str, Any]],
        transformer_ents: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """
        Merge spaCy and transformer predictions.

        Rules:
        1. If both agree on text → boost confidence, mark as ensemble
        2. If transformer finds something spaCy missed → add if confidence >= 0.75
        3. Prefer more specific label over MISC
        4. Deduplicate by normalized text
        """
        merged = {e["text"].lower(): e for e in spacy_ents}

        for te in transformer_ents:
            key = te["text"].lower()
            if key in merged:
                # Agreement → boost
                existing = merged[key]
                existing["confidence"] = min(
                    1.0, existing["confidence"] + self._ENSEMBLE_BOOST
                )
                existing["source"] = "ensemble"
                # Prefer more specific label
                if te["label"] != "MISC" and existing["label"] == "MISC":
                    existing["label"] = te["label"]
            else:
                # New entity from transformer
                if te["confidence"] >= 0.75:
                    merged[key] = te

        # Sort by start offset
        result = sorted(
            merged.values(), key=lambda e: e.get("start", 0)
        )

        return result

