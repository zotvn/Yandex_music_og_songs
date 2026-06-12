# Yandex Music OG Songs

Сканирует плейлисты Яндекс Музыки и показывает фейковые треки (cover, radio edit, загрузки и т.д.).

## 1. Скачать

```bash
git clone https://github.com/zotvn/Yandex_music_og_songs.git
cd Yandex_music_og_songs
```

## 2. Установить

На **Arch Linux** (и многих других дистрибутивах) нельзя ставить пакеты в системный Python.
Используй виртуальное окружение:

```bash
# один раз — автоматически
chmod +x setup.sh
./setup.sh
```

Или вручную:

```bash
python -m venv .venv
.venv/bin/pip install -e .
```

Дальше всегда запускай через `.venv/bin/python` (не просто `python`).

## 3. Получить токен

1. Открой https://oauth.yandex.ru/authorize?response_type=token&client_id=23cabbbdc6cd418abb4b39c32c41195d
2. Войди в аккаунт Яндекса
3. Скопируй `access_token=...` из адресной строки (до символа `&`)

## 4. Запустить

```bash
export YANDEX_MUSIC_TOKEN="ваш_токен"

# список плейлистов
.venv/bin/python -m yandex_music_og_songs list

# скан одного плейлиста (KIND — число из list или из URL)
.venv/bin/python -m yandex_music_og_songs scan 123

# скан всех плейлистов
.venv/bin/python -m yandex_music_og_songs scan
```

Токен можно передать в команде:

```bash
.venv/bin/python -m yandex_music_og_songs scan 123 --token "ваш_токен"
```

### Пример вывода

```
KIND     ТРЕКОВ   НАЗВАНИЕ
--------------------------------------------------
3        42       Мой плейлист
```

```
Playlist: Мой плейлист (kind=3)
Tracks: 42 | original: 38 | fake: 4
------------------------------------------------------------------------
   1. [FAKE] Artist - Song (Cover) [3:20]
   2. [OK  ] Artist - Real Song [3:45]
```

- `[OK]` — похоже на оригинал
- `[FAKE]` — похоже на фейк

## Где взять KIND

- Команда `list` — колонка **KIND**
- Или URL: `music.yandex.ru/playlists/123` → KIND = `123`

## Частые ошибки

| Ошибка | Решение |
|--------|---------|
| `externally-managed-environment` | Не используй системный `pip`. Запусти `./setup.sh` |
| `No module named yandex_music_og_songs` | Установка не прошла. Запусти `./setup.sh`, потом `.venv/bin/python ...` |
| `Нужен токен` | `export YANDEX_MUSIC_TOKEN="..."` |

## Разработка

```bash
.venv/bin/pip install -e ".[dev]"
.venv/bin/python -m pytest
```
