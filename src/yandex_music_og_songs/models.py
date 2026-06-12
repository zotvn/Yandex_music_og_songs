from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class TrackStatus(str, Enum):
    ORIGINAL = "original"
    FAKE = "fake"
    CHOOSE = "choose"


@dataclass(frozen=True)
class TrackRef:
    track_id: str
    album_id: str
    title: str
    artist: str
    version: Optional[str] = None
    duration_ms: Optional[int] = None
    track_source: Optional[str] = None
    is_user_upload: bool = False

    @property
    def key(self) -> str:
        return f"{self.track_id}:{self.album_id}"


@dataclass(frozen=True)
class ArtistCandidate:
    artist: str
    sources: tuple[str, ...]
    score: float


@dataclass
class ScannedTrack:
    index: int
    track: TrackRef
    status: TrackStatus
    reasons: list[str] = field(default_factory=list)
    artist_candidates: list[ArtistCandidate] = field(default_factory=list)
    expected_artist: Optional[str] = None


@dataclass
class PlaylistScanResult:
    kind: int
    title: str
    track_count: int
    tracks: list[ScannedTrack] = field(default_factory=list)

    @property
    def fake_count(self) -> int:
        return sum(1 for t in self.tracks if t.status == TrackStatus.FAKE)

    @property
    def original_count(self) -> int:
        return sum(1 for t in self.tracks if t.status == TrackStatus.ORIGINAL)

    @property
    def choose_count(self) -> int:
        return sum(1 for t in self.tracks if t.status == TrackStatus.CHOOSE)
