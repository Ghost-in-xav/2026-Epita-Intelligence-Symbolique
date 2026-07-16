"""Genere les sprites de tuiles (PNG) utilises par l'UI Streamlit.

Chaque tuile est dessinee en supersampling (4x) puis redimensionnee avec un
filtre Lanczos pour obtenir des icones lisses a taille d'affichage. Ce script
est deterministe (pas d'alea) : relancez-le si vous voulez retoucher le style
visuel, les PNG generes sont ensuite commit's comme assets du projet.

Usage : python ui/assets/generate_assets.py
"""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw

OUT_DIR = Path(__file__).parent / "tiles"
SUPERSAMPLE = 128
FINAL = 48

# Palette "donjon de pierre"
STONE_DARK = (43, 42, 36)
STONE_DARK_2 = (58, 56, 48)
MORTAR = (26, 25, 21)
STONE_LIGHT = (196, 184, 148)
STONE_LIGHT_2 = (176, 163, 128)
GROUT = (150, 138, 106)
GREEN = (46, 204, 113)
GREEN_DARK = (30, 140, 78)
RED = (231, 76, 60)
RED_DARK = (170, 50, 40)
GOLD = (241, 196, 15)
GOLD_DARK = (176, 137, 8)
PURPLE = (142, 68, 173)
PURPLE_DARK = (95, 45, 116)
WOOD = (110, 72, 41)
WOOD_DARK = (76, 48, 25)


def _canvas() -> tuple[Image.Image, ImageDraw.ImageDraw]:
    img = Image.new("RGBA", (SUPERSAMPLE, SUPERSAMPLE), (0, 0, 0, 0))
    return img, ImageDraw.Draw(img)


def _save(img: Image.Image, name: str) -> None:
    small = img.resize((FINAL, FINAL), Image.LANCZOS)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    small.save(OUT_DIR / f"{name}.png")


def _floor_base(draw: ImageDraw.ImageDraw) -> None:
    s = SUPERSAMPLE
    draw.rectangle([0, 0, s, s], fill=STONE_LIGHT)
    step = s // 4
    for i in range(1, 4):
        draw.line([(i * step, 0), (i * step, s)], fill=GROUT, width=3)
        draw.line([(0, i * step), (s, i * step)], fill=GROUT, width=3)
    for cx, cy, r in [(s * 0.22, s * 0.28, 6), (s * 0.7, s * 0.6, 5), (s * 0.55, s * 0.15, 4)]:
        draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=STONE_LIGHT_2)


def make_wall() -> None:
    s = SUPERSAMPLE
    img, draw = _canvas()
    draw.rectangle([0, 0, s, s], fill=STONE_DARK)
    brick_h = s // 5
    for row in range(5):
        y0 = row * brick_h
        offset = (brick_h * 1.5) if row % 2 else 0
        x = -brick_h
        while x < s:
            draw.rectangle([x + 3, y0 + 3, x + brick_h * 2 - 3, y0 + brick_h - 3], fill=STONE_DARK_2, outline=MORTAR, width=3)
            x += brick_h * 2
        draw.line([(0, y0), (s, y0)], fill=MORTAR, width=4)
    _save(img, "wall")


def make_floor() -> None:
    img, draw = _canvas()
    _floor_base(draw)
    _save(img, "floor")


def make_start() -> None:
    s = SUPERSAMPLE
    img, draw = _canvas()
    _floor_base(draw)
    draw.ellipse([s * 0.12, s * 0.12, s * 0.88, s * 0.88], fill=GREEN, outline=GREEN_DARK, width=5)
    cx, cy, r = s * 0.5, s * 0.5, s * 0.22
    draw.polygon([(cx - r, cy - r), (cx - r, cy + r), (cx + r, cy)], fill=(255, 255, 255))
    _save(img, "start")


def make_end() -> None:
    s = SUPERSAMPLE
    img, draw = _canvas()
    _floor_base(draw)
    draw.ellipse([s * 0.12, s * 0.12, s * 0.88, s * 0.88], fill=RED, outline=RED_DARK, width=5)
    cx, cy = s * 0.5, s * 0.5
    r = s * 0.16
    draw.rectangle([cx - r, cy - r, cx + r, cy + r], fill=(255, 255, 255))
    _save(img, "end")


def make_key() -> None:
    s = SUPERSAMPLE
    img, draw = _canvas()
    _floor_base(draw)
    cx, cy = s * 0.36, s * 0.38
    r = s * 0.16
    draw.ellipse([cx - r, cy - r, cx + r, cy + r], outline=GOLD_DARK, width=8)
    draw.line([(cx + r * 0.7, cy + r * 0.7), (s * 0.78, s * 0.8)], fill=GOLD, width=10)
    draw.line([(s * 0.7, s * 0.72), (s * 0.78, s * 0.64)], fill=GOLD, width=8)
    draw.line([(s * 0.62, s * 0.64), (s * 0.7, s * 0.56)], fill=GOLD, width=8)
    draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(0, 0, 0, 0), outline=GOLD, width=5)
    _save(img, "key")


def make_door() -> None:
    s = SUPERSAMPLE
    img, draw = _canvas()
    draw.rectangle([0, 0, s, s], fill=STONE_DARK)
    m = s * 0.12
    draw.rectangle([m, m * 0.6, s - m, s - m * 0.4], fill=WOOD, outline=WOOD_DARK, width=6)
    for fx in (0.33, 0.67):
        draw.rectangle([s * (fx - 0.12), s * 0.22, s * (fx + 0.12), s * 0.85], outline=WOOD_DARK, width=4)
    knob_x, knob_y, r = s * 0.72, s * 0.55, s * 0.05
    draw.ellipse([knob_x - r, knob_y - r, knob_x + r, knob_y + r], fill=GOLD, outline=GOLD_DARK, width=3)
    draw.rectangle([m, m * 0.6, s - m, s - m * 0.4], outline=PURPLE_DARK, width=5)
    _save(img, "door")


def make_enemy() -> None:
    s = SUPERSAMPLE
    img, draw = _canvas()
    _floor_base(draw)
    cx, cy = s * 0.5, s * 0.48
    r = s * 0.28
    draw.ellipse([cx - r, cy - r * 0.9, cx + r, cy + r], fill=RED_DARK, outline=(40, 10, 10), width=5)
    for dx in (-0.32, 0.32):
        draw.polygon(
            [(cx + dx * s - s * 0.05, cy - r), (cx + dx * s + s * 0.05, cy - r), (cx + dx * s, cy - r * 1.5)],
            fill=RED_DARK,
        )
    eye_r = s * 0.06
    for dx in (-0.13, 0.13):
        draw.ellipse([cx + dx * s - eye_r, cy - eye_r, cx + dx * s + eye_r, cy + eye_r], fill=(255, 255, 255))
        draw.ellipse([cx + dx * s - eye_r * 0.4, cy - eye_r * 0.4, cx + dx * s + eye_r * 0.4, cy + eye_r * 0.4], fill=(20, 20, 20))
    _save(img, "enemy")


def make_treasure() -> None:
    s = SUPERSAMPLE
    img, draw = _canvas()
    _floor_base(draw)
    x0, x1 = s * 0.2, s * 0.8
    y0, y1, y2 = s * 0.42, s * 0.55, s * 0.8
    draw.rectangle([x0, y1, x1, y2], fill=WOOD, outline=WOOD_DARK, width=5)
    draw.pieslice([x0, y0 - (y1 - y0), x1, y1 + (y1 - y0)], 180, 360, fill=GOLD_DARK, outline=WOOD_DARK, width=5)
    draw.rectangle([x0, y1 - s * 0.03, x1, y1 + s * 0.03], fill=GOLD)
    lock_cx, lock_cy, lr = s * 0.5, y1, s * 0.06
    draw.rectangle([lock_cx - lr, lock_cy - lr, lock_cx + lr, lock_cy + lr * 1.6], fill=GOLD, outline=GOLD_DARK, width=3)
    _save(img, "treasure")


def make_player() -> None:
    """Sprite du joueur : fond transparent (pas de `_floor_base`) pour se superposer
    a n'importe quelle tuile de la grille de jeu."""
    s = SUPERSAMPLE
    img, draw = _canvas()
    cx, cy = s * 0.5, s * 0.58
    r = s * 0.24
    draw.ellipse([cx - r, cy - r * 0.85, cx + r, cy + r], fill=(41, 128, 185), outline=(21, 67, 96), width=6)
    head_cy = cy - r * 1.05
    head_r = s * 0.16
    draw.ellipse(
        [cx - head_r, head_cy - head_r, cx + head_r, head_cy + head_r],
        fill=(241, 196, 158),
        outline=(120, 90, 60),
        width=5,
    )
    draw.line([(cx + r * 0.9, cy - r * 0.3), (cx + r * 1.6, cy - r * 1.1)], fill=(224, 224, 224), width=8)
    _save(img, "player")


def main() -> None:
    make_wall()
    make_floor()
    make_start()
    make_end()
    make_key()
    make_door()
    make_enemy()
    make_treasure()
    make_player()
    print(f"9 sprites ecrits dans {OUT_DIR}")


if __name__ == "__main__":
    main()
