from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from yandex_music.exceptions import NotFoundError

from yandex_music_og_songs.choices_io import apply_choices, parse_choices, write_choices_template
from yandex_music_og_songs.client import YandexMusicClient
from yandex_music_og_songs.config import AppConfig, PerformanceConfig
from yandex_music_og_songs.playlist import load_playlist_tracks, scan_playlist, scan_playlists
from yandex_music_og_songs.replace_io import replace_plan_path, write_replace_plan
from yandex_music_og_songs.models import TrackStatus
from yandex_music_og_songs.report import format_scan_text, print_choices_section, print_fake_section, print_scan_summary
from yandex_music_og_songs.review_io import apply_review_marks, parse_review_file, write_plain_export, write_review_export
from yandex_music_og_songs.scan_cache import load_scan_result, merge_scan_results, save_scan_result, scan_cache_path


@dataclass
class ParsedArgs:
    token: Optional[str] = None
    kind: Optional[int] = None
    path: Optional[Path] = None
    workers: Optional[int] = None
    track_from: Optional[int] = None
    track_to: Optional[int] = None
    head: Optional[int] = None
    tail: Optional[int] = None
    suffix: str = ""
    extra_paths: list[Path] | None = None


def _get_token(token: Optional[str]) -> str:
    value = (token or os.environ.get("YANDEX_MUSIC_TOKEN", "")).strip()
    if not value:
        print('Нужен токен: export YANDEX_MUSIC_TOKEN="..."', file=sys.stderr)
        sys.exit(1)
    return value


def _parse_args(args: list[str]) -> ParsedArgs:
    parsed = ParsedArgs(extra_paths=[])
    i = 0
    while i < len(args):
        arg = args[i]
        if arg in ("--token", "-t") and i + 1 < len(args):
            parsed.token = args[i + 1]
            i += 2
        elif arg == "--workers" and i + 1 < len(args):
            parsed.workers = int(args[i + 1])
            i += 2
        elif arg == "--from" and i + 1 < len(args):
            parsed.track_from = int(args[i + 1])
            i += 2
        elif arg == "--to" and i + 1 < len(args):
            parsed.track_to = int(args[i + 1])
            i += 2
        elif arg == "--head" and i + 1 < len(args):
            parsed.head = int(args[i + 1])
            i += 2
        elif arg == "--tail" and i + 1 < len(args):
            parsed.tail = int(args[i + 1])
            i += 2
        elif arg == "--suffix" and i + 1 < len(args):
            parsed.suffix = args[i + 1]
            i += 2
        elif arg.isdigit() and parsed.kind is None:
            parsed.kind = int(arg)
            i += 1
        elif not arg.startswith("-") and parsed.path is None:
            parsed.path = Path(arg)
            i += 1
        elif not arg.startswith("-"):
            parsed.extra_paths.append(Path(arg))
            i += 1
        else:
            i += 1
    return parsed


def _app_config(workers: Optional[int] = None) -> AppConfig:
    config = AppConfig()
    if workers is not None:
        config.performance = PerformanceConfig(
            track_workers=workers,
            artist_workers=max(workers * 2, 8),
            track_batch_size=config.performance.track_batch_size,
            artist_disk_cache=config.performance.artist_disk_cache,
            reuse_scan_cache=config.performance.reuse_scan_cache,
        )
    return config


def _get_playlist(client: YandexMusicClient, kind: int):
    try:
        return client.get_playlist(kind)
    except NotFoundError:
        print(f"Плейлист kind={kind} не найден.", file=sys.stderr)
        sys.exit(1)


def _resolve_range(playlist, parsed: ParsedArgs) -> tuple[Optional[int], Optional[int]]:
    total = playlist.track_count or 0
    if parsed.head is not None:
        return 1, parsed.head
    if parsed.tail is not None and total:
        return max(1, total - parsed.tail + 1), total
    return parsed.track_from, parsed.track_to


def cmd_list(token: Optional[str]) -> None:
    client = YandexMusicClient(_get_token(token))
    playlists = client.list_playlists()
    print(f"{'KIND':<8} {'ТРЕКОВ':<8} НАЗВАНИЕ")
    print("-" * 50)
    for p in playlists:
        print(f"{p.kind:<8} {p.track_count or 0:<8} {p.title}")


def cmd_scan(parsed: ParsedArgs) -> None:
    client = YandexMusicClient(_get_token(parsed.token))
    config = _app_config(parsed.workers)

    if parsed.kind is None:
        results = scan_playlists(client, config, artist_check=True, stream=True)
    else:
        playlist = _get_playlist(client, parsed.kind)
        track_from, track_to = _resolve_range(playlist, parsed)
        results = [
            scan_playlist(
                client,
                playlist,
                config,
                artist_check=True,
                stream=True,
                track_from=track_from,
                track_to=track_to,
            )
        ]

    if not results or results[0].track_count == 0:
        print("Плейлист пуст или диапазон пуст.", file=sys.stderr)
        sys.exit(1)

    result = results[0]
    if parsed.kind is not None:
        cache = scan_cache_path(parsed.kind, parsed.suffix)
        save_scan_result(result, cache)
        plan = replace_plan_path(parsed.kind, parsed.suffix)
        write_replace_plan(result, plan)
        write_choices_template(result, Path("choices.txt"))
        print(f"Кэш: {cache}", file=sys.stderr)
        print(f"План замены: {plan}", file=sys.stderr)
        if result.fake_count:
            print(
                f"FAKE: {result.fake_count} — после choose всё skip, кроме строк replace в choices.txt",
                file=sys.stderr,
            )


def cmd_merge(parsed: ParsedArgs) -> None:
    if parsed.kind is None:
        print("Использование: merge KIND scan_1020_a.json scan_1020_b.json", file=sys.stderr)
        sys.exit(1)
    paths: list[Path] = []
    if parsed.path:
        paths.append(parsed.path)
    if parsed.extra_paths:
        paths.extend(parsed.extra_paths)
    if not paths:
        print("Укажите файлы для merge", file=sys.stderr)
        sys.exit(1)
    merged = merge_scan_results(paths)
    out = scan_cache_path(parsed.kind)
    save_scan_result(merged, out)
    plan = replace_plan_path(parsed.kind)
    write_replace_plan(merged, plan)
    write_choices_template(merged, Path("choices.txt"))
    print_scan_summary(merged)
    print(f"Объединено {len(paths)} файлов → {out}", file=sys.stderr)


def cmd_export(parsed: ParsedArgs) -> None:
    if parsed.kind is None or parsed.path is None:
        print("Использование: export KIND файл.txt", file=sys.stderr)
        sys.exit(1)

    client = YandexMusicClient(_get_token(parsed.token))
    playlist = _get_playlist(client, parsed.kind)
    result = load_playlist_tracks(client, playlist, _app_config(parsed.workers))
    write_plain_export(result, parsed.path)
    print(f"Готово: {result.track_count} треков → {parsed.path}")


def cmd_review(parsed: ParsedArgs) -> None:
    if parsed.kind is None or parsed.path is None:
        print("Использование: review KIND файл.txt", file=sys.stderr)
        sys.exit(1)

    client = YandexMusicClient(_get_token(parsed.token))
    playlist = _get_playlist(client, parsed.kind)
    result = scan_playlist(client, playlist, _app_config(parsed.workers), artist_check=True, stream=True)
    write_review_export(result, parsed.path)
    save_scan_result(result, scan_cache_path(parsed.kind))
    print(f"Сохранено → {parsed.path}", file=sys.stderr)


def cmd_choose(parsed: ParsedArgs) -> None:
    if parsed.kind is None or parsed.path is None:
        print("Использование: choose KIND choices.txt", file=sys.stderr)
        sys.exit(1)
    if not parsed.path.exists():
        print(f"Файл не найден: {parsed.path}", file=sys.stderr)
        sys.exit(1)

    cache = scan_cache_path(parsed.kind)
    if cache.exists():
        base = load_scan_result(cache)
    else:
        client = YandexMusicClient(_get_token(parsed.token))
        playlist = _get_playlist(client, parsed.kind)
        base = scan_playlist(client, playlist, _app_config(parsed.workers), artist_check=True, stream=False)

    result = apply_choices(base, parse_choices(parsed.path))
    save_scan_result(result, cache)
    plan = replace_plan_path(parsed.kind)
    write_replace_plan(result, plan)
    print_scan_summary(result)
    print_fake_section(result)
    print_choices_section(result)
    to_replace = sum(1 for t in result.tracks if t.status == TrackStatus.FAKE and t.replace_track_id)
    print(
        f"\nК замене: {to_replace} | пропуск: {result.skip_count} | план: {plan}",
        file=sys.stderr,
    )


def cmd_import(parsed: ParsedArgs) -> None:
    if parsed.kind is None or parsed.path is None:
        print("Использование: import KIND файл.txt", file=sys.stderr)
        sys.exit(1)

    cache = scan_cache_path(parsed.kind)
    if cache.exists():
        base = load_scan_result(cache)
    else:
        client = YandexMusicClient(_get_token(parsed.token))
        playlist = _get_playlist(client, parsed.kind)
        base = load_playlist_tracks(client, playlist, _app_config(parsed.workers))

    result = apply_review_marks(base, parse_review_file(parsed.path))
    save_scan_result(result, cache)
    print(format_scan_text([result]), end="")


def main(argv: Optional[list[str]] = None) -> None:
    args = list(argv if argv is not None else sys.argv[1:])

    if not args or args[0] in ("-h", "--help", "help"):
        print(
            "  list\n"
            "  scan KIND [--from N] [--to M] [--head N] [--tail N] [--suffix a] [--workers N]\n"
            "  merge KIND scan_1020_a.json scan_1020_b.json\n"
            "  export KIND file.txt\n"
            "  choose KIND choices.txt\n"
            "  import KIND file.txt\n"
            "\n"
            "Два процесса параллельно:\n"
            "  scan 1020 --head 150 --suffix a\n"
            "  scan 1020 --tail 150 --suffix b\n"
            "  merge 1020 scan_1020_a.json scan_1020_b.json\n"
            "\n"
            "choices.txt (после choose всё FAKE → skip, кроме replace):\n"
            "  94: replace   заменить этот трек\n"
            "  28: 1          выбрать артиста (CHOOSE)\n"
        )
        return

    command = args[0]
    parsed = _parse_args(args[1:])

    handlers = {
        "list": lambda: cmd_list(parsed.token),
        "scan": lambda: cmd_scan(parsed),
        "merge": lambda: cmd_merge(parsed),
        "export": lambda: cmd_export(parsed),
        "review": lambda: cmd_review(parsed),
        "choose": lambda: cmd_choose(parsed),
        "import": lambda: cmd_import(parsed),
    }
    handler = handlers.get(command)
    if handler is None:
        print(f"Неизвестная команда: {command}", file=sys.stderr)
        sys.exit(1)
    handler()


if __name__ == "__main__":
    main()
