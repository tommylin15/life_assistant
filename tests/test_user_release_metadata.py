"""Release metadata policy must be independently testable without GCP."""
import unittest

from scripts.check_user_release_metadata import (
    is_user_web_path,
    notes_by_id,
    parsed_version,
    validate,
)

BASE = "version: 0.3.0+3\n"
NEW = "version: 0.4.0+4\n"
OLD_NEWS = """const lifeReleaseNotes = <LifeReleaseNote>[
  LifeReleaseNote(
    id: 'web-0.3.0-old',
    version: '0.3.0',
    title: '先前公告',
  ),
];"""
NEW_NEWS = OLD_NEWS.replace(
    "];",
    """  LifeReleaseNote(
    id: 'web-0.4.0-gmail',
    version: '0.4.0',
    featureKey: 'gmail_radar',
    changes: <String>['Gmail UI 更簡潔'],
  ),
  LifeReleaseNote(
    id: 'web-0.4.0-inbox',
    version: '0.4.0',
    featureKey: 'life_inbox',
    changes: <String>['多件快速新增'],
  ),
];""",
)


class UserReleaseMetadataTests(unittest.TestCase):
    def test_version_and_new_notes_for_two_real_surfaces_pass(self):
        self.assertEqual(validate(
            BASE, NEW, OLD_NEWS, NEW_NEWS,
            ["lib/web/gmail_radar_page.dart", "lib/web/life_capture_page.dart"],
        ), [])

    def test_same_version_and_build_cannot_publish_user_ui_changes(self):
        errors = validate(BASE, BASE, OLD_NEWS, NEW_NEWS,
                          ["lib/web/life_capture_page.dart"])
        self.assertTrue(any("MAJOR.MINOR.PATCH" in error for error in errors))

    def test_unpublished_note_not_usable_for_other_version(self):
        errors = validate(BASE, NEW, OLD_NEWS, OLD_NEWS,
                          ["lib/web/gmail_radar_page.dart"])
        self.assertTrue(any("new latest-news" in error for error in errors))

    def test_feature_specific_posts_cannot_be_replaced_by_generic_note(self):
        generic = NEW_NEWS.replace("featureKey: 'life_inbox',", "")
        errors = validate(BASE, NEW, OLD_NEWS, generic,
                          ["lib/web/life_capture_page.dart"])
        self.assertTrue(any("life_inbox" in error for error in errors))

    def test_web_source_requires_news_but_document_and_backend_only_do_not(self):
        self.assertTrue(is_user_web_path("lib/application/quick_input.dart"))
        self.assertFalse(is_user_web_path("lib/web/release_info.dart"))
        self.assertFalse(is_user_web_path("backend/app/api/release_notes.py"))
        self.assertEqual(validate(
            BASE, BASE, OLD_NEWS, OLD_NEWS,
            ["doc/PROJECT_RULES.md", "backend/app/services/worker.py"],
        ), [])
        errors = validate(
            BASE, NEW, OLD_NEWS, OLD_NEWS, ["lib/web/calendar_page.dart"])
        self.assertTrue(any("latest-news" in error for error in errors))

    def test_invalid_version_and_duplicate_ids_fail_closed(self):
        with self.assertRaises(ValueError):
            parsed_version("version: invalid")
        with self.assertRaises(ValueError):
            notes_by_id(NEW_NEWS + NEW_NEWS)

    def test_only_patch_without_new_build_is_rejected(self):
        errors = validate(BASE, "version: 0.3.1+3", OLD_NEWS, NEW_NEWS,
                          ["lib/web/life_capture_page.dart"])
        self.assertTrue(any("MAJOR.MINOR.PATCH" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
