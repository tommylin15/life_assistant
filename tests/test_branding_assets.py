import unittest

from scripts import prepare_branding_assets


class BrandingAssetQualityTests(unittest.TestCase):
    def test_canonical_icon_is_high_resolution_square(self):
        image = prepare_branding_assets._load_source()
        self.assertEqual(image.width, image.height)
        self.assertGreaterEqual(
            image.width,
            1024,
            f"canonical branding source is only {image.width}x{image.height}",
        )


if __name__ == "__main__":
    unittest.main()
