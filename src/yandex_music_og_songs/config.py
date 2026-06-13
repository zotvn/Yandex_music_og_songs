from __future__ import annotations

import os
from typing import Literal, Optional

from pydantic import BaseModel, Field


class PlaylistsConfig(BaseModel):
    mode: Literal["all", "selected", "exclude"] = "all"
    kinds: list[int] = Field(default_factory=list)
    exclude_kinds: list[int] = Field(default_factory=list)


class PerformanceConfig(BaseModel):
    track_workers: int = 8
    artist_workers: int = 16
    track_batch_size: int = 150
    artist_disk_cache: bool = True
    reuse_scan_cache: bool = False


class DetectionConfig(BaseModel):
    artist_match_threshold: float = 0.75
    artist_ok_threshold: float = 0.88
    duration_min_ratio: float = 0.85
    duration_tolerance_ms: int = 10000
    title_paren_fake_patterns: list[str] = Field(
        default_factory=lambda: [
            r"cover",
            r"karaoke",
            r"tribute",
            r"live",
            r"tiktok",
            r"radio",
            r"edit",
            r"sped",
            r"speed",
            r"slowed",
            r"nightcore",
            r"\b8d\b",
            r"reverb",
            r"remix",
            r"studio",
            r"version",
            r"instrumental",
        ]
    )
    title_fake_patterns: list[str] = Field(
        default_factory=lambda: [
            r"[\(\[]\s*cover\s*[\)\]]",
            r"[\(\[]\s*karaoke\s*[\)\]]",
            r"[\(\[]\s*tribute\s*[\)\]]",
            r"[\(\[]\s*live\s*[\)\]]",
            r"[\(\[]\s*tiktok[^)\]]*[\)\]]",
            r"[\(\[]\s*radio[^)\]]*[\)\]]",
            r"[\(\[]\s*8d[^)\]]*[\)\]]",
            r"[\(\[]\s*slowed[^)\]]*[\)\]]",
            r"[\(\[]\s*sped[^)\]]*[\)\]]",
            r"[\(\[]\s*nightcore\s*[\)\]]",
            r"[\(\[]\s*studio\s*version\s*[\)\]]",
            r"\bcover\s+version\b",
            r"\btiktok\s+version\b",
            r"\b8d\b",
        ]
    )
    suspicious_artist_patterns: list[str] = Field(
        default_factory=lambda: [
            r"tribute",
            r"karaoke",
            r"\b8d\b",
            r"tiktok",
            r"rhythm\s*rebel",
            r"ameritz",
            r"live\s*beat",
            r"sky\s*trucking",
            r"funky\s*groove",
            r"lil\s*flop",
            r"jxctis",
            r"\bcover\b",
            r"reverb",
            r"studio\s*version",
            r"xtm\s*remix",
            r"remix\s*edit",
            r"sunbeams",
            r"tim\s*mahendran",
            r"zxctis",
            r"jxctis",
        ]
    )
    version_word_patterns: list[str] = Field(
        default_factory=lambda: [
            r"\bversion\b",
            r"\bedit\b",
        ]
    )

    @property
    def title_suffix_patterns(self) -> list[str]:
        return list(self.title_fake_patterns)


class AppConfig(BaseModel):
    token_env: str = "YANDEX_MUSIC_TOKEN"
    playlists: PlaylistsConfig = Field(default_factory=PlaylistsConfig)
    detection: DetectionConfig = Field(default_factory=DetectionConfig)
    performance: PerformanceConfig = Field(default_factory=PerformanceConfig)

    def get_token(self, override: Optional[str] = None) -> str:
        if override:
            return override
        token = os.environ.get(self.token_env, "").strip()
        if not token:
            raise ValueError(
                f"Yandex Music token not found. Set {self.token_env} env var "
                "or pass --token."
            )
        return token


def load_config() -> AppConfig:
    return AppConfig()
