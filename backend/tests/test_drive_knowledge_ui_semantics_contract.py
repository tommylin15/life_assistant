import unittest
from pathlib import Path


class DriveKnowledgeUISemanticsContractTests(unittest.TestCase):
    def test_wait_for_text_checks_accessible_label_and_text_candidates(self):
        repo_root = Path(__file__).parents[2]
        source = (
            repo_root / ".github/scripts/verify_drive_knowledge_production.mjs"
        ).read_text(encoding="utf-8")

        start = source.index("async function waitForText")
        end = source.index("function record", start)
        wait_for_text = source[start:end]

        self.assertIn("page.getByLabel(pattern)", wait_for_text)
        self.assertIn("page.getByText(pattern)", wait_for_text)


if __name__ == "__main__":
    unittest.main()
