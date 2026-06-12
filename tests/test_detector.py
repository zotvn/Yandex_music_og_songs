from yandex_music_og_songs.config import DetectionConfig
from yandex_music_og_songs.detector import detect_track
from yandex_music_og_songs.models import TrackRef, TrackStatus


def _track(**kwargs) -> TrackRef:
    defaults = {
        "track_id": "1",
        "album_id": "2",
        "title": "Song",
        "artist": "Artist",
    }
    defaults.update(kwargs)
    return TrackRef(**defaults)


def test_detects_radio_edit_version():
    track = _track(version="Radio Edit")
    status, reasons = detect_track(track, DetectionConfig())
    assert status == TrackStatus.FAKE
    assert any("version" in reason for reason in reasons)


def test_keeps_remix_by_default():
    track = _track(version="Extended Remix")
    status, reasons = detect_track(track, DetectionConfig())
    assert status == TrackStatus.ORIGINAL
    assert reasons == []


def test_detects_user_upload():
    track = _track(is_user_upload=True)
    status, reasons = detect_track(track, DetectionConfig())
    assert status == TrackStatus.FAKE
    assert "user_upload" in reasons


def test_detects_title_suffix():
    track = _track(title="Song (Cover)")
    status, reasons = detect_track(track, DetectionConfig())
    assert status == TrackStatus.FAKE
    assert any("title_suffix" in reason for reason in reasons)
