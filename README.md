# Yandex Music OG Songs

## Установка

```bash
git clone https://github.com/zotvn/Yandex_music_og_songs.git
cd Yandex_music_og_songs
chmod +x setup.sh && ./setup.sh
export YANDEX_MUSIC_TOKEN="ваш_токен"
```

## Команды

```bash
# список плейлистов
.venv/bin/python -m yandex_music_og_songs list

# быстрый экспорт списка (без проверки артиста)
.venv/bin/python -m yandex_music_og_songs export 1020 songs.txt

# полный скан: Яндекс + MusicBrainz
.venv/bin/python -m yandex_music_og_songs scan 1020

# если в конце [????] — выбери исполнителя
.venv/bin/python -m yandex_music_og_songs choose 1020 choices.txt
```

## Выбор исполнителя

После `scan` создаётся `choices.txt`:

```
28. TommyMuzzic - back to friends
  1) sombr [yandex, musicbrainz]
  2) TommyMuzzic [yandex]
```

Запиши выбор:

```
28: 1
```

Потом:

```bash
.venv/bin/python -m yandex_music_og_songs choose 1020 choices.txt
```

## Статусы

- `[OK]` — исполнитель совпал с интернетом
- `[FAKE]` — найден другой исполнитель
- `[????]` — несколько вариантов, нужен твой выбор

Твои загрузки не помечаются как фейк.
