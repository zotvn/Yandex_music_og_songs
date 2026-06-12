from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from yandex_music_og_songs.artist_resolver import resolve_with_candidates
from yandex_music_og_songs.catalog import (
    best_official_artist,
    catalog_confirms_original,
    is_suspicious_artist,
    official_catalog_signal,
)
from yandex_music_og_songs.config import DetectionConfig
from yandex_music_og_songs.detector import detect_track
from yandex_music_og_songs.models import ArtistCandidate, TitleLookup, TrackRef, TrackStatus
from yandex_music_og_songs.normalizer import base_title, normalize_text


@dataclass(frozen=True)
class VerifyResult:
    status: TrackStatus
    reasons: list[str]
    candidates: list[ArtistCandidate]
    expected_artist: Optional[str]


_VERSION_HINTS = ("version:", "title_fake:", "track_source:", "user_upload")


def lookup_cache_key(title: str, detection: DetectionConfig) -> str:
    return normalize_text(base_title(title, detection.title_suffix_patterns))


def _only_version_hints(reasons: list[str]) -> bool:
    return bool(reasons) and all(
        r.startswith("pick_version") or any(r.startswith(p) for p in _VERSION_HINTS) for r in reasons
    )


def _prioritize_reasons(reasons: list[str]) -> list[str]:
    artist = [r for r in reasons if r.startswith("wrong_artist:") or r == "suspicious_artist"]
    if artist:
        return artist
    choose = [r for r in reasons if r == "pick_artist"]
    if choose:
        return choose + [r for r in reasons if r.startswith("pick_version")]
    version = [r for r in reasons if r.startswith("pick_version")]
    if version:
        return version
    return reasons


def verify_track(
    track: TrackRef,
    detection: DetectionConfig,
    lookup: TitleLookup | None,
) -> VerifyResult:
    det_status, det_reasons = detect_track(track, detection)

    if track.is_user_upload:
        return VerifyResult(TrackStatus.ORIGINAL, [], [], track.artist)

    if lookup and lookup.hits:
        confirmed = catalog_confirms_original(track, lookup.hits, detection)
        if confirmed:
            return VerifyResult(TrackStatus.ORIGINAL, [], lookup.candidates, confirmed.artist)

    if det_status == TrackStatus.CHOOSE and _only_version_hints(det_reasons):
        return VerifyResult(det_status, det_reasons, [], None)

    if is_suspicious_artist(track.artist, detection):
        official = None
        if lookup:
            official = best_official_artist(
                lookup.hits,
                base_title(track.title, detection.title_suffix_patterns),
                detection,
            )
        if official:
            return VerifyResult(
                TrackStatus.FAKE,
                [f"wrong_artist:{official}", "suspicious_artist"],
                lookup.candidates if lookup else [],
                official,
            )
        return VerifyResult(
            TrackStatus.FAKE,
            ["suspicious_artist"],
            lookup.candidates if lookup else [],
            None,
        )

    if lookup is None:
        if det_reasons:
            return VerifyResult(det_status, _prioritize_reasons(det_reasons), [], None)
        return VerifyResult(TrackStatus.ORIGINAL, [], [], track.artist)

    resolution = resolve_with_candidates(track, lookup.candidates)
    clean_title = base_title(track.title, detection.title_suffix_patterns)

    if resolution.status == TrackStatus.ORIGINAL and official_catalog_signal(lookup.hits, clean_title, detection) < 2:
        official = best_official_artist(lookup.hits, clean_title, detection)
        if official:
            from yandex_music_og_songs.normalizer import text_similarity

            if text_similarity(track.artist, official) < 0.82:
                return VerifyResult(
                    TrackStatus.FAKE,
                    [f"wrong_artist:{official}"],
                    lookup.candidates,
                    official,
                )

    if resolution.status == TrackStatus.ORIGINAL:
        if det_status == TrackStatus.CHOOSE:
            return VerifyResult(det_status, det_reasons, resolution.candidates, resolution.expected_artist)
        if det_status == TrackStatus.FAKE and _only_version_hints(det_reasons):
            if any(r.startswith("wrong_artist:") for r in resolution.reasons):
                return VerifyResult(
                    TrackStatus.FAKE,
                    _prioritize_reasons(resolution.reasons),
                    resolution.candidates,
                    resolution.expected_artist,
                )
            return VerifyResult(
                TrackStatus.FAKE,
                _prioritize_reasons(det_reasons),
                resolution.candidates,
                resolution.expected_artist,
            )
        return VerifyResult(TrackStatus.ORIGINAL, [], resolution.candidates, resolution.expected_artist)

    if any(r.startswith("wrong_artist:") for r in resolution.reasons):
        return VerifyResult(
            resolution.status,
            _prioritize_reasons(resolution.reasons),
            resolution.candidates,
            resolution.expected_artist,
        )

    if det_reasons and resolution.status != TrackStatus.CHOOSE:
        merged = _prioritize_reasons([*resolution.reasons, *det_reasons])
        return VerifyResult(
            TrackStatus.FAKE if merged else TrackStatus.ORIGINAL,
            merged,
            resolution.candidates,
            resolution.expected_artist,
        )

    return VerifyResult(
        resolution.status,
        _prioritize_reasons(resolution.reasons),
        resolution.candidates,
        resolution.expected_artist,
    )
