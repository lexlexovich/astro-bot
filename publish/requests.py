"""Сбор заявок на разбор пары знаков из комментариев канала (группа обсуждения).

Бот читает новые сообщения через getUpdates, находит в тексте два знака зодиака
и складывает заявку в content/requests.json. Claude берёт заявки оттуда для рубрики
«Разбор пары по заявке». Бот должен быть участником (лучше админом) группы обсуждения.
"""
from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent.parent
FILE = ROOT / "content" / "requests.json"
MSK = ZoneInfo("Europe/Moscow")

SIGNS = [
    ("Овен", r"ов(ен|н[аеуыо]\w*)"),
    ("Телец", r"тел(ец|ьц\w*)"),
    ("Близнецы", r"близнец\w*"),
    ("Рак", r"рак(а|у|ом|е|и|ов|ам)?"),
    ("Лев", r"(лев|льв(а|у|ом|е|ы|ов|ам|ица|ицы))"),
    ("Дева", r"дев(а|ы|е|у|ой|ам|ами|ах)"),
    ("Весы", r"вес(ы|ов|ам|ами|ах)"),
    ("Скорпион", r"скорпион\w*"),
    ("Стрелец", r"стрел(ец|ьц\w*)"),
    ("Козерог", r"козерог\w*"),
    ("Водолей", r"водоле\w*"),
    ("Рыбы", r"рыб(а|ы|е|у|ой|ам|ами|ах)?"),
]
PATTERNS = [(name, re.compile(rf"(?<![а-яё]){p}(?![а-яё])", re.I)) for name, p in SIGNS]


def find_signs(text: str) -> list[str]:
    found = []
    for name, pat in PATTERNS:
        for m in pat.finditer(text or ""):
            found.append((m.start(), name))
    found.sort()
    signs = [n for _, n in found]
    if len(set(signs)) == 1 and re.search(r"\bоба\b|\bобе\b|\bтоже\b", text or "", re.I):
        return [signs[0], signs[0]]
    out = []
    for s in signs:
        if s not in out:
            out.append(s)
    return out[:2]


def load() -> dict:
    if FILE.exists():
        return json.loads(FILE.read_text(encoding="utf-8"))
    return {"offset": 0, "requests": []}


def collect(tg) -> int:
    """Забирает новые сообщения и сохраняет заявки. Возвращает число новых заявок."""
    data = load()
    try:
        updates = tg.call("getUpdates", {"offset": data["offset"], "timeout": 0,
                                         "allowed_updates": json.dumps(["message"])})
    except Exception as exc:  # заявки не должны ронять публикацию
        print(f"getUpdates: {exc}")
        return 0
    new = 0
    for u in updates:
        data["offset"] = max(data["offset"], u["update_id"] + 1)
        msg = u.get("message") or {}
        chat = msg.get("chat", {})
        if chat.get("type") not in ("group", "supergroup"):
            continue
        frm = msg.get("from") or {}
        if frm.get("is_bot") or msg.get("is_automatic_forward"):
            continue
        text = msg.get("text") or msg.get("caption") or ""
        signs = find_signs(text)
        if len(signs) < 2:
            continue
        data["requests"].append({
            "at": datetime.fromtimestamp(msg.get("date", 0), MSK).isoformat(timespec="minutes"),
            "chat_id": chat.get("id"), "message_id": msg.get("message_id"),
            "name": frm.get("first_name", ""), "text": text[:300], "signs": signs, "used": None,
        })
        new += 1
        try:
            tg.call("sendMessage", {"chat_id": chat.get("id"), "reply_to_message_id": msg.get("message_id"),
                                    "text": f"Принято: {signs[0]} + {signs[1]} 🔭 Разберу вашу пару в канале в ближайшие дни."})
        except Exception as exc:
            print(f"Ответ на заявку не отправлен: {exc}")
    FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return new
