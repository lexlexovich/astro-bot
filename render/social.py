"""Форматы для Instagram и TikTok: карусель гороскопа и короткий Reels с картой Таро.

Запуск: python -m render.social content/2026-10-13
Карусель: carousel_1.jpg … carousel_6.jpg (1080×1350): обложка, 4 слайда по 3 знака, призыв в Telegram.
Reels: tarot_reel.mp4 (1080×1920, 9 с): карта дня с медленным наездом камеры и музыкой, без голоса.
Short: horoscope_short.mp4 (1080×1920, ~14 с): слайды карусели по очереди, для YouTube Shorts.
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
from datetime import date
from pathlib import Path

from PIL import Image, ImageDraw

from render.cards import (MONTHS, GREY, INK, PAPER, RED, SIGNS, double_rule, draw_lines, fit_font, masthead, mercury,
                          oswald, ru_date, serif, stamp, tag, wrap)

CW, CH, M = 1080, 1350, 72
REEL_SECONDS = 9


def _footer(d: ImageDraw.ImageDraw, page: int, total: int):
    foot = oswald(26, "Medium")
    d.text((M, CH - M + 10), "t.me/merkuriy_vinovat", font=foot, fill=INK, anchor="ls")
    d.text((CW - M, CH - M + 10), f"{page} / {total}", font=foot, fill=INK, anchor="rs")


def _small_head(d: ImageDraw.ImageDraw, issue: dict):
    hf = oswald(44)
    d.text((M, M), "МЕРКУРИЙ ВИНОВАТ", font=hf, fill=INK)
    d.text((CW - M, M + 12), ru_date(issue["date"]), font=serif(26), fill=INK, anchor="ra")
    double_rule(d, M, CW - M, M + 70)
    return M + 100


def carousel(issue: dict, folder: Path) -> list[Path]:
    total = 6
    out = []
    # 1 — обложка
    img = Image.new("RGB", (CW, CH), PAPER)
    d = ImageDraw.Draw(img)
    y = masthead(d, issue, M, CW - M, M)
    y = tag(d, (M, y + 20), "ГОРОСКОП ДНЯ", 34) + 36
    head = issue["headline"].upper()
    hf = fit_font(d, head, oswald, CW - 2 * M, 3, 112, 64)
    y = draw_lines(d, (M, y), wrap(d, head, hf, CW - 2 * M), hf, INK, int(hf.size * 1.12)) + 34
    lf = serif(34, "Italic")
    for size in (34, 32, 30, 28):  # подводка целиком, без обрыва
        lf = serif(size, "Italic")
        if len(wrap(d, issue["lead"], lf, CW - 2 * M)) * int(size * 1.35) <= CH - 250 - y:
            break
    lh = int(lf.size * 1.35)
    fit = int(max(0, (CH - 250 - y) // lh))  # подводка не должна налезать на плашку
    draw_lines(d, (M, y), wrap(d, issue["lead"], lf, CW - 2 * M)[:fit], lf, INK, lh)
    cta = oswald(46)
    d.rectangle([M, CH - 210, CW - M, CH - 120], fill=INK)
    d.text((CW / 2, CH - 165), "ЛИСТАЙТЕ: НАЙДИТЕ СВОЙ ЗНАК »", font=cta, fill=PAPER, anchor="mm")
    _footer(d, 1, total)
    out.append(img)
    # 2–5 — по три знака
    for g in range(4):
        img = Image.new("RGB", (CW, CH), PAPER)
        d = ImageDraw.Draw(img)
        y = _small_head(d, issue)
        signs = SIGNS[g * 3:(g + 1) * 3]
        block = (CH - M - 40 - y) // 3
        tf = serif(36)
        for size in (44, 42, 40, 38, 36, 34, 32, 30):
            f = serif(size)
            if all(len(wrap(d, issue["horoscope"].get(s, ""), f, CW - 2 * M)) <= 3 for s in signs):
                tf = f
                break
        for i, s in enumerate(signs):
            yy = y + i * block + 10
            d.text((M, yy), s.upper(), font=oswald(68), fill=INK)
            lines = wrap(d, issue["horoscope"].get(s, ""), tf, CW - 2 * M)[:3]
            draw_lines(d, (M, yy + 92), lines, tf, INK, int(tf.size * 1.3))
            if i < 2:
                d.line([M, yy + block - 22, CW - M, yy + block - 22], fill=GREY, width=2)
        _footer(d, g + 2, total)
        out.append(img)
    # 6 — призыв
    img = Image.new("RGB", (CW, CH), PAPER)
    d = ImageDraw.Draw(img)
    y = _small_head(d, issue) + 60
    big = "ПОЛНЫЙ ГОРОСКОП — КАЖДОЕ УТРО В TELEGRAM"
    bf = fit_font(d, big, oswald, CW - 2 * M, 4, 110, 70)
    y = draw_lines(d, (M, y), wrap(d, big, bf, CW - 2 * M), bf, INK, int(bf.size * 1.12)) + 30
    sf = serif(36, "Italic")
    y = draw_lines(d, (M, y), wrap(d, "Здесь только главное. Там — разборы неба, карта дня и опросы.", sf,
                                    CW - 2 * M), sf, INK, 48) + 50
    d.text((M, y), "t.me/merkuriy_vinovat", font=oswald(60), fill=RED)
    mercury(img, CW - 230, CH - 470, 260)
    stamp(img, "ВИНОВАТ", (CW - 270, CH - 200), 52)
    _footer(d, total, total)
    out.append(img)

    paths = []
    for i, im in enumerate(out, 1):
        p = folder / f"carousel_{i}.jpg"
        im.save(p, quality=92)
        paths.append(p)
    return paths


def _reel_frame_art(issue: dict, art: Path, out: Path):
    from render.cards import art_image
    W, H = 1080, 1920
    img = Image.new("RGB", (W, H), PAPER)
    d = ImageDraw.Draw(img)
    double_rule(d, 80, W - 80, 150)
    d.text((80, 175), "МЕРКУРИЙ ВИНОВАТ", font=oswald(40), fill=INK)
    d.text((W - 80, 185), "КАРТА ДНЯ", font=oswald(40), fill=RED, anchor="ra")
    d.rectangle([80, 242, W - 80, 244], fill=INK)
    a = art_image(art, 1230)
    x = (W - a.width) // 2
    img.paste(a, (x, 280))
    d.rectangle([x - 1, 279, x + a.width, 280 + a.height], outline=INK, width=3)
    t = issue["posts"]["tarot"]
    name = t["card"].upper()
    nf = fit_font(d, name, oswald, W - 160, 1, 100, 60)
    d.text((W / 2, 1555), name, font=nf, fill=INK, anchor="mt")
    kf = serif(38, "Italic")
    ky = 1555 + int(nf.size * 1.3)
    for ln in wrap(d, t.get("keywords", ""), kf, W - 160)[:2]:
        d.text((W / 2, ky), ln, font=kf, fill=INK, anchor="mt")
        ky += 50
    img.save(out)


def _reel_frame(issue: dict, folder: Path, out: Path):
    from render.cards import tarot_info
    art, _ = tarot_info(issue["posts"]["tarot"]["card"])
    if art:
        return _reel_frame_art(issue, art, out)
    W, H = 1080, 1920
    img = Image.new("RGB", (W, H), PAPER)
    d = ImageDraw.Draw(img)
    double_rule(d, 80, W - 80, 170)
    d.text((80, 195), "МЕРКУРИЙ ВИНОВАТ", font=oswald(40), fill=INK)
    d.text((W - 80, 205), ru_date(issue["date"]), font=serif(30), fill=INK, anchor="ra")
    d.rectangle([80, 262, W - 80, 264], fill=INK)
    d.text((W / 2, 330), "КАРТА ДНЯ", font=oswald(110), fill=RED, anchor="mt")
    card = Image.open(folder / "tarot.png").convert("RGB")
    # без газетной шапки: берём саму карту из центра карточки
    # находим рамку карты: первая тёмная точка на левой границе рамки (x=282)
    px = card.load()
    top = next((yy for yy in range(200, card.height - 120)
                if all(sum(px[284, yy + k]) < 150 for k in range(0, 120, 4))), 300)
    crop = card.crop((270, top - 10, 810, top + 772))
    crop = crop.resize((int(crop.width * 1.25), int(crop.height * 1.25)), Image.LANCZOS)
    img.paste(crop, ((W - crop.width) // 2, 520))
    d.text((W / 2, 1500 + 340 - 120), "Что она значит сегодня — в подписи", font=serif(40, "Italic"),
           fill=INK, anchor="mm")
    img.save(out)


def tarot_reel(issue: dict, folder: Path) -> Path | None:
    if not shutil.which("ffmpeg"):
        print("ffmpeg не найден, Reels с Таро пропущен")
        return None
    from render.video import MUSIC
    tmp = Path(tempfile.mkdtemp())
    frame = tmp / "frame.png"
    _reel_frame(issue, folder, frame)
    out = folder / "tarot_reel.mp4"
    tracks = json.loads((MUSIC / "tracks.json").read_text(encoding="utf-8"))
    pool = [t for t in tracks if t["mood"] == "space"] or tracks
    day = date.fromisoformat(issue["date"]).toordinal()
    track = MUSIC / pool[(day + 2) % len(pool)]["file"]  # не тот же трек, что в видео дня
    fps, n = 30, REEL_SECONDS * 30
    vf = (f"scale=2160:-1,zoompan=z='1+0.07*on/{n}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"
          f":d={n}:s=1080x1920:fps={fps},format=yuv420p")
    af = f"atrim=0:{REEL_SECONDS},loudnorm=I=-18:TP=-2,afade=t=in:d=1,afade=t=out:st={REEL_SECONDS - 1.5}:d=1.5"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-loop", "1", "-i", str(frame), "-i", str(track),
                    "-vf", vf, "-af", af, "-t", str(REEL_SECONDS), "-c:v", "libx264", "-preset", "medium",
                    "-crf", "20", "-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart", str(out)], check=True)
    shutil.rmtree(tmp, ignore_errors=True)
    return out


SLIDE_SECONDS = 2.6
FADE = 0.4


def horoscope_short(issue: dict, folder: Path) -> Path | None:
    """Гороскоп для YouTube Shorts: 6 слайдов карусели по очереди с наплывом и музыкой (~15 с)."""
    if not shutil.which("ffmpeg"):
        print("ffmpeg не найден, Short с гороскопом пропущен")
        return None
    from render.video import MUSIC
    tmp = Path(tempfile.mkdtemp())
    W, H = 1080, 1920
    frames = []
    for i in range(1, 7):
        slide = Image.open(folder / f"carousel_{i}.jpg").convert("RGB")
        img = Image.new("RGB", (W, H), PAPER)
        d = ImageDraw.Draw(img)
        dd = date.fromisoformat(issue["date"])
        head = f"ГОРОСКОП НА {dd.day} {MONTHS[dd.month - 1].upper()}"
        hf = fit_font(d, head, oswald, W - 160, 1, 96, 56)
        d.text((W / 2, 200), head, font=hf, fill=RED, anchor="mm")
        img.paste(slide, (0, 300))
        if i == 1:  # в видео листать не нужно — меняем плашку обложки
            d.rectangle([M, 300 + CH - 210, CW - M, 300 + CH - 120], fill=INK)
            d.text((CW / 2, 300 + CH - 165), "ВАШ ЗНАК — ЧЕРЕЗ ПАРУ СЕКУНД", font=oswald(46), fill=PAPER, anchor="mm")
        f = tmp / f"s{i}.png"
        img.save(f)
        frames.append(f)
    n = len(frames)
    total = n * SLIDE_SECONDS - (n - 1) * FADE
    inputs = []
    for f in frames:
        inputs += ["-loop", "1", "-t", f"{SLIDE_SECONDS}", "-i", str(f)]
    tracks = json.loads((MUSIC / "tracks.json").read_text(encoding="utf-8"))
    pool = [t for t in tracks if t["mood"] == "space"] or tracks
    day = date.fromisoformat(issue["date"]).toordinal()
    track = MUSIC / pool[(day + 4) % len(pool)]["file"]
    chain, last = [], "[0:v]"
    for k in range(1, n):
        off = k * (SLIDE_SECONDS - FADE)
        out = f"[x{k}]"
        chain.append(f"{last}[{k}:v]xfade=transition=fade:duration={FADE}:offset={off:.2f}{out}")
        last = out
    chain.append(f"{last}format=yuv420p[v]")
    chain.append(f"[{n}:a]atrim=0:{total:.2f},loudnorm=I=-18:TP=-2,afade=t=in:d=1,"
                 f"afade=t=out:st={total - 1.5:.2f}:d=1.5[a]")
    out = folder / "horoscope_short.mp4"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", *inputs, "-i", str(track),
                    "-filter_complex", ";".join(chain), "-map", "[v]", "-map", "[a]", "-r", "30",
                    "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-c:a", "aac", "-b:a", "160k",
                    "-t", f"{total:.2f}", "-movflags", "+faststart", str(out)], check=True)
    shutil.rmtree(tmp, ignore_errors=True)
    return out


def render_social(folder: Path, reel: bool = True):
    folder = folder.resolve()
    issue = json.loads((folder / "issue.json").read_text(encoding="utf-8"))
    carousel(issue, folder)
    if reel and not (folder / "tarot_reel.mp4").exists():
        tarot_reel(issue, folder)
    if reel and not (folder / "horoscope_short.mp4").exists():
        horoscope_short(issue, folder)
    print(f"Карусель, Reels Таро и Short с гороскопом готовы: {folder}")


if __name__ == "__main__":
    render_social(Path(sys.argv[1]))
