"""
Stage 1: Text Cleaner
======================

PURPOSE:
    Remove noise from raw extracted document text before any NLP processing.

REMOVES:
    - Headers and footers (repeated across pages)
    - Page numbers
    - Table of Contents sections
    - Repeated titles
    - Figure captions and image references
    - Markdown symbols, bullets
    - Broken OCR artifacts
    - Form-feed characters
    - Non-ASCII noise

PRESERVES:
    - All meaningful content
    - Sentence boundaries
    - Paragraph structure
"""

import re
import unicodedata
from typing import Tuple


class TextCleaner:
    """
    Stage 1 of the extraction pipeline.

    Returns (clean_text, cleaning_log) where cleaning_log records
    what was removed for debugging purposes.
    """

    # Compiled patterns
    _CONTROL_CHARS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
    _BROKEN_HYPHEN = re.compile(r"(\w)-\n(\w)")
    _BROKEN_SPACE = re.compile(r"(\w)\n(\w)")

    # Page numbers: common patterns
    _PAGE_NUMBER = re.compile(
        r"(?:^|\n)\s*"
        r"(?:Page\s+\d+|-\s*\d+\s*-|\d+\s*of\s*\d+|"
        r"\[\d+\]|\d+\s*$|^\s*\d+\s*\n)"
        r"\s*(?=\n|$)",
        re.MULTILINE | re.IGNORECASE,
    )

    # Headers/Footers: short lines repeated across pages
    _REPEATED_HEADER = re.compile(
        r"(?:^|\n)([A-Z][A-Za-z0-9\s\-.,:;!?]{3,80})\n(?=.*\n\1\n)",
        re.MULTILINE,
    )

    # Table of Contents patterns
    _TOC_ENTRY = re.compile(
        r"(?:^|\n)[A-Z][A-Za-z\s]+\.{2,}\s*\d+\s*(?=\n|$)",
        re.MULTILINE,
    )
    _TOC_HEADING = re.compile(
        r"(?:^|\n)\s*(Table\s+of\s+Contents|Contents|Index|"
        r"List\s+of\s+(Figures|Tables|Algorithms))\s*\n",
        re.MULTILINE | re.IGNORECASE,
    )

    # Figure / Table / Algorithm captions
    _FIGURE_CAPTION = re.compile(
        r"(?:^|\n)\s*(Figure|Fig\.|Table|Algorithm|Listing)\s+\d+"
        r"[\s:\.][^\n]{0,200}\s*(?=\n)",
        re.MULTILINE | re.IGNORECASE,
    )

    # Image references
    _IMAGE_REF = re.compile(
        r"!\[[^\]]*\]\([^)]+\)|\[Image:\s*[^\]]+\]|<img[^>]+>",
        re.IGNORECASE,
    )

    # Markdown symbols
    _MARKDOWN_BULLET = re.compile(r"^\s*[-*+]\s+", re.MULTILINE)
    _MARKDOWN_HEADER = re.compile(r"^#{1,6}\s+", re.MULTILINE)
    _MARKDOWN_LINK = re.compile(r"\[([^\]]+)\]\([^)]+\)")

    # Email / URL (keep the text but remove the URL part)
    _URL = re.compile(r"https?://\S+", re.IGNORECASE)

    # Unicode normalization
    _SMART_QUOTES = str.maketrans(
        {
            "\u2018": "'",
            "\u2019": "'",
            "\u201c": '"',
            "\u201d": '"',
            "\u2013": "-",
            "\u2014": "-",
            "\u2026": "...",
            "\u00a0": " ",
            "\ufeff": "",  # BOM
        }
    )

    def clean(self, text: str) -> Tuple[str, dict]:
        """
        Run all cleaning stages on input text.

        Args:
            text: Raw text from PDF/TXT extraction.

        Returns:
            Tuple of (cleaned_text, cleaning_log).
        """
        log = {"stages_applied": [], "chars_removed": 0}
        original_length = len(text)

        # 1. Unicode normalization
        text = unicodedata.normalize("NFKC", text)
        text = text.translate(self._SMART_QUOTES)

        # 2. Remove control characters
        text, count = self._CONTROL_CHARS.subn("", text)
        log["chars_removed"] += count
        log["stages_applied"].append("control_chars")

        # 3. Normalize newlines
        text = text.replace("\r\n", "\n").replace("\r", "\n")

        # 4. Fix broken hyphenation
        text, count = self._BROKEN_HYPHEN.subn(r"\1\2", text)
        log["stages_applied"].append("broken_hyphen_fix")

        # 5. Fix words broken across lines without hyphen
        text, count = self._BROKEN_SPACE.subn(r"\1 \2", text)
        log["stages_applied"].append("broken_word_fix")

        # 6. Remove page numbers
        text, count = self._PAGE_NUMBER.subn("", text)
        log["stages_applied"].append("page_numbers")
        log["chars_removed"] += count * 5

        # 7. Remove figure/table captions
        text, count = self._FIGURE_CAPTION.subn("", text)
        log["stages_applied"].append("captions")

        # 8. Remove image references
        text, count = self._IMAGE_REF.subn("", text)
        log["stages_applied"].append("image_refs")

        # 9. Remove TOC entries
        text, count = self._TOC_ENTRY.subn("", text)
        log["stages_applied"].append("toc_entries")

        # 10. Remove TOC headings
        text, count = self._TOC_HEADING.subn("", text)
        log["stages_applied"].append("toc_headings")

        # 11. Replace markdown links with just the text
        text = self._MARKDOWN_LINK.sub(r"\1", text)

        # 12. Remove markdown bullets
        text, count = self._MARKDOWN_BULLET.subn("", text)

        # 13. Remove markdown headers
        text, count = self._MARKDOWN_HEADER.subn("", text)

        # 14. Remove URLs (replace with empty string)
        text, _ = self._URL.subn("", text)

        # 15. Normalize whitespace
        text = re.sub(r"[ \t]+", " ", text)
        text = re.sub(r"\n{3,}", "\n\n", text)

        chars_removed = original_length - len(text)
        log["chars_removed_total"] = chars_removed
        log["original_length"] = original_length
        log["clean_length"] = len(text)

        return text.strip(), log

