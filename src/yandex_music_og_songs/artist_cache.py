from __future__ import annotations

import json
from pathlib import Path

from yandex_music_og_songs.models import ArtistCandidate

_DEFAULT_PATH = Path(".cache/artist_lookups.json")


def artist_cache_path(custom: Path | None = None) -> Path:
    return custom or _DEFAULT_PATH


def _serialize(candidates: list[ArtistCandidate]) -> list[dict]:
    return [
        {"artist": c.artist, "sources": list(c.sources), "score": c.score}
        for c in candidates
    ]


def _deserialize(items: list[dict]) -> list[ArtistCandidate]:
    return [
        ArtistCandidate(
            artist=item["artist"],
            sources=tuple(item["sources"]),
            score=item["score"],
        )
        for item in items
    ]


class ArtistLookupCache:
    def __init__(self, path: Path | None = None):
        self.path = artist_cache_path(path)
        self._data: dict[str, list[ArtistCandidate]] = {}
        self._dirty = False
        self._load()

    def _load(self) -> None:
        if not self.path.exists():
            return
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return
        for key, items in raw.items():
            self._data[key] = _deserialize(items)

    def get(self, key: str) -> list[ArtistCandidate] | None:
        return self._data.get(key)

    def put(self, key: str, candidates: list[ArtistCandidate]) -> None:
        self._data[key] = candidates
        self._dirty = True

    def save(self) -> None:
        if not self._dirty:
            return
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {key: _serialize(items) for key, items in self._data.items()}
        self.path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        self._dirty = False

    def __len__(self) -> int:
        return len(self._data)
