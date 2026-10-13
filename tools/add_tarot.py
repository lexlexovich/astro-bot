"""Добавить иллюстрации карт Таро в колоду: assets/tarot/<номер>.jpg.

Запуск: python -m tools.add_tarot "<папка>/Император.png" "<папка>/Туз жезлов.png" ...
Имя файла = название карты (регистр и ё/е не важны). Скрипт:
- обрезает чёрную рамку по краю, если генератор её нарисовал (у нас своя рамка);
- приводит цвет бумаги к фирменному #EFEBE0, чтобы карты из разных партий выглядели одной колодой;
- сохраняет в JPEG 1024×1536.
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


def _dark(px) -> bool:
    return sum(px[:3]) < 200


def crop_frame(im: Image.Image) -> Image.Image:
    """Если по краю есть тёмная линия рамки — режем по её внутренней стороне."""
    w, h = im.size
    px = im.load()

    def scan(points):
        # points: последовательность координат от края внутрь; ищем тёмную полосу и её конец
        seen = False
        for k, (x, y) in enumerate(points):
            if k > 90:
                return 0
            if _dark(px[x, y]):
                seen = True
            elif seen:
                return k + 8
        return 0

    def side(coords_fn, length):
        vals = [scan(coords_fn(t)) for t in (length // 3, length // 2, 2 * length // 3)]
        vals = [v for v in vals if v]
        return max(vals) if len(vals) >= 2 else 0

    left = side(lambda y: [(x, y) for x in range(w)], h)
    right = side(lambda y: [(w - 1 - x, y) for x in range(w)], h)
    top = side(lambda x: [(x, y) for y in range(h)], w)
    bottom = side(lambda x: [(x, h - 1 - y) for y in range(h)], w)
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


def add(path: Path) -> str:
    key = norm(path.stem)
    if key not in INDEX:
        return f"✗ {path.name}: не нашёл такую карту в колоде"
    i = INDEX[key]
    im = Image.open(path).convert("RGB")
    im = crop_frame(im)
    im = paper_balance(im)
    # вписываем в 2:3 целиком, без обрезки: поля добиваем цветом бумаги
    im = ImageOps.pad(im, SIZE, Image.LANCZOS, color=PAPER)
    OUT.mkdir(parents=True, exist_ok=True)
    im.save(OUT / f"{i:02d}.jpg", quality=88)
    return f"✓ {i:02d} {DECK[i]['name']}"


if __name__ == "__main__":
    for p in sys.argv[1:]:
        print(add(Path(p)))
