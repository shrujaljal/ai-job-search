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

    def test_cancel_new_account_restores_previous_account(self) -> None:
        store.add_application("Acme", "Operations Analyst")
        account = config.create_account("Temporary profile")
        account_dir = config.DATA_DIR

        self.assertTrue(config.can_cancel_account_setup())
        restored = config.cancel_account_setup()

        self.assertEqual(restored["id"], "default")
        self.assertEqual(config.active_account_id(), "default")
        self.assertFalse(account_dir.exists())
        self.assertNotIn(account["id"], {
            item["id"] for item in config.accounts()["accounts"]
        })
        self.assertEqual(store.list_applications()[0]["company"], "Acme")

    def test_finished_account_can_no_longer_be_cancelled(self) -> None:
        account = config.create_account("Permanent profile")

        config.finish_account_setup()

        self.assertFalse(config.can_cancel_account_setup())
        self.assertIn(account["id"], {
            item["id"] for item in config.accounts()["accounts"]
        })


if __name__ == "__main__":
    unittest.main()
