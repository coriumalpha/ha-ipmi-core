"""Test that HA's locally served custom-integration brand assets are present."""

from pathlib import Path
import struct
import unittest
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
BRAND = ROOT / "custom_components" / "ipmi_core" / "brand"
SOURCE = ROOT / "assets" / "ipmi-core-icon.svg"

class TestIntegrationBrand(unittest.TestCase):
    def test_local_brand_images_have_required_png_dimensions(self):
        for name, expected_size in (("icon.png", 256), ("icon@2x.png", 512)):
            with self.subTest(name=name):
                data = (BRAND / name).read_bytes()
                self.assertEqual(data[:8], b"\x89PNG\r\n\x1a\n")
                self.assertEqual(data[12:16], b"IHDR")
                dimensions = struct.unpack(">II", data[16:24])
                self.assertEqual(dimensions, (expected_size, expected_size))

    def test_branded_svg_source_is_present(self):
        document = ET.parse(SOURCE)
        self.assertEqual(document.getroot().attrib.get("viewBox"), "0 0 512 512")
        # The publisher-supplied artwork is embedded as a data URI in the SVG
        # wrapper, so rendering is self-contained and needs no network access.
        source = SOURCE.read_text(encoding="utf-8")
        self.assertIn("data:image/jpeg;base64,", source)

if __name__ == "__main__":
    unittest.main()
