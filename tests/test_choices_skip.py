from yandex_music_og_songs.choices_io import UserChoice, apply_choices
from yandex_music_og_songs.models import PlaylistScanResult, ScannedTrack, TrackRef, TrackStatus


def test_apply_skip_marks_track():
    result = PlaylistScanResult(
        kind=1,
        title="t",
        track_count=1,
        tracks=[
            ScannedTrack(
                index=0,
                track=TrackRef("1", "2", "Song", "Artist"),
                status=TrackStatus.FAKE,
                reasons=["wrong_artist:x"],
            )
        ],
    )
    updated = apply_choices(result, [UserChoice(track_number=1, value="skip")])
    assert updated.tracks[0].status == TrackStatus.SKIP
