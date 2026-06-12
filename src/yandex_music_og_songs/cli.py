from __future__ import annotations

import os
import sys
from typing import Optional

from yandex_music_og_songs.client import YandexMusicClient
from yandex_music_og_songs.config import AppConfig
from yandex_music_og_songs.playlist import scan_playlists
from yandex_music_og_songs.report import format_scan_text


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


def cmd_scan(token: Optional[str], kind: Optional[int]) -> None:
    config = AppConfig()
    client = YandexMusicClient(_get_token(token))
    kinds = [kind] if kind is not None else None
    results = scan_playlists(client, config, kinds=kinds)

    if not results:
        print("Плейлисты не найдены. Сначала: python -m yandex_music_og_songs list", file=sys.stderr)
        sys.exit(1)

    print(format_scan_text(results), end="")


def main(argv: Optional[list[str]] = None) -> None:
    args = list(argv if argv is not None else sys.argv[1:])
    token: Optional[str] = None
    kind: Optional[int] = None

    if not args or args[0] in ("-h", "--help", "help"):
        print(
            "Использование:\n"
            "  python -m yandex_music_og_songs list          # список плейлистов\n"
            "  python -m yandex_music_og_songs scan        # скан всех плейлистов\n"
            "  python -m yandex_music_og_songs scan 123      # скан одного плейлиста\n"
            "\n"
            "Токен: export YANDEX_MUSIC_TOKEN=\"...\"\n"
            "       или --token \"...\""
        )
        return

    command = args[0]
    rest = args[1:]

    i = 0
    while i < len(rest):
        if rest[i] in ("--token", "-t"):
            token = rest[i + 1]
            i += 2
        elif rest[i].isdigit():
            kind = int(rest[i])
            i += 1
        else:
            i += 1

    if command == "list":
        cmd_list(token)
    elif command == "scan":
        cmd_scan(token, kind)
    else:
        print(f"Неизвестная команда: {command}", file=sys.stderr)
        print("Команды: list, scan", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
