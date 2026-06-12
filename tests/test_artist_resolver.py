from unittest.mock import MagicMock, patch

from yandex_music_og_songs.artist_resolver import _build_candidates, resolve_track_artist
from yandex_music_og_songs.config import DetectionConfig
from yandex_music_og_songs.models import TrackRef, TrackStatus


def test_build_candidates_merges_sources():
    candidates = _build_candidates(["sombr", "TommyMuzzic"], ["Sombr", "Other"])
    assert candidates[0].artist in {"sombr", "Sombr"}
    assert "yandex" in candidates[0].sources
    assert len(candidates) >= 2


def test_resolve_wrong_artist_when_single_candidate():
    track = TrackRef(
        track_id="1",
        album_id="2",
        title="back to friends",
        artist="TommyMuzzic",
    )
    client = MagicMock()
    with patch(
        "yandex_music_og_songs.artist_resolver.lookup_artists",
        return_value=[MagicMock(artist="sombr", sources=("yandex",), score=2.0)],
    ):
        resolution = resolve_track_artist(client, track, DetectionConfig(), {})
    assert resolution.status == TrackStatus.FAKE
    assert "wrong_artist:sombr" in resolution.reasons


def test_resolve_ambiguous_when_close_scores():
    track = TrackRef(track_id="1", album_id="2", title="Song", artist="Unknown")
    client = MagicMock()
    with patch(
        "yandex_music_og_songs.artist_resolver.lookup_artists",
        return_value=[
            MagicMock(artist="Artist A", sources=("yandex",), score=1.0),
            MagicMock(artist="Artist B", sources=("musicbrainz",), score=0.95),
        ],
    ):
        resolution = resolve_track_artist(client, track, DetectionConfig(), {})
    assert resolution.status == TrackStatus.CHOOSE
