from __future__ import annotations

import json
from typing import Iterable

from yandex_music_og_songs.models import PlaylistScanResult, ScannedTrack, TrackStatus


def _format_duration(duration_ms: int | None) -> str:
    if not duration_ms:
        return "-"
    total_seconds = duration_ms // 1000
    minutes, seconds = divmod(total_seconds, 60)
    return f"{minutes}:{seconds:02d}"


def _track_line(item: ScannedTrack) -> str:
    status = "FAKE" if item.status == TrackStatus.FAKE else "OK"
    version = f" [{item.track.version}]" if item.track.version else ""
    reasons = f" ({', '.join(item.reasons)})" if item.reasons else ""
    return (
        f"{item.index + 1:>4}. [{status:<4}] "
        f"{item.track.artist} - {item.track.title}{version} "
        f"[{_format_duration(item.track.duration_ms)}]{reasons}"
    )


def format_scan_text(results: Iterable[PlaylistScanResult]) -> str:
    lines: list[str] = []
    for result in results:
        lines.append(f"Playlist: {result.title} (kind={result.kind})")
        lines.append(
            f"Tracks: {result.track_count} | "
            f"original: {result.original_count} | fake: {result.fake_count}"
        )
        lines.append("-" * 72)
        for item in result.tracks:
            lines.append(_track_line(item))
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def format_scan_json(results: Iterable[PlaylistScanResult]) -> str:
    payload = []
    for result in results:
        payload.append(
            {
                "kind": result.kind,
                "title": result.title,
                "track_count": result.track_count,
                "original_count": result.original_count,
                "fake_count": result.fake_count,
                "tracks": [
                    {
                        "index": item.index,
                        "status": item.status.value,
                        "reasons": item.reasons,
                        "track_id": item.track.track_id,
                        "album_id": item.track.album_id,
                        "artist": item.track.artist,
                        "title": item.track.title,
                        "version": item.track.version,
                        "duration_ms": item.track.duration_ms,
                        "track_source": item.track.track_source,
                        "is_user_upload": item.track.is_user_upload,
                    }
                    for item in result.tracks
                ],
            }
        )
    return json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
