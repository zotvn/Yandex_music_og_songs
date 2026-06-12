from __future__ import annotations

import sys
from typing import Optional

from yandex_music import Client, Playlist, Track
from yandex_music.track_short import TrackShort

from yandex_music_og_songs.config import AppConfig

_BATCH_SIZE = 100


class YandexMusicClient:
    def __init__(self, token: str):
        self._client = Client(token).init()

    @classmethod
    def from_config(cls, config: AppConfig, token_override: Optional[str] = None) -> "YandexMusicClient":
        return cls(config.get_token(token_override))

    @property
    def raw(self) -> Client:
        return self._client

    def list_playlists(self) -> list[Playlist]:
        playlists = self._client.users_playlists_list()
        return playlists or []

    def get_playlist(self, kind: int) -> Playlist:
        playlist = self._client.users_playlists(kind)
        if playlist is None:
            raise ValueError(f"Playlist kind={kind} not found")
        return playlist

    def playlist_track_shorts(self, playlist: Playlist) -> list[TrackShort]:
        shorts = playlist.tracks
        if shorts is None:
            shorts = playlist.fetch_tracks()
        return shorts or []

    def fetch_full_tracks(self, shorts: list[TrackShort]) -> list[Optional[Track]]:
        if not shorts:
            return []

        result: list[Optional[Track]] = []
        total_batches = (len(shorts) + _BATCH_SIZE - 1) // _BATCH_SIZE

        for batch_index, offset in enumerate(range(0, len(shorts), _BATCH_SIZE)):
            chunk_shorts = shorts[offset : offset + _BATCH_SIZE]
            chunk_ids = [short.track_id for short in chunk_shorts if short is not None]
            print(
                f"Загрузка треков {offset + 1}-{offset + len(chunk_shorts)} / {len(shorts)} "
                f"(пакет {batch_index + 1}/{total_batches})...",
                file=sys.stderr,
            )
            batch = self._client.tracks(chunk_ids) if chunk_ids else []
            batch = batch or []
            batch_iter = iter(batch)
            for short in chunk_shorts:
                if short is None:
                    result.append(None)
                    continue
                result.append(next(batch_iter, None))
        return result
