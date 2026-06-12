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
# быстрый список
.venv/bin/python -m yandex_music_og_songs export 1020 songs.txt

# скан — результат сразу по каждому треку
.venv/bin/python -m yandex_music_og_songs scan 1020

# выбор / исключение (без повторного скана)
.venv/bin/python -m yandex_music_og_songs choose 1020 choices.txt
```

## Статусы (появляются сразу)

| Статус | Значение |
|--------|----------|
| OK | Норм |
| FAKE | Фейк, будет заменён |
| ???? | Несколько исполнителей — выбери |
| SKIP | Не трогать |

## choices.txt

```
# выбрать исполнителя
28: 1

# НЕ менять трек (убрать из замены)
15: skip
```

## review.txt

```
15. [SKIP] Artist - Song [3:00]
28. [REPLACE] TommyMuzzic - back to friends [3:19]
```
