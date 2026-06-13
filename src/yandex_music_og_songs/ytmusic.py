from __future__ import annotations

from yandex_music_og_songs.normalizer import text_similarity


def search_youtube_music(title: str) -> list[tuple[str, int | None]]:
    try:
        from ytmusicapi import YTMusic
    except ImportError:
        return []

    try:
        yt = YTMusic()
        results = yt.search(title, filter="songs", limit=8)
    except Exception:
        return []

    artists: list[tuple[str, int | None]] = []
    for item in results:
        item_title = item.get("title") or ""
        if item_title and text_similarity(title, item_title) < 0.65:
            continue
        for artist_info in item.get("artists") or []:
            name = artist_info.get("name")
            if name:
                duration = item.get("duration_seconds")
                duration_ms = int(duration * 1000) if duration else None
                artists.append((name, duration_ms))
    return artists
