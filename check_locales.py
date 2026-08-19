#!/usr/bin/env python3
"""Controleer het LOCALES-blok in scorecard-generator.html.

Geen build-stap: dit script schrijft nooit naar de HTML, het leest en meldt
alleen. Draai het voor je een nieuwe versie uitdeelt (zie README).

    python3 check_locales.py [bestand] [--report]

Exitcode 0 = in orde, 1 = er is iets mis.
"""

import json
import re
import sys
from pathlib import Path

DEFAULT_FILE = "scorecard-generator.html"
FALLBACK = "nl"
START = "<script type=\"application/json\" id=\"locales\">"
END = "</script>"

PLACEHOLDER = re.compile(r"\{\w+\}")
PLURAL_FORMS = ("one", "other")


def read_locales(path: Path) -> dict:
    """Haal het JSON-blok uit de HTML. Faalt luid op elk probleem."""
    raw = path.read_bytes()
    if raw.startswith(b"\xef\xbb\xbf"):
        raise SystemExit(f"{path}: begint met een UTF-8 BOM, die hoort er niet in.")
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as e:
        raise SystemExit(f"{path}: geen geldige UTF-8 op byte {e.start}.")

    start = text.find(START)
    if start < 0:
        raise SystemExit(f"{path}: het blok {START} is niet gevonden.")
    start += len(START)
    end = text.find(END, start)
    if end < 0:
        raise SystemExit(f"{path}: het locales-blok wordt niet afgesloten.")

    try:
        return json.loads(text[start:end])
    except json.JSONDecodeError as e:
        raise SystemExit(f"{path}: ongeldige JSON in het locales-blok, regel {e.lineno}: {e.msg}")


def placeholders(value: str) -> set:
    return set(PLACEHOLDER.findall(value))


def budget_length(value: str) -> int:
    """Een {plaatshouder} telt als twee tekens: het langste getal dat er in de
    praktijk in komt te staan ("POGING 12"). Zelfde regel als in de app."""
    return len(PLACEHOLDER.sub("::", value))


def check(locales: dict) -> list:
    budgets = locales.get("_budgets", {})
    langs = [k for k in locales if not k.startswith("_")]
    if FALLBACK not in langs:
        raise SystemExit(f"De terugvaltaal {FALLBACK!r} ontbreekt.")

    base = locales[FALLBACK]
    plural_bases = [k[: -len(".one")] for k in base if k.endswith(".one")]
    problems = []

    for lang in langs:
        d = locales[lang]

        missing = [k for k in base if not isinstance(d.get(k), str) or not d[k]]
        if missing:
            problems.append(f"{lang}: {len(missing)} ontbrekende sleutels: " + ", ".join(missing))

        extra = [k for k in d if k not in base]
        if extra:
            problems.append(f"{lang}: {len(extra)} onbekende sleutels: " + ", ".join(extra))

        for key, want in base.items():
            got = d.get(key)
            if not isinstance(got, str):
                continue
            if placeholders(got) != placeholders(want):
                problems.append(
                    f"{key}: {lang} gebruikt {sorted(placeholders(got)) or '[]'}, "
                    f"nl gebruikt {sorted(placeholders(want)) or '[]'}"
                )

        for pb in plural_bases:
            for form in PLURAL_FORMS:
                if not isinstance(d.get(f"{pb}.{form}"), str):
                    problems.append(f"{pb}: {lang} mist de meervoudsvorm {form!r}")

        for key, budget in budgets.items():
            value = d.get(key)
            if not isinstance(value, str):
                continue
            n = budget_length(value)
            if n > budget:
                problems.append(
                    f"{key}: {lang} is {n} tekens, budget is {budget} — {value!r}"
                )

    return problems


def report(locales: dict) -> None:
    base = locales[FALLBACK]
    print(f"{len(base)} sleutels, terugval {FALLBACK}")
    for lang in [k for k in locales if not k.startswith("_")]:
        d = locales[lang]
        done = sum(1 for k in base if isinstance(d.get(k), str) and d[k])
        print(f"  {lang}: {done}/{len(base)} ({done / len(base):.0%})")


def main(argv: list) -> int:
    args = [a for a in argv if not a.startswith("--")]
    path = Path(args[0]) if args else Path(__file__).with_name(DEFAULT_FILE)
    locales = read_locales(path)

    if "--report" in argv:
        report(locales)

    problems = check(locales)
    if problems:
        print(f"{len(problems)} probleem(en) in {path}:", file=sys.stderr)
        for p in problems:
            print(f"  {p}", file=sys.stderr)
        return 1
    print(f"{path}: alle vertalingen in orde.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
