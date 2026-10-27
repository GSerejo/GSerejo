"""Gera plotter.svg: um plotter de mesa que desenha o retrato e o nome com caneta, em loop.

A ponte (eixo Y) e o carro (eixo X) seguem o mesmo cronograma do traço, vértice por vértice,
então a caneta está sempre na ponta da linha que aparece. Roda só quando a foto de perfil ou o texto mudam:
    python scripts/prep_avatar.py   # baixa a foto de perfil do GitHub e gera avatar-prepped.png
    python scripts/make_plotter_svg.py
"""

import math
import random

import cv2
import numpy as np
from PIL import Image

from oficina import ACCENT, BG, INK, LINE, METAL, MUTED, PAPER, ROOT, SURFACE, SURFACE_2, TEAL, TEXT, W, StrokeFont, anim, callout, eased, panel, pulse

OUTPUT = ROOT / "plotter.svg"
SOURCE = ROOT / "avatar-prepped.png"
HEIGHT = 450

INFO = [
    ("nome", "Gabriel Serejo"),
    ("cargo", "Dev Full Stack Júnior"),
    ("empresa", "CDS Solutions"),
    ("formação", "Ciência da Computação · IESB"),
    ("linguagens", "TypeScript · Python · Rust · Java"),
    ("front", "React · Next.js · React Native"),
    ("back", "Node.js · PostgreSQL · Docker"),
    ("base", "Brasília, DF"),
]

# Mesa e papel
BED_X, BED_Y, BED_W, BED_H = 34, 58, 512, 362
PAPER_X, PAPER_Y, PAPER_W, PAPER_H = 70, 92, 440, 296
PARK = (PAPER_X + PAPER_W - 6, PAPER_Y - 16)

# Ciclo (segundos)
CYCLE = 26.0
DRAW_START, DRAW_END = 0.9, 15.5
PARKED = 16.6
FADE_OUT, RESET, FADE_IN = (21.6, 22.6), 22.8, (23.6, 24.8)


def portrait(rng: random.Random, box: int, ox: float, oy: float) -> list[list[tuple[float, float]]]:
    """Contornos + três camadas de hachura cruzada, como um desenho de plotter."""
    im = Image.open(SOURCE).convert("LA")
    k = box / max(im.size)
    w, h = int(im.width * k), int(im.height * k)
    a = np.asarray(im.resize((w, h), Image.LANCZOS)).astype(float)
    gray, mask = a[..., 0], a[..., 1] > 128
    dark = np.where(mask, 1 - gray / 255, 0)
    out = []

    g8 = np.where(mask, gray, 255).astype(np.uint8)
    edges = cv2.Canny(cv2.GaussianBlur(g8, (5, 5), 0), 55, 140)
    contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    silhouette, _ = cv2.findContours(mask.astype(np.uint8) * 255, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    for c in list(silhouette) + list(contours):
        if cv2.arcLength(c, False) < 22:
            continue
        c = cv2.approxPolyDP(c, 1.3, False)
        out.append([(ox + p[0][0], oy + p[0][1]) for p in c])

    r = math.hypot(w, h) / 2
    ts = np.arange(-r, r, 1.0)
    for threshold, angle, gap in [(0.40, 35, 5.0), (0.60, -55, 4.6), (0.80, 80, 4.2), (0.90, 10, 1.6)]:
        th = math.radians(angle)
        d, n = np.array([math.cos(th), math.sin(th)]), np.array([-math.sin(th), math.cos(th)])
        for i, offset in enumerate(np.arange(-r, r, gap)):
            pts = np.array([w / 2, h / 2]) + n * offset + np.outer(ts, d)
            xi, yi = pts[:, 0].round().astype(int), pts[:, 1].round().astype(int)
            inside = (xi >= 0) & (xi < w) & (yi >= 0) & (yi < h)
            on = np.zeros(len(ts), bool)
            on[inside] = dark[yi[inside], xi[inside]] > threshold
            runs = np.flatnonzero(np.diff(np.r_[0, on.astype(int), 0]))
            for s, e in zip(runs[::2], runs[1::2]):
                if e - s >= (2 if gap < 2 else 5):
                    seg = [(ox + pts[s][0] + rng.uniform(-.4, .4), oy + pts[s][1] + rng.uniform(-.4, .4)),
                           (ox + pts[e - 1][0] + rng.uniform(-.4, .4), oy + pts[e - 1][1] + rng.uniform(-.4, .4))]
                    out.append(seg if i % 2 else seg[::-1])
    return nearest_order(out, (ox + w, oy))


def nearest_order(strokes, start):
    """Ordena os traços pelo vizinho mais próximo (invertendo se preciso), como um plotter otimiza."""
    left, ordered, pos = list(strokes), [], start
    while left:
        best, best_d, flip = 0, float("inf"), False
        for i, s in enumerate(left):
            for f, p in ((False, s[0]), (True, s[-1])):
                d = (p[0] - pos[0]) ** 2 + (p[1] - pos[1]) ** 2
                if d < best_d:
                    best, best_d, flip = i, d, f
        s = left.pop(best)
        s = s[::-1] if flip else s
        ordered.append(s)
        pos = s[-1]
    return ordered


def wobble(rng, x1, y1, x2, y2, amp=1.4):
    n = max(2, int(math.dist((x1, y1), (x2, y2)) / 10))
    ph = rng.uniform(0, 6.3)
    return [(x1 + (x2 - x1) * t, y1 + (y2 - y1) * t + amp * math.sin(t * 5.5 + ph) * math.sin(math.pi * t) ** .4)
            for t in (i / n for i in range(n + 1))]


def lettering(rng) -> list[list[tuple[float, float]]]:
    title, hand = StrokeFont("EMSTech"), StrokeFont("EMSCasualHand")
    x0, right = PAPER_X + 250, PAPER_X + PAPER_W - 18
    out = []
    fit = lambda font, text, size: min(size, size * (right - x0) / font.width(text, size))
    for text, y in (("Gabriel", PAPER_Y + 84), ("Serejo", PAPER_Y + 138)):
        out += title.strokes(text, x0, y, fit(title, "Gabriel", 54), rng, jitter=0.6)
    out.append(wobble(rng, x0 - 2, PAPER_Y + 152, x0 + 150, PAPER_Y + 149))
    for i, text in enumerate(("dev full stack júnior", "@ CDS Solutions", "Brasília · DF")):
        out += hand.strokes(text, x0, PAPER_Y + 190 + i * 30, fit(hand, "dev full stack júnior", 23), rng)
    out += hand.strokes("olá! :)", x0 + 96, PAPER_Y + 278, 22, rng)
    return out


def schedule(strokes):
    """Quadros (t, x, y, caneta_abaixada) e o intervalo de cada traço, a velocidade constante."""
    draw_len = sum(math.dist(a, b) for s in strokes for a, b in zip(s, s[1:]))
    travel, pos = 0.0, PARK
    for s in strokes:
        travel += math.dist(pos, s[0])
        pos = s[-1]
    lift = 0.012  # caneta subindo/descendo
    speed = (draw_len + travel / 4) / (DRAW_END - DRAW_START - lift * 2 * len(strokes))
    frames, spans, t, pos = [(0.0, *PARK, 0), (DRAW_START, *PARK, 0)], [], DRAW_START, PARK
    for s in strokes:
        t += math.dist(pos, s[0]) / (speed * 4)
        frames.append((t, *s[0], 0))
        t += lift
        frames.append((t, *s[0], 1))
        start = t
        for a, b in zip(s, s[1:]):
            t += math.dist(a, b) / speed
            frames.append((t, *b, 1))
        spans.append((start, t))
        t += lift
        frames.append((t, *s[-1], 0))
        pos = s[-1]
    frames.append((PARKED, *PARK, 0))
    return frames, spans


def main() -> None:
    rng = random.Random(7)
    strokes = portrait(rng, 220, PAPER_X + 16, PAPER_Y + 30) + lettering(rng)
    frames, spans = schedule(strokes)

    ink = []
    for s, (t0, t1) in zip(strokes, spans):
        d = "M" + "L".join(f"{x:.1f} {y:.1f}" for x, y in s)
        offset = anim("stroke-dashoffset", [(t0, 1.01), (t1, 0), (RESET, 0), (RESET + .01, 1.01)], CYCLE)
        ink.append(f'<path d="{d}" pathLength="1">{offset}</path>')

    carriage_xy = anim("transform", [(t, f"{x:.1f} {y:.1f}") for t, x, y, _ in frames], CYCLE, tag="animateTransform", extra=' type="translate"')
    bridge_y = anim("transform", [(t, f"0 {y:.1f}") for t, _, y, _ in frames], CYCLE, tag="animateTransform", extra=' type="translate"')
    pen_down = anim("opacity", [(t, down) for t, _, _, down in frames], CYCLE)
    paper_fade = eased("opacity", [(FADE_OUT[0], 1), (FADE_OUT[1], 0), (FADE_IN[0], 0), (FADE_IN[1], 1)], CYCLE)
    paper_move = eased("transform", [(FADE_OUT[0], "0 0"), (FADE_OUT[1], "0 -14"), (FADE_IN[0], "0 14"), (FADE_IN[1], "0 0")], CYCLE,
                       tag="animateTransform", extra=' type="translate"')

    # Painel de status à direita
    sx = 572
    status = []
    for label, color, on in (("desenhando", ACCENT, [(0, 1), (PARKED, 0)]), ("pronto", TEAL, [(0, 0), (PARKED, 1), (FADE_OUT[0], 0)]),
                             ("trocando o papel", MUTED, [(0, 0), (FADE_OUT[0], 1), (FADE_IN[1], 0)])):
        status.append(f'<g opacity="0">{anim("opacity", on, CYCLE, discrete=True)}'
                      f'<circle cx="{sx + 6}" cy="78" r="4" fill="{color}">{pulse("opacity", .35, 1, 1.2)}</circle>'
                      f'<text x="{sx + 18}" y="82" font-size="12" fill="{color}">{label}</text></g>')
    progress = anim("width", [(DRAW_START, 0), (DRAW_END, 254), (RESET, 254), (RESET + .01, 0)], CYCLE)
    rows = "".join(
        f'<text x="{sx}" y="{142 + i * 32}" font-size="10.5" fill="{MUTED}" letter-spacing=".06em">{key.upper()}</text>'
        f'<text x="{sx}" y="{158 + i * 32}" font-size="13">{value}</text>'
        for i, (key, value) in enumerate(INFO)
    )

    body = f'''
<rect x="{BED_X}" y="{BED_Y}" width="{BED_W}" height="{BED_H}" rx="14" fill="{SURFACE}" stroke="{LINE}" filter="url(#shadow)"/>
<rect x="{BED_X + 12}" y="{BED_Y + 10}" width="10" height="{BED_H - 20}" rx="5" fill="{SURFACE_2}" stroke="{LINE}"/>
<rect x="{BED_X + BED_W - 22}" y="{BED_Y + 10}" width="10" height="{BED_H - 20}" rx="5" fill="{SURFACE_2}" stroke="{LINE}"/>
<g opacity="1">{paper_fade}<g>{paper_move}
  <rect x="{PAPER_X}" y="{PAPER_Y}" width="{PAPER_W}" height="{PAPER_H}" rx="2" fill="{PAPER}" filter="url(#shadow)"/>
  <g fill="none" stroke="{INK}" stroke-width="1.15" stroke-linecap="round" stroke-linejoin="round" stroke-dasharray="1 2">{"".join(ink)}</g>
</g></g>
<g filter="url(#shadow)">{bridge_y}
  <rect x="{BED_X + 6}" y="-10" width="{BED_W - 12}" height="20" rx="7" fill="{METAL}" fill-opacity=".9" stroke="{LINE}"/>
  <path d="M{BED_X + 30} 0H{BED_X + BED_W - 30}" stroke="{BG}" stroke-width="2" stroke-linecap="round" opacity=".6"/>
  <rect x="{BED_X + 4}" y="-14" width="26" height="28" rx="6" fill="{SURFACE_2}" stroke="{LINE}"/>
  <rect x="{BED_X + BED_W - 30}" y="-14" width="26" height="28" rx="6" fill="{SURFACE_2}" stroke="{LINE}"/>
</g>
<g filter="url(#shadow)">{carriage_xy}
  <rect x="-17" y="-17" width="34" height="34" rx="8" fill="#323d52" stroke="#45536d"/>
  <circle r="8.5" fill="{BG}" stroke="{ACCENT}" stroke-width="2"/>
  <circle r="3.2" fill="{ACCENT}" opacity="0">{pen_down}</circle>
  <circle cx="11" cy="-11" r="2" fill="{TEAL}">{pulse("opacity", .3, 1, .9)}</circle>
</g>
{callout(BED_X + 17, BED_Y + 330, BED_X + 17, BED_Y + BED_H + 18, "eixo y · correia GT2")}
{"".join(status)}
<text x="{sx}" y="58" font-size="10.5" fill="{MUTED}" letter-spacing=".06em">PLOTTER GS-01 · CANETA 0.4 MM</text>
<rect x="{sx}" y="96" width="254" height="4" rx="2" fill="{SURFACE_2}"/>
<rect x="{sx}" y="96" width="0" height="4" rx="2" fill="{ACCENT}">{progress}</rect>
{rows}
'''
    alt = "Um plotter desenha com caneta o retrato de Gabriel Serejo e escreve: Dev Full Stack Júnior na CDS Solutions, Brasília, DF."
    svg = panel(HEIGHT, "01", "quem sou", alt, body)
    OUTPUT.write_text(svg, encoding="utf-8")
    print(f"{OUTPUT.name}: {len(svg) / 1024:.0f} KB, {len(strokes)} traços, {len(frames)} quadros")


if __name__ == "__main__":
    main()
