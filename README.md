# Yandex Music OG Songs

CLI tool to scan Yandex Music playlists and detect fake tracks (covers, radio edits, UGC uploads, etc.).

## Setup

```bash
pip install -e ".[dev]"
```

Set your Yandex Music OAuth token:

```bash
export YANDEX_MUSIC_TOKEN="your_token_here"
```

Optional config:

```bash
yandex-og-songs init-config > config.yaml
```

## Scan a playlist

```bash
# Scan all playlists
yandex-og-songs scan --config config.yaml

# Scan one playlist by kind
yandex-og-songs scan --kind 123

# JSON output
yandex-og-songs scan --kind 123 --json
```

Example text output:

```
Playlist: My Playlist (kind=123)
Tracks: 50 | original: 45 | fake: 5
------------------------------------------------------------------------
   1. [FAKE] Artist - Song (Cover) [3:20] (title_suffix:\(cover\))
   2. [OK  ] Artist - Real Song [3:45]
```

## Development

```bash
pytest
```

## Roadmap

- [x] Step 1: Scan playlists and detect fakes
- [ ] Step 2: Replace fakes with catalog originals
- [ ] Step 3: Auto-acquire missing tracks and upload via UGC
