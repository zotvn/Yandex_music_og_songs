from __future__ import annotations

import re
from typing import Optional

from yandex_music_og_songs.config import DetectionConfig
from yandex_music_og_songs.models import TrackRef, TrackStatus

_PAREN_SUFFIX_RE = re.compile(r"[\(\[]([^\)\]]+)[\)\]]\s*$", re.IGNORECASE)
_TRAILING_VERSION_RE = re.compile(
    r"\s*[-–—]\s*(radio\s*[-_]?\s*edit|sped\s*[-_]?\s*up|speed\s*[-_]?\s*up|slowed(?:\s*(?:&|and)\s*reverb)?|nightcore|\b8d\b)\s*$",
    re.IGNORECASE,
)


def _matches_any_pattern(value: str, patterns: list[str]) -> Optional[str]:
    for pattern in patterns:
        if re.search(pattern, value, flags=re.IGNORECASE):
            return pattern
    return None


def _is_kept_version(version: str, keep_patterns: list[str]) -> bool:
    return _matches_any_pattern(version, keep_patterns) is not None


def _parenthetical_suffix(title: str) -> Optional[str]:
    match = _PAREN_SUFFIX_RE.search(title.strip())
    return match.group(1).strip() if match else None


def _status_from_reasons(reasons: list[str]) -> TrackStatus:
    if any(reason.startswith("pick_version") for reason in reasons):
        return TrackStatus.CHOOSE
    if reasons:
        return TrackStatus.FAKE
    return TrackStatus.ORIGINAL


def detect_track(track: TrackRef, config: DetectionConfig) -> tuple[TrackStatus, list[str]]:
    reasons: list[str] = []

    if config.treat_replaced_to_ugc and track.track_source == "OWN_REPLACED_TO_UGC":
        reasons.append("track_source:OWN_REPLACED_TO_UGC")

    if track.version:
        version = track.version.strip()
        fake_matched = _matches_any_pattern(version, config.fake_version_patterns)
        if fake_matched:
            keep_matched = _is_kept_version(version, config.keep_version_patterns)
            priority_fake = _matches_any_pattern(version, config.title_ask_patterns) is not None
            if not keep_matched or priority_fake:
                reasons.append(f"version:{fake_matched}")

    paren_content = _parenthetical_suffix(track.title)
    if paren_content:
        if matched := _matches_any_pattern(paren_content, config.title_paren_fake_patterns):
            reasons.append(f"title_fake:{matched}")
        elif matched := _matches_any_pattern(paren_content, config.title_ask_patterns):
            reasons.append(f"pick_version:{matched}")

    if matched := _matches_any_pattern(track.title, config.title_fake_patterns):
        if not any(reason.startswith("title_fake") for reason in reasons):
            reasons.append(f"title_fake:{matched}")

    trailing = _TRAILING_VERSION_RE.search(track.title)
    if trailing and not any(reason.startswith("pick_version") for reason in reasons):
        reasons.append(f"pick_version:trailing:{trailing.group(1)}")

    if config.treat_ugc_as_fake and track.is_user_upload:
        reasons.append("user_upload")

    return _status_from_reasons(reasons), reasons
