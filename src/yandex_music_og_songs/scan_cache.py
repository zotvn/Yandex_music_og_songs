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


def scan_cache_path(kind: int) -> Path:
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
