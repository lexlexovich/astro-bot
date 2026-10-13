"""Добавить иллюстрации карт Таро в колоду: assets/tarot/<номер>.jpg.

Запуск: python -m tools.add_tarot "<папка>/Император.png" "<папка>/Туз жезлов.png" ...
Имя файла = название карты (регистр и ё/е не важны). Скрипт:
- обрезает чёрную рамку по краю, если генератор её нарисовал (у нас своя рамка);
- приводит цвет бумаги к фирменному #EFEBE0, чтобы карты из разных партий выглядели одной колодой;
- сохраняет в JPEG 1024×1536.
С флагом --recolor переводит картинку в тушь + красный (если генератор нарисовал золото и сепию).
"""
from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image, ImageOps

from astro.tarot import DECK

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "assets" / "tarot"
PAPER = (239, 235, 224)
SIZE = (1024, 1536)


def norm(s: str) -> str:
    return s.lower().replace("ё", "е").strip()


INDEX = {norm(c["name"]): i for i, c in enumerate(DECK)}


def crop_frame(im: Image.Image) -> Image.Image:
    """Режем только настоящую рамку: сплошную тёмную линию вдоль края (тёмных точек > 80% длины)."""
    import numpy as np
    g = np.asarray(im.convert("L"), dtype=np.int16)
    h, w = g.shape
    dark = g < 90

    def side(lines):
        start = None
        for k, frac in enumerate(lines):
            if k > 70:
                break
            if start is None and frac > 0.8:
                start = k
            elif start is not None and frac < 0.3:
                return k + 6
        return 0

    ys, xs = slice(int(h * 0.1), int(h * 0.9)), slice(int(w * 0.1), int(w * 0.9))
    left = side(dark[ys, k].mean() for k in range(w))
    right = side(dark[ys, w - 1 - k].mean() for k in range(w))
    top = side(dark[k, xs].mean() for k in range(h))
    bottom = side(dark[h - 1 - k, xs].mean() for k in range(h))
    if not any((left, right, top, bottom)):
        return im
    return im.crop((left, top, w - right, h - bottom))


def paper_balance(im: Image.Image) -> Image.Image:
    """Самые светлые 10% пикселей считаем бумагой и приводим их к фирменному цвету."""
    small = im.resize((256, 384))
    pix = sorted(list(small.getdata()), key=sum)
    light = pix[int(len(pix) * 0.9):]
    avg = [sum(p[c] for p in light) / len(light) for c in range(3)]
    k = [PAPER[c] / max(avg[c], 1) for c in range(3)]
    r, g, b = im.split()
    r = r.point(lambda v: min(255, int(v * k[0])))
    g = g.point(lambda v: min(255, int(v * k[1])))
    b = b.point(lambda v: min(255, int(v * k[2])))
    return Image.merge("RGB", (r, g, b))


def ink_and_red(im: Image.Image) -> Image.Image:
    """Для карт, где генератор ушёл в золото и сепию: всё переводим в тушь на бумаге,
    золотые монеты — в фирменный красный, родной красный оставляем."""
    import numpy as np
    hsv = np.asarray(im.convert("HSV")).astype(np.float32)
    rgb = np.asarray(im).astype(np.float32)
    h, s, v = hsv[..., 0] * 360 / 255, hsv[..., 1] / 255, hsv[..., 2] / 255
    gray = rgb.mean(axis=2)
    lo, hi = np.percentile(gray, 2), np.percentile(gray, 97)
    t = np.clip((gray - lo) / max(hi - lo, 1), 0, 1)[..., None]
    ink, paper = np.array([20, 18, 16]), np.array(PAPER)
    out = ink + (paper - ink) * t
    gold = (h > 30) & (h < 62) & (s > 0.7) & (v > 0.55)
    # закрываем блики внутри монет, не задевая бумагу
    from PIL import ImageFilter
    m = Image.fromarray((gold * 255).astype("uint8")).filter(ImageFilter.MaxFilter(7)).filter(ImageFilter.MinFilter(7))
    gold = np.asarray(m) > 127
    out[gold] = (np.array([200, 38, 30]) * np.clip(v[..., None] * 0.95, 0, 1))[gold]
    reds = ((h < 18) | (h > 340)) & (s > 0.55) & (v > 0.3)
    out[reds] = rgb[reds]
    return Image.fromarray(out.astype("uint8"))


def add(path: Path, recolor: bool = False) -> str:
    key = norm(path.stem)
    if key not in INDEX:
        return f"✗ {path.name}: не нашёл такую карту в колоде"
    i = INDEX[key]
    im = Image.open(path).convert("RGB")
    im = crop_frame(im)
    im = ink_and_red(im) if recolor else paper_balance(im)
    # вписываем в 2:3 целиком, без обрезки: поля добиваем цветом бумаги
    im = ImageOps.pad(im, SIZE, Image.LANCZOS, color=PAPER)
    OUT.mkdir(parents=True, exist_ok=True)
    im.save(OUT / f"{i:02d}.jpg", quality=88)
    return f"✓ {i:02d} {DECK[i]['name']}"


if __name__ == "__main__":
    args = sys.argv[1:]
    recolor = "--recolor" in args  # золото → красный, сепия → тушь
    for p in [a for a in args if a != "--recolor"]:
        print(add(Path(p), recolor))
