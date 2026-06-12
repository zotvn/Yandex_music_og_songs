# Yandex Music OG Songs

Сканирует плейлисты Яндекс Музыки и показывает фейковые треки (cover, radio edit, загрузки и т.д.).

## 1. Скачать

Нужны **Git** и **Python 3.10+**.

```bash
git clone https://github.com/zotvn/Yandex_music_og_songs.git
cd Yandex_music_og_songs
```

Или скачай ZIP с GitHub: https://github.com/zotvn/Yandex_music_og_songs → Code → Download ZIP.

## 2. Установить

```bash
pip install -e .
```

На Windows, если `pip` не находится:

```bash
python -m pip install -e .
```

## 3. Получить токен

1. Открой https://oauth.yandex.ru/authorize?response_type=token&client_id=23cabbbdc6cd418abb4b39c32c41195d
2. Войди в аккаунт Яндекса
3. После редиректа в адресной строке будет `access_token=...` — скопируй значение до `&`

Пример URL:

```
https://oauth.yandex.ru/verification_code#access_token=y0_AgAAAAAAxxxxx&token_type=bearer&expires_in=31536000
```

Токен: `y0_AgAAAAAAxxxxx`

## 4. Запустить

**Linux / macOS:**

```bash
export YANDEX_MUSIC_TOKEN="вставь_свой_токен"
```

**Windows (cmd):**

```cmd
set YANDEX_MUSIC_TOKEN=вставь_свой_токен
```

**Windows (PowerShell):**

```powershell
$env:YANDEX_MUSIC_TOKEN="вставь_свой_токен"
```

### Команды

```bash
# Список плейлистов (нужен KIND для скана)
python -m yandex_music_og_songs list

# Скан одного плейлиста (KIND — число из колонки KIND)
python -m yandex_music_og_songs scan 123

# Скан всех плейлистов
python -m yandex_music_og_songs scan
```

Токен можно передать напрямую:

```bash
python -m yandex_music_og_songs scan 123 --token "y0_AgAAAAAAxxxxx"
```

### Пример вывода

```
Playlist: Мой плейлист (kind=123)
Tracks: 50 | original: 45 | fake: 5
------------------------------------------------------------------------
   1. [FAKE] Artist - Song (Cover) [3:20] (title_suffix:\(cover\))
   2. [OK  ] Artist - Real Song [3:45]
```

- `[OK]` — похоже на оригинал
- `[FAKE]` — похоже на фейк, позже будет замена

## Где взять KIND плейлиста

1. Запусти `python -m yandex_music_og_songs list`
2. Или открой плейлист в браузере: `music.yandex.ru/playlists/123` — число **123** это KIND

## Разработка

```bash
pip install -e ".[dev]"
pytest
```
