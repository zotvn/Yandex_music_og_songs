from __future__ import annotations

import json
import urllib.parse
import urllib.request
from collections import defaultdict
from dataclasses import dataclass
from typing import Optional

from yandex_music_og_songs.config import DetectionConfig
from yandex_music_og_songs.models import ArtistCandidate, TitleLookup, TrackRef, TrackStatus
from yandex_music_og_songs.normalizer import base_title, exact_match, normalize_text, text_similarity
from yandex_music_og_songs.ytmusic import search_youtube_music

_USER_AGENT = "YandexMusicOGSongs/0.5 (https://github.com/zotvn/Yandex_music_og_songs)"
_AMBIGUOUS_GAP = 0.12
_MB_SCORE = 1.0
_YT_SCORE = 0.8


@dataclass(frozen=True)
class ArtistResolution:
    status: TrackStatus
    reasons: list[str]
    candidates: list[ArtistCandidate]
    expected_artist: Optional[str]


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
        if rec_title and text_similarity(title, rec_title) < 0.65:
            continue
        for credit in recording.get("artist-credit", []):
            artist = credit.get("artist", {})
            name = artist.get("name")
            if name:
                artists.append(name)
    return artists


def _build_candidates(musicbrainz: list[str], youtube: list[str]) -> list[ArtistCandidate]:
    scores: dict[str, float] = defaultdict(float)
    sources: dict[str, set[str]] = defaultdict(set)
    display: dict[str, str] = {}

    for name in musicbrainz:
        key = normalize_text(name)
        scores[key] += _MB_SCORE
        sources[key].add("musicbrainz")
        display.setdefault(key, name)

    for name, _duration in youtube:
        key = normalize_text(name)
        scores[key] += _YT_SCORE
        sources[key].add("youtube")
        display.setdefault(key, name)

    ranked = sorted(scores.items(), key=lambda item: item[1], reverse=True)
    return [
        ArtistCandidate(
            artist=display[key],
            sources=tuple(sorted(sources[key])),
            score=score,
        )
        for key, score in ranked[:8]
    ]


def lookup_truth(title: str, detection: DetectionConfig) -> TitleLookup:
    clean_title = base_title(title, detection.title_suffix_patterns)
    musicbrainz = _search_musicbrainz(clean_title)
    youtube = search_youtube_music(clean_title)
    candidates = _build_candidates(musicbrainz, youtube)
    return TitleLookup(candidates=candidates)


def pick_expected_artist(candidates: list[ArtistCandidate]) -> Optional[str]:
    if not candidates:
        return None
    return candidates[0].artist


def artist_matches(track_artist: str, expected: str, threshold: float) -> bool:
    if exact_match(track_artist, expected):
        return True
    return text_similarity(track_artist, expected) >= threshold


def artists_equivalent(track_artist: str, expected: str, ok_threshold: float) -> bool:
    return artist_matches(track_artist, expected, ok_threshold)


def artists_clearly_different(track_artist: str, expected: str, threshold: float) -> bool:
    if exact_match(track_artist, expected):
        return False
    return text_similarity(track_artist, expected) < threshold


def resolve_with_candidates(
    track: TrackRef,
    candidates: list[ArtistCandidate],
    threshold: float,
    ok_threshold: float,
) -> ArtistResolution:
    if not candidates:
        return ArtistResolution(TrackStatus.ORIGINAL, [], [], None)

    for candidate in candidates:
        if artists_equivalent(track.artist, candidate.artist, ok_threshold):
            return ArtistResolution(TrackStatus.ORIGINAL, [], candidates, candidate.artist)

    if len(candidates) == 1:
        only = candidates[0]
        if "musicbrainz" not in only.sources:
            return ArtistResolution(TrackStatus.ORIGINAL, [], candidates, track.artist)
        expected = only.artist
        if artists_clearly_different(track.artist, expected, threshold):
            return ArtistResolution(
                TrackStatus.FAKE,
                [f"wrong_artist:{expected}"],
                candidates,
                expected,
            )
        return ArtistResolution(TrackStatus.ORIGINAL, [], candidates, track.artist)

    mb_only = [c for c in candidates if "musicbrainz" in c.sources]
    if not mb_only:
        return ArtistResolution(TrackStatus.ORIGINAL, [], candidates, track.artist)

    top, second = candidates[0], candidates[1]
    if top.score - second.score < _AMBIGUOUS_GAP:
        return ArtistResolution(
            TrackStatus.CHOOSE,
            ["pick_artist"],
            candidates,
            None,
        )

    expected = top.artist
    if artists_clearly_different(track.artist, expected, threshold):
        return ArtistResolution(
            TrackStatus.FAKE,
            [f"wrong_artist:{expected}"],
            candidates,
            expected,
        )
    return ArtistResolution(TrackStatus.ORIGINAL, [], candidates, track.artist)
