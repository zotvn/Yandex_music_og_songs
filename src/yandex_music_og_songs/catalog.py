from __future__ import annotations

import re
from typing import Optional

from yandex_music_og_songs.client import YandexMusicClient
from yandex_music_og_songs.config import DetectionConfig
from yandex_music_og_songs.models import CatalogHit, TrackRef
from yandex_music_og_songs.normalizer import base_title, exact_match, normalize_match_key


def is_suspicious_artist(name: str, detection: DetectionConfig) -> bool:
    if not name or not isinstance(name, str):
        return False
    return any(re.search(pattern, name, flags=re.IGNORECASE) for pattern in detection.suspicious_artist_patterns)


def has_bad_version(version: Optional[str], detection: DetectionConfig) -> bool:
    if not version or not version.strip():
        return False
    if any(re.search(p, version, re.IGNORECASE) for p in detection.version_word_patterns):
        return True
    return any(
        re.search(p, version, re.IGNORECASE)
        for p in detection.title_paren_fake_patterns
    )


def duration_matches(
    left: Optional[int],
    right: Optional[int],
    *,
    min_ratio: float,
    tolerance_ms: int,
) -> bool:
    if left is None or right is None:
        return True
    if left <= 0 or right <= 0:
        return True
    diff = abs(left - right)
    if diff <= tolerance_ms:
        return True
    ratio = min(left, right) / max(left, right)
    return ratio >= min_ratio


def search_catalog(
    client: YandexMusicClient,
    query: str,
    detection: DetectionConfig,
    *,
    artist_filter: Optional[str] = None,
) -> list[CatalogHit]:
    search = client.raw.search(query, type_="track")
    if not search or not search.tracks or not search.tracks.results:
        return []

    hits: list[CatalogHit] = []
    for track in search.tracks.results[:25]:
        if not track.artists or not track.title:
            continue
        artist = track.artists[0].name or ""
        if artist_filter and normalize_match_key(artist) != normalize_match_key(artist_filter):
            continue
        if has_bad_version(track.version, detection):
            continue
        album_id = None
        if track.albums:
            album_id = str(track.albums[0].id)
        hits.append(
            CatalogHit(
                artist=artist,
                title=track.title,
                duration_ms=track.duration_ms,
                track_id=str(track.id) if track.id else None,
                album_id=album_id,
                version=track.version,
            )
        )
    return hits


def find_clean_yandex_match(
    client: YandexMusicClient,
    expected_artist: str,
    clean_title: str,
    duration_ms: Optional[int],
    detection: DetectionConfig,
) -> Optional[CatalogHit]:
    query = f"{expected_artist} {clean_title}"
    hits = search_catalog(client, query, detection, artist_filter=expected_artist)

    best: Optional[CatalogHit] = None
    best_duration_diff = 10**12

    for hit in hits:
        if not exact_match(hit.title, clean_title):
            continue
        if not exact_match(hit.artist, expected_artist):
            continue
        if hit.version and hit.version.strip():
            continue
        if is_suspicious_artist(hit.artist, detection):
            continue
        if not duration_matches(
            duration_ms,
            hit.duration_ms,
            min_ratio=detection.duration_min_ratio,
            tolerance_ms=detection.duration_tolerance_ms,
        ):
            continue
        if not hit.track_id:
            continue

        if duration_ms and hit.duration_ms:
            diff = abs(duration_ms - hit.duration_ms)
        else:
            diff = 0
        if diff < best_duration_diff:
            best_duration_diff = diff
            best = hit

    return best


def is_user_original(track: TrackRef) -> bool:
    if track.is_user_upload:
        return True
    return track.track_source == "OWN_REPLACED_TO_UGC"


def track_needs_metadata_check(track: TrackRef) -> bool:
    return not is_user_original(track)
