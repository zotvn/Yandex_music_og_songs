from unittest.mock import MagicMock

from yandex_music_og_songs.config import DetectionConfig
from yandex_music_og_songs.models import ArtistCandidate, TitleLookup, TrackRef, TrackStatus
from yandex_music_og_songs.verifier import needs_artist_lookup, verify_track


def test_clean_track_skips_artist_lookup():
    track = TrackRef("1", "2", "death bed", "Powfu", duration_ms=173000)
    assert not needs_artist_lookup(track, [], DetectionConfig())


def test_clean_artist_ok_without_mb():
    track = TrackRef("1", "2", "death bed (coffee for your head)", "Powfu", duration_ms=173000)
    truth = TitleLookup(
        [ArtistCandidate("Fusion 10015", ("yandex",), 1.0)]  # garbage, ignored path
    )
    client = MagicMock()
    result = verify_track(track, DetectionConfig(), truth, client)
    assert result.status == TrackStatus.ORIGINAL
    client.raw.search.assert_not_called()


def test_cover_still_fake():
    track = TrackRef("1", "2", "Song (Cover)", "Kimurus", version="Cover")
    truth = TitleLookup([ArtistCandidate("Måneskin", ("musicbrainz",), 1.0)])
    client = MagicMock()
    client.raw.search.return_value = None
    result = verify_track(track, DetectionConfig(), truth, client)
    assert result.status == TrackStatus.FAKE
