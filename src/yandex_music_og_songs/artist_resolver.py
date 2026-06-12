from __future__ import annotations

import json
import re
import urllib.parse
import urllib.request
from collections import Counter, defaultdict
from dataclasses import dataclass
from typing import Optional

from yandex_music_og_songs.catalog import (
    is_suspicious_artist,
    official_catalog_signal,
    search_catalog,
)
from yandex_music_og_songs.client import YandexMusicClient
from yandex_music_og_songs.config import DetectionConfig
from yandex_music_og_songs.models import ArtistCandidate, CatalogHit, TitleLookup, TrackRef, TrackStatus
from yandex_music_og_songs.normalizer import base_title, normalize_text, text_similarity

_USER_AGENT = "YandexMusicOGSongs/0.4 (https://github.com/zotvn/Yandex_music_og_songs)"
_AMBIGUOUS_GAP = 0.15
_MATCH_THRESHOLD = 0.82


@dataclass(frozen=True)
class ArtistResolution:
    status: TrackStatus
    reasons: list[str]
    candidates: list[ArtistCandidate]
    expected_artist: Optional[str]


def _similarity(a: str, b: str) -> float:
    return text_similarity(a, b)


def is_fake_version(version: str, detection: DetectionConfig) -> bool:
    for pattern in detection.fake_version_patterns:
        if re.search(pattern, version, flags=re.IGNORECASE):
            return True
    return False


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


def yandex_is_conclusive(yandex: list[str]) -> bool:
    if not yandex:
        return False

    counts = Counter(normalize_text(name) for name in yandex)
    if len(counts) == 1:
        return True

    top_count = counts.most_common(1)[0][1]
    total = len(yandex)
    if top_count >= 2 and top_count / total >= 0.6 and len(counts) <= 3:
        return True

    return False


def needs_musicbrainz(
    yandex: list[str],
    hits: list[CatalogHit],
    title: str,
    *,
    always: bool = False,
    track_artist: str = "",
    detection: DetectionConfig | None = None,
) -> bool:
    if always:
        return True
    if detection and track_artist and is_suspicious_artist(track_artist, detection):
        return True
    if detection and official_catalog_signal(hits, title, detection) < 2:
        return True
    return not yandex_is_conclusive(yandex)


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


def official_artists_from_hits(hits: list[CatalogHit], title: str, detection: DetectionConfig) -> list[str]:
    artists: list[str] = []
    for hit in hits:
        if is_suspicious_artist(hit.artist, detection):
            continue
        if _similarity(title, hit.title) < 0.72:
            continue
        artists.append(hit.artist)
    return artists


def lookup_title(
    client: YandexMusicClient,
    title: str,
    detection: DetectionConfig,
    *,
    musicbrainz_mode: str = "auto",
    track_artist: str = "",
) -> TitleLookup:
    clean_title = base_title(title, detection.title_suffix_patterns)
    hits = search_catalog(client, clean_title, detection)
    yandex = official_artists_from_hits(hits, clean_title, detection)

    musicbrainz: list[str] = []
    if musicbrainz_mode == "never":
        pass
    elif musicbrainz_mode == "always" or needs_musicbrainz(
        yandex,
        hits,
        clean_title,
        track_artist=track_artist,
        detection=detection,
    ):
        musicbrainz = _search_musicbrainz(clean_title)

    candidates = _build_candidates(yandex, musicbrainz)
    return TitleLookup(candidates=candidates, hits=hits)


def lookup_artists(
    client: YandexMusicClient,
    title: str,
    detection: DetectionConfig,
    cache: dict[str, TitleLookup],
    *,
    musicbrainz_mode: str = "auto",
    track_artist: str = "",
) -> list[ArtistCandidate]:
    key = normalize_text(base_title(title, detection.title_suffix_patterns))
    if key in cache:
        return cache[key].candidates

    result = lookup_title(
        client,
        title,
        detection,
        musicbrainz_mode=musicbrainz_mode,
        track_artist=track_artist,
    )
    cache[key] = result
    return result.candidates


def resolve_with_candidates(
    track: TrackRef,
    candidates: list[ArtistCandidate],
) -> ArtistResolution:
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


def resolve_track_artist(
    client: YandexMusicClient,
    track: TrackRef,
    detection: DetectionConfig,
    cache: dict[str, TitleLookup],
) -> ArtistResolution:
    if track.is_user_upload:
        return ArtistResolution(TrackStatus.ORIGINAL, [], [], track.artist)

    candidates = lookup_artists(client, track.title, detection, cache, track_artist=track.artist)
    return resolve_with_candidates(track, candidates)
