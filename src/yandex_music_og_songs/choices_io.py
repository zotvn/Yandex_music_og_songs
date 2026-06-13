from __future__ import annotations

import re
from dataclasses import dataclass
from difflib import SequenceMatcher
from pathlib import Path
from typing import Optional

from yandex_music_og_songs.models import ArtistCandidate, PlaylistScanResult, ScannedTrack, TrackStatus
from yandex_music_og_songs.normalizer import normalize_text


_CHOICE_RE = re.compile(r"^\s*(\d+)\s*:\s*(\S+)\s*$", re.IGNORECASE)
_SKIP_VALUES = {"skip", "keep", "s", "0"}
_REPLACE_VALUES = {"replace", "fake", "r", "1"}


@dataclass(frozen=True)
class UserChoice:
    track_number: int
    value: str


def write_choices_template(result: PlaylistScanResult, path: Path) -> None:
    lines = [
        "# FAKE — оставить или заменить:",
        "#   94: skip      оставить как есть",
        "#   94: replace   заменить (если есть replace_track_id)",
        "# CHOOSE — выбрать артиста:",
        "#   28: 1          вариант из списка",
        "#   28: Adele       имя артиста",
        "",
    ]

    for item in result.tracks:
        if item.status == TrackStatus.FAKE:
            replace_hint = ""
            if item.replace_track_id:
                replace_hint = f" → {item.replace_track_id}:{item.replace_album_id or ''}"
            lines.append(f"{item.index + 1}. {item.track.artist} - {item.track.title}")
            lines.append(f"   FAKE: {', '.join(item.reasons)}{replace_hint}")
            lines.append("")

        elif item.status == TrackStatus.CHOOSE:
            lines.append(f"{item.index + 1}. {item.track.artist} - {item.track.title}")
            for idx, candidate in enumerate(item.artist_candidates, start=1):
                sources = ", ".join(candidate.sources)
                lines.append(f"  {idx}) {candidate.artist} [{sources}]")
            lines.append("")

    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def parse_choices(path: Path) -> list[UserChoice]:
    choices: list[UserChoice] = []
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        match = _CHOICE_RE.match(line)
        if not match:
            continue
        choices.append(UserChoice(track_number=int(match.group(1)), value=match.group(2)))
    return choices


def _pick_candidate(candidates: list[ArtistCandidate], value: str) -> Optional[str]:
    if value.isdigit():
        index = int(value) - 1
        if 0 <= index < len(candidates):
            return candidates[index].artist
        return None

    best_name: Optional[str] = None
    best_score = 0.0
    for candidate in candidates:
        score = SequenceMatcher(None, normalize_text(value), normalize_text(candidate.artist)).ratio()
        if score > best_score:
            best_score = score
            best_name = candidate.artist
    if best_score >= 0.75:
        return best_name
    return None


def apply_choices(result: PlaylistScanResult, choices: list[UserChoice]) -> PlaylistScanResult:
    by_number = {choice.track_number: choice for choice in choices}
    updated: list[ScannedTrack] = []

    for item in result.tracks:
        number = item.index + 1
        choice = by_number.get(number)

        if choice and choice.value.lower() in _SKIP_VALUES:
            updated.append(
                ScannedTrack(
                    index=item.index,
                    track=item.track,
                    status=TrackStatus.SKIP,
                    reasons=["skipped_by_user"],
                    artist_candidates=item.artist_candidates,
                    expected_artist=item.expected_artist,
                    replace_track_id=item.replace_track_id,
                    replace_album_id=item.replace_album_id,
                )
            )
            continue

        if item.status == TrackStatus.FAKE and choice and choice.value.lower() in _REPLACE_VALUES:
            updated.append(item)
            continue

        if item.status == TrackStatus.CHOOSE and choice is not None:
            picked = _pick_candidate(item.artist_candidates, choice.value)
            if not picked:
                updated.append(item)
                continue

            from yandex_music_og_songs.artist_resolver import artists_equivalent

            if artists_equivalent(item.track.artist, picked, 0.88):
                status = TrackStatus.ORIGINAL
                reasons: list[str] = []
            else:
                status = TrackStatus.FAKE
                reasons = [f"wrong_artist:{picked}", "picked_by_user"]

            updated.append(
                ScannedTrack(
                    index=item.index,
                    track=item.track,
                    status=status,
                    reasons=reasons,
                    artist_candidates=item.artist_candidates,
                    expected_artist=picked,
                    replace_track_id=item.replace_track_id,
                    replace_album_id=item.replace_album_id,
                )
            )
            continue

        updated.append(item)

    return PlaylistScanResult(
        kind=result.kind,
        title=result.title,
        track_count=result.track_count,
        tracks=updated,
    )
