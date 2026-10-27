"""Gera impressora-3d.svg: uma impressora 3D imprime o gráfico de contribuições, camada por camada, em loop.

Cada dia com commits vira um pilar, mais alto quanto mais commits. Todos sobem juntos com a
camada atual, o topo sai laranja do bico quente e esfria para a cor do filamento.
Só biblioteca padrão: roda na Action diária depois do fetch_contributions.py.
    python scripts/render_printer_svg.py
"""

import json
import math
from datetime import date

from oficina import ACCENT, BG, LINE, METAL, MUTED, ROOT, SURFACE, SURFACE_2, TEAL, W, anim, callout, eased, panel, pulse

DATA = ROOT / "data" / "contributions.json"
OUTPUT = ROOT / "impressora-3d.svg"

MONTHS = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"]

# Projeção oblíqua: x = semana, d = profundidade (sábado na frente, domingo no fundo), z = altura
CELL, SX, SY, GAP = 11.0, 5.0, 4.2, 0.2
HMAX, NOZZLE, PARK_Z = 86, 24, 112
OY = 340
LAYERS = 40

# Ciclo (segundos)
CYCLE = 22.0
P0, P1 = 0.4, 10.4  # impressão
PARKED, EJECT, RESET = 11.6, (16.0, 17.2), 17.4
DESCEND = (19.8, 21.6)

TILE, BED_TOP, BED_FRONT = "#1f2737", "#171d29", "#10141d"
TOP, FRONT, SIDE = "#7ce8dc", "#4fd1c5", "#2f9b92"
HOT = "#ffa25f"


def main() -> None:
    data = json.loads(DATA.read_text(encoding="utf-8"))
    days = data["days"]
    first = date.fromisoformat(days[0]["date"])
    first_sunday = first.toordinal() - (first.weekday() + 1) % 7
    weeks = (date.fromisoformat(days[-1]["date"]).toordinal() - first_sunday) // 7 + 1
    ox = (W - weeks * CELL - 7 * SX) / 2

    def q(x, d, z=0.0):
        return ox + x * CELL + d * SX, OY - d * SY - z

    def poly(*pts):
        return " ".join(f"{x:.1f},{y:.1f}" for x, y in pts)

    # Mesa
    a, b, c, e = q(-0.7, -0.7), q(weeks + 0.5, -0.7), q(weeks + 0.5, 7.7), q(-0.7, 7.7)
    bed = (f'<polygon points="{poly(a, b, (b[0], b[1] + 12), (a[0], a[1] + 12))}" fill="{BED_FRONT}" stroke="{LINE}"/>'
           f'<polygon points="{poly(b, c, (c[0], c[1] + 12), (b[0], b[1] + 12))}" fill="#0c1018" stroke="{LINE}"/>'
           f'<polygon points="{poly(a, b, c, e)}" fill="{BED_TOP}" stroke="{LINE}"/>')

    tiles, bars, months, last_month = [], [], [], None
    max_count = max(day["count"] for day in days) or 1
    cells = []
    for day in days:
        d = date.fromisoformat(day["date"])
        row, col = (d.weekday() + 1) % 7, (d.toordinal() - first_sunday) // 7
        cells.append((row, col, day["count"]))
        if row == 0 and d.month != last_month and d.day <= 7:
            last_month = d.month
            x, y = q(col, -0.7)
            months.append(f'<text x="{x:.1f}" y="{y + 28:.1f}" font-size="10" fill="{MUTED}">{MONTHS[d.month - 1]}</text>')

    # Do fundo para a frente e da esquerda para a direita, para as faces se cobrirem certo
    for row, col, count in sorted(cells, key=lambda c: (c[0], c[1])):
        dF = 6 - row
        x0, x1, dB = col, col + 1 - GAP, dF + 1 - GAP
        tiles.append(f'<polygon points="{poly(q(x0, dF), q(x1, dF), q(x1, dB), q(x0, dB))}" fill="{TILE}"/>')
        if count == 0:
            continue
        h = 6 + (HMAX - 6) * math.sqrt(count / max_count)
        done = P0 + (P1 - P0) * h / HMAX
        front = lambda z: poly(q(x0, dF), q(x1, dF), q(x1, dF, z), q(x0, dF, z))
        side = lambda z: poly(q(x1, dF), q(x1, dB), q(x1, dB, z), q(x1, dF, z))
        top = lambda z: poly(q(x0, dF, z), q(x1, dF, z), q(x1, dB, z), q(x0, dB, z))
        grow = lambda shape: anim("points", [(P0, shape(0)), (done, shape(h)), (RESET, shape(h)), (RESET + .01, shape(0))], CYCLE)
        heat = anim("fill", [(P0, TILE), (P0 + .01, HOT), (done, HOT), (done + .9, TOP), (RESET, TOP), (RESET + .01, TILE)], CYCLE)
        bars.append(f'<polygon points="{front(0)}" fill="{FRONT}">{grow(front)}</polygon>'
                    f'<polygon points="{side(0)}" fill="{SIDE}">{grow(side)}</polygon>'
                    f'<polygon points="{top(0)}" fill="{TILE}">{grow(top)}{heat}</polygon>')

    eject = (eased("opacity", [(EJECT[0], 1), (EJECT[1], 0), (RESET + .05, 0), (RESET + .1, 1)], CYCLE)
             + eased("transform", [(EJECT[0], "0 0"), (EJECT[1], "46 0"), (RESET + .05, "46 0"), (RESET + .1, "0 0")], CYCLE,
                     tag="animateTransform", extra=' type="translate"'))

    # Estrutura: colunas nas laterais (no meio da profundidade) e viga do eixo X que sobe com a camada
    left_post, right_post = q(-1.9, 3.5), q(weeks + 1.0, 3.5)
    post_top = OY - 3.5 * SY - PARK_Z - NOZZLE - 46
    posts = "".join(f'<rect x="{x - 7:.1f}" y="{post_top:.1f}" width="14" height="{y - post_top + 6:.1f}" rx="5" fill="{SURFACE_2}" stroke="{LINE}"/>'
                    for x, y in (left_post, right_post))
    posts += f'<rect x="{left_post[0] - 10:.1f}" y="{post_top - 8:.1f}" width="{right_post[0] - left_post[0] + 20:.1f}" height="14" rx="6" fill="{SURFACE}" stroke="{LINE}"/>'

    beam_y = OY - 3.5 * SY - NOZZLE
    z_frames = [(P0, "0 0"), (P1, f"0 {-HMAX}", "linear"), (PARKED, f"0 {-PARK_Z}"), (DESCEND[0], f"0 {-PARK_Z}"), (DESCEND[1], "0 0")]
    lift = eased("transform", z_frames, CYCLE, tag="animateTransform", extra=' type="translate"')

    xa, xb = q(0.5, 3.5)[0], q(weeks - 1.5, 3.5)[0]
    sweeps, t, at_a = [(P0, f"{xb:.1f} 0")], P0, False
    while t + 0.62 < P1:
        t += 0.62
        sweeps.append((t, f"{(xa if not at_a else xb):.1f} 0", "linear"))
        at_a = not at_a
    sweeps += [(P1, f"{xb:.1f} 0"), (PARKED, f"{xb:.1f} 0")]
    slide = eased("transform", sweeps, CYCLE, tag="animateTransform", extra=' type="translate"')
    glow_on = anim("opacity", [(P0, 0), (P0 + .15, 1), (P1, 1), (P1 + .3, 0)], CYCLE)

    blades = "".join(f'<path d="M0 0L{6.5 * math.cos(a):.2f} {6.5 * math.sin(a):.2f}" stroke="{MUTED}" stroke-width="2.4" stroke-linecap="round"/>'
                     for a in (k * 2 * math.pi / 5 for k in range(5)))
    gantry = f'''
<g>{lift}
  <rect x="{left_post[0] - 12:.1f}" y="{beam_y - 6:.1f}" width="{right_post[0] - left_post[0] + 24:.1f}" height="12" rx="5" fill="{METAL}" stroke="{LINE}"/>
  <g>{slide}
    <rect x="-15" y="{beam_y - 30:.1f}" width="30" height="34" rx="6" fill="#323d52" stroke="#45536d"/>
    <g transform="translate(0 {beam_y - 15:.1f})"><circle r="9" fill="{BG}" stroke="#45536d"/>
      <g><animateTransform attributeName="transform" type="rotate" from="0" to="360" dur=".5s" repeatCount="indefinite"/>{blades}</g></g>
    <path d="M-5 {beam_y + 4:.1f}H5L1.5 {beam_y + NOZZLE - 3:.1f}H-1.5Z" fill="#c9a24a"/>
    <g opacity="0">{glow_on}<circle cy="{beam_y + NOZZLE - 1:.1f}" r="5" fill="{ACCENT}">{pulse("opacity", .35, .9, .35)}</circle></g>
  </g>
</g>'''

    # Status, camada e números
    sx = W - 26
    status = []
    for label, color, frames in (("imprimindo commits.gcode", ACCENT, [(0, 1), (P1, 0), (DESCEND[1], 1)]),
                                 ("impressão concluída", TEAL, [(0, 0), (P1, 1), (EJECT[0], 0)]),
                                 ("ejetando a peça", MUTED, [(0, 0), (EJECT[0], 1), (DESCEND[1], 0)])):
        status.append(f'<g opacity="0">{anim("opacity", frames, CYCLE, discrete=True)}'
                      f'<text x="{sx - 14}" y="76" font-size="12" fill="{color}" text-anchor="end">{label}</text>'
                      f'<circle cx="{sx - 4}" cy="72" r="4" fill="{color}">{pulse("opacity", .35, 1, 1.2)}</circle></g>')
    layer_numbers = []
    for n in range(LAYERS + 1):
        start = P0 + (P1 - P0) * n / LAYERS if n else 0
        end = P0 + (P1 - P0) * (n + 1) / LAYERS if n < LAYERS else RESET
        frames = [(0, 0), (start, 1), (end, 0)] if n else [(0, 1), (P0 + (P1 - P0) / LAYERS, 0), (RESET, 1)]
        layer_numbers.append(f'<tspan opacity="0">{anim("opacity", frames, CYCLE, discrete=True)}{n:02d}</tspan>')
    layers = ''.join(f'<text x="{sx - 23}" y="116" font-size="12" text-anchor="end">{t}</text>' for t in layer_numbers)
    progress = anim("width", [(P0, 0), (P1, 200), (RESET, 200), (RESET + .01, 0)], CYCLE)

    best = data["best_day"]
    best_date = date.fromisoformat(best["date"])
    stats = f'''
<text x="26" y="88" font-size="34" font-weight="700">{data["total"]}</text>
<text x="{26 + len(str(data["total"])) * 21 + 10}" y="74" font-size="12" fill="{MUTED}">contribuições</text>
<text x="{26 + len(str(data["total"])) * 21 + 10}" y="90" font-size="12" fill="{MUTED}">nos últimos 12 meses</text>
<text x="26" y="116" font-size="11.5" fill="{MUTED}">melhor dia <tspan fill="{TEAL}">{best["count"]} em {best_date:%d/%m}</tspan>   ·   maior sequência <tspan fill="{TEAL}">{data["longest_streak"]} dias</tspan></text>
{"".join(status)}
<rect x="{sx - 200}" y="88" width="200" height="4" rx="2" fill="{SURFACE_2}"/>
<rect x="{sx - 200}" y="88" width="0" height="4" rx="2" fill="{ACCENT}">{progress}</rect>
<text x="{sx}" y="116" font-size="12" fill="{MUTED}" text-anchor="end">/{LAYERS}</text>
<text x="{sx - 46}" y="116" font-size="12" fill="{MUTED}" text-anchor="end">camada</text>
{layers}'''

    bed_corner = q(weeks + 0.5, -0.7)
    body = f'''
{stats}
{posts}
<g filter="url(#shadow)">{bed}</g>
{"".join(tiles)}
<g>{eject}{"".join(bars)}</g>
{gantry}
{"".join(months)}
{callout(bed_corner[0] - 4, bed_corner[1] + 8, bed_corner[0] + 16, bed_corner[1] + 46, "mesa a 60 °C · cada pilar é um dia", "end")}
'''
    height = int(OY + 66)
    alt = (f"Uma impressora 3D imprime o gráfico de contribuições de Gabriel Serejo: {data['total']} contribuições nos últimos 12 meses, "
           f"melhor dia com {best['count']}.")
    svg = panel(height, "03", "commits", alt, body)
    OUTPUT.write_text(svg, encoding="utf-8")
    print(f"{OUTPUT.name}: {len(svg) / 1024:.0f} KB, {W}x{height}, {len(bars)} pilares")


if __name__ == "__main__":
    main()
