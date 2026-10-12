"""Home-card preference options must agree with the Flutter home and remain user-owned."""
import unittest
from pydantic import ValidationError
from app.api.ui_policies import DEFAULT_HOME, HOME_KEYS, UIPreferencesWrite

def _body(cards):
    return UIPreferencesWrite(
        expected_revision=0, nav_mode="auto",
        pinned=["tasks", "calendar", "projects"],
        more_order=["notes", "habits"],
        home_cards=cards,
    )

class HomeCardPreferenceTests(unittest.TestCase):
    def test_every_home_card_including_opportunities_and_explore_can_be_saved(self):
        all_cards = [
            "tasks", "calendar", "attention", "habits", "events", "opportunities",
            "explore", "projects", "notes", "shopping", "drive",
        ]
        assert set(all_cards) == HOME_KEYS
        assert set(DEFAULT_HOME).issubset(HOME_KEYS)
        assert _body(all_cards).home_cards == all_cards
        assert _body(["opportunities", "notes", "explore"]).home_cards == [
            "opportunities", "notes", "explore",
        ]
    
    def test_home_card_preferences_reject_duplicates_and_unknown_features(self):
        with self.assertRaises(ValidationError):
            _body(["tasks", "tasks"])
        with self.assertRaises(ValidationError):
            _body(["integrations", "opportunities"])
    