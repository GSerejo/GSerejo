"""Gera info-card.svg: um cartão estilo neofetch com cargo, stack e projetos, que aparece linha a linha.

Edite INFO quando algo mudar (cargo, stack, projetos) e rode de novo:
    python scripts/make_info_card.py
"""

from pathlib import Path
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parent.parent
OUTPUT = ROOT / "info-card.svg"

USER, HOST = "gabriel", "github"
INFO = [
    ("Cargo", "Estagiário Dev Full Stack @ CDS Solutions"),
    ("Antes", "Estagiário de TI @ CFN · IESB"),
    ("Formação", "Ciência da Computação @ IESB"),
    ("Linguagens", "TypeScript · Python · Rust · Java"),
    ("Front", "React · Next.js · React Native"),
    ("Back/Dados", "Node.js · PostgreSQL · Docker"),
    ("Testes", "Jest"),
    ("Projetos", "App Remédios · clone-tabnews"),
    ("Em breve", "novo projeto em construção"),
    ("Local", "Brasília, DF"),
    ("Idiomas", "Português · Inglês (B1)"),
]

# Mesmas dimensões de exibição do retrato (370px) e do cartão (490px) no README:
# a altura é calculada para os dois painéis terminarem na mesma linha.
PORTRAIT_SVG = ROOT / "ascii-portrait.svg"
PORTRAIT_DISPLAY_W, CARD_W = 370, 490

BG, PANEL_BORDER, TEXT, MUTED = "#0f172a", "#334155", "#e2e8f0", "#94a3b8"
PRIMARY, SECONDARY, ACCENT = "#38bdf8", "#818cf8", "#22c55e"
PALETTE = ["#ef4444", "#eab308", "#22c55e", "#38bdf8", "#818cf8", "#c084fc", "#f472b6", "#e2e8f0"]
FONT = "ui-monospace, SFMono-Regular, Menlo, Consolas, 'Liberation Mono', monospace"

PAD = 24
HEADER_H = 34
LINE_H = 24
KEY_W = 104
START_DELAY = 0.4  # espera o retrato começar a "digitar"
LINE_DELAY = 0.12


def card_height() -> int:
    import re

    match = re.search(r'viewBox="0 0 (\d+) (\d+)"', PORTRAIT_SVG.read_text(encoding="utf-8"))
    portrait_w, portrait_h = int(match.group(1)), int(match.group(2))
    return round(PORTRAIT_DISPLAY_W * portrait_h / portrait_w)


def line(index: int, y: int, content: str) -> str:
    delay = START_DELAY + index * LINE_DELAY
    return f'<g class="l" style="animation-delay:{delay:.2f}s">{content.format(y=y)}</g>'


def main() -> None:
    height = card_height()
    y = HEADER_H + PAD + 14
    lines = [
        line(0, y, f'<text x="{PAD}" y="{{y}}" class="big"><tspan fill="{ACCENT}">{USER}</tspan>'
                   f'<tspan fill="{MUTED}">@</tspan><tspan fill="{PRIMARY}">{HOST}</tspan></text>'),
        line(1, y + 12, f'<path d="M{PAD} {{y}}h{CARD_W - 2 * PAD}" stroke="{PANEL_BORDER}" stroke-dasharray="4 4"/>'),
    ]
    y += 12 + LINE_H + 4
    for i, (key, value) in enumerate(INFO, start=2):
        lines.append(line(i, y, f'<text x="{PAD}" y="{{y}}"><tspan class="k">{escape(key)}</tspan>'
                                f'<tspan x="{PAD + KEY_W}">{escape(value)}</tspan></text>'))
        y += LINE_H

    swatches = "".join(
        f'<rect x="{PAD + i * 26}" y="{{y}}" width="20" height="12" rx="3" fill="{color}"/>'
        for i, color in enumerate(PALETTE)
    )
    lines.append(line(len(INFO) + 2, y - 4, swatches))

    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{CARD_W}" height="{height}" viewBox="0 0 {CARD_W} {height}" role="img" aria-labelledby="t">
<title id="t">Gabriel Serejo: {escape(INFO[0][1])}. Stack: {escape(INFO[3][1])}.</title>
<style>
  text {{ font-family: {FONT}; font-size: 13px; fill: {TEXT}; }}
  .big {{ font-size: 16px; font-weight: 700; }}
  .k {{ fill: {PRIMARY}; font-weight: 700; }}
  .title {{ font-size: 12px; fill: {MUTED}; }}
  .l {{ opacity: 0; animation: in .45s ease-out forwards; }}
  @keyframes in {{ from {{ opacity: 0; transform: translateX(-8px); }} to {{ opacity: 1; transform: none; }} }}
  @media (prefers-reduced-motion: reduce) {{ .l {{ animation: none; opacity: 1; }} }}
</style>
<rect x=".5" y=".5" width="{CARD_W - 1}" height="{height - 1}" rx="12" fill="{BG}" stroke="{PANEL_BORDER}"/>
<path d="M.5 {HEADER_H}H{CARD_W - .5}" stroke="{PANEL_BORDER}"/>
<circle cx="20" cy="17" r="5" fill="#ef4444"/><circle cx="36" cy="17" r="5" fill="#eab308"/><circle cx="52" cy="17" r="5" fill="#22c55e"/>
<text class="title" x="70" y="21">neofetch</text>
{"".join(lines)}
</svg>
'''
    OUTPUT.write_text(svg, encoding="utf-8")
    print(f"{OUTPUT.name}: {CARD_W}x{height}, conteúdo até y={y}")


if __name__ == "__main__":
    main()
