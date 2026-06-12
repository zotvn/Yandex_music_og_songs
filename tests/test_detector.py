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


def test_detects_radio_edit_in_brackets_as_choose():
    track = _track(title="Song (Radio Edit)")
    status, reasons = detect_track(track, DetectionConfig())
    assert status == TrackStatus.CHOOSE
    assert any(reason.startswith("pick_version") for reason in reasons)


def test_detects_slowed_in_brackets_as_choose():
    track = _track(title="Song [Slowed + Reverb]")
    status, reasons = detect_track(track, DetectionConfig())
    assert status == TrackStatus.CHOOSE


def test_detects_trailing_radio_edit_as_choose():
    track = _track(title="Song - Radio Edit")
    status, reasons = detect_track(track, DetectionConfig())
    assert status == TrackStatus.CHOOSE


def test_detects_radio_edit_remix_combo():
    track = _track(version="Radio Edit Remix")
    status, reasons = detect_track(track, DetectionConfig())
    assert status == TrackStatus.FAKE


def test_keeps_remix_by_default():
    track = _track(version="Extended Remix")
    status, reasons = detect_track(track, DetectionConfig())
    assert status == TrackStatus.ORIGINAL
    assert reasons == []


def test_keeps_soundtrack_version():
    track = _track(version="from the series Arcane League of Legends")
    status, reasons = detect_track(track, DetectionConfig())
    assert status == TrackStatus.ORIGINAL


def test_user_upload_not_fake_by_default():
    track = _track(is_user_upload=True)
    status, reasons = detect_track(track, DetectionConfig())
    assert status == TrackStatus.ORIGINAL
    assert reasons == []


def test_user_upload_fake_when_enabled():
    config = DetectionConfig(treat_ugc_as_fake=True)
    track = _track(is_user_upload=True)
    status, reasons = detect_track(track, config)
    assert status == TrackStatus.FAKE
    assert "user_upload" in reasons


def test_detects_title_cover_as_fake():
    track = _track(title="Song (Cover)")
    status, reasons = detect_track(track, DetectionConfig())
    assert status == TrackStatus.FAKE
    assert any("title_fake" in reason for reason in reasons)
