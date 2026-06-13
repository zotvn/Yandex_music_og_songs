from __future__ import annotations

import json
from pathlib import Path

from yandex_music_og_songs.models import (
    ArtistCandidate,
    PlaylistScanResult,
    ScannedTrack,
    TrackRef,
    TrackStatus,
)


def scan_cache_path(kind: int, suffix: str = "") -> Path:
    if suffix:
        return Path(f"scan_{kind}_{suffix}.json")
    return Path(f"scan_{kind}.json")


def save_scan_result(result: PlaylistScanResult, path: Path) -> None:
    payload = {
        "kind": result.kind,
        "title": result.title,
        "track_count": result.track_count,
        "tracks": [
            {
                "index": item.index,
                "status": item.status.value,
                "reasons": item.reasons,
                "expected_artist": item.expected_artist,
                "replace_track_id": item.replace_track_id,
                "replace_album_id": item.replace_album_id,
                "artist_candidates": [
                    {"artist": c.artist, "sources": list(c.sources), "score": c.score}
                    for c in item.artist_candidates
                ],
                "track": {
                    "track_id": item.track.track_id,
                    "album_id": item.track.album_id,
                    "title": item.track.title,
                    "artist": item.track.artist,
                    "version": item.track.version,
                    "duration_ms": item.track.duration_ms,
                    "track_source": item.track.track_source,
                    "is_user_upload": item.track.is_user_upload,
                },
            }
            for item in result.tracks
        ],
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def load_scan_result(path: Path) -> PlaylistScanResult:
    data = json.loads(path.read_text(encoding="utf-8"))
    tracks: list[ScannedTrack] = []
    for item in data["tracks"]:
        track_data = item["track"]
        tracks.append(
            ScannedTrack(
                index=item["index"],
                status=TrackStatus(item["status"]),
                reasons=item.get("reasons", []),
                expected_artist=item.get("expected_artist"),
                replace_track_id=item.get("replace_track_id"),
                replace_album_id=item.get("replace_album_id"),
                artist_candidates=[
                    ArtistCandidate(
                        artist=c["artist"],
                        sources=tuple(c["sources"]),
                        score=c["score"],
                    )
                    for c in item.get("artist_candidates", [])
                ],
                track=TrackRef(
                    track_id=track_data["track_id"],
                    album_id=track_data["album_id"],
                    title=track_data["title"],
                    artist=track_data["artist"],
                    version=track_data.get("version"),
                    duration_ms=track_data.get("duration_ms"),
                    track_source=track_data.get("track_source"),
                    is_user_upload=track_data.get("is_user_upload", False),
                ),
            )
        )
    return PlaylistScanResult(
        kind=data["kind"],
        title=data["title"],
        track_count=data["track_count"],
        tracks=tracks,
    )


def merge_scan_results(paths: list[Path]) -> PlaylistScanResult:
    if not paths:
        raise ValueError("Нет файлов для merge")

    loaded = [load_scan_result(path) for path in paths]
    base = loaded[0]
    tracks_by_index = {item.index: item for item in base.tracks}
    for result in loaded[1:]:
        if result.kind != base.kind:
            raise ValueError("Разные kind в файлах merge")
        for item in result.tracks:
            tracks_by_index[item.index] = item

    merged_tracks = [tracks_by_index[key] for key in sorted(tracks_by_index)]
    return PlaylistScanResult(
        kind=base.kind,
        title=base.title,
        track_count=len(merged_tracks),
        tracks=merged_tracks,
    )
