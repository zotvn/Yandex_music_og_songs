from yandex_music_og_songs.config import DetectionConfig
from yandex_music_og_songs.detector import detect_track
from yandex_music_og_songs.models import TrackRef, TrackStatus


def _track(**kwargs) -> TrackRef:
    defaults = {"track_id": "1", "album_id": "2", "title": "Song", "artist": "Artist"}
    defaults.update(kwargs)
    return TrackRef(**defaults)


def test_any_version_field_is_fake():
    track = _track(version="Remix")
    status, reasons = detect_track(track, DetectionConfig())
    assert status == TrackStatus.FAKE
    assert "version:field" in reasons


def test_live_in_brackets_is_fake():
    track = _track(title="Song [Live]")
    status, reasons = detect_track(track, DetectionConfig())
    assert status == TrackStatus.FAKE


def test_tiktok_version_is_fake():
    track = _track(title="Song [TikTok Version]")
    status, _ = detect_track(track, DetectionConfig())
    assert status == TrackStatus.FAKE


def test_cover_in_brackets_is_fake():
    track = _track(title="Song (Cover)")
    status, reasons = detect_track(track, DetectionConfig())
    assert status == TrackStatus.FAKE
    assert any("title_tag" in r for r in reasons)


def test_clean_track_is_original():
    track = _track(title="Skyfall", artist="Adele")
    status, reasons = detect_track(track, DetectionConfig())
    assert status == TrackStatus.ORIGINAL
    assert reasons == []


def test_version_word_in_title_is_fake():
    track = _track(title="Song (Studio Version)")
    status, reasons = detect_track(track, DetectionConfig())
    assert status == TrackStatus.FAKE
