"""Сборка вертикального видео 1080×1920 из сценария выпуска.

Запуск: python -m render.video content/2026-10-13
Сценарий: issue.json → posts.video.script = [{"onscreen": "крупный текст", "voice": "что говорит Вега"}, ...]
Первый кадр — обложка cover.png (её TikTok покажет как превью).
Озвучка: edge-tts, голос ru-RU-SvetlanaNeural. Если синтез недоступен — видео без голоса, с субтитрами.
"""
from __future__ import annotations

import asyncio
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw

from render.cards import INK, PAPER, RED, double_rule, draw_lines, fit_font, oswald, serif, wrap, mercury

VOICE = "ru-RU-SvetlanaNeural"
W, H, M = 1080, 1920, 80
COVER_SECONDS = 1.2


def frame(issue: dict, onscreen: str, voice: str, n: int, total: int, out: Path):
    img = Image.new("RGB", (W, H), PAPER)
    d = ImageDraw.Draw(img)
    double_rule(d, M, W - M, 230)
    d.text((M, 252), "МЕРКУРИЙ ВИНОВАТ", font=oswald(34), fill=INK)
    d.text((W - M, 252), f"{n}/{total}", font=oswald(34), fill=INK, anchor="ra")
    d.rectangle([M, 310, W - M, 312], fill=INK)
    text = onscreen.upper()
    hf = fit_font(d, text, oswald, W - 2 * M, 5, 140, 72)
    y = draw_lines(d, (M, 480), wrap(d, text, hf, W - 2 * M), hf, INK, int(hf.size * 1.12)) + 40
    d.rectangle([M, y, M + 160, y + 10], fill=RED)
    # субтитры — то, что говорит голос; держим над нижней зоной интерфейса TikTok/Reels
    sf = serif(44, "Italic")
    lines = wrap(d, voice, sf, W - 2 * M)[:6]
    sy = 1480 - len(lines) * 58
    draw_lines(d, (M, sy), lines, sf, INK, 58)
    img.save(out)


def ending(issue: dict, out: Path):
    img = Image.new("RGB", (W, H), PAPER)
    d = ImageDraw.Draw(img)
    double_rule(d, M, W - M, 230)
    hf = oswald(120)
    draw_lines(d, (M, 520), ["БОЛЬШЕ —", "В TELEGRAM"], hf, INK, 140)
    d.text((M, 840), "t.me/merkuriy_vinovat", font=oswald(64, "Medium"), fill=RED)
    d.text((M, 940), "Ведёт AI-астролог Вега", font=serif(44, "Italic"), fill=INK)
    mercury(img, 800, 1150, 300)
    img.save(out)


async def _tts(text: str, out: Path) -> bool:
    try:
        import edge_tts
        await edge_tts.Communicate(text, VOICE, rate="+5%").save(str(out))
        return out.exists() and out.stat().st_size > 1000
    except Exception as exc:
        print(f"TTS недоступен: {exc}", file=sys.stderr)
        return False


def duration(path: Path) -> float:
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
                       capture_output=True, text=True, check=True)
    return float(r.stdout.strip())


def silence(seconds: float, out: Path):
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i", "anullsrc=r=24000:cl=mono",
                    "-t", f"{seconds:.2f}", "-c:a", "libmp3lame", str(out)], check=True)


def build(folder: Path) -> Path:
    folder = folder.resolve()
    issue = json.loads((folder / "issue.json").read_text(encoding="utf-8"))
    script = issue["posts"]["video"]["script"]
    tmp = Path(tempfile.mkdtemp())
    images, audios, durs = [], [], []

    # 1) обложка — первый кадр
    cover = folder / "cover.png"
    if not cover.exists():
        from render.cards import video_cover
        video_cover(issue, cover)
    a = tmp / "a00.mp3"
    silence(COVER_SECONDS, a)
    images.append(cover); audios.append(a); durs.append(COVER_SECONDS)

    voiced = True
    for i, seg in enumerate(script, 1):
        img = tmp / f"f{i:02d}.png"
        frame(issue, seg["onscreen"], seg["voice"], i, len(script), img)
        a = tmp / f"a{i:02d}.mp3"
        ok = asyncio.run(_tts(seg["voice"], a))
        if not ok:
            voiced = False
            words = len(seg["voice"].split())
            silence(max(3.0, words / 2.6), a)
        dur = duration(a) + 0.35
        images.append(img); audios.append(a); durs.append(dur)

    end = tmp / "end.png"
    ending(issue, end)
    a = tmp / "aend.mp3"
    silence(2.0, a)
    images.append(end); audios.append(a); durs.append(2.0)

    # видео-дорожка из картинок с длительностями
    lst = tmp / "images.txt"
    with open(lst, "w") as fh:
        for img, dur in zip(images, durs):
            fh.write(f"file '{img}'\nduration {dur:.2f}\n")
        fh.write(f"file '{images[-1]}'\n")
    alst = tmp / "audio.txt"
    with open(alst, "w") as fh:
        for a, dur in zip(audios, durs):
            padded = a.with_suffix(".pad.wav")
            subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(a), "-af", "apad",
                            "-t", f"{dur:.2f}", "-ar", "44100", "-ac", "2", str(padded)], check=True)
            fh.write(f"file '{padded}'\n")
    audio = tmp / "voice.wav"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(alst),
                    "-c", "copy", str(audio)], check=True)
    out = folder / "video.mp4"
    subprocess.run([
        "ffmpeg", "-y", "-loglevel", "error",
        "-f", "concat", "-safe", "0", "-i", str(lst), "-i", str(audio),
        "-vf", "scale=1080:1920,format=yuv420p,fps=30",
        "-c:v", "libx264", "-preset", "medium", "-crf", "23",
        "-c:a", "aac", "-b:a", "128k", "-shortest", "-movflags", "+faststart", str(out),
    ], check=True)
    shutil.rmtree(tmp, ignore_errors=True)
    (folder / "video.json").write_text(json.dumps({"voiced": voiced, "seconds": round(sum(durs), 1)},
                                                  ensure_ascii=False), encoding="utf-8")
    print(f"Видео готово: {out} ({sum(durs):.1f} с, голос: {'да' if voiced else 'нет'})")
    return out


if __name__ == "__main__":
    build(Path(sys.argv[1]))
