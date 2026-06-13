from __future__ import annotations

import re
import unicodedata
from difflib import SequenceMatcher


def normalize_text(value: str) -> str:
    text = unicodedata.normalize("NFKC", value or "")
    text = text.lower().strip()
    text = re.sub(r"\s+", " ", text)
    return text


def normalize_match_key(value: str) -> str:
    """Strict key for title/artist equality in Yandex catalog."""
    text = normalize_text(value)
    text = re.sub(r"[^\w\s]", "", text, flags=re.UNICODE)
    text = re.sub(r"\s+featuring\s+.*$", "", text)
    text = re.sub(r"\s+feat\.?\s+.*$", "", text)
    return re.sub(r"\s+", " ", text).strip()


def strip_title_suffixes(title: str, patterns: list[str]) -> str:
    result = title
    for pattern in patterns:
        result = re.sub(pattern, "", result, flags=re.IGNORECASE).strip()
    return re.sub(r"\s+", " ", result).strip(" -")


def base_title(title: str, title_suffix_patterns: list[str]) -> str:
    cleaned = strip_title_suffixes(title, title_suffix_patterns)
    cleaned = re.sub(r"\s*[\(\[].*?[\)\]]\s*", "", cleaned).strip()
    cleaned = re.sub(r"\s*[-–—]\s*[^-–—]+$", "", cleaned).strip()
    return cleaned or title


def primary_artist(artists: list[str]) -> str:
    return artists[0] if artists else "Unknown"


def text_similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, normalize_text(a), normalize_text(b)).ratio()


def exact_match(a: str, b: str) -> bool:
    return normalize_match_key(a) == normalize_match_key(b)
