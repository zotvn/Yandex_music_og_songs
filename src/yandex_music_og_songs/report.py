from __future__ import annotations

import sys
from typing import Iterable, TextIO

from yandex_music_og_songs.models import PlaylistScanResult, ScannedTrack, TrackStatus


def format_duration(duration_ms: int | None) -> str:
    if not duration_ms:
        return "-"
    total_seconds = duration_ms // 1000
    minutes, seconds = divmod(total_seconds, 60)
    return f"{minutes}:{seconds:02d}"


def format_track_label(item: ScannedTrack) -> str:
    version = f" [{item.track.version}]" if item.track.version else ""
    return f"{item.track.artist} - {item.track.title}{version}"


def status_label(status: TrackStatus) -> str:
    if status == TrackStatus.FAKE:
        return "FAKE"
    if status == TrackStatus.CHOOSE:
        return "????"
    if status == TrackStatus.SKIP:
        return "SKIP"
    return "OK"


def format_track_line(item: ScannedTrack) -> str:
    reasons = f" ({', '.join(item.reasons)})" if item.reasons else ""
    expected = f" -> {item.expected_artist}" if item.expected_artist else ""
    og = ""
    if item.replace_track_id:
        og = f" OG:{item.replace_track_id}"
    return (
        f"{item.index + 1:>4}. [{status_label(item.status):<4}] "
        f"{format_track_label(item)} "
        f"[{format_duration(item.track.duration_ms)}]{expected}{og}{reasons}"
    )


def print_track_line(item: ScannedTrack, file: TextIO = sys.stdout) -> None:
    print(format_track_line(item), file=file, flush=True)


def print_scan_header(result: PlaylistScanResult, file: TextIO = sys.stdout) -> None:
    print(f"Playlist: {result.title} (kind={result.kind})", file=file, flush=True)
    print("-" * 72, file=file, flush=True)


def print_scan_summary(result: PlaylistScanResult, file: TextIO = sys.stdout) -> None:
    print("-" * 72, file=file, flush=True)
    print(
        f"Итого: {result.track_count} | ok: {result.original_count} | "
        f"fake: {result.fake_count} | choose: {result.choose_count} | "
        f"skip: {result.skip_count} | og_in_ya: {result.og_in_ya_count}",
        file=file,
        flush=True,
    )


def format_fake_section(result: PlaylistScanResult) -> list[str]:
    fake_tracks = [item for item in result.tracks if item.status == TrackStatus.FAKE]
    if not fake_tracks:
        return []

    lines = [
        "",
        "=" * 72,
        "FAKE — choices.txt:  N: skip (оставить)  или  N: replace (заменить)",
        "=" * 72,
    ]
    for item in fake_tracks:
        lines.append(f"{item.index + 1}. {format_track_label(item)}")
        if item.replace_track_id:
            lines.append(f"     OG in ya: {item.replace_track_id}:{item.replace_album_id or '?'}")
        else:
            lines.append("     нет clean-версии в Яндексе")
    lines.append("")
    return lines


def print_fake_section(result: PlaylistScanResult, file: TextIO = sys.stdout) -> None:
    for line in format_fake_section(result):
        print(line, file=file, flush=True)


def format_choices_section(result: PlaylistScanResult) -> list[str]:
    choose_tracks = [item for item in result.tracks if item.status == TrackStatus.CHOOSE]
    if not choose_tracks:
        return []

    lines = [
        "",
        "=" * 72,
        "НУЖЕН ВЫБОР ИСПОЛНИТЕЛЯ",
        "choices.txt:  28: 1   или   28: skip",
        "=" * 72,
    ]
    for item in choose_tracks:
        lines.append(f"{item.index + 1}. {format_track_label(item)}")
        for idx, candidate in enumerate(item.artist_candidates, start=1):
            sources = ", ".join(candidate.sources)
            lines.append(f"     {idx}) {candidate.artist} [{sources}]")
    lines.append("")
    return lines


def print_choices_section(result: PlaylistScanResult, file: TextIO = sys.stdout) -> None:
    for line in format_choices_section(result):
        print(line, file=file, flush=True)


def format_scan_text(results: Iterable[PlaylistScanResult]) -> str:
    lines: list[str] = []
    for result in results:
        lines.append(f"Playlist: {result.title} (kind={result.kind})")
        lines.append(
            f"Tracks: {result.track_count} | ok: {result.original_count} | "
            f"fake: {result.fake_count} | choose: {result.choose_count} | "
            f"skip: {result.skip_count} | og_in_ya: {result.og_in_ya_count}"
        )
        lines.append("-" * 72)
        for item in result.tracks:
            lines.append(format_track_line(item))
        lines.extend(format_fake_section(result))
        lines.extend(format_choices_section(result))
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"
