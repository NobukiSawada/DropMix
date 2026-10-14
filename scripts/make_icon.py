"""Generate assets/icon.ico (the green "D" logo) with Pillow.

    python scripts/make_icon.py
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw

GREEN = (22, 163, 74, 255)
WHITE = (255, 255, 255, 255)
SIZE = 256


def draw_logo(size: int = SIZE) -> Image.Image:
    # favicon.svg (viewBox 64x64) と同じ形を描く
    s = size / 64
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((0, 0, size - 1, size - 1), radius=14 * s, fill=GREEN)
    # 外側の D: 左上(20,14) 高さ36、右側は半径18の半円
    d.rectangle((20 * s, 14 * s, 34 * s, 50 * s), fill=WHITE)
    d.pieslice((16 * s, 14 * s, 52 * s, 50 * s), start=-90, end=90, fill=WHITE)
    # 内側のくり抜き: 左上(27,22) 高さ20、半径10
    d.rectangle((27 * s, 22 * s, 34 * s, 42 * s), fill=GREEN)
    d.pieslice((24 * s, 22 * s, 44 * s, 42 * s), start=-90, end=90, fill=GREEN)
    return img


def main() -> None:
    out = Path(__file__).resolve().parent.parent / "assets" / "icon.ico"
    out.parent.mkdir(parents=True, exist_ok=True)
    draw_logo().save(out, sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
