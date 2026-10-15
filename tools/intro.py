"""Визитка канала: закреплённое видео для TikTok/Reels и карточка для закреплённого поста в Telegram.

Запуск: python -m tools.intro → assets/intro/intro.mp4 (≈16 с, без голоса, с музыкой) и assets/intro/intro_tg.png
"""
from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw

from render.cards import (INK, PAPER, RED, double_rule, draw_lines, fit_font, mercury, oswald, serif, stamp,
                          video_cover, wrap)
from render.video import MUSIC, ending, frame

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "assets" / "intro"

SLIDES = [
    ("Я Вега — AI-астролог", "Я не человек и не скрываю этого. Читаю реальное небо и перевожу его на человеческий."),
    ("Астрология без драмы", "Никаких «опасных дней» и «порчи». Символика, ирония и пара здравых мыслей на день."),
    ("Каждый день здесь", "08:00 — гороскоп. 13:00 — карта Таро. 18:00 — разбор неба."),
    ("Полный гороскоп — в Telegram", "Все 12 знаков каждое утро, карта дня и опросы. Ссылка в профиле."),
]

TG_TEXT = """Знакомьтесь: «Меркурий виноват» 🪐

Я Вега — AI-астролог. Не человек и не притворяюсь им: считаю реальное положение планет и перевожу небо на человеческий язык. Без запугивания, «опасных дней» и обещаний судьбы — астрология здесь язык символов и повод подумать.

Что здесь каждый день:
07:30 — гороскоп для всех 12 знаков
12:30 — карта Таро дня
18:00 — видео: разбор неба, совместимость, зеркальные часы
21:00 — опрос, а утром — его итоги

Включите уведомления, чтобы гороскоп приходил к утреннему кофе. А если что-то пошло не так — вы знаете, кто виноват."""


def tg_card(out: Path):
    W, H, M = 1080, 1350, 72
    img = Image.new("RGB", (W, H), PAPER)
    d = ImageDraw.Draw(img)
    size = 124
    while d.textlength("МЕРКУРИЙ ВИНОВАТ", font=oswald(size)) > W - 2 * M:
        size -= 2
    d.text((W / 2, M), "МЕРКУРИЙ ВИНОВАТ", font=oswald(size), fill=INK, anchor="mt")
    y = M + int(size * 1.25)
    double_rule(d, M, W - M, y)
    y += 40
    d.text((M, y), "Ежедневная сводка неба. Ведёт AI-астролог Вега", font=serif(32, "Italic"), fill=INK)
    y += 90
    rows = [("07:30", "Гороскоп для всех 12 знаков"), ("12:30", "Карта Таро дня"),
            ("18:00", "Видео: разбор неба"), ("21:00", "Опрос — итоги утром")]
    for t, label in rows:
        d.text((M, y), t, font=oswald(84), fill=RED)
        d.text((M + 270, y + 18), label, font=serif(44), fill=INK)
        y += 130
        d.line([M, y - 22, W - M, y - 22], fill=(185, 178, 160), width=2)
    mercury(img, W - 230, H - 420, 250)
    stamp(img, "ВИНОВАТ", (W - 260, H - 170), 52)
    d.text((M, H - 150), "t.me/merkuriy_vinovat", font=oswald(48, "Medium"), fill=INK)
    img.save(out, optimize=True)


def video(out: Path):
    tmp = Path(tempfile.mkdtemp())
    issue = {"date": "2026-10-15", "issue_no": 0,
             "posts": {"video": {"cover_headline": "Кто такая Вега?", "cover_sub": "AI-астролог канала «Меркурий виноват»"}}}
    frames = []
    cover = tmp / "c.png"
    video_cover(issue, cover)
    # обложка для визитки: без номера выпуска и плашки «срочно»
    from render.cards import tag
    im = Image.open(cover)
    d = ImageDraw.Draw(im)
    d.rectangle([560, 245, 1000, 305], fill=PAPER)
    d.rectangle([80, 466, 560, 535], fill=PAPER)
    tag(d, (80, 470), "ЗНАКОМСТВО", 40)
    im.save(cover)
    frames.append((cover, 2.2))
    for i, (on, sub) in enumerate(SLIDES, 1):
        f = tmp / f"f{i}.png"
        frame(issue, on, sub, i, len(SLIDES), f)
        frames.append((f, 3.4))
    end = tmp / "e.png"
    ending(issue, end)
    frames.append((end, 2.6))
    fade = 0.4
    inputs, chain = [], []
    for f, dur in frames:
        inputs += ["-loop", "1", "-t", f"{dur}", "-i", str(f)]
    last, off = "[0:v]", 0.0
    for k in range(1, len(frames)):
        off += frames[k - 1][1] - fade
        chain.append(f"{last}[{k}:v]xfade=transition=fade:duration={fade}:offset={off:.2f}[x{k}]")
        last = f"[x{k}]"
    total = sum(d for _, d in frames) - fade * (len(frames) - 1)
    chain.append(f"{last}format=yuv420p[v]")
    tracks = json.loads((MUSIC / "tracks.json").read_text(encoding="utf-8"))
    track = MUSIC / next(t["file"] for t in tracks if t["mood"] == "light")
    n = len(frames)
    chain.append(f"[{n}:a]atrim=0:{total:.2f},loudnorm=I=-18:TP=-2,afade=t=in:d=1,"
                 f"afade=t=out:st={total - 1.5:.2f}:d=1.5[a]")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", *inputs, "-i", str(track),
                    "-filter_complex", ";".join(chain), "-map", "[v]", "-map", "[a]", "-r", "30",
                    "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-c:a", "aac", "-b:a", "160k",
                    "-t", f"{total:.2f}", "-movflags", "+faststart", str(out)], check=True)
    shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    tg_card(OUT / "intro_tg.png")
    (OUT / "intro_tg.txt").write_text(TG_TEXT, encoding="utf-8")
    video(OUT / "intro.mp4")
    print("Визитка готова:", OUT)
