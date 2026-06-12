from unittest.mock import MagicMock, patch

from yandex_music_og_songs.artist_resolver import (
    _build_candidates,
    lookup_artists,
    needs_musicbrainz,
    resolve_track_artist,
    yandex_is_conclusive,
)
from yandex_music_og_songs.config import DetectionConfig
from yandex_music_og_songs.models import CatalogHit, TrackRef, TrackStatus


def test_build_candidates_merges_sources():
    candidates = _build_candidates(["sombr", "TommyMuzzic"], ["Sombr", "Other"])
    assert candidates[0].artist in {"sombr", "Sombr"}
    assert "yandex" in candidates[0].sources
    assert len(candidates) >= 2


def test_yandex_conclusive_when_unanimous():
    assert yandex_is_conclusive(["sombr", "sombr", "Sombr"]) is True
    assert yandex_is_conclusive(["A", "B"]) is False
    assert yandex_is_conclusive([]) is False


def test_needs_musicbrainz_when_catalog_signal_weak():
    detection = DetectionConfig()
    hits = [CatalogHit("Zamyr", "Swing Lynn", 1000)]
    assert needs_musicbrainz(["Zamyr"], hits, "Swing Lynn", detection=detection) is True


def test_lookup_skips_musicbrainz_when_conclusive():
    client = MagicMock()
    hits = [
        CatalogHit("sombr", "back to friends", 1000),
        CatalogHit("sombr", "back to friends", 1000),
    ]
    with patch("yandex_music_og_songs.artist_resolver.search_catalog", return_value=hits):
        with patch("yandex_music_og_songs.artist_resolver._search_musicbrainz") as mb:
            lookup_artists(client, "back to friends", DetectionConfig(), {}, track_artist="sombr")
    mb.assert_not_called()


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
