from __future__ import annotations

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

        track_ids = [short.track_id for short in shorts if short is not None]
        fetched: list[Track] = []

        for offset in range(0, len(track_ids), _BATCH_SIZE):
            chunk = track_ids[offset : offset + _BATCH_SIZE]
            batch = self._client.tracks(chunk)
            if batch:
                fetched.extend(batch)

        by_id = {str(track.id): track for track in fetched}
        result: list[Optional[Track]] = []
        for short in shorts:
            if short is None:
                result.append(None)
                continue
            result.append(by_id.get(str(short.id)))
        return result
