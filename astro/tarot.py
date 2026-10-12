"""Карта Таро дня: детерминированный выбор из 78 карт без повторов внутри недели.

Запуск: python -m astro.tarot 2026-10-13
"""
from __future__ import annotations

import json
import random
import sys
from datetime import date

MAJOR = [
    "Шут", "Маг", "Верховная Жрица", "Императрица", "Император", "Иерофант", "Влюблённые",
    "Колесница", "Сила", "Отшельник", "Колесо Фортуны", "Справедливость", "Повешенный",
    "Смерть", "Умеренность", "Дьявол", "Башня", "Звезда", "Луна", "Солнце", "Суд", "Мир",
]
SUITS = {"Жезлов": "огонь", "Кубков": "вода", "Мечей": "воздух", "Пентаклей": "земля"}
RANKS = ["Туз", "Двойка", "Тройка", "Четвёрка", "Пятёрка", "Шестёрка", "Семёрка", "Восьмёрка",
         "Девятка", "Десятка", "Паж", "Рыцарь", "Королева", "Король"]

DECK = [{"name": n, "arcana": "старший аркан", "number": i} for i, n in enumerate(MAJOR)] + [
    {"name": f"{r} {s}", "arcana": "младший аркан", "suit": s, "element": el}
    for s, el in SUITS.items() for r in RANKS
]


def card_of_day(d: date) -> dict:
    year, week, weekday = d.isocalendar()
    deck = DECK[:]
    random.Random(f"{year}-W{week}").shuffle(deck)
    return deck[weekday - 1]


if __name__ == "__main__":
    target = date.fromisoformat(sys.argv[1]) if len(sys.argv) > 1 else date.today()
    print(json.dumps(card_of_day(target), ensure_ascii=False))
