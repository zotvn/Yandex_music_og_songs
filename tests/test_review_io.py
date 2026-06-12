from yandex_music_og_songs.models import PlaylistScanResult, ScannedTrack, TrackRef, TrackStatus
from yandex_music_og_songs.review_io import apply_review_marks, parse_review_file


def _item(index: int, artist: str, title: str, fake: bool) -> ScannedTrack:
    return ScannedTrack(
        index=index,
        track=TrackRef(
            track_id=str(index),
            album_id="1",
            title=title,
            artist=artist,
        ),
        status=TrackStatus.FAKE if fake else TrackStatus.ORIGINAL,
        reasons=["auto"] if fake else [],
    )


def test_parse_review_file(tmp_path):
    content = """
1. Artist - Song [3:00]
28. [REPLACE] TommyMuzzic - back to friends [3:19]
"""
    path = tmp_path / "review.txt"
    path.write_text(content, encoding="utf-8")
    entries = parse_review_file(path)
    assert len(entries) == 2
    assert entries[0].replace is False
    assert entries[1].replace is True


def test_apply_review_marks():
    result = PlaylistScanResult(
        kind=1,
        title="Test",
        track_count=2,
        tracks=[
            _item(0, "A", "Song", fake=False),
            _item(27, "TommyMuzzic", "back to friends", fake=False),
        ],
    )
    from yandex_music_og_songs.review_io import ReviewEntry

    updated = apply_review_marks(
        result,
        [
            ReviewEntry(number=1, replace=False, label="A - Song"),
            ReviewEntry(number=28, replace=True, label="TommyMuzzic - back to friends"),
        ],
    )
    assert updated.tracks[0].status == TrackStatus.ORIGINAL
    assert updated.tracks[1].status == TrackStatus.FAKE
    assert "manual_replace" in updated.tracks[1].reasons
