"""
Document Preprocessor
======================

WHY THIS MATTERS:
    The old pipeline called spaCy directly on raw, uncleaned text.  PDFs
    commonly introduce OCR noise (form-feed chars, broken hyphens, repeated
    whitespace, garbled unicode) that confuses the NER model and sentence
    segmenter, producing badly split entities and missed spans.

HOW IT WORKS:
    1. Unicode normalization (NFKC) unifies visually identical characters.
    2. OCR noise removal strips control characters and fixes broken words.
    3. Whitespace normalization collapses repeated spaces / newlines.
    4. Paragraph and sentence segmentation provide structured input to
       downstream stages without re-running spaCy on the full corpus.

IMPROVEMENT OVER OLD CODE:
    Old: text passed raw to spaCy → OCR noise creates phantom tokens
    New: clean text → better tokenization → better NER → better relationships
"""

import re
import unicodedata
from typing import List, Tuple


class DocumentPreprocessor:
    """
    Stage 1 of the extraction pipeline.

    Returns:
        clean_text : str          – single cleaned string
        sentences  : List[str]   – sentence-segmented list
        paragraphs : List[str]   – paragraph-segmented list
    """

    # Regex compiled once for speed
    _CONTROL_CHARS   = re.compile(r"[\x01-\x08\x0b\x0e-\x1f\x7f]")
    _BROKEN_HYPHEN   = re.compile(r"(\w)-\n(\w)")
    _MULTI_SPACE     = re.compile(r"[ \t]+")
    _MULTI_NEWLINE   = re.compile(r"\n{3,}")
    _SENTENCE_SPLIT  = re.compile(r"(?<=[.!?])\s+(?=[A-Z\"\'])")
    _PARA_SPLIT      = re.compile(r"\n{2,}")

    # Smart punctuation replacements
    _SMART_QUOTES = str.maketrans({
        "\u2018": "'", "\u2019": "'",
        "\u201c": '"', "\u201d": '"',
        "\u2013": "-", "\u2014": "-",
        "\u2026": "...",
        "\u00a0": " ",  # non-breaking space
    })

    def process(self, text: str) -> Tuple[str, List[str], List[str]]:
        """
        Full preprocessing pipeline.

        Args:
            text: Raw document text (from PDF/TXT extraction).

        Returns:
            Tuple of (clean_text, sentences, paragraphs).
        """
        text = self._normalize_unicode(text)
        text = self._normalize_smart_punctuation(text)
        text = self._remove_ocr_noise(text)
        text = self._normalize_whitespace(text)
        paragraphs = self._segment_paragraphs(text)
        sentences  = self._segment_sentences(text)
        return text, sentences, paragraphs

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _normalize_unicode(self, text: str) -> str:
        """NFKC normalization: unify visually identical unicode characters."""
        return unicodedata.normalize("NFKC", text)

    def _normalize_smart_punctuation(self, text: str) -> str:
        """Replace curly quotes, em-dashes, ellipsis with ASCII equivalents."""
        return text.translate(self._SMART_QUOTES)

    def _remove_ocr_noise(self, text: str) -> str:
        """Remove PDF form-feed, null bytes, control characters, broken hyphens."""
        text = text.replace("\x0c", "\n")   # form-feed → newline
        text = text.replace("\x00", "")     # null byte
        text = self._CONTROL_CHARS.sub("", text)
        # Fix words broken across lines: "infor-\nmation" → "information"
        text = self._BROKEN_HYPHEN.sub(r"\1\2", text)
        return text

    def _normalize_whitespace(self, text: str) -> str:
        """Collapse repeated spaces/tabs; cap consecutive newlines at 2."""
        text = self._MULTI_SPACE.sub(" ", text)
        text = self._MULTI_NEWLINE.sub("\n\n", text)
        return text.strip()

    def _segment_paragraphs(self, text: str) -> List[str]:
        """Split on double newlines; discard very short fragments."""
        paras = self._PARA_SPLIT.split(text)
        return [p.strip() for p in paras if len(p.strip()) > 50]

    def _segment_sentences(self, text: str) -> List[str]:
        """
        Regex-based sentence splitting on .!? followed by whitespace + capital.
        Fast on CPU, no heavy model required.
        """
        sentences = self._SENTENCE_SPLIT.split(text)
        return [s.strip() for s in sentences if len(s.strip()) > 10]
