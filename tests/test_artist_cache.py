from pathlib import Path

from yandex_music_og_songs.artist_cache import ArtistLookupCache
from yandex_music_og_songs.models import ArtistCandidate, TitleLookup


def test_artist_cache_roundtrip(tmp_path: Path):
    path = tmp_path / "cache.json"
    cache = ArtistLookupCache(path)
    cache.put("song", TitleLookup(candidates=[ArtistCandidate("Artist", ("musicbrainz",), 1.0)]))
    cache.save()

    loaded = ArtistLookupCache(path)
    items = loaded.get("song")
    assert items is not None
    assert items.candidates[0].artist == "Artist"
