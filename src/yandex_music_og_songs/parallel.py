from __future__ import annotations

import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Optional

from yandex_music import Track
from yandex_music.track_short import TrackShort

from yandex_music_og_songs.artist_cache import ArtistLookupCache
from yandex_music_og_songs.artist_resolver import lookup_truth
from yandex_music_og_songs.client import YandexMusicClient
from yandex_music_og_songs.config import DetectionConfig, PerformanceConfig
from yandex_music_og_songs.models import TitleLookup
from yandex_music_og_songs.network import retry_network
from yandex_music_og_songs.normalizer import base_title
from yandex_music_og_songs.verifier import lookup_cache_key

_thread_local = threading.local()
_mb_lock = threading.Lock()
_mb_last_at = 0.0
_mb_calls = 0


def _lookup_truth_throttled(title: str, detection: DetectionConfig) -> tuple[str, TitleLookup]:
    global _mb_last_at, _mb_calls
    key = lookup_cache_key(title, detection)
    clean = base_title(title, detection.title_suffix_patterns)

    with _mb_lock:
        wait = 1.05 - (time.monotonic() - _mb_last_at)
        if wait > 0:
            time.sleep(wait)

    lookup = retry_network(lambda: lookup_truth(clean, detection), label=f"истина «{clean[:40]}»")

    with _mb_lock:
        _mb_last_at = time.monotonic()
        _mb_calls += 1

    return key, lookup


def prefetch_truth_lookups(
    titles: list[str],
    detection: DetectionConfig,
    perf: PerformanceConfig,
    disk_cache: ArtistLookupCache | None = None,
) -> dict[str, TitleLookup]:
    global _mb_calls
    _mb_calls = 0

    unique = list(dict.fromkeys(titles))
    if not unique:
        return {}

    cache: dict[str, TitleLookup] = {}
    from_disk = 0
    if disk_cache is not None:
        for title in unique:
            key = lookup_cache_key(title, detection)
            cached = disk_cache.get(key)
            if cached is not None:
                cache[key] = cached
                from_disk += 1

    to_fetch = [title for title in unique if lookup_cache_key(title, detection) not in cache]
    total = len(unique)
    done = from_disk
    done_lock = threading.Lock()

    if from_disk:
        print(f"  из кэша: {from_disk}/{total}", file=sys.stderr, flush=True)

    if to_fetch:
        print(
            f"Поиск автора: {len(to_fetch)} песен ({perf.artist_workers} потоков, MB+YouTube)...",
            file=sys.stderr,
            flush=True,
        )
        with ThreadPoolExecutor(max_workers=perf.artist_workers) as pool:
            futures = {pool.submit(_lookup_truth_throttled, title, detection): title for title in to_fetch}
            for future in as_completed(futures):
                key, lookup = future.result()
                cache[key] = lookup
                if disk_cache is not None:
                    disk_cache.put(key, lookup)
                with done_lock:
                    done += 1
                    if done % 10 == 0 or done == total:
                        print(f"  артисты: {done}/{total}", file=sys.stderr, flush=True)

    if disk_cache is not None:
        disk_cache.save()

    if to_fetch:
        print(f"  MusicBrainz запросов: {_mb_calls}", file=sys.stderr, flush=True)

    return cache


def _fetch_chunk(token: str, chunk_shorts: list[TrackShort]) -> list[Optional[Track]]:
    client = getattr(_thread_local, "client", None)
    if client is None:
        client = YandexMusicClient(token)
        _thread_local.client = client

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
