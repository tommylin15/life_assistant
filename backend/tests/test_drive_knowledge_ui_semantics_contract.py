import unittest
from pathlib import Path


class DriveKnowledgeUISemanticsContractTests(unittest.TestCase):
    def _source(self) -> str:
        repo_root = Path(__file__).parents[2]
        return (
            repo_root / ".github/scripts/verify_drive_knowledge_production.mjs"
        ).read_text(encoding="utf-8")

    def test_wait_for_text_checks_accessible_label_and_text_candidates(self):
        source = self._source()

        start = source.index("async function waitForText")
        end = source.index("function record", start)
        wait_for_text = source[start:end]

        self.assertIn("page.getByLabel(pattern)", wait_for_text)
        self.assertIn("page.getByText(pattern)", wait_for_text)

    def test_manual_relation_dialog_expands_note_selector_before_waiting_for_note(self):
        source = self._source()
        start = source.index("await (await named(page, '關聯既有筆記')).click();")
        end = source.index("record('manual_relation_dialog_contract');", start)
        manual_relation_flow = source[start:end]

        open_selector = "await (await named(page, '筆記')).click();"
        wait_for_option = "await waitForText(page, note.title);"
        self.assertIn(open_selector, manual_relation_flow)
        self.assertIn(wait_for_option, manual_relation_flow)
        self.assertLess(
            manual_relation_flow.index(open_selector),
            manual_relation_flow.index(wait_for_option),
        )


if __name__ == "__main__":
    unittest.main()
