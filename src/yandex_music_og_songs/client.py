from __future__ import annotations

from typing import Optional

from yandex_music import Client
from yandex_music import Playlist

from yandex_music_og_songs.config import AppConfig


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

    def fetch_playlist_tracks(self, playlist: Playlist):
        tracks = playlist.fetch_tracks()
        if tracks is None:
            return []
        return tracks
