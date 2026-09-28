"""Prepara a foto para virar ASCII: remove o fundo, recorta o busto e realça o contraste.

Roda só quando a foto muda (não faz parte da atualização diária):
    python scripts/prep_photo.py source-photo.jpg

Gera source-prepped.png em tons de cinza, com o fundo transparente.
"""

import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageFilter, ImageOps
from rembg import new_session, remove

ROOT = Path(__file__).resolve().parent.parent
OUTPUT = ROOT / "source-prepped.png"
ALPHA_CUTOFF = 128
MODEL = "u2net_human_seg"  # treinado para recortar pessoas


def head_crop(mask: Image.Image) -> tuple[int, int, int, int]:
    """Recorte quadrado centrado na cabeça, pegando só o começo dos ombros."""
    left, top, right, bottom = mask.getbbox()
    head_band = mask.crop((left, top, right, top + (bottom - top) // 4))
    # Centro horizontal da cabeça = média das colunas ocupadas no topo da silhueta
    columns = [x for x in range(head_band.width) if head_band.crop((x, 0, x + 1, head_band.height)).getbbox()]
    center_x = left + (columns[0] + columns[-1]) // 2

    side = min(int((right - left) * 0.72), bottom - top)
    crop_left = max(0, min(center_x - side // 2, mask.width - side))
    return crop_left, top, crop_left + side, top + side


def main(source: str) -> None:
    photo = Image.open(source).convert("RGB")
    cutout = remove(photo, session=new_session(MODEL))  # RGBA com o fundo transparente

    subject_mask = cutout.getchannel("A").point(lambda a: 255 if a > ALPHA_CUTOFF else 0)
    crop = head_crop(subject_mask)
    cutout = cutout.crop(crop)
    subject_mask = subject_mask.crop(crop)

    gray = ImageOps.grayscale(cutout.convert("RGB"))
    # CLAHE (contraste local adaptativo): dá luz e sombra a um rosto com iluminação chapada,
    # para olhos, sorriso e barba sobreviverem à redução para a grade de caracteres
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
    gray = Image.fromarray(clahe.apply(np.asarray(gray)))
    # Contraste global calculado só sobre a pessoa, para o fundo removido não distorcer o histograma
    gray = ImageOps.autocontrast(gray, cutoff=1, mask=subject_mask)
    gray = gray.filter(ImageFilter.UnsharpMask(radius=3, percent=60, threshold=3))

    prepped = Image.merge("LA", (gray, subject_mask))
    prepped.save(OUTPUT)
    print(f"{OUTPUT.name}: {prepped.size[0]}x{prepped.size[1]}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("uso: python scripts/prep_photo.py <foto>")
    main(sys.argv[1])
