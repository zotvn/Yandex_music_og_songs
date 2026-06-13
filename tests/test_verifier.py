from unittest.mock import MagicMock

from yandex_music_og_songs.catalog import duration_matches, is_user_original
from yandex_music_og_songs.config import DetectionConfig
from yandex_music_og_songs.models import ArtistCandidate, CatalogHit, TitleLookup, TrackRef, TrackStatus
from yandex_music_og_songs.verifier import verify_track


def test_user_upload_is_ok():
    track = TrackRef("1", "2", "Song", "Artist", is_user_upload=True)
    client = MagicMock()
    result = verify_track(track, DetectionConfig(), TitleLookup([]), client)
    assert result.status == TrackStatus.ORIGINAL


def test_own_replaced_to_ugc_is_ok():
    track = TrackRef("1", "2", "Song", "Artist", track_source="OWN_REPLACED_TO_UGC")
    client = MagicMock()
    result = verify_track(track, DetectionConfig(), TitleLookup([]), client)
    assert result.status == TrackStatus.ORIGINAL


def test_version_field_marks_fake_even_if_artist_matches():
    track = TrackRef("1", "2", "Song", "Adele", version="Radio Edit", duration_ms=220000)
    truth = TitleLookup([ArtistCandidate("Adele", ("musicbrainz",), 1.0)])
    client = MagicMock()
    client.raw.search.return_value = None
    result = verify_track(track, DetectionConfig(), truth, client)
    assert result.status == TrackStatus.FAKE
    assert any("version" in r for r in result.reasons)


def test_wrong_artist_marks_fake():
    track = TrackRef("1", "2", "Skyfall", "Adelaide", duration_ms=280000)
    truth = TitleLookup([ArtistCandidate("Adele", ("musicbrainz",), 1.0)])
    client = MagicMock()
    client.raw.search.return_value = None
    result = verify_track(track, DetectionConfig(), truth, client)
    assert result.status == TrackStatus.FAKE
    assert any(r.startswith("wrong_artist:") for r in result.reasons)


def test_duration_matches_ratio_or_tolerance():
    cfg = DetectionConfig()
    assert duration_matches(200000, 180000, min_ratio=cfg.duration_min_ratio, tolerance_ms=cfg.duration_tolerance_ms)
    assert duration_matches(200000, 199000, min_ratio=cfg.duration_min_ratio, tolerance_ms=cfg.duration_tolerance_ms)
    assert not duration_matches(200000, 100000, min_ratio=cfg.duration_min_ratio, tolerance_ms=cfg.duration_tolerance_ms)
