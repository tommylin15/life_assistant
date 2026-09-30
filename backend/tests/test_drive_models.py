import importlib.util
import unittest


class DriveModelContractTests(unittest.TestCase):
    def test_drive_model_module_exists(self):
        self.assertIsNotNone(importlib.util.find_spec("app.models.drive"))

    def test_drive_schema_module_exists(self):
        self.assertIsNotNone(importlib.util.find_spec("app.models.drive_schemas"))


if __name__ == "__main__":
    unittest.main()
