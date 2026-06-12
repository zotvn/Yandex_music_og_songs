from __future__ import annotations

import os
from pathlib import Path
from typing import Literal, Optional

import yaml
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
        default_factory=lambda: [r"remix", r"acoustic"]
    )
    title_suffix_patterns: list[str] = Field(
        default_factory=lambda: [
            r"\(cover\)",
            r"\(radio edit\)",
            r"\[karaoke\]",
        ]
    )
    treat_ugc_as_fake: bool = True
    treat_replaced_to_ugc: bool = True
    duration_shorter_threshold: float = 0.15


class ArtistWhitelistEntry(BaseModel):
    expected: str
    allowed: list[str]


class ArtistConfig(BaseModel):
    mode: Literal["off", "optional", "strict", "warn_only"] = "optional"
    fuzzy_threshold: float = 0.85
    whitelist: list[ArtistWhitelistEntry] = Field(default_factory=list)


class ApplyConfig(BaseModel):
    dry_run: bool = True


class AppConfig(BaseModel):
    token_env: str = "YANDEX_MUSIC_TOKEN"
    playlists: PlaylistsConfig = Field(default_factory=PlaylistsConfig)
    detection: DetectionConfig = Field(default_factory=DetectionConfig)
    artist: ArtistConfig = Field(default_factory=ArtistConfig)
    apply: ApplyConfig = Field(default_factory=ApplyConfig)

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


def load_config(path: Optional[Path] = None) -> AppConfig:
    if path is None:
        return AppConfig()
    with path.open(encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    return AppConfig.model_validate(data)


def default_config_yaml() -> str:
    example = Path(__file__).resolve().parents[2] / "config.example.yaml"
    return example.read_text(encoding="utf-8")
