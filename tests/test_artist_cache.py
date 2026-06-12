from pathlib import Path

from yandex_music_og_songs.artist_cache import ArtistLookupCache
from yandex_music_og_songs.models import ArtistCandidate


def test_artist_cache_roundtrip(tmp_path: Path):
    path = tmp_path / "cache.json"
    cache = ArtistLookupCache(path)
    cache.put("song", [ArtistCandidate("Artist", ("yandex",), 2.0)])
    cache.save()

    loaded = ArtistLookupCache(path)
    items = loaded.get("song")
    assert items is not None
    assert items[0].artist == "Artist"
