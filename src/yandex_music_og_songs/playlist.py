from __future__ import annotations

import sys
from typing import Iterable, Optional

from yandex_music import Playlist, Track

from yandex_music_og_songs.artist_cache import ArtistLookupCache
from yandex_music_og_songs.catalog import is_user_original, track_needs_metadata_check
from yandex_music_og_songs.client import YandexMusicClient
from yandex_music_og_songs.config import AppConfig
from yandex_music_og_songs.models import PlaylistScanResult, ScannedTrack, TrackRef, TrackStatus
from yandex_music_og_songs.normalizer import primary_artist
from yandex_music_og_songs.parallel import fetch_full_tracks_parallel, prefetch_truth_lookups
from yandex_music_og_songs.report import print_choices_section, print_fake_section, print_scan_header, print_scan_summary, print_track_line
from yandex_music_og_songs.verifier import lookup_cache_key, verify_track


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


def scan_playlist(
    client: YandexMusicClient,
    playlist: Playlist,
    config: AppConfig,
    *,
    artist_check: bool = True,
    stream: bool = False,
    track_from: Optional[int] = None,
    track_to: Optional[int] = None,
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

    full_tracks = fetch_full_tracks_parallel(client.token, shorts, config.performance)
    track_rows: list[tuple[int, TrackRef]] = []

    for index, track in enumerate(full_tracks):
        if track is None:
            continue
        number = index + 1
        if track_from is not None and number < track_from:
            continue
        if track_to is not None and number > track_to:
            continue
        album_id = shorts[index].album_id if index < len(shorts) and shorts[index] else None
        track_ref = _track_ref_from_yandex(track, album_id)
        track_rows.append((index, track_ref))

    if track_from or track_to:
        print(f"  диапазон: {track_from or 1}-{track_to or len(shorts)}", file=sys.stderr, flush=True)

    truth_cache: dict = {}
    if artist_check:
        titles = [track_ref.title for _, track_ref in track_rows if track_needs_metadata_check(track_ref)]
        disk_cache = ArtistLookupCache() if config.performance.artist_disk_cache else None
        truth_cache = prefetch_truth_lookups(
            titles,
            config.detection,
            config.performance,
            disk_cache=disk_cache,
        )

    scanned: list[ScannedTrack] = []
    if stream:
        print_scan_header(
            PlaylistScanResult(
                kind=playlist.kind,
                title=playlist.title or f"Playlist {playlist.kind}",
                track_count=0,
            )
        )

    for index, track_ref in track_rows:
        if not artist_check or is_user_original(track_ref):
            item = ScannedTrack(index=index, track=track_ref, status=TrackStatus.ORIGINAL, reasons=[])
        else:
            key = lookup_cache_key(track_ref.title, config.detection)
            result = verify_track(track_ref, config.detection, truth_cache.get(key), client)
            item = ScannedTrack(
                index=index,
                track=track_ref,
                status=result.status,
                reasons=result.reasons,
                artist_candidates=result.candidates,
                expected_artist=result.expected_artist,
                replace_track_id=result.replace_track_id,
                replace_album_id=result.replace_album_id,
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
        print_fake_section(result)
        print_choices_section(result)

    return result


def scan_playlists(
    client: YandexMusicClient,
    config: AppConfig,
    kinds: Optional[Iterable[int]] = None,
    *,
    artist_check: bool = True,
    stream: bool = False,
    track_from: Optional[int] = None,
    track_to: Optional[int] = None,
) -> list[PlaylistScanResult]:
    if kinds is not None:
        playlists = [client.get_playlist(kind) for kind in kinds]
    else:
        playlists = client.list_playlists()

    return [
        scan_playlist(
            client,
            playlist,
            config,
            artist_check=artist_check,
            stream=stream,
            track_from=track_from,
            track_to=track_to,
        )
        for playlist in playlists
    ]
