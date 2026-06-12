from unittest.mock import MagicMock

from yandex_music_og_songs.config import AppConfig
from yandex_music_og_songs.models import TrackStatus
from yandex_music_og_songs.playlist import scan_playlist


def test_scan_playlist_marks_fake_and_original():
    playlist = MagicMock()
    playlist.kind = 42
    playlist.title = "Test Playlist"
    playlist.tracks = [MagicMock(album_id=100)]

    fake_track = MagicMock()
    fake_track.id = 1
    fake_track.title = "Song (Cover)"
    fake_track.version = None
    fake_track.artists = [MagicMock(name="Artist A")]
    fake_track.albums = [MagicMock(id=100)]
    fake_track.duration_ms = 200000
    fake_track.track_source = None
    fake_track.filename = None
    fake_track.user_info = None

    original_track = MagicMock()
    original_track.id = 2
    original_track.title = "Real Song"
    original_track.version = None
    original_track.artists = [MagicMock(name="Artist B")]
    original_track.albums = [MagicMock(id=101)]
    original_track.duration_ms = 210000
    original_track.track_source = "OWN"
    original_track.filename = None
    original_track.user_info = None

    playlist.tracks.append(MagicMock(album_id=101))

    client = MagicMock()
    client.fetch_playlist_tracks.return_value = [fake_track, original_track]

    result = scan_playlist(client, playlist, AppConfig())

    assert result.kind == 42
    assert result.track_count == 2
    assert result.fake_count == 1
    assert result.original_count == 1
    assert result.tracks[0].status == TrackStatus.FAKE
    assert result.tracks[1].status == TrackStatus.ORIGINAL
