from __future__ import annotations

import json
from pathlib import Path

from yandex_music_og_songs.models import ArtistCandidate, CatalogHit, TitleLookup

_DEFAULT_PATH = Path(".cache/artist_lookups.json")
_CACHE_VERSION = 2


def artist_cache_path(custom: Path | None = None) -> Path:
    return custom or _DEFAULT_PATH


def _serialize_lookup(lookup: TitleLookup) -> dict:
    return {
        "candidates": [
            {"artist": c.artist, "sources": list(c.sources), "score": c.score}
            for c in lookup.candidates
        ],
        "hits": [
            {
                "artist": h.artist,
                "title": h.title,
                "duration_ms": h.duration_ms,
                "version": h.version,
            }
            for h in lookup.hits
        ],
    }


def _deserialize_lookup(data: dict) -> TitleLookup:
    candidates = [
        ArtistCandidate(
            artist=item["artist"],
            sources=tuple(item["sources"]),
            score=item["score"],
        )
        for item in data.get("candidates", [])
    ]
    hits = [
        CatalogHit(
            artist=item["artist"],
            title=item["title"],
            duration_ms=item.get("duration_ms"),
            version=item.get("version"),
        )
        for item in data.get("hits", [])
    ]
    return TitleLookup(candidates=candidates, hits=hits)


class ArtistLookupCache:
    def __init__(self, path: Path | None = None):
        self.path = artist_cache_path(path)
        self._data: dict[str, TitleLookup] = {}
        self._dirty = False
        self._load()

    def _load(self) -> None:
        if not self.path.exists():
            return
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return
        if raw.get("version") != _CACHE_VERSION:
            return
        for key, payload in raw.get("lookups", {}).items():
            self._data[key] = _deserialize_lookup(payload)

    def get(self, key: str) -> TitleLookup | None:
        return self._data.get(key)

    def put(self, key: str, lookup: TitleLookup) -> None:
        self._data[key] = lookup
        self._dirty = True

    def save(self) -> None:
        if not self._dirty:
            return
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "version": _CACHE_VERSION,
            "lookups": {key: _serialize_lookup(lookup) for key, lookup in self._data.items()},
        }
        self.path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        self._dirty = False

    def __len__(self) -> int:
        return len(self._data)
