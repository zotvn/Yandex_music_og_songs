from __future__ import annotations

import os
from typing import Literal, Optional

from pydantic import BaseModel, Field


class PlaylistsConfig(BaseModel):
    mode: Literal["all", "selected", "exclude"] = "all"
    kinds: list[int] = Field(default_factory=list)
    exclude_kinds: list[int] = Field(default_factory=list)


class DetectionConfig(BaseModel):
    fake_version_patterns: list[str] = Field(
        default_factory=lambda: [
            r"radio\s*edit",
            r"cover",
            r"karaoke",
            r"tribute",
            r"instrumental",
            r"sped\s*up",
            r"slowed",
            r"nightcore",
            r"\b8d\b",
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
    title_suffix_patterns: list[str] = Field(
        default_factory=lambda: [
            r"\(cover\)",
            r"\(radio edit\)",
            r"\[karaoke\]",
        ]
    )
    treat_ugc_as_fake: bool = False
    treat_replaced_to_ugc: bool = True
    artist_check_rate_limit: float = 0.15


class AppConfig(BaseModel):
    token_env: str = "YANDEX_MUSIC_TOKEN"
    playlists: PlaylistsConfig = Field(default_factory=PlaylistsConfig)
    detection: DetectionConfig = Field(default_factory=DetectionConfig)

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
