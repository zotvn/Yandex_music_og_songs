from __future__ import annotations

import re
from typing import Optional

from yandex_music_og_songs.client import YandexMusicClient
from yandex_music_og_songs.config import DetectionConfig
from yandex_music_og_songs.models import CatalogHit, TrackRef
from yandex_music_og_songs.normalizer import base_title, normalize_text, text_similarity


def is_suspicious_artist(name: str, detection: DetectionConfig) -> bool:
    if not name or not isinstance(name, str):
        return False
    return any(re.search(pattern, name, flags=re.IGNORECASE) for pattern in detection.suspicious_artist_patterns)


def duration_close(
    left: Optional[int],
    right: Optional[int],
    *,
    tolerance_ms: int,
    tolerance_ratio: float,
) -> bool:
    if left is None or right is None:
        return True
    diff = abs(left - right)
    limit = max(tolerance_ms, int(max(left, right) * tolerance_ratio))
    return diff <= limit


def title_has_suffixes(track: TrackRef, detection: DetectionConfig) -> bool:
    title = track.title or ""
    if track.version and track.version.strip():
        return True
    paren = re.search(r"[\(\[]([^\)\]]+)[\)\]]\s*$", title, re.IGNORECASE)
    if paren:
        content = paren.group(1)
        patterns = (
            detection.title_paren_fake_patterns
            + detection.title_ask_patterns
            + [r"studio\s*version", r"tiktok", r"remix", r"edit", r"8d"]
        )
        if any(re.search(p, content, re.IGNORECASE) for p in patterns):
            return True
    trailing = re.search(
        r"\s*[-–—]\s*(radio|sped|speed|slowed|nightcore|8d|studio)",
        title,
        re.IGNORECASE,
    )
    return trailing is not None


def search_catalog(
    client: YandexMusicClient,
    title: str,
    detection: DetectionConfig,
) -> list[CatalogHit]:
    from yandex_music_og_songs.artist_resolver import is_fake_version

    search = client.raw.search(title, type_="track")
    if not search or not search.tracks or not search.tracks.results:
        return []

    hits: list[CatalogHit] = []
    for track in search.tracks.results[:20]:
        if not track.artists or not track.title:
            continue
        artist = track.artists[0].name or ""
        if track.version and is_fake_version(track.version, detection):
            continue
        hits.append(
            CatalogHit(
                artist=artist,
                title=track.title,
                duration_ms=track.duration_ms,
                version=track.version,
            )
        )
    return hits


def catalog_confirms_original(
    track: TrackRef,
    hits: list[CatalogHit],
    detection: DetectionConfig,
) -> Optional[CatalogHit]:
    if title_has_suffixes(track, detection):
        return None

    clean = base_title(track.title, detection.title_suffix_patterns)
    official = [h for h in hits if not is_suspicious_artist(h.artist, detection)]

    for hit in official:
        if text_similarity(clean, hit.title) < 0.85:
            continue
        if text_similarity(track.artist, hit.artist) < 0.88:
            continue
        if not duration_close(
            track.duration_ms,
            hit.duration_ms,
            tolerance_ms=detection.duration_tolerance_ms,
            tolerance_ratio=detection.duration_tolerance_ratio,
        ):
            continue
        return hit
    return None


def best_official_artist(hits: list[CatalogHit], title: str, detection: DetectionConfig) -> Optional[str]:
    counts: dict[str, int] = {}
    display: dict[str, str] = {}
    for hit in hits:
        if is_suspicious_artist(hit.artist, detection):
            continue
        if text_similarity(title, hit.title) < 0.72:
            continue
        key = normalize_text(hit.artist)
        counts[key] = counts.get(key, 0) + 1
        display.setdefault(key, hit.artist)
    if not counts:
        return None
    best_key = max(counts, key=counts.get)
    if counts[best_key] < 1:
        return None
    return display[best_key]


def official_catalog_signal(hits: list[CatalogHit], title: str, detection: DetectionConfig) -> int:
    return sum(
        1
        for hit in hits
        if not is_suspicious_artist(hit.artist, detection) and text_similarity(title, hit.title) >= 0.72
    )
