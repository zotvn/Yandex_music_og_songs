from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Optional

from yandex_music.exceptions import NotFoundError

from yandex_music_og_songs.client import YandexMusicClient
from yandex_music_og_songs.config import AppConfig
from yandex_music_og_songs.playlist import scan_playlist, scan_playlists
from yandex_music_og_songs.report import format_scan_text
from yandex_music_og_songs.review_io import (
    apply_review_marks,
    parse_review_file,
    write_plain_export,
    write_review_export,
)


def _get_token(token: Optional[str]) -> str:
    value = (token or os.environ.get("YANDEX_MUSIC_TOKEN", "")).strip()
    if not value:
        print(
            "Нужен токен Яндекс Музыки.\n"
            "Установите: export YANDEX_MUSIC_TOKEN=\"ваш_токен\"\n"
            "Или передайте: --token ваш_токен",
            file=sys.stderr,
        )
        sys.exit(1)
    return value


def _parse_args(args: list[str]) -> tuple[Optional[str], Optional[int], Optional[Path], list[str]]:
    token: Optional[str] = None
    kind: Optional[int] = None
    out_path: Optional[Path] = None
    rest: list[str] = []

    i = 0
    while i < len(args):
        if args[i] in ("--token", "-t") and i + 1 < len(args):
            token = args[i + 1]
            i += 2
        elif args[i].isdigit() and kind is None:
            kind = int(args[i])
            i += 1
        elif not args[i].startswith("-") and out_path is None and args[i].endswith(".txt"):
            out_path = Path(args[i])
            i += 1
        else:
            rest.append(args[i])
            i += 1

    return token, kind, out_path, rest


def _load_scan_result(client: YandexMusicClient, kind: int, *, artist_check: bool = True):
    try:
        results = scan_playlists(client, AppConfig(), kinds=[kind], artist_check=artist_check)
    except NotFoundError:
        print(f"Плейлист kind={kind} не найден.", file=sys.stderr)
        print("KIND — первый столбец в list, не число треков.", file=sys.stderr)
        sys.exit(1)
    if not results:
        sys.exit(1)
    return results[0]


def cmd_list(token: Optional[str]) -> None:
    client = YandexMusicClient(_get_token(token))
    playlists = client.list_playlists()
    if not playlists:
        print("Плейлистов не найдено.")
        return
    print(f"{'KIND':<8} {'ТРЕКОВ':<8} НАЗВАНИЕ")
    print("-" * 50)
    for p in playlists:
        count = p.track_count or 0
        print(f"{p.kind:<8} {count:<8} {p.title}")
    print()
    print("Скан:     .venv/bin/python -m yandex_music_og_songs scan 1020")
    print("Экспорт:  .venv/bin/python -m yandex_music_og_songs export 1020 songs.txt")


def cmd_scan(token: Optional[str], kind: Optional[int]) -> None:
    client = YandexMusicClient(_get_token(token))
    if kind is None:
        try:
            results = scan_playlists(client, AppConfig())
        except NotFoundError:
            results = []
    else:
        result = _load_scan_result(client, kind)
        results = [result]

    if not results:
        print("Плейлисты не найдены.", file=sys.stderr)
        sys.exit(1)

    print(format_scan_text(results), end="")


def cmd_export(token: Optional[str], kind: Optional[int], out_path: Optional[Path]) -> None:
    if kind is None or out_path is None:
        print("Использование: export KIND файл.txt", file=sys.stderr)
        sys.exit(1)

    client = YandexMusicClient(_get_token(token))
    playlist = client.get_playlist(kind)
    result = scan_playlist(client, playlist, AppConfig(), artist_check=False)
    write_plain_export(result, out_path)
    print(f"Экспортировано {result.track_count} треков → {out_path}")


def cmd_review(token: Optional[str], kind: Optional[int], out_path: Optional[Path]) -> None:
    if kind is None or out_path is None:
        print("Использование: review KIND файл.txt", file=sys.stderr)
        sys.exit(1)

    client = YandexMusicClient(_get_token(token))
    result = _load_scan_result(client, kind, artist_check=True)
    write_review_export(result, out_path)
    print(
        f"Файл для проверки: {out_path}\n"
        f"Пометь [REPLACE] у треков для замены, потом: import {kind} {out_path}",
        file=sys.stderr,
    )


def cmd_import(token: Optional[str], kind: Optional[int], in_path: Optional[Path]) -> None:
    if kind is None or in_path is None:
        print("Использование: import KIND файл.txt", file=sys.stderr)
        sys.exit(1)
    if not in_path.exists():
        print(f"Файл не найден: {in_path}", file=sys.stderr)
        sys.exit(1)

    client = YandexMusicClient(_get_token(token))
    base = _load_scan_result(client, kind, artist_check=False)
    entries = parse_review_file(in_path)
    result = apply_review_marks(base, entries)

    replace_count = sum(1 for t in result.tracks if t.status.value == "fake")
    print(f"К замене: {replace_count} из {result.track_count}")
    print(format_scan_text([result]), end="")


def main(argv: Optional[list[str]] = None) -> None:
    args = list(argv if argv is not None else sys.argv[1:])

    if not args or args[0] in ("-h", "--help", "help"):
        print(
            "Команды:\n"
            "  list                     список плейлистов\n"
            "  scan [KIND]              скан (с проверкой артиста)\n"
            "  export KIND file.txt     экспорт без меток FAKE/OK\n"
            "  review KIND file.txt     экспорт с [REPLACE] у фейков\n"
            "  import KIND file.txt     применить [REPLACE] из файла\n"
            "\n"
            "Токен: export YANDEX_MUSIC_TOKEN=\"...\""
        )
        return

    command = args[0]
    token, kind, path, _ = _parse_args(args[1:])

    if command == "list":
        cmd_list(token)
    elif command == "scan":
        cmd_scan(token, kind)
    elif command == "export":
        cmd_export(token, kind, path)
    elif command == "review":
        cmd_review(token, kind, path)
    elif command == "import":
        cmd_import(token, kind, path)
    else:
        print(f"Неизвестная команда: {command}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
