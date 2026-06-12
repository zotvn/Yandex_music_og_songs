from __future__ import annotations

import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Optional

from yandex_music import Track
from yandex_music.track_short import TrackShort

from yandex_music_og_songs.artist_resolver import (
    ArtistResolution,
    _build_candidates,
    _search_musicbrainz,
    _search_yandex,
    resolve_with_candidates,
)
from yandex_music_og_songs.client import YandexMusicClient
from yandex_music_og_songs.config import DetectionConfig, PerformanceConfig
from yandex_music_og_songs.models import ArtistCandidate, TrackRef, TrackStatus
from yandex_music_og_songs.network import retry_network
from yandex_music_og_songs.normalizer import base_title, normalize_text

_thread_local = threading.local()
_mb_lock = threading.Lock()
_mb_last_at = 0.0


def _thread_client(token: str) -> YandexMusicClient:
    client = getattr(_thread_local, "client", None)
    if client is None:
        client = YandexMusicClient(token)
        _thread_local.client = client
    return client


def _search_musicbrainz_throttled(title: str) -> list[str]:
    global _mb_last_at
    with _mb_lock:
        wait = 1.05 - (time.monotonic() - _mb_last_at)
        if wait > 0:
            time.sleep(wait)
        artists = _search_musicbrainz(title)
        _mb_last_at = time.monotonic()
        return artists


def _lookup_title(
    token: str,
    title: str,
    detection: DetectionConfig,
) -> tuple[str, list[ArtistCandidate]]:
    clean_title = base_title(title, detection.title_suffix_patterns)
    key = normalize_text(clean_title)
    client = _thread_client(token)

    with ThreadPoolExecutor(max_workers=2) as pool:
        yandex_future = pool.submit(_search_yandex, client, clean_title, detection)
        mb_future = pool.submit(_search_musicbrainz_throttled, clean_title)
        yandex = yandex_future.result()
        musicbrainz = mb_future.result()

    return key, _build_candidates(yandex, musicbrainz)


def prefetch_artist_candidates(
    token: str,
    titles: list[str],
    detection: DetectionConfig,
    perf: PerformanceConfig,
) -> dict[str, list[ArtistCandidate]]:
    unique = list(dict.fromkeys(titles))
    if not unique:
        return {}

    cache: dict[str, list[ArtistCandidate]] = {}
    total = len(unique)
    done = 0
    done_lock = threading.Lock()

    print(f"Проверка {total} уникальных песен ({perf.artist_workers} потоков)...", file=sys.stderr, flush=True)

    with ThreadPoolExecutor(max_workers=perf.artist_workers) as pool:
        futures = {
            pool.submit(_lookup_title, token, title, detection): title for title in unique
        }
        for future in as_completed(futures):
            key, candidates = future.result()
            cache[key] = candidates
            with done_lock:
                done += 1
                if done % 10 == 0 or done == total:
                    print(f"  артисты: {done}/{total}", file=sys.stderr, flush=True)

    return cache


def resolve_from_cache(
    track: TrackRef,
    detection: DetectionConfig,
    cache: dict[str, list[ArtistCandidate]],
) -> ArtistResolution:
    if track.is_user_upload:
        return ArtistResolution(TrackStatus.ORIGINAL, [], [], track.artist)

    key = normalize_text(base_title(track.title, detection.title_suffix_patterns))
    candidates = cache.get(key, [])
    return resolve_with_candidates(track, candidates)


def _fetch_chunk(token: str, chunk_shorts: list[TrackShort]) -> list[Optional[Track]]:
    client = _thread_client(token)
    chunk_ids = [short.track_id for short in chunk_shorts if short is not None]
    batch = (
        retry_network(lambda: client.raw.tracks(chunk_ids), label="треки")
        if chunk_ids
        else []
    )
    batch = batch or []
    batch_iter = iter(batch)
    chunk_result: list[Optional[Track]] = []
    for short in chunk_shorts:
        if short is None:
            chunk_result.append(None)
            continue
        chunk_result.append(next(batch_iter, None))
    return chunk_result


def fetch_full_tracks_parallel(
    token: str,
    shorts: list[TrackShort],
    perf: PerformanceConfig,
) -> list[Optional[Track]]:
    if not shorts:
        return []

    chunks = [shorts[i : i + perf.track_batch_size] for i in range(0, len(shorts), perf.track_batch_size)]
    total = len(shorts)
    print(f"Загрузка {total} треков ({perf.track_workers} потоков)...", file=sys.stderr, flush=True)

    ordered: list[Optional[list[Optional[Track]]]] = [None] * len(chunks)
    with ThreadPoolExecutor(max_workers=perf.track_workers) as pool:
        future_map = {
            pool.submit(_fetch_chunk, token, chunk): index for index, chunk in enumerate(chunks)
        }
        for future in as_completed(future_map):
            ordered[future_map[future]] = future.result()

    result: list[Optional[Track]] = []
    for chunk in ordered:
        if chunk:
            result.extend(chunk)
    print("Проверка треков:", file=sys.stderr, flush=True)
    return result
