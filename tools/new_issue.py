"""Подготовка данных для выпуска: небо, карта Таро, номер выпуска.

Запуск: python -m tools.new_issue 2026-10-13
Создаёт content/<дата>/brief.json — по нему Claude пишет issue.json (схема в CONTENT_GUIDE.md).
"""
from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

from astro.sky import sky
from astro.tarot import card_of_day

ROOT = Path(__file__).resolve().parent.parent


def main():
    d = date.fromisoformat(sys.argv[1])
    content = ROOT / "content"
    folder = content / d.isoformat()
    folder.mkdir(parents=True, exist_ok=True)
    earlier = sorted(p.name for p in content.iterdir()
                     if p.is_dir() and p.name[:4].isdigit() and p.name < d.isoformat()
                     and (p / "issue.json").exists())
    recent_titles = []
    for name in earlier[-7:]:
        try:
            iss = json.loads((content / name / "issue.json").read_text(encoding="utf-8"))
            recent_titles.append({"date": name, "headline": iss.get("headline"),
                                  "video": iss["posts"]["video"].get("title"),
                                  "evening": iss["posts"]["evening"].get("rubric")})
        except Exception:
            pass
    brief = {
        "date": d.isoformat(),
        "weekday": ["понедельник", "вторник", "среда", "четверг", "пятница", "суббота", "воскресенье"][d.weekday()],
        "issue_no": len(earlier) + 1,
        "sky": sky(d),
        "tarot": card_of_day(d),
        "recent_issues": recent_titles,
    }
    (folder / "brief.json").write_text(json.dumps(brief, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(brief, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
