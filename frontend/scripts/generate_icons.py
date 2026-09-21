"""Generate the PWA icons into public/.

    python3 scripts/generate_icons.py

A droplet on the brand pink, drawn with no image library so the icons can be
regenerated anywhere. The mark stays inside the middle 80% so it survives
maskable cropping.
"""

import struct
import zlib
from pathlib import Path

BACKGROUND = (181, 71, 109)
MARK = (255, 255, 255)
PUBLIC = Path(__file__).resolve().parent.parent / "public"


def droplet_alpha(x: float, y: float, size: float) -> float:
    """Coverage of the droplet at a point, 0..1, softened at the edge."""
    cx = size / 2
    bulb_cy = size * 0.60
    bulb_r = size * 0.22
    apex_y = size * 0.24

    # Circular bulb.
    dist = ((x - cx) ** 2 + (y - bulb_cy) ** 2) ** 0.5
    inside = bulb_r - dist

    # Cone from the apex down to the bulb's widest point.
    if apex_y <= y <= bulb_cy:
        progress = (y - apex_y) / (bulb_cy - apex_y)
        half_width = bulb_r * progress
        inside = max(inside, half_width - abs(x - cx))

    return max(0.0, min(1.0, inside + 0.5))  # 1px feather


def render(size: int) -> bytes:
    rows = bytearray()
    for py in range(size):
        rows.append(0)  # PNG filter type: none
        for px in range(size):
            alpha = droplet_alpha(px + 0.5, py + 0.5, size)
            for channel in range(3):
                value = BACKGROUND[channel] * (1 - alpha) + MARK[channel] * alpha
                rows.append(int(round(value)))
    return bytes(rows)


def chunk(tag: bytes, payload: bytes) -> bytes:
    return (
        struct.pack(">I", len(payload))
        + tag
        + payload
        + struct.pack(">I", zlib.crc32(tag + payload) & 0xFFFFFFFF)
    )


def write_png(path: Path, size: int) -> None:
    header = struct.pack(">IIBBBBB", size, size, 8, 2, 0, 0, 0)  # 8-bit truecolour
    png = (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", header)
        + chunk(b"IDAT", zlib.compress(render(size), 9))
        + chunk(b"IEND", b"")
    )
    path.write_bytes(png)
    print(f"wrote {path.name} ({size}x{size}, {len(png)} bytes)")


if __name__ == "__main__":
    PUBLIC.mkdir(exist_ok=True)
    for dimension in (192, 512):
        write_png(PUBLIC / f"icon-{dimension}.png", dimension)
