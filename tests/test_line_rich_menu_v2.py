"""LINE v2 eight-grid artwork, geometry, action and allowed-host contracts."""
from importlib.util import module_from_spec, spec_from_file_location, find_spec
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
MOD = ROOT / "scripts" / "line_rich_menu_v2.py"
SPEC = spec_from_file_location("life_v2_eight_grid", MOD)
MENU = module_from_spec(SPEC)
SPEC.loader.exec_module(MENU)
HOST = "https://gen-lang-client-0593591102.web.app/today"


class EightGridMenuTests(unittest.TestCase):
    def test_exact_eight_cells_cover_canvas_without_overlap(self):
        menu = MENU.menu(HOST)
        self.assertEqual(menu["size"], {"width": 2500, "height": 1686})
        self.assertTrue(menu["selected"])
        self.assertEqual(len(menu["areas"]), 8)
        seen = set()
        for i, area in enumerate(menu["areas"]):
            expected = {"x": 625 * (i % 4), "y": 843 * (i // 4),
                        "width": 625, "height": 843}
            self.assertEqual(area["bounds"], expected)
            cells = {(xx, yy) for xx in range(expected["x"], expected["x"] + 625, 625)
                     for yy in range(expected["y"], expected["y"] + 843, 843)}
            self.assertFalse(seen.intersection(cells))
            seen.update(cells)
        self.assertEqual(len(seen), 8)
        self.assertEqual(sum(a["bounds"]["width"] * a["bounds"]["height"]
                             for a in menu["areas"]), 2500 * 1686)

    def test_seven_postbacks_and_life_uri_match_current_backend(self):
        actions = [a["action"] for a in MENU.menu(HOST)["areas"]]
        self.assertEqual([a["label"] for a in actions], list(MENU.LABELS))
        self.assertEqual([a["type"] for a in actions], ["postback"] * 7 + ["uri"])
        self.assertEqual([a["data"] for a in actions[:7]],
                         ["v=2&cmd=" + x for x in MENU.COMMANDS[:7]])
        self.assertEqual(actions[-1]["uri"], HOST)
        self.assertEqual(actions[6]["data"], "v=2&cmd=events.latest")
        backend = (ROOT / "backend" / "app" / "services" / "line_v2.py").read_text()
        for command in MENU.COMMANDS[:7]:
            self.assertIn('"' + command + '"', backend)

    def test_life_uri_allowlist(self):
        self.assertEqual(MENU.life_url("https://life-assistant-v3-stage-tl15.web.app/"),
                         "https://life-assistant-v3-stage-tl15.web.app/today")
        for url in ("http://gen-lang-client-0593591102.web.app/today",
                    "https://evil.test/today",
                    "https://gen-lang-client-0593591102.web.app/today?redirect=https://evil.test",
                    "https://gen-lang-client-0593591102.web.app/other"):
            with self.assertRaises(ValueError):
                MENU.life_url(url)

    @unittest.skipUnless(find_spec("PIL"), "Pillow optional for art tool")
    def test_art_image_dimensions_and_file_size(self):
        from PIL import Image
        with tempfile.TemporaryDirectory() as t:
            f = Path(t) / "richmenu.jpg"
            Image.new("RGB", (2500, 1686), "#d3e8dc").save(f, "JPEG", quality=75)
            self.assertEqual(MENU.verify_image(f), "image/jpeg")
            Image.new("RGB", (800, 250), "white").save(f, "JPEG")
            with self.assertRaisesRegex(ValueError, "2500x1686"):
                MENU.verify_image(f)


if __name__ == "__main__":
    unittest.main()
