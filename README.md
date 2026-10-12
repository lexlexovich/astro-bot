# astro-bot · «Меркурий виноват»

Автоматический Telegram-канал об астрологии. Ведёт AI-астролог Вега.

## Как это работает

1. Каждый вечер Claude готовит выпуск на завтра: считает реальное небо (`astro/sky.py`), выбирает карту Таро (`astro/tarot.py`), пишет тексты по `CONTENT_GUIDE.md` в `content/<дата>/issue.json`, рисует карточки (`render/cards.py`) и пушит в репозиторий.
2. Пуш запускает «Сборку видео» (`.github/workflows/video.yml`): озвучка, субтитры, MP4 9:16 в `content/<дата>/video.mp4`.
3. «Публикация» (`.github/workflows/publish.yml`) выкладывает посты в канал: 07:30, 12:30, 18:00, 21:00 по Москве, а в 21:40 присылает отчёт владельцу.

GitHub запускает задачи по расписанию с задержкой до 10–20 минут — это нормально.

## Секреты репозитория

| Секрет | Что это |
| --- | --- |
| `TELEGRAM_TOKEN` | токен бота @Vega_astrolog_bot |
| `CHANNEL_ID` | `@merkuriy_vinovat` |
| `ADMIN_CHAT_ID` | chat id владельца для отчётов |

## Ручной запуск

GitHub → Actions → «Публикация» → Run workflow → слот (`morning`, `tarot`, `video`, `evening`, `report`) и дата.

## Локально

```bash
pip install -r requirements.txt
python -m tools.new_issue 2026-10-13      # бриф с небом
python -m render.cards content/2026-10-13 # карточки
python -m render.video content/2026-10-13 # видео
```

Шрифты Oswald и PT Serif — под лицензией SIL Open Font License (`assets/fonts/OFL-*.txt`).
