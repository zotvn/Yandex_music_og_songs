from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Optional

from yandex_music.exceptions import NotFoundError

from yandex_music_og_songs.choices_io import apply_choices, parse_choices, write_choices_template
from yandex_music_og_songs.client import YandexMusicClient
from yandex_music_og_songs.config import AppConfig, PerformanceConfig
from yandex_music_og_songs.playlist import load_playlist_tracks, scan_playlist, scan_playlists
from yandex_music_og_songs.report import format_scan_text, print_choices_section, print_scan_summary
from yandex_music_og_songs.review_io import apply_review_marks, parse_review_file, write_plain_export, write_review_export
from yandex_music_og_songs.scan_cache import load_scan_result, save_scan_result, scan_cache_path


def _get_token(token: Optional[str]) -> str:
    value = (token or os.environ.get("YANDEX_MUSIC_TOKEN", "")).strip()
    if not value:
        print('Нужен токен: export YANDEX_MUSIC_TOKEN="..."', file=sys.stderr)
        sys.exit(1)
    return value


def _parse_args(args: list[str]) -> tuple[Optional[str], Optional[int], Optional[Path], Optional[int]]:
    token: Optional[str] = None
    kind: Optional[int] = None
    path: Optional[Path] = None
    workers: Optional[int] = None

    i = 0
    while i < len(args):
        if args[i] in ("--token", "-t") and i + 1 < len(args):
            token = args[i + 1]
            i += 2
        elif args[i] == "--workers" and i + 1 < len(args):
            workers = int(args[i + 1])
            i += 2
        elif args[i].isdigit() and kind is None:
            kind = int(args[i])
            i += 1
        elif not args[i].startswith("-") and path is None:
            path = Path(args[i])
            i += 1
        else:
            i += 1

    return token, kind, path, workers


def _app_config(workers: Optional[int] = None) -> AppConfig:
    config = AppConfig()
    if workers is not None:
        config.performance = PerformanceConfig(
            track_workers=workers,
            artist_workers=max(workers * 2, 4),
            track_batch_size=config.performance.track_batch_size,
        )
    return config


def _get_playlist(client: YandexMusicClient, kind: int):
    try:
        return client.get_playlist(kind)
    except NotFoundError:
        print(f"Плейлист kind={kind} не найден.", file=sys.stderr)
        sys.exit(1)


def cmd_list(token: Optional[str]) -> None:
    client = YandexMusicClient(_get_token(token))
    playlists = client.list_playlists()
    print(f"{'KIND':<8} {'ТРЕКОВ':<8} НАЗВАНИЕ")
    print("-" * 50)
    for p in playlists:
        print(f"{p.kind:<8} {p.track_count or 0:<8} {p.title}")


def cmd_scan(token: Optional[str], kind: Optional[int], workers: Optional[int]) -> None:
    client = YandexMusicClient(_get_token(token))
    config = _app_config(workers)

    if kind is None:
        results = scan_playlists(client, config, artist_check=True, stream=True)
    else:
        playlist = _get_playlist(client, kind)
        results = [scan_playlist(client, playlist, config, artist_check=True, stream=True)]

    if not results or results[0].track_count == 0:
        print("Плейлист пуст.", file=sys.stderr)
        sys.exit(1)

    result = results[0]
    if kind is not None:
        cache = scan_cache_path(kind)
        save_scan_result(result, cache)
        if result.choose_count:
            write_choices_template(result, Path("choices.txt"))
            print("Создан choices.txt", file=sys.stderr)


def cmd_export(token: Optional[str], kind: Optional[int], out_path: Optional[Path], workers: Optional[int]) -> None:
    if kind is None or out_path is None:
        print("Использование: export KIND файл.txt", file=sys.stderr)
        sys.exit(1)

    client = YandexMusicClient(_get_token(token))
    playlist = _get_playlist(client, kind)
    result = load_playlist_tracks(client, playlist, _app_config(workers))
    write_plain_export(result, out_path)
    print(f"Готово: {result.track_count} треков → {out_path}")


def cmd_review(token: Optional[str], kind: Optional[int], out_path: Optional[Path], workers: Optional[int]) -> None:
    if kind is None or out_path is None:
        print("Использование: review KIND файл.txt", file=sys.stderr)
        sys.exit(1)

    client = YandexMusicClient(_get_token(token))
    playlist = _get_playlist(client, kind)
    result = scan_playlist(client, playlist, _app_config(workers), artist_check=True, stream=True)
    write_review_export(result, out_path)
    save_scan_result(result, scan_cache_path(kind))
    print(f"Сохранено → {out_path}", file=sys.stderr)


def cmd_choose(token: Optional[str], kind: Optional[int], in_path: Optional[Path], workers: Optional[int]) -> None:
    if kind is None or in_path is None:
        print("Использование: choose KIND choices.txt", file=sys.stderr)
        sys.exit(1)
    if not in_path.exists():
        print(f"Файл не найден: {in_path}", file=sys.stderr)
        sys.exit(1)

    cache = scan_cache_path(kind)
    if cache.exists():
        base = load_scan_result(cache)
    else:
        client = YandexMusicClient(_get_token(token))
        playlist = _get_playlist(client, kind)
        base = scan_playlist(client, playlist, _app_config(workers), artist_check=True, stream=False)

    result = apply_choices(base, parse_choices(in_path))
    save_scan_result(result, cache)
    print_scan_summary(result)
    print_choices_section(result)
    print(f"\nК замене: {result.fake_count} | пропуск: {result.skip_count}", file=sys.stderr)


def cmd_import(token: Optional[str], kind: Optional[int], in_path: Optional[Path], workers: Optional[int]) -> None:
    if kind is None or in_path is None:
        print("Использование: import KIND файл.txt", file=sys.stderr)
        sys.exit(1)

    cache = scan_cache_path(kind)
    if cache.exists():
        base = load_scan_result(cache)
    else:
        client = YandexMusicClient(_get_token(token))
        playlist = _get_playlist(client, kind)
        base = load_playlist_tracks(client, playlist, _app_config(workers))

    result = apply_review_marks(base, parse_review_file(in_path))
    save_scan_result(result, cache)
    print(format_scan_text([result]), end="")


def main(argv: Optional[list[str]] = None) -> None:
    args = list(argv if argv is not None else sys.argv[1:])

    if not args or args[0] in ("-h", "--help", "help"):
        print(
            "  list\n"
            "  export KIND file.txt\n"
            "  scan KIND [--workers N]  результат сразу по каждому треку\n"
            "  choose KIND choices.txt\n"
            "  import KIND file.txt\n"
            "\n"
            "choices.txt:\n"
            "  28: 1         выбрать артиста\n"
            "  15: skip       не менять трек\n"
            "  15: replace    заменить версию (radio edit и т.п.)\n"
        )
        return

    command = args[0]
    token, kind, path, workers = _parse_args(args[1:])

    handlers = {
        "list": lambda: cmd_list(token),
        "scan": lambda: cmd_scan(token, kind, workers),
        "export": lambda: cmd_export(token, kind, path, workers),
        "review": lambda: cmd_review(token, kind, path, workers),
        "choose": lambda: cmd_choose(token, kind, path, workers),
        "import": lambda: cmd_import(token, kind, path, workers),
    }
    handler = handlers.get(command)
    if handler is None:
        print(f"Неизвестная команда: {command}", file=sys.stderr)
        sys.exit(1)
    handler()


if __name__ == "__main__":
    main()
