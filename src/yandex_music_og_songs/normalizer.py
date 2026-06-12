from __future__ import annotations

import re
import unicodedata


def normalize_text(value: str) -> str:
    text = unicodedata.normalize("NFKC", value or "")
    text = text.lower().strip()
    text = re.sub(r"\s+", " ", text)
    return text


def strip_title_suffixes(title: str, patterns: list[str]) -> str:
    result = title
    for pattern in patterns:
        result = re.sub(pattern, "", result, flags=re.IGNORECASE).strip()
    return re.sub(r"\s+", " ", result).strip(" -")


def base_title(title: str, title_suffix_patterns: list[str]) -> str:
    cleaned = strip_title_suffixes(title, title_suffix_patterns)
    cleaned = re.sub(r"\s*[\(\[].*?[\)\]]\s*$", "", cleaned).strip()
    return cleaned or title


def primary_artist(artists: list[str]) -> str:
    return artists[0] if artists else "Unknown"
