from pathlib import Path

from yandex_music_og_songs.artist_cache import ArtistLookupCache
from yandex_music_og_songs.models import ArtistCandidate, CatalogHit, TitleLookup


def test_artist_cache_roundtrip(tmp_path: Path):
    path = tmp_path / "cache.json"
    cache = ArtistLookupCache(path)
    cache.put(
        "song",
        TitleLookup(
            candidates=[ArtistCandidate("Artist", ("yandex",), 2.0)],
            hits=[CatalogHit("Artist", "Song", 1000)],
        ),
    )
    cache.save()

    loaded = ArtistLookupCache(path)
    items = loaded.get("song")
    assert items is not None
    assert items.candidates[0].artist == "Artist"
    assert items.hits[0].title == "Song"
