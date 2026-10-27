"""Gera recibo.svg: uma impressora térmica imprime os projetos num cupom, rasga e imprime de novo.

O cupom sai do slot linha a linha, a fila à esquerda acompanha cada projeto e o rodapé
traz os números do dia (data/contributions.json). Só biblioteca padrão: roda na Action diária.
    python scripts/render_receipt_svg.py
"""

import html
import json
import random
from datetime import datetime, timedelta

from oficina import ACCENT, BG, LINE, MUTED, ROOT, SURFACE, SURFACE_2, TEAL, W, anim, callout, eased, panel, pulse

DATA = ROOT / "data" / "contributions.json"
OUTPUT = ROOT / "recibo.svg"

PROJECTS = [
    ("App Remédios", ["alarme na hora de cada remédio", "e foto da cartela p/ o cuidador"], "react native · expo · ts"),
    ("clone-tabnews", ["api em next.js, postgres no", "docker e testes de integração"], "next.js · postgres · jest"),
    ("Curriculo", ["portfólio e currículo bilíngues", "com pdf pronto para ats"], "html · css · js"),
    ("365prints", ["busca no que é dito em 365", "vídeos de impressão 3d"], "next.js · python · whisper"),
]

CYCLE = 22.0
PRINT_START, ROW_STEP, ROW_PAUSE = 0.8, 0.07, 0.13
TEAR, RESET = 17.4, 18.8
CX, RW = W / 2, 268
RX = CX - RW / 2
PAPER_TOP = 58
INK = "#2b2b31"
FS = 11.5  # fonte do cupom
CHAR_W = FS * 0.6


def rows(data: dict) -> list[tuple]:
    fetched = datetime.fromisoformat(data["fetched_at"]) - timedelta(hours=3)  # horário de Brasília
    best = data["best_day"]
    best_date = datetime.fromisoformat(best["date"]).strftime("%d/%m")
    out = [("title", "OFICINA DO GABRIEL"), ("center", "dev full stack · brasília/df"), ("sep",),
           ("pair", "DATA", fetched.strftime("%d/%m/%Y")), ("pair", "PEDIDO", f"#{fetched.timetuple().tm_yday:04d}"), ("sep",)]
    for n, (name, desc, tags) in enumerate(PROJECTS, start=1):
        out.append(("item", f"{n:02d}", name, n - 1))
        out += [("desc", line) for line in desc]
        out.append(("tags", tags))
        out.append(("gap",))
    out += [("sep",), ("pair", "PROJETOS", str(len(PROJECTS))), ("pair", "COMMITS 12 MESES", str(data["total"])),
            ("pair", "MELHOR DIA", f"{best['count']} em {best_date}"), ("pair", "MAIOR SEQUÊNCIA", f"{data['longest_streak']} dias"),
            ("sep",), ("barcode",), ("center", "obrigado pela visita :)"), ("center", "gserejo.github.io/Curriculo")]
    return out


HEIGHTS = {"title": 24, "center": 16, "sep": 14, "pair": 17, "item": 21, "desc": 15, "tags": 17, "gap": 8, "barcode": 56}


def render_row(row: tuple, y: float) -> str:
    kind, left, right = row[0], RX + 16, RX + RW - 16
    text = lambda x, s, anchor="start", extra="": f'<text x="{x:.1f}" y="{y:.1f}" text-anchor="{anchor}"{extra}>{html.escape(s)}</text>'
    if kind == "title":
        return text(CX, "OFICINA DO GABRIEL", "middle", ' font-size="15" font-weight="700" letter-spacing=".12em"')
    if kind == "center":
        return text(CX, row[1], "middle", f' fill="#6b6b73"')
    if kind == "sep":
        return f'<path d="M{left} {y - 4:.1f}H{right}" stroke="{INK}" stroke-dasharray="4 3" stroke-width="1"/>'
    if kind == "pair":
        a, b = row[1], row[2]
        x1, x2 = left + len(a) * CHAR_W + 6, right - len(b) * CHAR_W - 6
        return (text(left, a) + text(right, b, "end")
                + f'<path d="M{x1:.1f} {y - 3:.1f}H{x2:.1f}" stroke="{INK}" stroke-dasharray="1 3" stroke-linecap="round"/>')
    if kind == "item":
        return text(left, row[1], extra=f' fill="{ACCENT}" font-weight="700"') + text(left + 26, row[2], extra=' font-weight="700" font-size="13"')
    if kind == "desc":
        return text(left + 26, row[1], extra=' fill="#55555d"')
    if kind == "tags":
        return text(left + 26, row[1], extra=f' fill="#8a8a92" font-size="10"')
    if kind == "barcode":
        rng, x, bars = random.Random("gserejo"), left + 22, []
        while x < right - 24:
            w = rng.choice((1, 1, 2, 3))
            bars.append(f'<rect x="{x:.1f}" y="{y - 38:.1f}" width="{w}" height="28" fill="{INK}"/>')
            x += w + rng.choice((1, 2, 2, 3))
        return "".join(bars) + text(CX, "2 0 2 6   0 3 6 5   G S", "middle", ' font-size="8.5" fill="#6b6b73" dy="2"')
    return ""


def main() -> None:
    data = json.loads(DATA.read_text(encoding="utf-8"))
    items = rows(data)
    top_margin, bottom_margin = 26, 22
    paper_h = top_margin + sum(HEIGHTS[r[0]] for r in items) + bottom_margin
    slot = PAPER_TOP + paper_h
    height = int(slot + 118)

    # Linhas no papel (coordenadas absolutas com o cupom já impresso) e o cronograma de cada uma
    body_rows, feed, item_times = [], [(0, paper_h), (PRINT_START, paper_h), (PRINT_START + 0.3, paper_h - top_margin)], {}
    y, t = PAPER_TOP + top_margin, PRINT_START + 0.3
    head = [(0, 0)]
    for row in items:
        h = HEIGHTS[row[0]]
        body_rows.append(render_row(row, y + h - 5))
        y += h
        t += ROW_PAUSE
        head += [(t - ROW_PAUSE, 1), (t, 0.35)]
        t += ROW_STEP
        feed.append((t, round(paper_h - (y - PAPER_TOP), 1)))
        if row[0] == "item":
            item_times[row[3]] = t
    printed = t + 0.35
    feed += [(printed, 0)]
    end_times = sorted(item_times.values())[1:] + [printed]
    head += [(printed, 0)]

    move = anim("transform", [(tt, f"0 {v}") for tt, v in feed] + [(TEAR, "0 0"), (TEAR + 1.2, "0 -34"), (RESET, "0 -34"), (RESET + .01, f"0 {paper_h}")],
                CYCLE, tag="animateTransform", extra=' type="translate"')
    fade = eased("opacity", [(TEAR, 1), (TEAR + 1.2, 0), (RESET + .05, 0), (RESET + .1, 1)], CYCLE)
    head_glow = anim("opacity", head, CYCLE)

    # Bordas serrilhadas do cupom (em cima, o corte do cupom anterior; embaixo, o rasgo)
    teeth = lambda y0, d: "".join(f"L{RX + i * 8 + 4:.1f} {y0 + d}L{RX + i * 8 + 8:.1f} {y0}" for i in range(int(RW / 8)))
    paper = (f'<path d="M{RX} {PAPER_TOP}{teeth(PAPER_TOP, -5)}L{RX + RW} {slot + 40}H{RX}Z" fill="url(#paperfade)"/>'
             f'<path d="M{RX} {PAPER_TOP}{teeth(PAPER_TOP, -5)}" fill="none" stroke="#d9d3c6" stroke-width=".8"/>')

    # Fila de impressão à esquerda
    queue = [f'<text x="44" y="122" font-size="10.5" fill="{MUTED}" letter-spacing=".08em">FILA DE IMPRESSÃO</text>']
    for i, (name, _, _) in enumerate(PROJECTS):
        y0 = 152 + i * 34
        start, done = item_times[i] - ROW_STEP - ROW_PAUSE, end_times[i]
        states = [("na fila", MUTED, [(0, 1), (start, 0), (RESET, 1)]),
                  ("imprimindo", ACCENT, [(0, 0), (start, 1), (done, 0)]),
                  ("impresso", TEAL, [(0, 0), (done, 1), (RESET, 0)])]
        queue.append(f'<text x="58" y="{y0}" font-size="13">{html.escape(name)}</text>')
        for label, color, frames in states:
            queue.append(f'<g opacity="0">{anim("opacity", frames, CYCLE, discrete=True)}'
                         f'<circle cx="47" cy="{y0 - 4}" r="3.5" fill="{color}"/>'
                         f'<text x="58" y="{y0 + 15}" font-size="10.5" fill="{color}">{label}</text></g>')

    px, pw = CX - 168, 336
    printer = f'''
<ellipse cx="{CX}" cy="{slot + 92}" rx="{pw / 2 + 10}" ry="10" fill="#000" opacity=".45"/>
<rect x="{px}" y="{slot - 12}" width="{pw}" height="98" rx="20" fill="{SURFACE}" stroke="{LINE}"/>
<rect x="{px + 14}" y="{slot - 12}" width="{pw - 28}" height="20" rx="9" fill="{SURFACE_2}" stroke="{LINE}"/>
<rect x="{RX - 12}" y="{slot - 3}" width="{RW + 24}" height="6" rx="3" fill="#05070b"/>
<rect x="{RX - 4}" y="{slot - 1.5}" width="{RW + 8}" height="3" rx="1.5" fill="{ACCENT}" opacity="0">{head_glow}</rect>
<circle cx="{px + 30}" cy="{slot + 52}" r="5" fill="{TEAL}">{pulse("opacity", .3, 1, 1.6)}</circle>
<text x="{px + 44}" y="{slot + 56}" font-size="10.5" fill="{MUTED}" letter-spacing=".08em">TÉRMICA · 58 MM</text>
<circle cx="{px + pw - 34}" cy="{slot + 50}" r="13" fill="{SURFACE_2}" stroke="{LINE}"/>
<path d="M{px + pw - 39} {slot + 46}l5 6l5 -6" fill="none" stroke="{MUTED}" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/>
'''
    body = f'''
<g clip-path="url(#above)"><g>{fade}<g>{move}
  {paper}
  <g font-size="{FS}" fill="{INK}">{"".join(body_rows)}</g>
</g></g></g>
{printer}
{"".join(queue)}
{callout(RX + RW + 10, slot, RX + RW + 70, slot - 46, "cabeça térmica · 203 dpi")}
{callout(px + pw - 34, slot + 64, px + pw + 40, slot + 64, "avanço do papel")}
'''
    defs = f'''  <clipPath id="above"><rect x="0" y="0" width="{W}" height="{slot}"/></clipPath>
  <linearGradient id="paperfade" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0" stop-color="#fbf9f4"/><stop offset=".85" stop-color="#f4f0e7"/><stop offset="1" stop-color="#d8d2c5"/>
  </linearGradient>'''
    alt = "Uma impressora térmica imprime um cupom com os projetos: " + ", ".join(p[0] for p in PROJECTS) + "."
    svg = panel(height, "02", "projetos", alt, body, defs)
    OUTPUT.write_text(svg, encoding="utf-8")
    print(f"{OUTPUT.name}: {len(svg) / 1024:.0f} KB, {W}x{height}, cupom de {paper_h}px impresso em {printed:.1f}s")


if __name__ == "__main__":
    main()
