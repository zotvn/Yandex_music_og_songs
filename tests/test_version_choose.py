from yandex_music_og_songs.choices_io import UserChoice, apply_choices
from yandex_music_og_songs.models import PlaylistScanResult, ScannedTrack, TrackRef, TrackStatus


def _version_choose_track() -> ScannedTrack:
    return ScannedTrack(
        index=4,
        track=TrackRef("1", "2", "Song (Radio Edit)", "Artist"),
        status=TrackStatus.CHOOSE,
        reasons=["pick_version:radio\\s*[-_]?\\s*edit"],
    )


def test_version_choose_skip_leaves_track():
    result = PlaylistScanResult(kind=1, title="t", track_count=1, tracks=[_version_choose_track()])
    updated = apply_choices(result, [UserChoice(track_number=5, value="skip")])
    assert updated.tracks[0].status == TrackStatus.SKIP


def test_version_choose_replace_marks_fake():
    result = PlaylistScanResult(kind=1, title="t", track_count=1, tracks=[_version_choose_track()])
    updated = apply_choices(result, [UserChoice(track_number=5, value="replace")])
    assert updated.tracks[0].status == TrackStatus.FAKE
    assert "replace_version_by_user" in updated.tracks[0].reasons
