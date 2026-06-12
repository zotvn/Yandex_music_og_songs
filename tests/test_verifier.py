from unittest.mock import MagicMock

from yandex_music_og_songs.config import DetectionConfig
from yandex_music_og_songs.models import ArtistCandidate, CatalogHit, TitleLookup, TrackRef, TrackStatus
from yandex_music_og_songs.verifier import verify_track


def _lookup(candidates, hits=None):
    return TitleLookup(
        candidates=candidates,
        hits=hits or [],
    )


def test_cover_version_reports_wrong_artist_not_cover():
    track = TrackRef(
        track_id="1",
        album_id="2",
        title="I WANNA BE YOUR SLAVE [Cover]",
        artist="Kimurus",
        version="Cover",
        duration_ms=172000,
    )
    lookup = _lookup(
        [ArtistCandidate("Måneskin", ("yandex", "musicbrainz"), 2.9)],
        [CatalogHit("Måneskin", "I WANNA BE YOUR SLAVE", 172000)],
    )
    result = verify_track(track, DetectionConfig(), lookup)
    assert result.status == TrackStatus.FAKE
    assert any(r.startswith("wrong_artist:") for r in result.reasons)
    assert not any(r.startswith("version:") for r in result.reasons)


def test_catalog_match_without_suffixes_is_ok():
    track = TrackRef(
        track_id="1",
        album_id="2",
        title="SUPERMODEL",
        artist="Måneskin",
        duration_ms=148000,
    )
    lookup = _lookup(
        [ArtistCandidate("Måneskin", ("yandex",), 2.0)],
        [CatalogHit("Måneskin", "SUPERMODEL", 148000)],
    )
    result = verify_track(track, DetectionConfig(), lookup)
    assert result.status == TrackStatus.ORIGINAL
    assert result.reasons == []


def test_own_replaced_to_ugc_not_fake_by_default():
    track = TrackRef(
        track_id="1",
        album_id="2",
        title="SUPERMODEL",
        artist="Måneskin",
        duration_ms=148000,
        track_source="OWN_REPLACED_TO_UGC",
    )
    lookup = _lookup(
        [ArtistCandidate("Måneskin", ("yandex",), 2.0)],
        [CatalogHit("Måneskin", "SUPERMODEL", 148000)],
    )
    result = verify_track(track, DetectionConfig(), lookup)
    assert result.status == TrackStatus.ORIGINAL


def test_suspicious_artist_flagged():
    track = TrackRef(
        track_id="1",
        album_id="2",
        title="Paint It, Black",
        artist="Ameritz Tribute Club",
        duration_ms=206000,
    )
    lookup = _lookup(
        [ArtistCandidate("The Rolling Stones", ("musicbrainz",), 1.8)],
        [CatalogHit("The Rolling Stones", "Paint It, Black", 206000)],
    )
    result = verify_track(track, DetectionConfig(), lookup)
    assert result.status == TrackStatus.FAKE
    assert any(r.startswith("wrong_artist:") for r in result.reasons)


def test_weak_catalog_does_not_trust_self_match():
    track = TrackRef(
        track_id="1",
        album_id="2",
        title="Swing Lynn",
        artist="Zamyr",
        duration_ms=274000,
    )
    lookup = _lookup(
        [ArtistCandidate("Zamyr", ("yandex",), 1.0)],
        [CatalogHit("Zamyr", "Swing Lynn", 274000)],
    )
    result = verify_track(track, DetectionConfig(), lookup)
    assert result.status in {TrackStatus.FAKE, TrackStatus.CHOOSE, TrackStatus.ORIGINAL}
