from __future__ import annotations

import re
import time
from difflib import SequenceMatcher
from typing import Optional

from yandex_music_og_songs.client import YandexMusicClient
from yandex_music_og_songs.config import ArtistConfig, DetectionConfig
from yandex_music_og_songs.models import TrackRef
from yandex_music_og_songs.normalizer import base_title, normalize_text


def _similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, normalize_text(a), normalize_text(b)).ratio()


def _is_fake_version(version: str, detection: DetectionConfig) -> bool:
    for pattern in detection.fake_version_patterns:
        if re.search(pattern, version, flags=re.IGNORECASE):
            return True
    return False


def _canonical_artist_for_title(
    client: YandexMusicClient,
    title: str,
    detection: DetectionConfig,
    cache: dict[str, Optional[str]],
    rate_limit: float,
) -> Optional[str]:
    key = normalize_text(base_title(title, detection.title_suffix_patterns))
    if key in cache:
        return cache[key]

    if rate_limit > 0:
        time.sleep(rate_limit)

    search = client.raw.search(title, type_="track")
    if not search or not search.tracks or not search.tracks.results:
        cache[key] = None
        return None

    best_artist: Optional[str] = None
    best_score = 0.0

    for track in search.tracks.results[:12]:
        if not track.artists or not track.title:
            continue
        if track.version and _is_fake_version(track.version, detection):
            continue

        title_score = _similarity(title, track.title)
        if title_score < 0.75:
            continue

        artist_name = track.artists[0].name
        if title_score > best_score:
            best_score = title_score
            best_artist = artist_name

    cache[key] = best_artist
    return best_artist


def check_wrong_artist(
    client: YandexMusicClient,
    track: TrackRef,
    artist_config: ArtistConfig,
    detection: DetectionConfig,
    cache: dict[str, Optional[str]],
    rate_limit: float = 0.25,
) -> Optional[str]:
    if artist_config.mode == "off":
        return None
    if track.is_user_upload:
        return None

    canonical = _canonical_artist_for_title(client, track.title, detection, cache, rate_limit)
    if not canonical:
        return None

    for entry in artist_config.whitelist:
        if _similarity(track.artist, entry.expected) >= artist_config.fuzzy_threshold:
            for allowed in entry.allowed:
                if _similarity(canonical, allowed) >= artist_config.fuzzy_threshold:
                    return None

    if _similarity(track.artist, canonical) >= artist_config.fuzzy_threshold:
        return None

    return f"wrong_artist:{canonical}"
