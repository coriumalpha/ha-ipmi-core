"""Generate Home Assistant icon sizes without altering the master logo.

- When assets/ipmi-core-logo-master.png exists, render from that exact PNG using
  high-quality LANCZOS resampling and lossless, full-colour PNG output.
- Until the replacement master is supplied, preserve the legacy SVG renderer
  so existing committed assets remain reproducible.

The master logo is for the README and project presentation. The brand/ files are
separate, derived, square assets only for Home Assistant's integration tile.
"""

from pathlib import Path
import io

import cairosvg
from PIL import Image, ImageOps

ROOT = Path(__file__).resolve().parents[1]
MASTER = ROOT / "assets" / "ipmi-core-logo-master.png"
LEGACY = ROOT / "assets" / "ipmi-core-icon.svg"
DESTINATION = ROOT / "custom_components" / "ipmi_core" / "brand"


def main() -> None:
    DESTINATION.mkdir(parents=True, exist_ok=True)

    if MASTER.is_file():
        with Image.open(MASTER) as original:
            source = ImageOps.exif_transpose(original).convert("RGBA")
        if min(source.size) < 512:
            raise ValueError("Master logo must be at least 512px on each side")

        for size, filename in ((256, "icon.png"), (512, "icon@2x.png")):
            # Keep every original pixel/colour in the master. Only derivatives
            # are resized, with transparent padding if the source is non-square.
            icon = ImageOps.pad(
                source,
                (size, size),
                method=Image.Resampling.LANCZOS,
                color=(0, 0, 0, 0),
            )
            icon.save(DESTINATION / filename, format="PNG", optimize=True)
    else:
        # Backward-compatible render path for the pre-existing branding. Remove
        # after the publisher's final master PNG and derivatives are committed.
        for size, filename in ((256, "icon.png"), (512, "icon@2x.png")):
            rendered = cairosvg.svg2png(
                url=str(LEGACY), output_width=size, output_height=size
            )
            image = Image.open(io.BytesIO(rendered)).convert("RGBA")
            image.quantize(
                colors=128,
                method=Image.Quantize.FASTOCTREE
            ).save(DESTINATION / filename, optimize=True)

    for size, filename in ((256, "icon.png"), (512, "icon@2x.png")):
        with Image.open(DESTINATION / filename) as result:
            if result.size != (size, size):
                raise ValueError(f"Unexpected PNG dimensions: {filename}")


if __name__ == "__main__":
    main()
