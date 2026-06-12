from __future__ import annotations

import sys
from typing import Iterable, Optional

from yandex_music import Playlist, Track

from yandex_music_og_songs.artist_resolver import resolve_track_artist
from yandex_music_og_songs.client import YandexMusicClient
from yandex_music_og_songs.config import AppConfig
from yandex_music_og_songs.detector import detect_track
from yandex_music_og_songs.models import PlaylistScanResult, ScannedTrack, TrackRef, TrackStatus
from yandex_music_og_songs.normalizer import primary_artist


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


def load_playlist_tracks(client: YandexMusicClient, playlist: Playlist) -> PlaylistScanResult:
    shorts = client.playlist_track_shorts(playlist)
    full_tracks = client.fetch_full_tracks(shorts)
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

    full_tracks = client.fetch_full_tracks(shorts)
    scanned: list[ScannedTrack] = []
    artist_cache: dict[str, list] = {}
    unique_titles: set[str] = set()

    for index, track in enumerate(full_tracks):
        if track is None:
            continue

        album_id = shorts[index].album_id if index < len(shorts) and shorts[index] else None
        track_ref = _track_ref_from_yandex(track, album_id)
        status, reasons = detect_track(track_ref, config.detection)
        candidates = []
        expected = None

        if status == TrackStatus.ORIGINAL and artist_check:
            title_key = track_ref.title.casefold()
            if title_key not in unique_titles:
                unique_titles.add(title_key)
                print(
                    f"Проверка исполнителя {len(unique_titles)}: {track_ref.artist} - {track_ref.title}",
                    file=sys.stderr,
                )
            resolution = resolve_track_artist(
                client,
                track_ref,
                config.detection,
                artist_cache,
                config.detection.artist_check_rate_limit,
            )
            status = resolution.status
            reasons.extend(resolution.reasons)
            candidates = resolution.candidates
            expected = resolution.expected_artist

        scanned.append(
            ScannedTrack(
                index=index,
                track=track_ref,
                status=status,
                reasons=reasons,
                artist_candidates=candidates,
                expected_artist=expected,
            )
        )

    return PlaylistScanResult(
        kind=playlist.kind,
        title=playlist.title or f"Playlist {playlist.kind}",
        track_count=len(scanned),
        tracks=scanned,
    )


def scan_playlists(
    client: YandexMusicClient,
    config: AppConfig,
    kinds: Optional[Iterable[int]] = None,
    *,
    artist_check: bool = True,
) -> list[PlaylistScanResult]:
    if kinds is not None:
        playlists = [client.get_playlist(kind) for kind in kinds]
    else:
        playlists = client.list_playlists()

    return [
        scan_playlist(client, playlist, config, artist_check=artist_check)
        for playlist in playlists
    ]
