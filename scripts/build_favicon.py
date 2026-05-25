"""Regenerate public/favicon.ico and public/apple-touch-icon.png.

The design mirrors public/favicon.svg: a rounded vermilion square with a
cream-on-vermilion geometric "A". Each ICO entry is rendered natively at its
target resolution (then 4x-supersampled and Lanczos-downscaled for AA),
instead of being downscaled from a single master, so the small entries stay
legible at 16x16 / 24x24 in the browser tab.

Run:
    python scripts/build_favicon.py
"""

from __future__ import annotations

import io
import struct
from pathlib import Path

from PIL import Image, ImageDraw

VERMILION = "#d94e2a"
ON_VERMILION = "#faf6ee"

# Design in a 64-unit coordinate system (matches public/favicon.svg).
CORNER_RADIUS_UNITS = 10.0
OUTER_A = [
    (9.0, 53.0),
    (26.0, 11.0),
    (38.0, 11.0),
    (55.0, 53.0),
    (44.0, 53.0),
    (40.5, 44.0),
    (23.5, 44.0),
    (20.0, 53.0),
]
COUNTER = [(26.5, 36.0), (37.5, 36.0), (32.0, 22.0)]


def _scale(points: list[tuple[float, float]], factor: float) -> list[tuple[float, float]]:
    return [(x * factor, y * factor) for x, y in points]


def render(size: int) -> Image.Image:
    """Render the favicon at the given pixel size using 4x supersampling."""
    ss = 4
    big = size * ss
    factor = big / 64.0

    img = Image.new("RGBA", (big, big), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    radius = max(1.0, CORNER_RADIUS_UNITS * factor)
    draw.rounded_rectangle(
        (0, 0, big - 1, big - 1),
        radius=radius,
        fill=VERMILION,
    )
    draw.polygon(_scale(OUTER_A, factor), fill=ON_VERMILION)
    # Re-fill the counter (triangular hole above the crossbar) with vermilion
    # to produce the inner negative space. The 16x entry would otherwise have
    # the crossbar dissolve into the leg fills.
    draw.polygon(_scale(COUNTER, factor), fill=VERMILION)

    return img.resize((size, size), Image.LANCZOS)


def _write_ico(path: Path, frames: list[Image.Image]) -> None:
    """Write a multi-resolution ICO with each frame PNG-encoded.

    Pillow's ICO writer only persists a single source image; using
    ``append_images`` silently drops the extra frames. The ICO format itself
    permits per-entry PNG payloads, so we assemble the file directly.
    """
    payloads: list[bytes] = []
    for frame in frames:
        buf = io.BytesIO()
        frame.save(buf, format="PNG", optimize=True)
        payloads.append(buf.getvalue())

    header = struct.pack("<HHH", 0, 1, len(frames))
    dir_size = 6 + 16 * len(frames)
    offsets: list[int] = []
    offset = dir_size
    for payload in payloads:
        offsets.append(offset)
        offset += len(payload)

    directory = bytearray()
    for frame, payload, off in zip(frames, payloads, offsets):
        w, h = frame.size
        directory += struct.pack(
            "<BBBBHHII",
            0 if w >= 256 else w,
            0 if h >= 256 else h,
            0,            # palette size (0 for true-color)
            0,            # reserved
            1,            # color planes
            32,           # bits per pixel
            len(payload),
            off,
        )

    with open(path, "wb") as fh:
        fh.write(header)
        fh.write(directory)
        for payload in payloads:
            fh.write(payload)


def main() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    public = repo_root / "public"
    public.mkdir(exist_ok=True)

    ico_sizes = [16, 24, 32, 48, 64, 128, 256]
    frames = [render(s) for s in ico_sizes]

    ico_path = public / "favicon.ico"
    _write_ico(ico_path, frames)
    print(f"wrote {ico_path} ({ico_path.stat().st_size} bytes)")

    apple = render(180)
    apple_path = public / "apple-touch-icon.png"
    apple.save(apple_path, format="PNG", optimize=True)
    print(f"wrote {apple_path} ({apple_path.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
