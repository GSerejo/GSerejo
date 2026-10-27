"""Peças comuns das três máquinas da oficina: paleta, moldura do painel, animações SMIL em loop e fonte de traço único.

Toda animação é SMIL (<animate> dentro do SVG): o GitHub roda SMIL em <img>, e cada uma
tem dur = ciclo e repeatCount="indefinite", então as máquinas ficam trabalhando em loop.
"""

import html
import math
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FONTS = Path(__file__).resolve().parent / "fonts"

W = 860
BG, BORDER, DOT = "#0d1017", "#232a38", "#1b2130"
SURFACE, SURFACE_2, METAL, LINE = "#151a24", "#1c2230", "#2a3345", "#334058"
TEXT, MUTED, ACCENT, TEAL = "#e7eaf0", "#8a93a6", "#ff7a45", "#4fd1c5"
PAPER, INK = "#f3eee3", "#1d1d24"
FONT = "ui-monospace, SFMono-Regular, Menlo, Consolas, 'Liberation Mono', monospace"
EASE = "0.45 0 0.2 1"  # keySpline de entrada e saída suaves


def anim(attr: str, frames: list[tuple[float, object]], cycle: float, discrete: bool = False, tag: str = "animate", extra: str = "") -> str:
    """Animação em loop a partir de (segundo, valor). Completa o início e o fim do ciclo."""
    frames = sorted(frames, key=lambda f: f[0])
    if frames[0][0] > 0:
        frames.insert(0, (0, frames[0][1]))
    if frames[-1][0] < cycle:
        frames.append((cycle, frames[-1][1]))
    times = ";".join(f"{min(max(t / cycle, 0), 1):.5f}" for t, _ in frames)
    values = ";".join(str(v) for _, v in frames)
    mode = ' calcMode="discrete"' if discrete else ""
    return (f'<{tag} attributeName="{attr}" dur="{cycle}s" repeatCount="indefinite"{mode} '
            f'keyTimes="{times}" values="{values}"{extra}/>')


def eased(attr: str, frames: list[tuple], cycle: float, tag: str = "animate", extra: str = "") -> str:
    """Como anim, mas cada trecho com aceleração suave (para movimentos de máquina).
    Um quadro (t, valor, "linear") faz o trecho que chega nele andar em velocidade constante."""
    frames = sorted(frames, key=lambda f: f[0])
    if frames[0][0] > 0:
        frames.insert(0, (0, frames[0][1]))
    if frames[-1][0] < cycle:
        frames.append((cycle, frames[-1][1]))
    times = ";".join(f"{f[0] / cycle:.5f}" for f in frames)
    values = ";".join(str(f[1]) for f in frames)
    splines = ";".join("0 0 1 1" if len(f) > 2 else EASE for f in frames[1:])
    return (f'<{tag} attributeName="{attr}" dur="{cycle}s" repeatCount="indefinite" calcMode="spline" '
            f'keyTimes="{times}" keySplines="{splines}" values="{values}"{extra}/>')


def pulse(attr: str, low, high, dur: float) -> str:
    """Respiração contínua (LEDs, brilho do bico)."""
    return (f'<animate attributeName="{attr}" dur="{dur}s" repeatCount="indefinite" calcMode="spline" '
            f'keyTimes="0;0.5;1" keySplines="{EASE};{EASE}" values="{low};{high};{low}"/>')


def callout(x1: float, y1: float, x2: float, y2: float, label: str, anchor: str = "start") -> str:
    """Legenda técnica: ponto na peça, linha fina e rótulo."""
    tx = x2 + (6 if anchor == "start" else -6)
    return (f'<circle cx="{x1}" cy="{y1}" r="2.5" fill="{ACCENT}"/>'
            f'<path d="M{x1} {y1}L{x2} {y2}" stroke="{LINE}" stroke-width="1" stroke-dasharray="3 3"/>'
            f'<text class="note" x="{tx}" y="{y2 + 4}" text-anchor="{anchor}" fill="{MUTED}">{html.escape(label)}</text>')


def panel(height: int, index: str, title: str, alt: str, body: str, defs: str = "", style: str = "") -> str:
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{height}" viewBox="0 0 {W} {height}" role="img" aria-labelledby="t">
<title id="t">{html.escape(alt)}</title>
<style>
  svg {{ fill: {TEXT}; }}
  text {{ font-family: {FONT}; }}
  .head {{ font-size: 12px; letter-spacing: .08em; }}
  .note {{ font-size: 10.5px; }}
{style}
</style>
<defs>
  <pattern id="dots" width="18" height="18" patternUnits="userSpaceOnUse"><circle cx="1.5" cy="1.5" r="1" fill="{DOT}"/></pattern>
  <filter id="shadow" x="-20%" y="-20%" width="140%" height="160%"><feDropShadow dx="0" dy="6" stdDeviation="7" flood-color="#000" flood-opacity=".45"/></filter>
{defs}
</defs>
<rect x=".5" y=".5" width="{W - 1}" height="{height - 1}" rx="16" fill="{BG}" stroke="{BORDER}"/>
<rect x="1" y="1" width="{W - 2}" height="{height - 2}" rx="16" fill="url(#dots)"/>
<text class="head" x="26" y="34" fill="{MUTED}"><tspan fill="{ACCENT}">{index}</tspan>  /  {html.escape(title)}</text>
<text class="head" x="{W - 26}" y="34" text-anchor="end" fill="{MUTED}">oficina do gabriel</text>
{body}
</svg>
'''


# ---------------------------------------------------------------- fonte de traço único
def _parse_path(d: str) -> list[list[tuple[float, float]]]:
    toks = re.findall(r"-?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?|[A-Za-z]", d)
    strokes, cmd, i = [], None, 0
    while i < len(toks):
        if toks[i].isalpha():
            cmd = toks[i]
            i += 1
            continue
        if cmd == "C":  # curvas viram polilinha
            (x0, y0), (x1, y1, x2, y2, x, y) = strokes[-1][-1], map(float, toks[i:i + 6])
            i += 6
            for t in (k / 6 for k in range(1, 7)):
                u = 1 - t
                strokes[-1].append((u**3 * x0 + 3 * u * u * t * x1 + 3 * u * t * t * x2 + t**3 * x,
                                    u**3 * y0 + 3 * u * u * t * y1 + 3 * u * t * t * y2 + t**3 * y))
            continue
        x, y = float(toks[i]), float(toks[i + 1])
        i += 2
        if cmd == "M":
            strokes.append([(x, y)])
            cmd = "L"
        else:
            strokes[-1].append((x, y))
    return [s for s in strokes if len(s) > 1]


class StrokeFont:
    """Fonte SVG de traço único (EMS, licença OFL): cada letra é uma linha, como a caneta faria."""

    def __init__(self, name: str):
        s = (FONTS / f"{name}.svg").read_text(encoding="utf-8")
        default = float(re.search(r'<font [^>]*horiz-adv-x="([\d.]+)"', s).group(1))
        self.glyphs = {}
        for tag in re.findall(r"<glyph\b[^>]*>", s):
            attrs = dict(re.findall(r'([\w-]+)="([^"]*)"', tag))
            ch = html.unescape(attrs.get("unicode", ""))
            if len(ch) == 1:
                self.glyphs[ch] = (float(attrs.get("horiz-adv-x", default)), _parse_path(attrs.get("d", "")))
        self.space = self.glyphs[" "][0] if " " in self.glyphs else default * 0.6

    def glyph(self, ch: str):
        return self.glyphs.get(ch) or self.glyphs["?"]

    def width(self, text: str, size: float) -> float:
        return sum((self.space if c == " " else self.glyph(c)[0]) * size / 1000 + size * 0.01 for c in text)

    def strokes(self, text: str, x: float, y: float, size: float, rng, jitter: float = 1.0):
        """Polilinhas da frase sobre a linha de base y, com a pequena irregularidade da mão."""
        out, cx, sc = [], x, size / 1000
        for ch in text:
            if ch == " ":
                cx += self.space * sc
                continue
            adv, glyph = self.glyph(ch)
            s = sc * rng.uniform(0.97, 1.03)
            rot = math.radians(rng.uniform(-2, 2) * jitter)
            dy = rng.uniform(-0.5, 0.5) * jitter * size * 0.03
            cos, sin = math.cos(rot), math.sin(rot)
            for st in glyph:
                out.append([(cx + px * s * cos + py * s * sin, y + dy + px * s * sin - py * s * cos) for px, py in st])
            cx += adv * s + size * 0.01
        return out
