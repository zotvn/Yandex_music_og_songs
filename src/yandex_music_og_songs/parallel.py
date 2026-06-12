from __future__ import annotations

import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Optional

from yandex_music import Track
from yandex_music.track_short import TrackShort

from yandex_music_og_songs.artist_cache import ArtistLookupCache
from yandex_music_og_songs.artist_resolver import (
    ArtistResolution,
    _build_candidates,
    _search_musicbrainz,
    _search_yandex,
    needs_musicbrainz,
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
_mb_calls = 0
_mb_skipped = 0


def _thread_client(token: str) -> YandexMusicClient:
    client = getattr(_thread_local, "client", None)
    if client is None:
        client = YandexMusicClient(token)
        _thread_local.client = client
    return client


def _search_musicbrainz_throttled(title: str) -> list[str]:
    global _mb_last_at, _mb_calls
    with _mb_lock:
        wait = 1.05 - (time.monotonic() - _mb_last_at)
        if wait > 0:
            time.sleep(wait)
        artists = _search_musicbrainz(title)
        _mb_last_at = time.monotonic()
        _mb_calls += 1
        return artists


def _lookup_title(
    token: str,
    title: str,
    detection: DetectionConfig,
    perf: PerformanceConfig,
    disk_cache: ArtistLookupCache | None,
) -> tuple[str, list[ArtistCandidate]]:
    global _mb_skipped
    clean_title = base_title(title, detection.title_suffix_patterns)
    key = normalize_text(clean_title)

    if disk_cache is not None:
        cached = disk_cache.get(key)
        if cached is not None:
            return key, cached

    client = _thread_client(token)
    yandex = retry_network(
        lambda: _search_yandex(client, clean_title, detection),
        label=f"поиск «{clean_title[:40]}»",
    )

    musicbrainz: list[str] = []
    if perf.musicbrainz_mode == "never":
        _mb_skipped += 1
    elif perf.musicbrainz_mode == "always" or needs_musicbrainz(yandex, always=False):
        musicbrainz = _search_musicbrainz_throttled(clean_title)
    else:
        _mb_skipped += 1

    candidates = _build_candidates(yandex, musicbrainz)
    if disk_cache is not None:
        disk_cache.put(key, candidates)
    return key, candidates


def prefetch_artist_candidates(
    token: str,
    titles: list[str],
    detection: DetectionConfig,
    perf: PerformanceConfig,
    disk_cache: ArtistLookupCache | None = None,
) -> dict[str, list[ArtistCandidate]]:
    global _mb_calls, _mb_skipped
    _mb_calls = 0
    _mb_skipped = 0

    unique = list(dict.fromkeys(titles))
    if not unique:
        return {}

    cache: dict[str, list[ArtistCandidate]] = {}
    from_disk = 0
    if disk_cache is not None:
        for title in unique:
            key = normalize_text(base_title(title, detection.title_suffix_patterns))
            cached = disk_cache.get(key)
            if cached is not None:
                cache[key] = cached
                from_disk += 1

    to_fetch = [
        title
        for title in unique
        if normalize_text(base_title(title, detection.title_suffix_patterns)) not in cache
    ]
    total = len(unique)
    done = from_disk
    done_lock = threading.Lock()

    if from_disk:
        print(f"  из кэша: {from_disk}/{total}", file=sys.stderr, flush=True)

    if to_fetch:
        print(
            f"Проверка {len(to_fetch)} песен ({perf.artist_workers} потоков, "
            f"MusicBrainz: {perf.musicbrainz_mode})...",
            file=sys.stderr,
            flush=True,
        )
        with ThreadPoolExecutor(max_workers=perf.artist_workers) as pool:
            futures = {
                pool.submit(_lookup_title, token, title, detection, perf, disk_cache): title
                for title in to_fetch
            }
            for future in as_completed(futures):
                key, candidates = future.result()
                cache[key] = candidates
                with done_lock:
                    done += 1
                    if done % 20 == 0 or done == total:
                        print(f"  артисты: {done}/{total}", file=sys.stderr, flush=True)

    if disk_cache is not None:
        disk_cache.save()

    if perf.musicbrainz_mode == "auto" and to_fetch:
        print(
            f"  MusicBrainz: { _mb_calls} запросов, пропущено {_mb_skipped} (Yandex достаточно)",
            file=sys.stderr,
            flush=True,
        )

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
