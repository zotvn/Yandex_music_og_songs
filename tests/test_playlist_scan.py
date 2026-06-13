from unittest.mock import MagicMock, patch

from yandex_music_og_songs.config import AppConfig
from yandex_music_og_songs.models import TrackStatus
from yandex_music_og_songs.playlist import scan_playlist


def _make_track(**kwargs):
    track = MagicMock()
    track.id = kwargs.get("id", 1)
    track.title = kwargs.get("title", "Song")
    track.version = kwargs.get("version")
    artist = MagicMock()
    artist.name = kwargs.get("artist", "Artist")
    track.artists = [artist]
    track.albums = [MagicMock(id=kwargs.get("album_id", 100))]
    track.duration_ms = kwargs.get("duration_ms", 200000)
    track.track_source = kwargs.get("track_source")
    track.filename = kwargs.get("filename")
    track.user_info = kwargs.get("user_info")
    return track


def test_scan_playlist_marks_cover_fake():
    playlist = MagicMock()
    playlist.kind = 42
    playlist.title = "Test Playlist"
    playlist.tracks = [MagicMock(album_id=100), MagicMock(album_id=101)]

    fake_track = _make_track(id=1, title="Song (Cover)")
    original_track = _make_track(id=2, title="Real Song", artist="Artist B", album_id=101)

    client = MagicMock()
    client.token = "test-token"
    client.playlist_track_shorts.return_value = playlist.tracks

    with patch(
        "yandex_music_og_songs.playlist.fetch_full_tracks_parallel",
        return_value=[fake_track, original_track],
    ), patch(
        "yandex_music_og_songs.playlist.prefetch_truth_lookups",
        return_value={},
    ), patch(
        "yandex_music_og_songs.verifier.find_clean_yandex_match",
        return_value=None,
    ):
        result = scan_playlist(client, playlist, AppConfig(), artist_check=True)

    assert result.tracks[0].status == TrackStatus.FAKE
    assert result.tracks[1].status == TrackStatus.ORIGINAL
