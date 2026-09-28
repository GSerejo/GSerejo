"""Baixa o calendário público de contribuições do GitHub e salva em data/contributions.json.

Não precisa de token: usa o mesmo fragmento HTML que a página de perfil carrega.
Só biblioteca padrão, para a Action diária não precisar instalar nada.
    python scripts/fetch_contributions.py
"""

import json
import re
import urllib.request
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

USERNAME = "GSerejo"
URL = f"https://github.com/users/{USERNAME}/contributions"
ROOT = Path(__file__).resolve().parent.parent
OUTPUT = ROOT / "data" / "contributions.json"

DAY_CELL = re.compile(r"<td\b[^>]*\bContributionCalendar-day\b[^>]*>")
ATTR = re.compile(r'([\w-]+)="([^"]*)"')
TOOLTIP = re.compile(r'<tool-tip\b[^>]*\bfor="([^"]+)"[^>]*>([^<]*)</tool-tip>')
COUNT = re.compile(r"^([\d,]+) contributions?")


def fetch_html() -> str:
    request = urllib.request.Request(URL, headers={"User-Agent": "profile-readme-bot"})
    with urllib.request.urlopen(request, timeout=30) as response:
        return response.read().decode("utf-8")


def parse_days(html: str) -> list[dict]:
    # O número exato de contribuições de cada dia só aparece no tooltip ligado à célula
    counts = {}
    for cell_id, text in TOOLTIP.findall(html):
        match = COUNT.match(text.strip())
        counts[cell_id] = int(match.group(1).replace(",", "")) if match else 0

    days = []
    for tag in DAY_CELL.findall(html):
        attrs = dict(ATTR.findall(tag))
        days.append({
            "date": attrs["data-date"],
            "level": int(attrs.get("data-level", 0)),
            "count": counts.get(attrs.get("id"), 0),
        })
    days.sort(key=lambda day: day["date"])
    if not days:
        raise SystemExit("Nenhum dia encontrado: o HTML do GitHub mudou?")
    return days


def streaks(days: list[dict]) -> tuple[int, int]:
    longest = run = 0
    for day in days:
        run = run + 1 if day["count"] > 0 else 0
        longest = max(longest, run)

    # A sequência atual não quebra só porque hoje ainda não teve commit
    active = [day["count"] > 0 for day in days]
    if active and not active[-1]:
        active.pop()
    current = 0
    for is_active in reversed(active):
        if not is_active:
            break
        current += 1
    return current, longest


def main() -> None:
    days = parse_days(fetch_html())
    current, longest = streaks(days)
    best = max(days, key=lambda day: day["count"])

    data = {
        "user": USERNAME,
        "fetched_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "total": sum(day["count"] for day in days),
        "current_streak": current,
        "longest_streak": longest,
        "best_day": {"date": best["date"], "count": best["count"]},
        "days": days,
    }
    OUTPUT.parent.mkdir(exist_ok=True)
    OUTPUT.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    print(f"{len(days)} dias, {data['total']} contribuições, sequência atual {current}, maior {longest}")


if __name__ == "__main__":
    main()
