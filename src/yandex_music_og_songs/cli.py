from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer

from yandex_music_og_songs.client import YandexMusicClient
from yandex_music_og_songs.config import default_config_yaml, load_config
from yandex_music_og_songs.playlist import scan_playlists
from yandex_music_og_songs.report import format_scan_json, format_scan_text

app = typer.Typer(
    name="yandex-og-songs",
    help="Scan and fix fake tracks in Yandex Music playlists.",
    no_args_is_help=True,
)


@app.command("init-config")
def init_config() -> None:
    """Print example config.yaml to stdout."""
    typer.echo(default_config_yaml(), nl=False)


@app.command("scan")
def scan(
    config_path: Optional[Path] = typer.Option(
        None, "--config", "-c", help="Path to config.yaml"
    ),
    token: Optional[str] = typer.Option(
        None, "--token", help="Yandex Music OAuth token"
    ),
    kind: Optional[list[int]] = typer.Option(
        None, "--kind", "-k", help="Playlist kind (repeatable)"
    ),
    json_report: bool = typer.Option(
        False, "--json", help="Output scan report as JSON"
    ),
) -> None:
    """Scan playlist(s) and report original vs fake tracks."""
    config = load_config(config_path)
    client = YandexMusicClient.from_config(config, token_override=token)
    results = scan_playlists(client, config, kinds=kind)

    if not results:
        typer.echo("No playlists matched the selection.", err=True)
        raise typer.Exit(code=1)

    output = format_scan_json(results) if json_report else format_scan_text(results)
    typer.echo(output, nl=False)


if __name__ == "__main__":
    app()
