from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import config
import main


class OnboardingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.original_data_dir = config.DATA_DIR
        config.DATA_DIR = Path(self.temp.name)
        config.ensure_config()

    def tearDown(self) -> None:
        config.DATA_DIR = self.original_data_dir
        self.temp.cleanup()

    def test_fresh_defaults_require_onboarding(self) -> None:
        status = main.onboarding_status()

        self.assertFalse(status["complete"])
        self.assertTrue(status["role_families"])
        self.assertNotIn("api_keys", status["defaults"])

    def test_configured_legacy_profile_is_inferred_complete(self) -> None:
        settings = config.load("settings")
        settings.pop("onboarding_complete", None)
        config.save("settings", settings)
        profile = config.load("profile")
        profile["identity"]["name"] = "Configured User"
        config.save("profile", profile)

        status = main.onboarding_status()

        self.assertTrue(status["complete"])
        self.assertTrue(status["legacy_inferred"])

    def test_completion_updates_profile_rules_and_settings(self) -> None:
        role = config.load("rules")["role_families"][0]["name"]
        result = main.complete_onboarding(main.OnboardingRequest(
            full_name="Ada Lovelace",
            display_name="Ada",
            location="California",
            work_authorization="OPT",
            needs_sponsorship=True,
            target_roles=[role],
            preferred_locations=["California", "Remote", "California"],
            max_years_experience=5,
            output_dir="",
            ai_enabled=False,
        ))

        profile = config.load("profile")
        rules = config.load("rules")
        settings = config.load("settings")
        self.assertEqual(result, {"complete": True})
        self.assertEqual(profile["identity"]["name"], "Ada Lovelace")
        self.assertTrue(profile["identity"]["needs_sponsorship"])
        self.assertEqual(settings["username"], "Ada")
        self.assertTrue(settings["onboarding_complete"])
        self.assertEqual(rules["preferred_locations"], ["california", "remote"])
        self.assertEqual(rules["max_years_experience"], 5)
        self.assertEqual(next(f for f in rules["role_families"] if f["name"] == role)["tier"], 1)

    def test_reset_preserves_values_and_reopens_wizard(self) -> None:
        settings = config.load("settings")
        settings["onboarding_complete"] = True
        settings["candidate_name"] = "Ada Lovelace"
        config.save("settings", settings)

        result = main.reset_onboarding()

        self.assertEqual(result, {"complete": False})
        self.assertEqual(config.load("settings")["candidate_name"], "Ada Lovelace")


if __name__ == "__main__":
    unittest.main()
