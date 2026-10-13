"""Публикация слота дня в Telegram-канал и отчёт админу.

Запуск: python -m publish.telegram morning|tarot|video|evening|report [--date ГГГГ-ММ-ДД]
Переменные окружения: TELEGRAM_TOKEN, CHANNEL_ID, ADMIN_CHAT_ID.
Состояние публикаций пишется в content/<дата>/status.json, повторный запуск слот не дублирует.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import requests

ROOT = Path(__file__).resolve().parent.parent
MSK = ZoneInfo("Europe/Moscow")
API = "https://api.telegram.org/bot{token}/{method}"
SLOTS = {
    "morning": "07:30 Гороскоп дня",
    "tarot": "12:30 Карта Таро",
    "video": "18:00 Видео",
    "evening": "21:00 Вечерний пост",
}
CAPTION_LIMIT = 1024
SLOT_TIME = {"morning": (7, 30), "tarot": (12, 30), "video": (18, 0), "evening": (21, 0), "report": (21, 40)}
MAX_LATE_HOURS = 3  # запуск по расписанию, опоздавший сильнее и перешедший за полночь, не публикуем


def scheduled_day(slot: str, now: datetime) -> tuple[str, float]:
    """GitHub иногда запускает cron с опозданием на часы. Определяем, к какому дню
    относится запуск: если сейчас раньше времени слота, это вчерашний слот."""
    h, m = SLOT_TIME[slot]
    planned = now.replace(hour=h, minute=m, second=0, microsecond=0)
    if now < planned:
        planned -= timedelta(days=1)
    late = (now - planned).total_seconds() / 3600
    return planned.date().isoformat(), late


class TG:
    def __init__(self):
        self.token = os.environ["TELEGRAM_TOKEN"]
        self.channel = os.environ["CHANNEL_ID"]
        self.admin = os.environ.get("ADMIN_CHAT_ID")

    def call(self, method: str, data: dict, files: dict | None = None) -> dict:
        r = requests.post(API.format(token=self.token, method=method), data=data, files=files, timeout=120)
        body = r.json()
        if not body.get("ok"):
            raise RuntimeError(f"{method}: {body.get('description')}")
        return body["result"]

    def text(self, chat, text: str):
        return self.call("sendMessage", {"chat_id": chat, "text": text, "disable_web_page_preview": True})

    def media(self, chat, kind: str, path: Path, caption: str):
        """kind: photo | video. Длинную подпись отправляем отдельным сообщением."""
        short = caption if len(caption) <= CAPTION_LIMIT else ""
        method = "sendPhoto" if kind == "photo" else "sendVideo"
        data = {"chat_id": chat, "caption": short}
        if kind == "video":
            data["supports_streaming"] = True
        with open(path, "rb") as fh:
            self.call(method, data, files={kind: fh})
        if not short and caption:
            self.text(chat, caption)

    def poll(self, chat, question: str, options: list[str]):
        return self.call("sendPoll", {"chat_id": chat, "question": question,
                                      "options": json.dumps(options, ensure_ascii=False),
                                      "is_anonymous": True})

    def alert(self, text: str):
        if self.admin:
            try:
                self.text(self.admin, text)
            except Exception as exc:  # отчёт не должен ронять публикацию
                print(f"Не удалось написать админу: {exc}", file=sys.stderr)


def load_status(folder: Path) -> dict:
    f = folder / "status.json"
    return json.loads(f.read_text(encoding="utf-8")) if f.exists() else {}


def save_status(folder: Path, status: dict):
    (folder / "status.json").write_text(json.dumps(status, ensure_ascii=False, indent=2), encoding="utf-8")


def publish(slot: str, day: str, tg: TG) -> None:
    folder = ROOT / "content" / day
    if not (folder / "issue.json").exists():
        tg.alert(f"⚠️ Меркурий виноват: выпуск на {day} не найден, слот «{SLOTS[slot]}» пропущен.\n"
                 f"Напишите Claude: «сделай выпуск на {day}».")
        sys.exit(1)
    issue = json.loads((folder / "issue.json").read_text(encoding="utf-8"))
    status = load_status(folder)
    if status.get(slot, {}).get("ok"):
        print(f"{slot} уже опубликован, пропускаю")
        return
    post = issue["posts"][slot]
    try:
        if slot == "morning":
            tg.media(tg.channel, "photo", folder / "horoscope.png", post["text"])
        elif slot == "tarot":
            tg.media(tg.channel, "photo", folder / "tarot.png", post["text"])
        elif slot == "video":
            video = folder / "video.mp4"
            if video.exists():
                tg.media(tg.channel, "video", video, post["caption"])
            else:
                tg.media(tg.channel, "photo", folder / "cover.png", post["caption"])
                tg.alert(f"⚠️ {day}: видео не собралось, вместо него вышла обложка. "
                         "Проверьте вкладку Actions → «Сборка видео».")
        elif slot == "evening":
            if post.get("text"):
                tg.text(tg.channel, post["text"])
            if post.get("poll"):
                tg.poll(tg.channel, post["poll"]["question"], post["poll"]["options"])
        status[slot] = {"ok": True, "at": datetime.now(MSK).isoformat(timespec="minutes")}
        print(f"{slot}: опубликован")
    except Exception as exc:
        status[slot] = {"ok": False, "error": str(exc)}
        tg.alert(f"❌ {day}, «{SLOTS[slot]}» не вышел: {exc}")
        save_status(folder, status)
        sys.exit(1)
    save_status(folder, status)


def report(day: str, tg: TG) -> None:
    folder = ROOT / "content" / day
    status = load_status(folder) if folder.exists() else {}
    issue = {}
    if (folder / "issue.json").exists():
        issue = json.loads((folder / "issue.json").read_text(encoding="utf-8"))
    lines = [f"Меркурий виноват · {day}"]
    done = 0
    for slot, label in SLOTS.items():
        st = status.get(slot, {})
        extra = ""
        if slot == "tarot" and issue:
            extra = f": {issue['posts']['tarot'].get('card', '')}"
        if slot == "video" and issue:
            extra = f": {issue['posts']['video'].get('title', '')}"
        if st.get("ok"):
            done += 1
            lines.append(f"✅ {label}{extra}")
        else:
            lines.append(f"❌ {label}{extra} — {st.get('error', 'не опубликован')}")
    tomorrow = (datetime.fromisoformat(day) + timedelta(days=1)).date().isoformat()
    tfolder = ROOT / "content" / tomorrow
    if (tfolder / "issue.json").exists():
        video = "видео собрано" if (tfolder / "video.mp4").exists() else "видео ещё собирается"
        lines.append(f"Завтра: выпуск готов, {video}")
    else:
        lines.append("Завтра: выпуска пока нет — Claude готовит его в 20:00, проверьте позже")
    lines.insert(1, f"Вышло {done} из {len(SLOTS)}")
    tg.alert("\n".join(lines))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("slot", choices=[*SLOTS, "report"])
    ap.add_argument("--date")
    args = ap.parse_args()
    tg = TG()
    now = datetime.now(MSK)
    if args.date is None:
        if os.environ.get("GITHUB_EVENT_NAME") == "schedule":
            args.date, late = scheduled_day(args.slot, now)
            if args.date != now.date().isoformat() and late > MAX_LATE_HOURS and args.slot != "report":
                label = SLOTS[args.slot]
                tg.alert(f"⚠️ GitHub запустил слот «{label}» за {args.date} с опозданием {late:.1f} ч. "
                         f"Пропускаю, чтобы пост не вышел ночью. Опубликовать вручную: Actions → Публикация.")
                print(f"{args.slot}: опоздание {late:.1f} ч, пропуск")
                return
        else:
            args.date = now.date().isoformat()
    if args.slot == "report":
        report(args.date, tg)
    else:
        publish(args.slot, args.date, tg)


if __name__ == "__main__":
    main()
