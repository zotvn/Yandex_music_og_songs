from __future__ import annotations

import os
from typing import Literal, Optional

from pydantic import BaseModel, Field


class PlaylistsConfig(BaseModel):
    mode: Literal["all", "selected", "exclude"] = "all"
    kinds: list[int] = Field(default_factory=list)
    exclude_kinds: list[int] = Field(default_factory=list)


class PerformanceConfig(BaseModel):
    track_workers: int = 4
    artist_workers: int = 8
    track_batch_size: int = 100


class DetectionConfig(BaseModel):
    fake_version_patterns: list[str] = Field(
        default_factory=lambda: [
            r"radio\s*[-_]?\s*edit",
            r"cover",
            r"karaoke",
            r"tribute",
            r"instrumental",
            r"sped\s*[-_]?\s*up",
            r"speed\s*[-_]?\s*up",
            r"slowed(?:\s*(?:&|and)\s*reverb)?",
            r"nightcore",
            r"\b8d\b",
            r"reverb(?:\s*only)?",
        ]
    )
    keep_version_patterns: list[str] = Field(
        default_factory=lambda: [
            r"remix",
            r"acoustic",
            r"from the series",
            r"soundtrack",
            r"\bost\b",
        ]
    )
    title_paren_fake_patterns: list[str] = Field(
        default_factory=lambda: [
            r"cover",
            r"karaoke",
            r"tribute",
        ]
    )
    title_fake_patterns: list[str] = Field(
        default_factory=lambda: [
            r"[\(\[]\s*cover\s*[\)\]]",
            r"[\(\[]\s*karaoke\s*[\)\]]",
            r"[\(\[]\s*tribute\s*[\)\]]",
            r"\bcover\s+version\b",
        ]
    )
    title_ask_patterns: list[str] = Field(
        default_factory=lambda: [
            r"radio\s*[-_]?\s*edit",
            r"sped\s*[-_]?\s*up",
            r"speed\s*[-_]?\s*up",
            r"slowed",
            r"nightcore",
            r"\b8d\b",
            r"reverb",
            r"pitch\s*shift",
        ]
    )
    treat_ugc_as_fake: bool = False
    treat_replaced_to_ugc: bool = True

    @property
    def title_suffix_patterns(self) -> list[str]:
        """Patterns stripped from titles before artist lookup."""
        return list(self.title_fake_patterns) + [
            r"[\(\[]\s*radio\s*[-_]?\s*edit\s*[\)\]]",
            r"[\(\[]\s*sped\s*[-_]?\s*up\s*[\)\]]",
            r"[\(\[]\s*speed\s*[-_]?\s*up\s*[\)\]]",
            r"[\(\[]\s*slowed[^)\]]*[\)\]]",
            r"[\(\[]\s*nightcore\s*[\)\]]",
            r"[\(\[]\s*8d\s*[\)\]]",
        ]


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
