from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from yandex_music_og_songs.artist_resolver import resolve_with_candidates
from yandex_music_og_songs.catalog import (
    find_clean_yandex_match,
    is_suspicious_artist,
    is_user_original,
)
from yandex_music_og_songs.client import YandexMusicClient
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
    replace_track_id: Optional[str] = None
    replace_album_id: Optional[str] = None


def lookup_cache_key(title: str, detection: DetectionConfig) -> str:
    return normalize_text(base_title(title, detection.title_suffix_patterns))


def needs_artist_lookup(track: TrackRef, local_reasons: list[str], detection: DetectionConfig) -> bool:
    if local_reasons:
        return True
    return is_suspicious_artist(track.artist, detection)


def _prioritize_reasons(reasons: list[str]) -> list[str]:
    artist = [r for r in reasons if r.startswith("wrong_artist:")]
    if artist:
        return artist
    tags = [r for r in reasons if r.startswith("title_tag:") or r.startswith("version:")]
    if tags:
        return tags
    return reasons


def _attach_replacement(
    client: YandexMusicClient,
    track: TrackRef,
    detection: DetectionConfig,
    expected_artist: str,
    status: TrackStatus,
    reasons: list[str],
    candidates: list[ArtistCandidate],
) -> VerifyResult:
    clean_title = base_title(track.title, detection.title_suffix_patterns)
    match = find_clean_yandex_match(client, expected_artist, clean_title, track.duration_ms, detection)
    if match and match.track_id:
        final_reasons = _prioritize_reasons(reasons)
        if "og_in_ya" not in final_reasons:
            final_reasons = [*final_reasons, "og_in_ya"]
        return VerifyResult(
            status=status,
            reasons=final_reasons,
            candidates=candidates,
            expected_artist=expected_artist,
            replace_track_id=match.track_id,
            replace_album_id=match.album_id,
        )
    return VerifyResult(
        status=status,
        reasons=[*_prioritize_reasons(reasons), "no_clean_yandex_match"],
        candidates=candidates,
        expected_artist=expected_artist,
    )


def verify_track(
    track: TrackRef,
    detection: DetectionConfig,
    truth: TitleLookup | None,
    client: YandexMusicClient,
) -> VerifyResult:
    if is_user_original(track):
        return VerifyResult(TrackStatus.ORIGINAL, [], [], track.artist)

    _det_status, local_reasons = detect_track(track, detection)

    if not needs_artist_lookup(track, local_reasons, detection):
        return VerifyResult(TrackStatus.ORIGINAL, [], [], track.artist)

    candidates = truth.candidates if truth else []
    threshold = detection.artist_match_threshold

    if is_suspicious_artist(track.artist, detection):
        from yandex_music_og_songs.artist_resolver import pick_expected_artist

        expected = pick_expected_artist(candidates)
        reasons = list(local_reasons)
        if expected:
            reasons.append(f"wrong_artist:{expected}")
        else:
            reasons.append("suspicious_artist")
        if expected:
            return _attach_replacement(client, track, detection, expected, TrackStatus.FAKE, reasons, candidates)
        return VerifyResult(TrackStatus.FAKE, _prioritize_reasons(reasons), candidates, None)

    resolution = (
        resolve_with_candidates(track, candidates, threshold, detection.artist_ok_threshold)
        if candidates
        else None
    )

    if resolution and resolution.status == TrackStatus.CHOOSE:
        mb_candidates = [c for c in resolution.candidates if "musicbrainz" in c.sources]
        if len(mb_candidates) < 2:
            return VerifyResult(TrackStatus.ORIGINAL, [], candidates, track.artist)
        return VerifyResult(
            TrackStatus.CHOOSE,
            ["pick_artist", *local_reasons],
            resolution.candidates,
            None,
        )

    fake_reasons = list(local_reasons)
    expected = resolution.expected_artist if resolution else None

    if resolution and resolution.status == TrackStatus.FAKE:
        fake_reasons.extend(resolution.reasons)
    elif resolution and resolution.status == TrackStatus.ORIGINAL:
        if local_reasons:
            fake_reasons.extend(local_reasons)
        else:
            return VerifyResult(TrackStatus.ORIGINAL, [], candidates, expected)

    if not fake_reasons:
        return VerifyResult(TrackStatus.ORIGINAL, [], candidates, expected or track.artist)

    status = TrackStatus.FAKE
    if expected:
        return _attach_replacement(client, track, detection, expected, status, fake_reasons, candidates)

    return VerifyResult(
        status,
        _prioritize_reasons(fake_reasons),
        candidates,
        None,
    )
