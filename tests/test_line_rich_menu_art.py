"""LINE U16: deterministic rich-menu artwork and immutable six-cell mapping."""
from importlib.util import module_from_spec, spec_from_file_location, find_spec
from pathlib import Path
import struct
import tempfile
import unittest
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "scripts" / "build_line_rich_menu.py"
SPEC = spec_from_file_location("life_line_menu_art", BUILD)
ART = module_from_spec(SPEC)
SPEC.loader.exec_module(ART)


class SixGridArtworkTests(unittest.TestCase):
    def test_exact_size_and_six_text_labels(self):
        root = ET.fromstring(ART.svg_markup())
        self.assertEqual((root.attrib["width"], root.attrib["height"]), ("2500", "1686"))
        self.assertEqual(root.attrib["viewBox"], "0 0 2500 1686")
        texts = [node.text for node in root.findall("{http://www.w3.org/2000/svg}text")]
        labels = [area["action"]["label"] for area in ART.menu("123-test")["areas"]]
        self.assertEqual(texts[::3], labels)
        self.assertEqual(len(texts), 18)
        self.assertEqual(len(ART.ICONS), 6)

    def test_committed_svg_matches_generator(self):
        expected = (ROOT / "assets" / "line" / "rich_menu_v1.svg").read_text(encoding="utf-8")
        self.assertEqual(expected, ART.svg_markup())

    def test_image_cells_match_action_grid(self):
        root = ET.fromstring(ART.svg_markup())
        rectangles = root.findall("{http://www.w3.org/2000/svg}rect")[1:]
        self.assertEqual(len(rectangles), 6)
        for rect, area in zip(rectangles, ART.menu("123-test")["areas"]):
            for key in ("x", "y", "width", "height"):
                self.assertEqual(int(rect.attrib[key]), area["bounds"][key])
        self.assertEqual(sum(int(r.attrib["width"]) * int(r.attrib["height"]) for r in rectangles), 2500 * 1686)

    def test_rejects_forged_or_wrong_size_png(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "menu.png"
            path.write_bytes(b"not-a-png")
            with self.assertRaisesRegex(ValueError, "not a PNG"):
                ART.verify_png(path)
            path.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 8 + struct.pack(">II", 800, 250))
            with self.assertRaisesRegex(ValueError, "Unexpected PNG size"):
                ART.verify_png(path)

    @unittest.skipUnless(find_spec("cairosvg"), "CairoSVG optional; local design build separately verified")
    def test_png_render_within_line_limit(self):
        import cairosvg
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "menu.png"
            cairosvg.svg2png(bytestring=ART.svg_markup().encode(), write_to=str(path))
            self.assertGreater(ART.verify_png(path), 0)
            self.assertLess(path.stat().st_size, 1_000_000)


if __name__ == "__main__":
    unittest.main()
