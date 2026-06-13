from yandex_music_og_songs.choices_io import UserChoice, apply_choices
from yandex_music_og_songs.models import PlaylistScanResult, ScannedTrack, TrackRef, TrackStatus


def test_fake_defaults_to_skip_without_replace():
    result = PlaylistScanResult(
        kind=1,
        title="t",
        track_count=2,
        tracks=[
            ScannedTrack(
                index=0,
                track=TrackRef("1", "2", "Song", "Artist", version="Cover"),
                status=TrackStatus.FAKE,
                reasons=["version:field"],
                replace_track_id="99",
            ),
            ScannedTrack(
                index=1,
                track=TrackRef("3", "4", "Other", "X"),
                status=TrackStatus.FAKE,
                reasons=["title_tag:cover"],
            ),
        ],
    )
    updated = apply_choices(result, [])
    assert updated.tracks[0].status == TrackStatus.SKIP
    assert updated.tracks[1].status == TrackStatus.SKIP


def test_fake_replace_keeps_fake():
    result = PlaylistScanResult(
        kind=1,
        title="t",
        track_count=1,
        tracks=[
            ScannedTrack(
                index=3,
                track=TrackRef("1", "2", "Song", "Artist"),
                status=TrackStatus.FAKE,
                replace_track_id="99",
            )
        ],
    )
    updated = apply_choices(result, [UserChoice(track_number=4, value="replace")])
    assert updated.tracks[0].status == TrackStatus.FAKE
