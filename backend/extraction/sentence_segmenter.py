"""
Stage 2: Sentence Segmenter
============================

PURPOSE:
    Split cleaned text into meaningful sentences while preserving
    sentence boundaries for provenance tracking.

FEATURES:
    - Handles abbreviations (Mr., Dr., U.S., etc.)
    - Handles ellipsis and multiple punctuation
    - Handles numbered lists
    - Preserves sentence index for relationship provenance
    - Returns sentence metadata (start_char, end_char)
"""

import re
from typing import Dict, List


class SentenceSegmenter:
    """
    Stage 2 of the extraction pipeline.

    Splits text into sentences with provenance metadata.
    """

    # Abbreviations that don't end a sentence
    _ABBREVIATIONS = re.compile(
        r"\b(?:Mr|Mrs|Ms|Dr|Prof|Sr|Jr|St|Ave|Blvd|Rd|"
        r"Dept|Univ|Inc|Corp|Ltd|Co|vs|etc|e\.g|i\.e|"
        r"al|fig|Fig|Eq|eq|Vol|No|pp|pg)\.",
        re.IGNORECASE,
    )

    # Common initials like "J. K. Rowling"
    _INITIAL = re.compile(r"\b[A-Z]\.\s*(?=[A-Z])")

    # Sentence boundary pattern
    _SENTENCE_BOUNDARY = re.compile(
    r"(?<=[.!?])\s+(?=[\"'(]?[A-Z0-9])"
)

    def segment(self, text: str) -> List[Dict]:
        """
        Split text into sentences with metadata.

        Args:
            text: Cleaned text from TextCleaner.

        Returns:
            List of dicts with keys:
                - text: The sentence text
                - index: Sentence index (0-based)
                - start_char: Character offset in original text
                - end_char: Character offset end
        """
        if not text.strip():
            return []

        # Protect abbreviations and initials from being split
        protected = self._protect_abbreviations(text)

        # Split into sentences
        raw_sentences = self._SENTENCE_BOUNDARY.split(protected)

        # Restore protected text and build metadata
        sentences = []
        char_offset = 0

        for i, raw_sent in enumerate(raw_sentences):
            sent_text = self._restore_protection(raw_sent).strip()
            if not sent_text:
                continue

            # Handle trailing punctuation that wasn't split
            if sent_text.endswith("?") or sent_text.endswith("!") or sent_text.endswith("."):
                pass
            elif not sent_text[-1] in ".!?":
                # Add period if missing (numbered items, headings)
                sent_text += "."

            # Find the actual position in cleaned text for longer sentences
            start = text.find(sent_text[:30], char_offset)
            if start == -1:
                start = char_offset
            end = start + len(sent_text)

            sentences.append({
                "text": sent_text,
                "index": i,
                "start_char": start,
                "end_char": end,
            })

            char_offset = end

        # Filter out very short fragments
        sentences = [s for s in sentences if len(s["text"]) > 10]

        return sentences

    def _protect_abbreviations(self, text: str) -> str:
        """Replace period in abbreviations with a placeholder to avoid split."""
        # Replace abbreviation periods with unique marker
        protected = self._ABBREVIATIONS.sub(
            lambda m: m.group(0).replace(".", "\x00ABBR\x00"),
            text,
        )
        # Handle initials
        protected = self._INITIAL.sub(
            lambda m: m.group(0).replace(".", "\x00INIT\x00"),
            protected,
        )
        return protected

    def _restore_protection(self, text: str) -> str:
        """Restore periods from protected placeholders."""
        text = text.replace("\x00ABBR\x00", ".")
        text = text.replace("\x00INIT\x00", ".")
        return text

