from __future__ import annotations

import sys
from typing import Iterable, Optional

from yandex_music import Playlist, Track

from yandex_music_og_songs.artist_resolver import ArtistResolution
from yandex_music_og_songs.client import YandexMusicClient
from yandex_music_og_songs.config import AppConfig
from yandex_music_og_songs.detector import detect_track
from yandex_music_og_songs.models import PlaylistScanResult, ScannedTrack, TrackRef, TrackStatus
from yandex_music_og_songs.normalizer import normalize_text, primary_artist
from yandex_music_og_songs.parallel import (
    fetch_full_tracks_parallel,
    prefetch_artist_candidates,
    resolve_from_cache,
)
from yandex_music_og_songs.report import print_choices_section, print_scan_header, print_scan_summary, print_track_line


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


def _resolution_cache_key(track: TrackRef) -> str:
    return f"{normalize_text(track.title)}|{normalize_text(track.artist)}"


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

    full_tracks = fetch_full_tracks_parallel(client.token, shorts, config.performance)
    detected: list[tuple[int, TrackRef, TrackStatus, list[str]]] = []

    for index, track in enumerate(full_tracks):
        if track is None:
            continue
        album_id = shorts[index].album_id if index < len(shorts) and shorts[index] else None
        track_ref = _track_ref_from_yandex(track, album_id)
        status, reasons = detect_track(track_ref, config.detection)
        detected.append((index, track_ref, status, list(reasons)))

    artist_cache: dict[str, list] = {}
    if artist_check:
        titles_to_check = [
            track_ref.title
            for _, track_ref, status, _ in detected
            if status == TrackStatus.ORIGINAL and not track_ref.is_user_upload
        ]
        artist_cache = prefetch_artist_candidates(
            client.token,
            titles_to_check,
            config.detection,
            config.performance,
        )

    scanned: list[ScannedTrack] = []
    resolution_cache: dict[str, ArtistResolution] = {}

    result_header = PlaylistScanResult(
        kind=playlist.kind,
        title=playlist.title or f"Playlist {playlist.kind}",
        track_count=0,
        tracks=[],
    )
    if stream:
        print_scan_header(result_header)

    for index, track_ref, status, reasons in detected:
        candidates = []
        expected = None

        if status == TrackStatus.ORIGINAL and artist_check:
            cache_key = _resolution_cache_key(track_ref)
            if cache_key in resolution_cache:
                resolution = resolution_cache[cache_key]
            else:
                resolution = resolve_from_cache(track_ref, config.detection, artist_cache)
                resolution_cache[cache_key] = resolution
            status = resolution.status
            reasons.extend(resolution.reasons)
            candidates = resolution.candidates
            expected = resolution.expected_artist

        item = ScannedTrack(
            index=index,
            track=track_ref,
            status=status,
            reasons=reasons,
            artist_candidates=candidates,
            expected_artist=expected,
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
