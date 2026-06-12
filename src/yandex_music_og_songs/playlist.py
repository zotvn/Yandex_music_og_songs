from __future__ import annotations

import sys
from typing import Iterable, Optional

from yandex_music import Playlist, Track

from yandex_music_og_songs.client import YandexMusicClient
from yandex_music_og_songs.config import AppConfig
from yandex_music_og_songs.detector import detect_track
from yandex_music_og_songs.models import PlaylistScanResult, ScannedTrack, TrackRef
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


def select_playlists(client: YandexMusicClient, config: AppConfig) -> list[Playlist]:
    all_playlists = client.list_playlists()
    cfg = config.playlists

    if cfg.mode == "all":
        selected = all_playlists
    elif cfg.mode == "selected":
        kinds = set(cfg.kinds)
        selected = [p for p in all_playlists if p.kind in kinds]
    else:
        excluded = set(cfg.exclude_kinds)
        selected = [p for p in all_playlists if p.kind not in excluded]

    return selected


def scan_playlist(
    client: YandexMusicClient,
    playlist: Playlist,
    config: AppConfig,
) -> PlaylistScanResult:
    shorts = client.playlist_track_shorts(playlist)
    if shorts:
        print(f"Загрузка {len(shorts)} треков...", file=sys.stderr)
    full_tracks = client.fetch_full_tracks(shorts)
    scanned: list[ScannedTrack] = []

    for index, track in enumerate(full_tracks):
        if track is None:
            continue

        album_id = None
        if index < len(shorts) and shorts[index] is not None:
            album_id = shorts[index].album_id

        track_ref = _track_ref_from_yandex(track, album_id)
        status, reasons = detect_track(track_ref, config.detection)
        scanned.append(
            ScannedTrack(
                index=index,
                track=track_ref,
                status=status,
                reasons=reasons,
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
) -> list[PlaylistScanResult]:
    if kinds is not None:
        playlists = [client.get_playlist(kind) for kind in kinds]
    else:
        playlists = select_playlists(client, config)

    return [scan_playlist(client, playlist, config) for playlist in playlists]
