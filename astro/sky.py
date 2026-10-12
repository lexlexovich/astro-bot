"""Расчёт неба на дату: знаки планет, ретрограды, аспекты, фаза Луны, события недели.

Запуск: python -m astro.sky 2026-10-13  → печатает JSON.
Считается на 07:00 по Москве — время утреннего гороскопа.
"""
from __future__ import annotations

import io
import json
import logging
import sys
from contextlib import redirect_stderr, redirect_stdout
from datetime import date, timedelta

logging.disable(logging.WARNING)

from kerykeion import AstrologicalSubjectFactory  # noqa: E402

PLANETS = ["sun", "moon", "mercury", "venus", "mars", "jupiter", "saturn", "uranus", "neptune", "pluto"]

PLANET_RU = {
    "sun": "Солнце", "moon": "Луна", "mercury": "Меркурий", "venus": "Венера", "mars": "Марс",
    "jupiter": "Юпитер", "saturn": "Сатурн", "uranus": "Уран", "neptune": "Нептун", "pluto": "Плутон",
}

SIGNS = ["Ari", "Tau", "Gem", "Can", "Leo", "Vir", "Lib", "Sco", "Sag", "Cap", "Aqu", "Pis"]
SIGN_RU = {
    "Ari": "Овен", "Tau": "Телец", "Gem": "Близнецы", "Can": "Рак", "Leo": "Лев", "Vir": "Дева",
    "Lib": "Весы", "Sco": "Скорпион", "Sag": "Стрелец", "Cap": "Козерог", "Aqu": "Водолей", "Pis": "Рыбы",
}
# Предложный падеж: «Луна в Скорпионе»
SIGN_RU_IN = {
    "Ari": "Овне", "Tau": "Тельце", "Gem": "Близнецах", "Can": "Раке", "Leo": "Льве", "Vir": "Деве",
    "Lib": "Весах", "Sco": "Скорпионе", "Sag": "Стрельце", "Cap": "Козероге", "Aqu": "Водолее", "Pis": "Рыбах",
}

ASPECTS = [  # угол, орбис, название
    (0, 6, "соединение"),
    (60, 4, "секстиль"),
    (90, 6, "квадрат"),
    (120, 6, "трин"),
    (180, 6, "оппозиция"),
]

PHASE_RU = {
    "New Moon": "новолуние",
    "Waxing Crescent": "растущий серп",
    "First Quarter": "первая четверть",
    "Waxing Gibbous": "растущая Луна",
    "Full Moon": "полнолуние",
    "Waning Gibbous": "убывающая Луна",
    "Last Quarter": "последняя четверть",
    "Waning Crescent": "убывающий серп",
}

MOSCOW = dict(lng=37.62, lat=55.75, tz_str="Europe/Moscow")


def _subject(d: date, hour: int = 7):
    # kerykeion/libephemeris печатают предупреждения про малые тела — глушим их
    with redirect_stderr(io.StringIO()), redirect_stdout(io.StringIO()):
        return AstrologicalSubjectFactory.from_birth_data(
            "Sky", d.year, d.month, d.day, hour, 0, online=False, **MOSCOW
        )


def _planets(s) -> dict:
    out = {}
    for key in PLANETS:
        p = getattr(s, key)
        out[key] = {
            "name": PLANET_RU[key],
            "sign": p.sign,
            "sign_ru": SIGN_RU[p.sign],
            "sign_ru_in": SIGN_RU_IN[p.sign],
            "degree": round(p.position, 1),
            "abs": round(p.abs_pos, 2),
            "retrograde": bool(p.retrograde),
        }
    return out


def _aspects(planets: dict) -> list[dict]:
    keys = list(planets)
    found = []
    for i, a in enumerate(keys):
        for b in keys[i + 1:]:
            diff = abs(planets[a]["abs"] - planets[b]["abs"]) % 360
            diff = min(diff, 360 - diff)
            for angle, orb, name in ASPECTS:
                delta = abs(diff - angle)
                if delta <= orb:
                    found.append({
                        "a": planets[a]["name"], "b": planets[b]["name"], "aspect": name,
                        "orb": round(delta, 1),
                    })
    found.sort(key=lambda x: x["orb"])
    return found


def _phase(s) -> dict:
    lp = s.lunar_phase
    angle = lp.degrees_between_s_m % 360
    return {
        "phase": PHASE_RU.get(lp.moon_phase_name, lp.moon_phase_name),
        "angle": round(angle, 1),
        "illumination_pct": round((1 - __import__("math").cos(__import__("math").radians(angle))) / 2 * 100),
        "waxing": angle < 180,
    }


def _events(d: date, days: int = 7) -> list[dict]:
    """События на ближайшие дни: смена знака, развороты ретроградов, новолуние и полнолуние."""
    events = []
    prev = _planets(_subject(d))
    prev_angle = _phase(_subject(d))["angle"]
    for i in range(1, days + 1):
        day = d + timedelta(days=i)
        s = _subject(day)
        cur = _planets(s)
        angle = _phase(s)["angle"]
        for key in PLANETS:
            if key == "moon":
                continue
            if cur[key]["sign"] != prev[key]["sign"]:
                events.append({"date": day.isoformat(), "type": "ingress",
                               "text": f"{cur[key]['name']} входит в знак {cur[key]['sign_ru']}"})
            if cur[key]["retrograde"] != prev[key]["retrograde"]:
                kind = "становится ретроградным" if cur[key]["retrograde"] else "выходит из ретроградности"
                events.append({"date": day.isoformat(), "type": "station",
                               "text": f"{cur[key]['name']} {kind}"})
        if prev_angle > 300 and angle < 60:
            events.append({"date": day.isoformat(), "type": "new_moon", "text": "Новолуние"})
        if prev_angle < 180 <= angle:
            events.append({"date": day.isoformat(), "type": "full_moon", "text": "Полнолуние"})
        prev, prev_angle = cur, angle
    return events


def sky(d: date) -> dict:
    s = _subject(d)
    planets = _planets(s)
    return {
        "date": d.isoformat(),
        "computed_for": "07:00 Europe/Moscow",
        "planets": planets,
        "retrograde": [p["name"] for k, p in planets.items() if p["retrograde"]],
        "moon": {**planets["moon"], **_phase(s)},
        "aspects": _aspects(planets)[:12],
        "events_next_7_days": _events(d),
    }


if __name__ == "__main__":
    target = date.fromisoformat(sys.argv[1]) if len(sys.argv) > 1 else date.today()
    print(json.dumps(sky(target), ensure_ascii=False, indent=2))
