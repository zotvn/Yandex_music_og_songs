from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from yandex_music_og_songs.models import PlaylistScanResult, ScannedTrack, TrackStatus
from yandex_music_og_songs.report import format_duration, format_track_label

_LINE_RE = re.compile(
    r"^\s*(\d+)\.\s*(?:\[(REPLACE|KEEP|SKIP|CHOOSE)\]\s*)?(.+?)(?:\s+\[(\d+:\d+|-)\])?\s*$",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class ReviewEntry:
    number: int
    replace: bool
    skip: bool
    label: str


def format_plain_line(item: ScannedTrack) -> str:
    return (
        f"{item.index + 1}. {format_track_label(item)} "
        f"[{format_duration(item.track.duration_ms)}]"
    )


def format_review_line(item: ScannedTrack) -> str:
    if item.status == TrackStatus.FAKE:
        tag = "[REPLACE] "
    elif item.status == TrackStatus.CHOOSE:
        tag = "[CHOOSE] "
    elif item.status == TrackStatus.SKIP:
        tag = "[SKIP] "
    else:
        tag = ""
    return (
        f"{item.index + 1}. {tag}{format_track_label(item)} "
        f"[{format_duration(item.track.duration_ms)}]"
    )


def write_plain_export(result: PlaylistScanResult, path: Path) -> None:
    lines = [format_plain_line(item) for item in result.tracks]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_review_export(result: PlaylistScanResult, path: Path) -> None:
    header = (
        "# [REPLACE] — заменить | [SKIP] — не трогать | убери тег чтобы оставить\n"
    )
    lines = [format_review_line(item) for item in result.tracks]
    path.write_text(header + "\n".join(lines) + "\n", encoding="utf-8")


def parse_review_file(path: Path) -> list[ReviewEntry]:
    entries: list[ReviewEntry] = []
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        match = _LINE_RE.match(line)
        if not match:
            continue
        tag = (match.group(2) or "").upper()
        entries.append(
            ReviewEntry(
                number=int(match.group(1)),
                replace=tag == "REPLACE",
                skip=tag == "SKIP",
                label=match.group(3).strip(),
            )
        )
    return entries


def apply_review_marks(result: PlaylistScanResult, entries: list[ReviewEntry]) -> PlaylistScanResult:
    by_number = {entry.number: entry for entry in entries}
    updated: list[ScannedTrack] = []

    for item in result.tracks:
        number = item.index + 1
        entry = by_number.get(number)
        if entry is None:
            updated.append(item)
            continue

        if entry.skip:
            updated.append(
                ScannedTrack(
                    index=item.index,
                    track=item.track,
                    status=TrackStatus.SKIP,
                    reasons=["skipped_by_user"],
                    artist_candidates=item.artist_candidates,
                    expected_artist=item.expected_artist,
                )
            )
            continue

        if entry.replace:
            reasons = list(item.reasons)
            if "manual_replace" not in reasons:
                reasons.append("manual_replace")
            updated.append(
                ScannedTrack(
                    index=item.index,
                    track=item.track,
                    status=TrackStatus.FAKE,
                    reasons=reasons,
                    artist_candidates=item.artist_candidates,
                    expected_artist=item.expected_artist,
                )
            )
            continue

        updated.append(
            ScannedTrack(
                index=item.index,
                track=item.track,
                status=TrackStatus.ORIGINAL,
                reasons=[],
                artist_candidates=item.artist_candidates,
                expected_artist=item.expected_artist,
            )
        )

    return PlaylistScanResult(
        kind=result.kind,
        title=result.title,
        track_count=result.track_count,
        tracks=updated,
    )
