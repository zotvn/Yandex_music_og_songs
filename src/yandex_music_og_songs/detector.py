from __future__ import annotations

import re
from typing import Optional

from yandex_music_og_songs.config import DetectionConfig
from yandex_music_og_songs.models import TrackRef, TrackStatus


def _matches_any_pattern(value: str, patterns: list[str]) -> Optional[str]:
    for pattern in patterns:
        if re.search(pattern, value, flags=re.IGNORECASE):
            return pattern
    return None


def _is_kept_version(version: str, keep_patterns: list[str]) -> bool:
    return _matches_any_pattern(version, keep_patterns) is not None


def detect_track(track: TrackRef, config: DetectionConfig) -> tuple[TrackStatus, list[str]]:
    reasons: list[str] = []

    if config.treat_replaced_to_ugc and track.track_source == "OWN_REPLACED_TO_UGC":
        reasons.append("track_source:OWN_REPLACED_TO_UGC")

    if track.version:
        version = track.version.strip()
        if version and not _is_kept_version(version, config.keep_version_patterns):
            if matched := _matches_any_pattern(version, config.fake_version_patterns):
                reasons.append(f"version:{matched}")
            else:
                reasons.append(f"version:{version}")

    if matched := _matches_any_pattern(track.title, config.title_suffix_patterns):
        reasons.append(f"title_suffix:{matched}")

    if config.treat_ugc_as_fake and track.is_user_upload:
        reasons.append("user_upload")

    if reasons:
        return TrackStatus.FAKE, reasons
    return TrackStatus.ORIGINAL, []
