"""Render Home Assistant brand PNGs from the supplied, SVG-wrapped artwork."""

from pathlib import Path
import io

import cairosvg
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "assets" / "ipmi-core-icon.svg"
DESTINATION = ROOT / "custom_components" / "ipmi_core" / "brand"

def main() -> None:
    DESTINATION.mkdir(parents=True, exist_ok=True)
    for size, name in ((256, "icon.png"), (512, "icon@2x.png")):
        png = cairosvg.svg2png(
            url=str(SOURCE), output_width=size, output_height=size
        )
        # Indexed PNG keeps the integration assets small without changing the
        # intended palette. Alpha transparency is preserved by Pillow.
        img = Image.open(io.BytesIO(png)).convert("RGBA")
        img.quantize(colors=128, method=Image.Quantize.FASTOCTREE).save(
            DESTINATION / name, optimize=True
        )
        checked = Image.open(DESTINATION / name)
        if checked.size != (size, size):
            raise ValueError("Unexpected PNG dimensions")

if __name__ == "__main__":
    main()
