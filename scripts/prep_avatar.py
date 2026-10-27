"""Baixa a foto de perfil do GitHub e prepara para o plotter: tira o fundo e realça o contraste.

O avatar tem fundo escuro e liso, então um preenchimento a partir das bordas separa a figura
(sem modelo de IA). Rode quando trocar a foto de perfil, antes do make_plotter_svg.py:
    python scripts/prep_avatar.py

Gera avatar-prepped.png em tons de cinza, com o fundo transparente.
"""

import urllib.request

import cv2
import numpy as np
from PIL import Image, ImageFilter, ImageOps

from oficina import ROOT

USERNAME = "GSerejo"
URL = f"https://github.com/{USERNAME}.png?size=460"
OUTPUT = ROOT / "avatar-prepped.png"
TOLERANCE = 30  # diferença para a cor da borda ainda considerada fundo


def download() -> np.ndarray:
    request = urllib.request.Request(URL, headers={"User-Agent": "profile-readme-bot"})
    with urllib.request.urlopen(request, timeout=30) as response:
        data = np.frombuffer(response.read(), np.uint8)
    return cv2.imdecode(data, cv2.IMREAD_COLOR)


def subject_mask(bgr: np.ndarray) -> np.ndarray:
    """Tudo que não é alcançável a partir das bordas com cor parecida é a figura."""
    h, w = bgr.shape[:2]
    blurred = cv2.GaussianBlur(bgr, (5, 5), 0)
    flood = np.zeros((h + 2, w + 2), np.uint8)
    diff = (TOLERANCE,) * 3
    background = np.median(blurred[0], axis=0)  # a borda de cima é sempre fundo
    border = [(x, y) for x in range(0, w, 8) for y in (0, h - 1)] + [(x, y) for y in range(0, h, 8) for x in (0, w - 1)]
    for x, y in border:
        # A camisa encosta na borda de baixo: só vira semente o que tem cor de fundo
        if not flood[y + 1, x + 1] and np.abs(blurred[y, x] - background).max() <= TOLERANCE:
            cv2.floodFill(blurred, flood, (x, y), 0, diff, diff, cv2.FLOODFILL_MASK_ONLY | cv2.FLOODFILL_FIXED_RANGE | (255 << 8))
    mask = np.where(flood[1:-1, 1:-1] > 0, 0, 255).astype(np.uint8)
    # Fica só com a maior região (a figura) e fecha furinhos
    count, labels, stats, _ = cv2.connectedComponentsWithStats(mask)
    if count > 1:
        biggest = 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))
        mask = np.where(labels == biggest, 255, 0).astype(np.uint8)
    return cv2.morphologyEx(mask, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8))


def main() -> None:
    bgr = download()
    mask = subject_mask(bgr)
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    # CLAHE dá luz e sombra local, para olhos, sorriso e barba sobreviverem às hachuras
    gray = cv2.createCLAHE(clipLimit=2.5, tileGridSize=(8, 8)).apply(gray)
    image = ImageOps.autocontrast(Image.fromarray(gray), cutoff=1, mask=Image.fromarray(mask))
    image = image.filter(ImageFilter.UnsharpMask(radius=2, percent=60, threshold=3))
    prepped = Image.merge("LA", (image, Image.fromarray(mask)))
    prepped.save(OUTPUT)
    print(f"{OUTPUT.name}: {prepped.size[0]}x{prepped.size[1]}, figura em {np.count_nonzero(mask) / mask.size:.0%} da imagem")


if __name__ == "__main__":
    main()
