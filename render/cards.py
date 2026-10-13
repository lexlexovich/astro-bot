"""Карточки в стиле «Срочная сводка»: гороскоп дня, карта Таро, обложка видео.

Запуск: python -m render.cards content/2026-10-13
Берёт issue.json из папки выпуска и кладёт рядом horoscope.png, tarot.png, cover.png.
"""
from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
FONTS = ROOT / "assets" / "fonts"

PAPER = (239, 235, 224)
INK = (17, 17, 17)
RED = (215, 38, 30)
GREY = (185, 178, 160)

SIGNS = ["Овен", "Телец", "Близнецы", "Рак", "Лев", "Дева", "Весы", "Скорпион",
         "Стрелец", "Козерог", "Водолей", "Рыбы"]
MONTHS = ["января", "февраля", "марта", "апреля", "мая", "июня", "июля", "августа",
          "сентября", "октября", "ноября", "декабря"]


def oswald(size: int, weight: str = "Bold") -> ImageFont.FreeTypeFont:
    f = ImageFont.truetype(str(FONTS / "Oswald.ttf"), size)
    try:
        f.set_variation_by_name(weight)
    except Exception:
        pass
    return f


def serif(size: int, style: str = "Regular") -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(FONTS / f"PTSerif-{style}.ttf"), size)


def ru_date(iso: str) -> str:
    d = date.fromisoformat(iso)
    return f"{d.day} {MONTHS[d.month - 1]} {d.year}"


def wrap(draw: ImageDraw.ImageDraw, text: str, font, width: int) -> list[str]:
    lines, line = [], ""
    for word in text.split():
        test = f"{line} {word}".strip()
        if draw.textlength(test, font=font) <= width:
            line = test
        else:
            if line:
                lines.append(line)
            line = word
    if line:
        lines.append(line)
    return lines


def draw_lines(draw, xy, lines, font, fill, spacing):
    x, y = xy
    for ln in lines:
        draw.text((x, y), ln, font=font, fill=fill)
        y += spacing
    return y


def fit_font(draw, text, make_font, width, max_lines, start, minimum):
    size = start
    while size > minimum:
        f = make_font(size)
        if len(wrap(draw, text, f, width)) <= max_lines:
            return f
        size -= 4
    return make_font(minimum)


def double_rule(draw, x0, x1, y, thick=6):
    draw.rectangle([x0, y, x1, y + 2], fill=INK)
    draw.rectangle([x0, y + thick - 2, x1, y + thick], fill=INK)


def mercury(img: Image.Image, cx: int, top: int, height: int, color=INK):
    """Символ Меркурия: рога, круг, крест. height — общая высота знака."""
    d = ImageDraw.Draw(img)
    k = height / 420  # исходная схема 420 px высотой
    w = int(34 * k)
    r = 95 * k
    # рога — нижняя половина окружности
    hr = 95 * k
    d.arc([cx - hr, top - hr, cx + hr, top + hr], start=0, end=180, fill=color, width=w)
    cy = top + 190 * k
    d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=color, width=w)
    d.line([cx, cy + r, cx, cy + r + 135 * k], fill=color, width=w)
    d.line([cx - 65 * k, cy + r + 70 * k, cx + 65 * k, cy + r + 70 * k], fill=color, width=w)


def stamp(img: Image.Image, text: str, center: tuple[int, int], size: int = 68, angle: float = 12):
    font = oswald(size)
    tmp = ImageDraw.Draw(img)
    tw = tmp.textlength(text, font=font)
    pad_x, pad_y, border = int(size * 0.45), int(size * 0.25), max(5, size // 9)
    w, h = int(tw + pad_x * 2), int(size * 1.35 + pad_y * 2)
    layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    ld = ImageDraw.Draw(layer)
    ld.rectangle([0, 0, w - 1, h - 1], fill=PAPER + (210,), outline=RED + (255,), width=border)
    ld.text((w / 2, h / 2), text, font=font, fill=RED + (255,), anchor="mm")
    layer = layer.rotate(angle, expand=True, resample=Image.BICUBIC)
    img.paste(layer, (int(center[0] - layer.width / 2), int(center[1] - layer.height / 2)), layer)


def tag(draw, xy, text, size=28):
    font = oswald(size)
    x, y = xy
    tw = draw.textlength(text, font=font)
    draw.rectangle([x, y, x + tw + 28, y + size * 1.45], fill=RED)
    draw.text((x + 14, y + size * 0.72), text, font=font, fill=PAPER, anchor="lm")
    return y + size * 1.45


def masthead(draw, issue, x0, x1, y, size=124):
    while draw.textlength("МЕРКУРИЙ ВИНОВАТ", font=oswald(size)) > (x1 - x0) and size > 40:
        size -= 2
    font = oswald(size)
    draw.text(((x0 + x1) / 2, y), "МЕРКУРИЙ ВИНОВАТ", font=font, fill=INK, anchor="mt")
    y += int(size * 1.25)
    draw.rectangle([x0, y, x1, y + 2], fill=INK)
    meta = serif(24)
    y += 12
    draw.text((x0, y), "Ежедневная сводка неба", font=meta, fill=INK)
    draw.text(((x0 + x1) / 2, y), ru_date(issue["date"]), font=meta, fill=INK, anchor="ma")
    draw.text((x1, y), f"Выпуск № {issue.get('issue_no', 1)}", font=meta, fill=INK, anchor="ra")
    y += 40
    double_rule(draw, x0, x1, y)
    return y + 22


def horoscope_card(issue: dict, out: Path):
    W, H, M = 1080, 1350, 64
    img = Image.new("RGB", (W, H), PAPER)
    d = ImageDraw.Draw(img)
    y = masthead(d, issue, M, W - M, M)
    y = tag(d, (M, y + 6), "ГЛАВНОЕ") + 14
    head_font = fit_font(d, issue["headline"].upper(), oswald, W - 2 * M, 2, 84, 52)
    lines = wrap(d, issue["headline"].upper(), head_font, W - 2 * M)
    y = draw_lines(d, (M, y), lines, head_font, INK, int(head_font.size * 1.2)) + 26
    lead_font = serif(26, "Italic")
    y = draw_lines(d, (M, y), wrap(d, issue["lead"], lead_font, W - 2 * M)[:3], lead_font, INK, 35) + 18
    d.rectangle([M, y, W - M, y + 2], fill=INK)
    y += 22
    # 12 знаков в три колонки
    col_w = (W - 2 * M - 2 * 32) // 3
    rows_h = (H - M - 50 - y) // 4
    name_f = oswald(30)
    # один размер текста для всех знаков: самый крупный, при котором каждый влезает в 3 строки
    text_f = serif(17)
    for size in (22, 21, 20, 19, 18, 17):
        f = serif(size)
        if all(len(wrap(d, issue["horoscope"].get(s, ""), f, col_w)) <= 3 for s in SIGNS):
            text_f = f
            break
    for i, sign in enumerate(SIGNS):
        col, row = i % 3, i // 3
        x = M + col * (col_w + 32)
        yy = y + row * rows_h
        d.text((x, yy), sign.upper(), font=name_f, fill=INK)
        body = issue["horoscope"].get(sign, "")
        tl = wrap(d, body, text_f, col_w)
        draw_lines(d, (x, yy + 44), tl[:3], text_f, INK, int(text_f.size * 1.28))
        d.line([x, yy + rows_h - 14, x + col_w, yy + rows_h - 14], fill=GREY, width=1)
    foot = oswald(24, "Medium")
    d.text((M, H - M), "t.me/merkuriy_vinovat", font=foot, fill=INK, anchor="ls")
    d.text((W - M, H - M), "Ведёт AI-астролог Вега", font=foot, fill=INK, anchor="rs")
    img.save(out, optimize=True)


TAROT_ART = ROOT / "assets" / "tarot"


def tarot_info(name: str) -> tuple[Path | None, dict | None]:
    """Иллюстрация карты (assets/tarot/<номер в колоде>.jpg) и её описание из колоды."""
    from astro.tarot import DECK
    for i, c in enumerate(DECK):
        if c["name"].lower() == name.strip().lower():
            p = TAROT_ART / f"{i:02d}.jpg"
            return (p if p.exists() else None), c
    return None, None


def tarot_subtitle(c: dict | None) -> str:
    if not c:
        return ""
    if c["arcana"] == "старший аркан":
        return f"Старший аркан · № {c['number']}"
    return f"Младший аркан · масть {c['suit']} · стихия {c['element']}"


def art_image(path: Path, height: int) -> Image.Image:
    im = Image.open(path).convert("RGB")
    return im.resize((int(im.width * height / im.height), height), Image.LANCZOS)


def tarot_card_art(issue: dict, out: Path, art: Path, info: dict | None):
    W, H, M = 1080, 1350, 64
    img = Image.new("RGB", (W, H), PAPER)
    d = ImageDraw.Draw(img)
    y = masthead(d, issue, M, W - M, M)
    tag(d, (M, y + 6), "КАРТА ДНЯ")
    t = issue["posts"]["tarot"]
    a = art_image(art, 800)
    ax, ay = W - M - a.width, y + 6
    img.paste(a, (ax, ay))
    d.rectangle([ax - 1, ay - 1, ax + a.width, ay + a.height], outline=INK, width=3)
    tw = ax - M - 36
    name = t["card"].upper()
    nf = fit_font(d, name, oswald, tw, 3, 96, 44)
    ny = y + 90
    for ln in wrap(d, name, nf, tw):
        d.text((M, ny), ln, font=nf, fill=INK)
        ny += int(nf.size * 1.15)
    ny += 20
    d.rectangle([M, ny, M + tw, ny + 2], fill=INK)
    ny += 24
    kf = serif(30, "Italic")
    for ln in wrap(d, t.get("keywords", ""), kf, tw)[:5]:
        d.text((M, ny), ln, font=kf, fill=INK)
        ny += 40
    sub = tarot_subtitle(info)
    if sub:
        sf = serif(24)
        sl = wrap(d, sub, sf, tw)
        sy = ay + a.height - len(sl) * 32
        d.rectangle([M, sy - 18, M + tw, sy - 16], fill=INK)
        for ln in sl:
            d.text((M, sy), ln, font=sf, fill=INK)
            sy += 32
    foot = oswald(24, "Medium")
    d.text((M, H - M), "t.me/merkuriy_vinovat", font=foot, fill=INK, anchor="ls")
    d.text((W - M, H - M), "Ведёт AI-астролог Вега", font=foot, fill=INK, anchor="rs")
    img.save(out, optimize=True)


def tarot_card(issue: dict, out: Path):
    art, info = tarot_info(issue["posts"]["tarot"]["card"])
    if art:
        return tarot_card_art(issue, out, art, info)
    W, H, M = 1080, 1350, 64
    img = Image.new("RGB", (W, H), PAPER)
    d = ImageDraw.Draw(img)
    y = masthead(d, issue, M, W - M, M)
    y = tag(d, (M, y + 10), "КАРТА ДНЯ") + 40
    t = issue["posts"]["tarot"]
    # рамка карты
    cw, ch = 520, 760
    cx0 = (W - cw) // 2
    d.rectangle([cx0, y, cx0 + cw, y + ch], outline=INK, width=8)
    d.rectangle([cx0 + 18, y + 18, cx0 + cw - 18, y + ch - 18], outline=INK, width=2)
    star_y = y + 150
    pts = []
    import math
    for k in range(16):
        ang = -math.pi / 2 + k * math.pi / 8
        r = 110 if k % 4 == 0 else (60 if k % 2 == 0 else 20)
        pts.append((W / 2 + r * math.cos(ang), star_y + r * math.sin(ang)))
    d.polygon(pts, fill=INK)
    d.ellipse([W / 2 - 14, star_y - 14, W / 2 + 14, star_y + 14], fill=RED)
    name = t["card"].upper()
    nf = fit_font(d, name, oswald, cw - 80, 3, 92, 48)
    lines = wrap(d, name, nf, cw - 80)
    ny = y + 330
    for ln in lines:
        d.text((W / 2, ny), ln, font=nf, fill=INK, anchor="mt")
        ny += int(nf.size * 1.18)
    kw = serif(28, "Italic")
    kl = wrap(d, t.get("keywords", ""), kw, cw - 80)[:3]
    ny += 36
    for ln in kl:
        d.text((W / 2, ny), ln, font=kw, fill=INK, anchor="mt")
        ny += 38
    foot = oswald(24, "Medium")
    d.text((M, H - M), "t.me/merkuriy_vinovat", font=foot, fill=INK, anchor="ls")
    d.text((W - M, H - M), "Ведёт AI-астролог Вега", font=foot, fill=INK, anchor="rs")
    img.save(out, optimize=True)


def video_cover(issue: dict, out: Path, headline: str | None = None, sub: str | None = None):
    W, H, M = 1080, 1920, 80
    v = issue["posts"]["video"]
    headline = (headline or v["cover_headline"]).upper()
    sub = sub or v.get("cover_sub", "")
    img = Image.new("RGB", (W, H), PAPER)
    d = ImageDraw.Draw(img)
    y = 230
    double_rule(d, M, W - M, y)
    mf = oswald(34)
    d.text((M, y + 22), "МЕРКУРИЙ ВИНОВАТ", font=mf, fill=INK)
    d.text((W - M, y + 22), f"ВЫПУСК № {issue.get('issue_no', 1)}", font=mf, fill=INK, anchor="ra")
    d.rectangle([M, y + 80, W - M, y + 82], fill=INK)
    y = tag(d, (M, 470), "СРОЧНО", 40) + 32
    hf = fit_font(d, headline, oswald, W - 2 * M, 4, 168, 96)
    y = draw_lines(d, (M, y), wrap(d, headline, hf, W - 2 * M), hf, INK, int(hf.size * 1.12)) + 56
    sf = serif(52, "Italic")
    draw_lines(d, (M, y), wrap(d, sub, sf, W - 2 * M)[:3], sf, INK, 64)
    mercury(img, 790, 1120, 340)
    stamp(img, "ВИНОВАТ", (750, 1380), 62)
    ff = oswald(36, "Medium")
    d.text((M, 1290), "Ведёт AI-астролог Вега", font=ff, fill=INK)
    d.text((M, 1338), "t.me/merkuriy_vinovat", font=ff, fill=INK)
    img.save(out, optimize=True)


def story_card(issue: dict, out: Path):
    """Сторис 1080×1920 для вечернего поста: вопрос и варианты, голосование — в Telegram."""
    W, H, M = 1080, 1920, 80
    ev = issue["posts"]["evening"]
    poll = ev.get("poll") or {}
    question = poll.get("question") or ev.get("rubric", "Вопрос дня")
    options = poll.get("options", [])
    img = Image.new("RGB", (W, H), PAPER)
    d = ImageDraw.Draw(img)
    y = 250
    double_rule(d, M, W - M, y)
    mf = oswald(34)
    d.text((M, y + 22), "МЕРКУРИЙ ВИНОВАТ", font=mf, fill=INK)
    d.text((W - M, y + 22), "ВЕЧЕРНИЙ ВОПРОС", font=mf, fill=INK, anchor="ra")
    d.rectangle([M, y + 80, W - M, y + 82], fill=INK)
    y = tag(d, (M, 460), "ОПРОС", 40) + 36
    qf = fit_font(d, question.upper(), oswald, W - 2 * M, 3, 120, 64)
    y = draw_lines(d, (M, y), wrap(d, question.upper(), qf, W - 2 * M), qf, INK, int(qf.size * 1.15)) + 70
    of = serif(46)
    for i, opt in enumerate(options[:6]):
        lines = wrap(d, opt, of, W - 2 * M - 110)
        h = max(1, len(lines)) * 58 + 36
        d.rectangle([M, y, W - M, y + h], outline=INK, width=4)
        d.text((M + 30, y + h / 2), chr(ord("А") + i), font=oswald(52), fill=RED, anchor="lm")
        draw_lines(d, (M + 100, y + 18), lines, of, INK, 58)
        y += h + 22
    ff = oswald(48)
    d.text((W / 2, 1540), "ГОЛОСУЙТЕ В TELEGRAM", font=ff, fill=INK, anchor="mm")
    d.text((W / 2, 1610), "t.me/merkuriy_vinovat · ссылка в профиле", font=serif(36, "Italic"), fill=INK, anchor="mm")
    img.save(out, optimize=True)


def render_issue(folder: Path):
    issue = json.loads((folder / "issue.json").read_text(encoding="utf-8"))
    horoscope_card(issue, folder / "horoscope.png")
    tarot_card(issue, folder / "tarot.png")
    video_cover(issue, folder / "cover.png")
    story_card(issue, folder / "story.png")
    # TikTok принимает фото только в JPEG/WebP
    for name in ("horoscope", "tarot"):
        Image.open(folder / f"{name}.png").convert("RGB").save(folder / f"{name}.jpg", quality=92)
    print(f"Карточки готовы: {folder}")
    # карусель гороскопа и Reels с картой Таро для Instagram и TikTok
    from render.social import render_social
    render_social(folder)


if __name__ == "__main__":
    render_issue(Path(sys.argv[1]))
