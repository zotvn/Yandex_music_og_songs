from __future__ import annotations

from typing import Iterable

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


def _status_label(status: TrackStatus) -> str:
    if status == TrackStatus.FAKE:
        return "FAKE"
    if status == TrackStatus.CHOOSE:
        return "????"
    return "OK"


def _track_line(item: ScannedTrack) -> str:
    reasons = f" ({', '.join(item.reasons)})" if item.reasons else ""
    expected = f" -> {item.expected_artist}" if item.expected_artist else ""
    return (
        f"{item.index + 1:>4}. [{_status_label(item.status):<4}] "
        f"{format_track_label(item)} "
        f"[{format_duration(item.track.duration_ms)}]{expected}{reasons}"
    )


def _format_choices_section(result: PlaylistScanResult) -> list[str]:
    choose_tracks = [item for item in result.tracks if item.status == TrackStatus.CHOOSE]
    if not choose_tracks:
        return []

    lines = [
        "",
        "=" * 72,
        "НУЖЕН ВЫБОР ИСПОЛНИТЕЛЯ",
        "Сохрани в choices.txt и запусти: choose KIND choices.txt",
        "=" * 72,
    ]
    for item in choose_tracks:
        lines.append(f"{item.index + 1}. {format_track_label(item)}")
        for idx, candidate in enumerate(item.artist_candidates, start=1):
            sources = ", ".join(candidate.sources)
            lines.append(f"     {idx}) {candidate.artist} [{sources}]")
    lines.append("")
    return lines


def format_scan_text(results: Iterable[PlaylistScanResult]) -> str:
    lines: list[str] = []
    for result in results:
        lines.append(f"Playlist: {result.title} (kind={result.kind})")
        lines.append(
            f"Tracks: {result.track_count} | "
            f"ok: {result.original_count} | fake: {result.fake_count} | choose: {result.choose_count}"
        )
        lines.append("-" * 72)
        for item in result.tracks:
            lines.append(_track_line(item))
        lines.extend(_format_choices_section(result))
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"
