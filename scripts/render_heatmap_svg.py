"""Desenha data/contributions.json como um calendário animado em contrib-heatmap.svg.

As células aparecem na diagonal, uma vez só, e param. Tudo fica dentro do SVG
(o GitHub bloqueia JavaScript e CSS externo no README, mas roda animação de SVG).
    python scripts/render_heatmap_svg.py
"""

import json
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "contributions.json"
OUTPUT = ROOT / "contrib-heatmap.svg"

# Mesma paleta do portfólio: vazio -> ciano mais forte
PALETTE = ["#1e293b", "#0c4a6e", "#0369a1", "#0ea5e9", "#7dd3fc"]
BG, PANEL_BORDER, TEXT, MUTED, PRIMARY = "#0f172a", "#334155", "#e2e8f0", "#94a3b8", "#38bdf8"
FONT = "ui-monospace, SFMono-Regular, Menlo, Consolas, 'Liberation Mono', monospace"

MONTHS = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez"]
WEEKDAY_LABELS = {1: "Seg", 3: "Qua", 5: "Sex"}  # linha 0 = domingo, como no GitHub

CELL, GAP = 12, 3
STEP = CELL + GAP
PAD = 24
HEADER_H = 34  # barra de título estilo janela de terminal
LABEL_W = 34
MONTH_H = 20
STAGGER = 0.012  # segundos entre cada diagonal


def br_date(iso: str) -> str:
    d = date.fromisoformat(iso)
    return f"{d.day:02d}/{d.month:02d}"


def main() -> None:
    data = json.loads(DATA.read_text(encoding="utf-8"))
    days = data["days"]

    first = date.fromisoformat(days[0]["date"])
    first_sunday = first.toordinal() - (first.weekday() + 1) % 7
    weeks = (date.fromisoformat(days[-1]["date"]).toordinal() - first_sunday) // 7 + 1

    grid_x = PAD + LABEL_W
    grid_y = HEADER_H + PAD + MONTH_H
    width = grid_x + weeks * STEP - GAP + PAD
    footer_y = grid_y + 7 * STEP + 22
    height = footer_y + 20 + PAD

    cells, month_starts = [], []
    last_month = None
    for day in days:
        d = date.fromisoformat(day["date"])
        row = (d.weekday() + 1) % 7
        col = (d.toordinal() - first_sunday) // 7
        x, y = grid_x + col * STEP, grid_y + row * STEP
        delay = (col + row) * STAGGER
        label = f"{day['count']} contribuição(ões) em {br_date(day['date'])}"
        cells.append(
            f'<rect class="c" x="{x}" y="{y}" width="{CELL}" height="{CELL}" rx="3" '
            f'fill="{PALETTE[day["level"]]}" style="animation-delay:{delay:.3f}s"><title>{label}</title></rect>'
        )
        if row == 0 and d.month != last_month:
            month_starts.append((col, d.month))
            last_month = d.month

    # Rótulo do mês na primeira semana dele; pula quando o próximo começa perto demais
    # (acontece com o mês parcial na primeira ou na última coluna)
    month_labels = []
    for i, (col, month) in enumerate(month_starts):
        next_col = month_starts[i + 1][0] if i + 1 < len(month_starts) else weeks
        if next_col - col >= 3:
            month_labels.append(f'<text x="{grid_x + col * STEP}" y="{grid_y - 8}">{MONTHS[month - 1]}</text>')

    weekday_labels = [
        f'<text x="{PAD}" y="{grid_y + row * STEP + CELL - 2}">{text}</text>'
        for row, text in WEEKDAY_LABELS.items()
    ]

    stats = [f'{data["total"]} contribuições no último ano']
    if data["current_streak"] > 0:
        stats.append(f'sequência atual: {data["current_streak"]} dias')
    stats.append(f'maior sequência: {data["longest_streak"]} dias')
    best = data["best_day"]
    if best["count"] > 0:
        stats.append(f'melhor dia: {best["count"]} em {br_date(best["date"])}')

    legend_x = width - PAD - (len(PALETTE) * STEP) - 40
    legend = [f'<text x="{legend_x - 8}" y="{footer_y}" text-anchor="end">menos</text>']
    for i, color in enumerate(PALETTE):
        legend.append(f'<rect x="{legend_x + i * STEP}" y="{footer_y - CELL + 2}" width="{CELL}" height="{CELL}" rx="3" fill="{color}"/>')
    legend.append(f'<text x="{legend_x + len(PALETTE) * STEP + 4}" y="{footer_y}">mais</text>')

    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-labelledby="t">
<title id="t">Contribuições de {data["user"]} no GitHub: {stats[0]}</title>
<style>
  text {{ font-family: {FONT}; font-size: 11px; fill: {MUTED}; }}
  .title {{ fill: {TEXT}; font-size: 12px; }}
  .stats {{ fill: {TEXT}; }}
  .c {{ opacity: 0; transform-box: fill-box; transform-origin: center; animation: pop .45s ease-out forwards; }}
  @keyframes pop {{ from {{ opacity: 0; transform: translateY(-6px) scale(.6); }} to {{ opacity: 1; transform: none; }} }}
  @media (prefers-reduced-motion: reduce) {{ .c {{ animation: none; opacity: 1; }} }}
</style>
<rect x=".5" y=".5" width="{width - 1}" height="{height - 1}" rx="12" fill="{BG}" stroke="{PANEL_BORDER}"/>
<path d="M.5 {HEADER_H}H{width - .5}" stroke="{PANEL_BORDER}"/>
<circle cx="20" cy="17" r="5" fill="#ef4444"/><circle cx="36" cy="17" r="5" fill="#eab308"/><circle cx="52" cy="17" r="5" fill="#22c55e"/>
<text class="title" x="70" y="21">contributions — últimos 12 meses</text>
{"".join(month_labels)}
{"".join(weekday_labels)}
{"".join(cells)}
<text class="stats" x="{grid_x}" y="{footer_y}">{" · ".join(stats)}</text>
{"".join(legend)}
</svg>
'''
    OUTPUT.write_text(svg, encoding="utf-8")
    print(f"{OUTPUT.name}: {width}x{height}, {len(cells)} células")


if __name__ == "__main__":
    main()
