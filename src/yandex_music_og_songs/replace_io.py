from __future__ import annotations

import json
from pathlib import Path

from yandex_music_og_songs.models import PlaylistScanResult, TrackStatus


def replace_plan_path(kind: int, suffix: str = "") -> Path:
    if suffix:
        return Path(f"replace_{kind}_{suffix}.json")
    return Path(f"replace_{kind}.json")


def write_replace_plan(result: PlaylistScanResult, path: Path) -> None:
    items: list[dict] = []
    for item in result.tracks:
        if item.status != TrackStatus.FAKE:
            continue
        if not item.replace_track_id:
            continue
        items.append(
            {
                "index": item.index + 1,
                "action": "replace",
                "status": item.status.value,
                "reasons": item.reasons,
                "current": {
                    "track_id": item.track.track_id,
                    "album_id": item.track.album_id,
                    "artist": item.track.artist,
                    "title": item.track.title,
                    "version": item.track.version,
                    "duration_ms": item.track.duration_ms,
                },
                "expected_artist": item.expected_artist,
                "replace_track_id": item.replace_track_id,
                "replace_album_id": item.replace_album_id,
            }
        )
    path.write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")
