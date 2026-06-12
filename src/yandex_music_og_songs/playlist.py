from __future__ import annotations

import sys
from typing import Iterable, Optional

from yandex_music import Playlist, Track

from yandex_music_og_songs.artist_cache import ArtistLookupCache
from yandex_music_og_songs.client import YandexMusicClient
from yandex_music_og_songs.config import AppConfig
from yandex_music_og_songs.models import PlaylistScanResult, ScannedTrack, TrackRef, TrackStatus
from yandex_music_og_songs.normalizer import primary_artist
from yandex_music_og_songs.parallel import fetch_full_tracks_parallel, prefetch_title_lookups
from yandex_music_og_songs.report import print_choices_section, print_scan_header, print_scan_summary, print_track_line
from yandex_music_og_songs.scan_cache import load_scan_result, scan_cache_path
from yandex_music_og_songs.verifier import TitleLookup, lookup_cache_key, verify_track


def _track_ref_from_yandex(track: Track, album_id: Optional[int]) -> TrackRef:
    artists = [a.name for a in (track.artists or []) if a.name]
    resolved_album_id = album_id
    if resolved_album_id is None and track.albums:
        resolved_album_id = track.albums[0].id
    return TrackRef(
        track_id=str(track.id),
        album_id=str(resolved_album_id or ""),
        title=track.title or "",
        artist=primary_artist(artists),
        version=track.version,
        duration_ms=track.duration_ms,
        track_source=getattr(track, "track_source", None),
        is_user_upload=bool(track.filename or track.user_info),
    )


def load_playlist_tracks(client: YandexMusicClient, playlist: Playlist, config: AppConfig) -> PlaylistScanResult:
    shorts = client.playlist_track_shorts(playlist)
    full_tracks = fetch_full_tracks_parallel(client.token, shorts, config.performance)
    scanned: list[ScannedTrack] = []

    for index, track in enumerate(full_tracks):
        if track is None:
            continue
        album_id = shorts[index].album_id if index < len(shorts) and shorts[index] else None
        track_ref = _track_ref_from_yandex(track, album_id)
        scanned.append(
            ScannedTrack(
                index=index,
                track=track_ref,
                status=TrackStatus.ORIGINAL,
                reasons=[],
            )
        )

    return PlaylistScanResult(
        kind=playlist.kind,
        title=playlist.title or f"Playlist {playlist.kind}",
        track_count=len(scanned),
        tracks=scanned,
    )


def _can_reuse_previous(prev: ScannedTrack, track_ref: TrackRef) -> bool:
    if prev.track.title != track_ref.title or prev.track.artist != track_ref.artist:
        return False
    if prev.status == TrackStatus.ORIGINAL:
        return False
    return prev.status in {TrackStatus.FAKE, TrackStatus.CHOOSE, TrackStatus.SKIP}


def scan_playlist(
    client: YandexMusicClient,
    playlist: Playlist,
    config: AppConfig,
    *,
    artist_check: bool = True,
    stream: bool = False,
) -> PlaylistScanResult:
    shorts = client.playlist_track_shorts(playlist)
    if not shorts:
        print("Плейлист пуст.", file=sys.stderr)
        return PlaylistScanResult(
            kind=playlist.kind,
            title=playlist.title or f"Playlist {playlist.kind}",
            track_count=0,
            tracks=[],
        )

    previous_by_id: dict[str, ScannedTrack] = {}
    cache_path = scan_cache_path(playlist.kind)
    if artist_check and config.performance.reuse_scan_cache and cache_path.exists():
        previous = load_scan_result(cache_path)
        previous_by_id = {item.track.track_id: item for item in previous.tracks}

    full_tracks = fetch_full_tracks_parallel(client.token, shorts, config.performance)
    track_rows: list[tuple[int, TrackRef]] = []
    reused: dict[int, ScannedTrack] = {}

    for index, track in enumerate(full_tracks):
        if track is None:
            continue
        album_id = shorts[index].album_id if index < len(shorts) and shorts[index] else None
        track_ref = _track_ref_from_yandex(track, album_id)
        track_rows.append((index, track_ref))

        if artist_check and previous_by_id:
            prev = previous_by_id.get(track_ref.track_id)
            if prev and _can_reuse_previous(prev, track_ref):
                reused[index] = prev

    lookup_cache: dict[str, TitleLookup] = {}
    if artist_check:
        to_verify = [
            (track_ref.title, track_ref.artist)
            for index, track_ref in track_rows
            if not track_ref.is_user_upload and index not in reused
        ]
        disk_cache = ArtistLookupCache() if config.performance.artist_disk_cache else None
        lookup_cache = prefetch_title_lookups(
            client.token,
            to_verify,
            config.detection,
            config.performance,
            disk_cache=disk_cache,
        )
        if reused:
            print(f"  повторный скан: {len(reused)} из кэша", file=sys.stderr, flush=True)

    scanned: list[ScannedTrack] = []
    result_header = PlaylistScanResult(
        kind=playlist.kind,
        title=playlist.title or f"Playlist {playlist.kind}",
        track_count=0,
        tracks=[],
    )
    if stream:
        print_scan_header(result_header)

    for index, track_ref in track_rows:
        if index in reused:
            item = reused[index]
        elif not artist_check or track_ref.is_user_upload:
            item = ScannedTrack(index=index, track=track_ref, status=TrackStatus.ORIGINAL, reasons=[])
        else:
            key = lookup_cache_key(track_ref.title, config.detection)
            result = verify_track(track_ref, config.detection, lookup_cache.get(key))
            item = ScannedTrack(
                index=index,
                track=track_ref,
                status=result.status,
                reasons=result.reasons,
                artist_candidates=result.candidates,
                expected_artist=result.expected_artist,
            )

        scanned.append(item)
        if stream:
            print_track_line(item)

    result = PlaylistScanResult(
        kind=playlist.kind,
        title=playlist.title or f"Playlist {playlist.kind}",
        track_count=len(scanned),
        tracks=scanned,
    )

    if stream:
        print_scan_summary(result)
        print_choices_section(result)

    return result


def scan_playlists(
    client: YandexMusicClient,
    config: AppConfig,
    kinds: Optional[Iterable[int]] = None,
    *,
    artist_check: bool = True,
    stream: bool = False,
) -> list[PlaylistScanResult]:
    if kinds is not None:
        playlists = [client.get_playlist(kind) for kind in kinds]
    else:
        playlists = client.list_playlists()

    return [
        scan_playlist(client, playlist, config, artist_check=artist_check, stream=stream)
        for playlist in playlists
    ]
