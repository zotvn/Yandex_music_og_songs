from unittest.mock import patch

from yandex_music_og_songs.artist_resolver import _build_candidates, artist_matches, resolve_with_candidates
from yandex_music_og_songs.config import DetectionConfig
from yandex_music_og_songs.models import ArtistCandidate, TrackRef, TrackStatus


def test_build_candidates_mb_priority():
    candidates = _build_candidates(["Adele"], [("Adele", None)])
    assert candidates[0].artist == "Adele"
    assert "musicbrainz" in candidates[0].sources
    assert candidates[0].score >= 1.0


def test_artist_matches_exact():
    assert artist_matches("Adele", "adele", 0.75)


def test_adelaide_not_equivalent_to_adele():
    from yandex_music_og_songs.artist_resolver import artists_equivalent

    assert not artists_equivalent("Adelaide", "Adele", 0.88)


def test_resolve_wrong_artist():
    track = TrackRef("1", "2", "Skyfall", "Random Cover Band")
    candidates = [ArtistCandidate("Adele", ("musicbrainz",), 1.0)]
    resolution = resolve_with_candidates(track, candidates, 0.75, 0.88)
    assert resolution.status == TrackStatus.FAKE
    assert "wrong_artist:Adele" in resolution.reasons


def test_youtube_only_does_not_fake():
    track = TrackRef("1", "2", "death bed", "Powfu")
    candidates = [ArtistCandidate("Garbage", ("youtube",), 0.8)]
    resolution = resolve_with_candidates(track, candidates, 0.75, 0.88)
    assert resolution.status == TrackStatus.ORIGINAL


def test_lookup_truth_calls_mb():
    with patch("yandex_music_og_songs.artist_resolver._search_musicbrainz", return_value=["Adele"]):
        with patch("yandex_music_og_songs.artist_resolver.search_youtube_music", return_value=[]):
            from yandex_music_og_songs.artist_resolver import lookup_truth

            result = lookup_truth("Skyfall", DetectionConfig())
    assert result.candidates[0].artist == "Adele"
