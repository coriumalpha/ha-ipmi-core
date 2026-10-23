# IPMI Core branding assets

The repository has two different branding responsibilities:

1. **Master artwork** (`assets/ipmi-core-logo-master.png`): the publisher's original, full-quality PNG, retained unchanged and referenced in the GitHub README. Do not convert it to JPEG, flatten transparent pixels, reduce its palette, or resave it as a low-resolution source.
2. **Home Assistant integration icons** (`custom_components/ipmi_core/brand/icon.png` and `icon@2x.png`): 256×256 and 512×512 lossless PNG derivatives. These can be reduced to fit Home Assistant's integration UI; they never replace the master artwork.

After adding or replacing the master PNG, run:

```bash
python -m pip install "Pillow==11.3.0" "CairoSVG==2.8.2"
python scripts/render_brand.py
python -m unittest discover -s tests -v
```

Commit both derived PNGs alongside the master. The branding GitHub Action verifies that the committed icons can be regenerated identically with the pinned dependencies.

The older `assets/ipmi-core-icon.svg` wraps an embedded compressed JPEG and is retained only for backward compatibility until the master PNG is committed. It is **not** a suitable high-fidelity project logo source.

The HACS repository information page is provided by `info.md`. The official catalog and the Home Assistant device panel may have additional requirements for logos; do not infer that the GitHub README banner and Home Assistant icon are interchangeable.
