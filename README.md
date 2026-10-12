# Yandex Music OG Songs

CLI для поиска фейковых / не тех треков в плейлистах Яндекс Музыки и подготовки списка на замену.

Сейчас инструмент **сканирует и помечает** треки (`OK` / `FAKE` / `????` / `SKIP`). Автоматической подмены треков в плейлисте ещё нет — результат остаётся в кэше скана / `choices.txt` / `review.txt`.

## Установка

```bash
git clone https://github.com/zotvn/Yandex_music_og_songs.git
cd Yandex_music_og_songs
chmod +x setup.sh && ./setup.sh
export YANDEX_MUSIC_TOKEN="ваш_токен"
```

Токен: аккаунт Яндекс Музыки → настройки / токен для API (как для `yandex-music` Python lib).

## Команды

```bash
# список плейлистов (KIND = id плейлиста)
.venv/bin/python -m yandex_music_og_songs list

# быстрый экспорт названий без детекта
.venv/bin/python -m yandex_music_og_songs export 1020 songs.txt

# скан — статус печатается сразу по каждому треку; кэш + choices.txt при неоднозначностях
.venv/bin/python -m yandex_music_og_songs scan 1020

# выбор / исключение без повторного скана (читает кэш скана)
.venv/bin/python -m yandex_music_og_songs choose 1020 choices.txt

# review-файл с тегами [REPLACE]/[SKIP]/[CHOOSE]
.venv/bin/python -m yandex_music_og_songs review 1020 review.txt

# применить правки из review-файла к кэшу скана
.venv/bin/python -m yandex_music_og_songs import 1020 review.txt
```

Алиас после установки: `yandex-og-songs` (тот же CLI).

## Статусы

| Статус | Значение |
|--------|----------|
| OK | Оригинал / ок |
| FAKE | Помечен как фейк / к замене (по версии, UGC, артисту и т.п.) |
| ???? | Несколько кандидатов артиста — нужен выбор в `choices.txt` |
| SKIP | Не трогать (исключён вручную) |

Как помечается FAKE (по умолчанию):
- версия трека матчит `cover` / `karaoke` / `sped up` / … (см. `config.example.yaml`)
- суффиксы в названии вроде `(cover)`
- `track_source == OWN_REPLACED_TO_UGC`
- проверка артиста через поиск Яндекс Музыки + MusicBrainz (при неоднозначности → `????`)

`remix` / `acoustic` и похожие версии по умолчанию **не** считаются фейком.

## choices.txt

Создаётся после `scan`, если есть `????`.

```
# выбрать исполнителя
28: 1

# или по имени
28: sombr

# НЕ менять трек
15: skip
```

## review.txt

```
15. [SKIP] Artist - Song [3:00]
28. [REPLACE] TommyMuzzic - back to friends [3:19]
```

Теги: `[REPLACE]` → FAKE, `[SKIP]` → SKIP, без тега / `[KEEP]` → OK.

## Конфиг

Скопируй `config.example.yaml` при необходимости. Сейчас `AppConfig` читает в основном дефолты из кода (`token_env`, паттерны детекта); секции `artist:` / `apply:` в примере — задел под будущий apply, **пока не подключены**.

## Ограничения

- Нет команды, которая реально меняет состав плейлиста в Яндекс Музыке.
- Для API из-за рубежа часто нужен RU VPN / split tunnel только для этого процесса.
- `scan` без KIND сканирует все плейлисты подряд (может быть долго).
