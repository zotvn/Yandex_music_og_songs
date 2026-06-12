# Yandex Music OG Songs

Сканирует плейлисты Яндекс Музыки, находит фейки и готовит список на замену.

## Установка (Arch Linux)

```bash
git clone https://github.com/zotvn/Yandex_music_og_songs.git
cd Yandex_music_og_songs
chmod +x setup.sh && ./setup.sh
export YANDEX_MUSIC_TOKEN="ваш_токен"
```

## Команды

```bash
# список плейлистов (KIND — первый столбец)
.venv/bin/python -m yandex_music_og_songs list

# скан с авто-детектом фейков
.venv/bin/python -m yandex_music_og_songs scan 1020

# экспорт в txt без меток FAKE/OK
.venv/bin/python -m yandex_music_og_songs export 1020 songs.txt

# экспорт для проверки нейронкой ([REPLACE] у найденных фейков)
.venv/bin/python -m yandex_music_og_songs review 1020 review.txt

# после правки файла — применить метки [REPLACE]
.venv/bin/python -m yandex_music_og_songs import 1020 review.txt
```

## Формат review.txt

```
# Отметь [REPLACE] у треков для замены
1. Artist - Song [3:00]
28. [REPLACE] TommyMuzzic - back to friends [3:19]
```

Добавь `[REPLACE]` к любым трекам, которые нейронка нашла. `import` покажет финальный план замены.

## Что считается фейком

- cover, radio edit, karaoke в version/title
- чужой артист (сверка с каталогом Яндекса)
- `OWN_REPLACED_TO_UGC`

**Не фейк:**
- твои загрузки (user upload)
- официальные версии (Arcane, soundtrack, remix)

## Токен

Получить: https://oauth.yandex.ru/authorize?response_type=token&client_id=23cabbbdc6cd418abb4b39c32c41195d

Отозвать: https://id.yandex.ru/security → Приложения → отключить
