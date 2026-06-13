from __future__ import annotations

import re
from typing import Optional

from yandex_music_og_songs.config import DetectionConfig
from yandex_music_og_songs.models import TrackRef, TrackStatus

_PAREN_RE = re.compile(r"[\(\[]([^\)\]]+)[\)\]]", re.IGNORECASE)


def _matches_any_pattern(value: str, patterns: list[str]) -> Optional[str]:
    for pattern in patterns:
        if re.search(pattern, value, flags=re.IGNORECASE):
            return pattern
    return None


def _has_version_words(value: str, detection: DetectionConfig) -> bool:
    return _matches_any_pattern(value, detection.version_word_patterns) is not None


def detect_track(track: TrackRef, config: DetectionConfig) -> tuple[TrackStatus, list[str]]:
    reasons: list[str] = []

    if track.version and track.version.strip():
        reasons.append("version:field")
        if _has_version_words(track.version, config):
            reasons.append("version:word")

    for match in _PAREN_RE.finditer(track.title or ""):
        content = match.group(1).strip()
        if matched := _matches_any_pattern(content, config.title_paren_fake_patterns):
            reasons.append(f"title_tag:{matched}")
        elif _has_version_words(content, config):
            reasons.append("title_tag:version")

    if matched := _matches_any_pattern(track.title, config.title_fake_patterns):
        if not any(r.startswith("title_tag") for r in reasons):
            reasons.append(f"title_tag:{matched}")

    combined = f"{track.title} {track.version or ''}"
    if _has_version_words(combined, config) and not any("version" in r for r in reasons):
        reasons.append("version:word")

    if reasons:
        return TrackStatus.FAKE, reasons
    return TrackStatus.ORIGINAL, []
