from pathlib import Path

from yandex_music_og_songs.models import PlaylistScanResult, ScannedTrack, TrackRef, TrackStatus
from yandex_music_og_songs.scan_cache import merge_scan_results, save_scan_result


def test_merge_scan_results(tmp_path: Path):
    kind = 42
    a = PlaylistScanResult(
        kind=kind,
        title="t",
        track_count=1,
        tracks=[ScannedTrack(0, TrackRef("1", "2", "A", "X"), TrackStatus.FAKE, ["x"])],
    )
    b = PlaylistScanResult(
        kind=kind,
        title="t",
        track_count=1,
        tracks=[ScannedTrack(1, TrackRef("3", "4", "B", "Y"), TrackStatus.ORIGINAL, [])],
    )
    pa = tmp_path / "a.json"
    pb = tmp_path / "b.json"
    save_scan_result(a, pa)
    save_scan_result(b, pb)
    merged = merge_scan_results([pa, pb])
    assert merged.track_count == 2
    assert merged.tracks[0].index == 0
    assert merged.tracks[1].index == 1
