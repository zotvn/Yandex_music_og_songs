from __future__ import annotations

import json
import re
import urllib.parse
import urllib.request
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from difflib import SequenceMatcher
from typing import Optional

from yandex_music_og_songs.client import YandexMusicClient
from yandex_music_og_songs.config import DetectionConfig
from yandex_music_og_songs.models import ArtistCandidate, TrackRef, TrackStatus
from yandex_music_og_songs.normalizer import base_title, normalize_text

_USER_AGENT = "YandexMusicOGSongs/0.3 (https://github.com/zotvn/Yandex_music_og_songs)"
_AMBIGUOUS_GAP = 0.15
_MATCH_THRESHOLD = 0.82


@dataclass(frozen=True)
class ArtistResolution:
    status: TrackStatus
    reasons: list[str]
    candidates: list[ArtistCandidate]
    expected_artist: Optional[str]


def _similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, normalize_text(a), normalize_text(b)).ratio()


def _is_fake_version(version: str, detection: DetectionConfig) -> bool:
    for pattern in detection.fake_version_patterns:
        if re.search(pattern, version, flags=re.IGNORECASE):
            return True
    return False


def _search_yandex(client: YandexMusicClient, title: str, detection: DetectionConfig) -> list[str]:
    search = client.raw.search(title, type_="track")
    if not search or not search.tracks or not search.tracks.results:
        return []

    artists: list[str] = []
    for track in search.tracks.results[:12]:
        if not track.artists or not track.title:
            continue
        if track.version and _is_fake_version(track.version, detection):
            continue
        if _similarity(title, track.title) < 0.72:
            continue
        name = track.artists[0].name
        if name:
            artists.append(name)
    return artists


def _search_musicbrainz(title: str) -> list[str]:
    query = urllib.parse.quote(f'recording:"{title}"')
    url = f"https://musicbrainz.org/ws/2/recording?query={query}&fmt=json&limit=10"
    request = urllib.request.Request(url, headers={"User-Agent": _USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=8) as response:
            data = json.loads(response.read().decode("utf-8"))
    except Exception:
        return []

    artists: list[str] = []
    for recording in data.get("recordings", []):
        rec_title = recording.get("title", "")
        if rec_title and _similarity(title, rec_title) < 0.65:
            continue
        for credit in recording.get("artist-credit", []):
            artist = credit.get("artist", {})
            name = artist.get("name")
            if name:
                artists.append(name)
    return artists


def _build_candidates(yandex: list[str], musicbrainz: list[str]) -> list[ArtistCandidate]:
    scores: dict[str, float] = defaultdict(float)
    sources: dict[str, set[str]] = defaultdict(set)

    for name in yandex:
        key = normalize_text(name)
        scores[key] += 1.0
        sources[key].add("yandex")

    for name in musicbrainz:
        key = normalize_text(name)
        scores[key] += 0.9
        sources[key].add("musicbrainz")

    display_name: dict[str, str] = {}
    for name in yandex + musicbrainz:
        key = normalize_text(name)
        display_name.setdefault(key, name)

    ranked = sorted(scores.items(), key=lambda item: item[1], reverse=True)
    return [
        ArtistCandidate(
            artist=display_name[key],
            sources=tuple(sorted(sources[key])),
            score=score,
        )
        for key, score in ranked[:8]
    ]


def _yandex_is_confident(yandex: list[str]) -> bool:
    if len(yandex) < 2:
        return len(yandex) == 1
    counts = Counter(normalize_text(name) for name in yandex)
    top = counts.most_common(1)[0][1]
    return top >= 2 and len(counts) <= 2


def lookup_artists(
    client: YandexMusicClient,
    title: str,
    detection: DetectionConfig,
    cache: dict[str, list[ArtistCandidate]],
) -> list[ArtistCandidate]:
    key = normalize_text(base_title(title, detection.title_suffix_patterns))
    if key in cache:
        return cache[key]

    clean_title = base_title(title, detection.title_suffix_patterns)
    yandex = _search_yandex(client, clean_title, detection)

    if _yandex_is_confident(yandex):
        candidates = _build_candidates(yandex, [])
        cache[key] = candidates
        return candidates

    with ThreadPoolExecutor(max_workers=2) as pool:
        yandex_future = pool.submit(_search_yandex, client, clean_title, detection)
        mb_future = pool.submit(_search_musicbrainz, clean_title)
        yandex = yandex_future.result()
        musicbrainz = mb_future.result()

    candidates = _build_candidates(yandex, musicbrainz)
    cache[key] = candidates
    return candidates


def resolve_track_artist(
    client: YandexMusicClient,
    track: TrackRef,
    detection: DetectionConfig,
    cache: dict[str, list[ArtistCandidate]],
) -> ArtistResolution:
    if track.is_user_upload:
        return ArtistResolution(TrackStatus.ORIGINAL, [], [], track.artist)

    candidates = lookup_artists(client, track.title, detection, cache)
    if not candidates:
        return ArtistResolution(TrackStatus.ORIGINAL, ["artist_unknown"], [], None)

    for candidate in candidates:
        if _similarity(track.artist, candidate.artist) >= _MATCH_THRESHOLD:
            return ArtistResolution(TrackStatus.ORIGINAL, [], candidates, candidate.artist)

    if len(candidates) == 1:
        expected = candidates[0].artist
        return ArtistResolution(
            TrackStatus.FAKE,
            [f"wrong_artist:{expected}"],
            candidates,
            expected,
        )

    top, second = candidates[0], candidates[1]
    if top.score - second.score < _AMBIGUOUS_GAP:
        return ArtistResolution(
            TrackStatus.CHOOSE,
            ["pick_artist"],
            candidates,
            None,
        )

    return ArtistResolution(
        TrackStatus.FAKE,
        [f"wrong_artist:{top.artist}"],
        candidates,
        top.artist,
    )
