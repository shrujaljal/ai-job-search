from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import config
import store


class AccountIsolationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.original_root = config.DATA_ROOT
        self.original_dir = config.DATA_DIR
        config.DATA_ROOT = Path(self.temp.name) / "data"
        config.DATA_DIR = config.DATA_ROOT
        config.initialize_accounts()

    def tearDown(self) -> None:
        config.DATA_ROOT = self.original_root
        config.DATA_DIR = self.original_dir
        self.temp.cleanup()

    def test_new_account_has_isolated_tracker_and_config(self) -> None:
        store.add_application("Acme", "Operations Analyst")
        account = config.create_account("Marketing profile")

        self.assertEqual(config.active_account_id(), account["id"])
        self.assertEqual(store.list_applications(), [])
        self.assertFalse(config.load("settings")["onboarding_complete"])

        config.activate_account("default")
        self.assertEqual(store.list_applications()[0]["company"], "Acme")

    def test_legacy_data_becomes_default_account(self) -> None:
        settings = config.load("settings")
        settings["candidate_name"] = "Configured User"
        config.save("settings", settings)
        config.DATA_DIR = config.DATA_ROOT
        (config.DATA_ROOT / "accounts.json").unlink()

        result = config.initialize_accounts()

        self.assertEqual(result["active_id"], "default")
        self.assertEqual(result["accounts"][0]["name"], "Configured User")


if __name__ == "__main__":
    unittest.main()
