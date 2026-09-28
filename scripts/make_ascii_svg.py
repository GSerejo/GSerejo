"""Converte source-prepped.png em ascii-portrait.svg: um retrato em ASCII que se "digita" linha a linha.

Roda só quando a foto muda, depois do prep_photo.py:
    python scripts/make_ascii_svg.py
"""

from pathlib import Path
from xml.sax.saxutils import escape

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "source-prepped.png"
OUTPUT = ROOT / "ascii-portrait.svg"

COLS = 96
FONT_SIZE = 6
CHAR_W = FONT_SIZE * 0.6  # largura de um caractere monoespaçado
LINE_H = FONT_SIZE * 1.0
# Claro -> esparso, escuro -> denso: sobrancelhas, olhos, barba e cabelo viram traços fortes,
# como num desenho a lápis, e a pele fica leve
RAMP = " .`:-=+*cs#%@"
MIN_GLYPH = 1  # a silhueta nunca some: pixel da pessoa vira no mínimo "."
GAMMA = 1.15  # > 1 clareia um pouco os tons médios, deixando as sombras de verdade densas

BG, PANEL_BORDER, INK, CURSOR, MUTED = "#0f172a", "#334155", "#cbd5e1", "#22c55e", "#94a3b8"
FONT = "ui-monospace, SFMono-Regular, Menlo, Consolas, 'Liberation Mono', monospace"

PAD = 20
HEADER_H = 34
ROW_DELAY = 0.03  # segundos entre o início de cada linha
ROW_DURATION = 0.35


def to_ascii(image: Image.Image) -> list[str]:
    rows = round(COLS * image.height / image.width * CHAR_W / LINE_H)
    small = image.resize((COLS, rows), Image.LANCZOS)
    lines = []
    for y in range(rows):
        line = []
        for x in range(COLS):
            lum, alpha = small.getpixel((x, y))
            if alpha < 128:
                line.append(" ")
            else:
                darkness = 1 - (lum / 255) ** (1 / GAMMA)
                index = MIN_GLYPH + round(darkness * (len(RAMP) - 1 - MIN_GLYPH))
                line.append(RAMP[index])
        lines.append("".join(line))
    return lines


def main() -> None:
    lines = to_ascii(Image.open(SOURCE).convert("LA"))
    art_w = COLS * CHAR_W
    width = round(art_w + 2 * PAD)
    top = HEADER_H + PAD
    height = round(top + len(lines) * LINE_H + PAD)

    defs, rows = [], []
    for i, line in enumerate(lines):
        if not line.strip():
            continue
        y = top + i * LINE_H
        begin = f"{i * ROW_DELAY:.3f}s"
        # Cada linha é revelada por um recorte que cresce da esquerda para a direita
        defs.append(
            f'<clipPath id="r{i}"><rect x="{PAD}" y="{y:.1f}" width="0" height="{LINE_H + 1}">'
            f'<animate attributeName="width" from="0" to="{art_w:.1f}" begin="{begin}" dur="{ROW_DURATION}s" fill="freeze"/>'
            f"</rect></clipPath>"
        )
        rows.append(
            f'<text clip-path="url(#r{i})" x="{PAD}" y="{y + LINE_H * 0.8:.1f}" textLength="{art_w:.1f}" '
            f'lengthAdjust="spacingAndGlyphs" xml:space="preserve">{escape(line)}</text>'
        )
        # Cursor em bloco que acompanha a borda do recorte e some no fim da linha
        rows.append(
            f'<rect x="{PAD}" y="{y:.1f}" width="{CHAR_W:.1f}" height="{LINE_H}" fill="{CURSOR}" opacity="0">'
            f'<animate attributeName="x" from="{PAD}" to="{PAD + art_w:.1f}" begin="{begin}" dur="{ROW_DURATION}s" fill="freeze"/>'
            f'<animate attributeName="opacity" values="1;1;0" keyTimes="0;0.9;1" begin="{begin}" dur="{ROW_DURATION}s" fill="freeze"/>'
            f"</rect>"
        )

    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-labelledby="t">
<title id="t">Retrato em ASCII de Gabriel Serejo</title>
<style>
  text {{ font-family: {FONT}; font-size: {FONT_SIZE}px; fill: {INK}; }}
  .title {{ font-size: 12px; fill: {MUTED}; }}
</style>
<rect x=".5" y=".5" width="{width - 1}" height="{height - 1}" rx="12" fill="{BG}" stroke="{PANEL_BORDER}"/>
<path d="M.5 {HEADER_H}H{width - .5}" stroke="{PANEL_BORDER}"/>
<circle cx="20" cy="17" r="5" fill="#ef4444"/><circle cx="36" cy="17" r="5" fill="#eab308"/><circle cx="52" cy="17" r="5" fill="#22c55e"/>
<text class="title" x="70" y="21">~/avatar.txt</text>
<defs>{"".join(defs)}</defs>
{"".join(rows)}
</svg>
'''
    OUTPUT.write_text(svg, encoding="utf-8")
    print(f"{OUTPUT.name}: {width}x{height}, {len(lines)} linhas x {COLS} colunas")


if __name__ == "__main__":
    main()
