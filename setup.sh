#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

if [ ! -d ".venv" ]; then
    echo "Создаю виртуальное окружение .venv ..."
    python -m venv .venv
fi

echo "Устанавливаю зависимости ..."
.venv/bin/pip install -q --upgrade pip
.venv/bin/pip install -q -e .

echo ""
echo "Готово. Дальше:"
echo '  export YANDEX_MUSIC_TOKEN="ваш_токен"'
echo "  .venv/bin/python -m yandex_music_og_songs list"
echo "  .venv/bin/python -m yandex_music_og_songs scan 123"
