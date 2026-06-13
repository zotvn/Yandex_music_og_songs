from yandex_music_og_songs.choices_io import UserChoice, apply_choices
from yandex_music_og_songs.models import PlaylistScanResult, ScannedTrack, TrackRef, TrackStatus


def test_fake_skip_marks_skip():
    result = PlaylistScanResult(
        kind=1,
        title="t",
        track_count=1,
        tracks=[
            ScannedTrack(
                index=3,
                track=TrackRef("1", "2", "Song", "Artist", version="Cover"),
                status=TrackStatus.FAKE,
                reasons=["version:field"],
                replace_track_id="99",
                replace_album_id="88",
            )
        ],
    )
    updated = apply_choices(result, [UserChoice(track_number=4, value="skip")])
    assert updated.tracks[0].status == TrackStatus.SKIP
