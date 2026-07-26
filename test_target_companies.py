"""Tests for target-company import, matching, and persistent job history."""

from pathlib import Path
from tempfile import TemporaryDirectory
import json
import unittest
from unittest.mock import patch

from target_companies import (
    company_matches,
    finish_search_run,
    import_records,
    initialize_database,
    fetch_career_jobs,
    list_companies,
    record_job,
    role_match_score,
    run_jobs,
    SEED_FILE,
    start_search_run,
)


class TargetCompanyTests(unittest.TestCase):
    def test_seed_contains_every_unique_company(self):
        seed = json.loads(SEED_FILE.read_text(encoding="utf-8"))
        self.assertEqual(97, len(seed))
        self.assertEqual(97, len({
            company["company_name"].casefold() for company in seed
        }))
        self.assertEqual(260, sum(len(company["roles"]) for company in seed))

        merged = {
            company["company_name"]: company
            for company in seed
            if len(company["source_tabs"]) > 1
        }
        self.assertEqual(7, len(merged))
        self.assertIn("Doximity", merged)
        self.assertIn("Doximity Inc.", merged["Doximity"]["aliases"])
        self.assertIn("Wordware", merged)
        self.assertIn("Wordware (Sauna)", merged["Wordware"]["aliases"])

    def test_import_is_idempotent_and_only_fills_missing_url(self):
        with TemporaryDirectory() as temp:
            db = Path(temp) / "targets.sqlite3"
            base = [{
                "company_name": "Example Inc.",
                "aliases": ["Example Inc."],
                "location": "San Francisco",
                "roles": ["Business Analyst"],
                "career_url": "",
                "category": "Technology",
                "source_tabs": ["Initial"],
                "notes": "",
            }]
            first = import_records(base, db)
            self.assertEqual(1, first["companies_added"])
            self.assertEqual(1, first["roles_added"])

            update = [{
                **base[0],
                "company_name": "Example",
                "roles": ["Business Analyst", "Strategy Analyst"],
                "career_url": "https://example.com/careers",
                "source_tabs": ["Update"],
            }]
            second = import_records(update, db)
            third = import_records(update, db)
            companies = list_companies(db)

            self.assertEqual(1, len(companies))
            self.assertEqual(2, len(companies[0]["roles"]))
            self.assertEqual(
                "https://example.com/careers", companies[0]["career_url"]
            )
            self.assertEqual(1, second["career_urls_added"])
            self.assertEqual(0, third["roles_added"])

    def test_broad_role_and_company_matching(self):
        score, role = role_match_score(
            "Strategic Business Operations Analyst",
            ["Strategy & Operations Analyst"],
        )
        self.assertGreaterEqual(score, 45)
        self.assertEqual("Strategy & Operations Analyst", role)
        self.assertEqual(
            (0, ""),
            role_match_score(
                "Senior Strategy Director", ["Strategy Analyst"]
            ),
        )
        self.assertTrue(company_matches(
            "Amazon Web Services (AWS)",
            {
                "company_name": "Amazon / AWS",
                "aliases": ["Amazon / AWS"],
            },
        ))

    def test_seen_job_is_new_only_once_across_sources(self):
        with TemporaryDirectory() as temp:
            db = Path(temp) / "targets.sqlite3"
            initialize_database(db, seed_path=Path(temp) / "missing.json")
            import_records([{
                "company_name": "Example",
                "roles": ["Business Analyst"],
                "aliases": ["Example"],
                "location": "",
                "career_url": "",
                "category": "",
                "source_tabs": ["Test"],
                "notes": "",
            }], db)
            company = list_companies(db)[0]

            run_one = start_search_run("", "any", ["LinkedIn"], 1, db)
            linked_in = {
                "id": "LI-123",
                "title": "Business Analyst",
                "company": "Example",
                "location": "San Francisco, CA",
                "url": "https://linkedin.com/jobs/view/123?trk=test",
                "board": "LinkedIn",
            }
            _, is_new = record_job(
                run_one, linked_in, company, "Business Analyst", db
            )
            self.assertTrue(is_new)

            same_career_job = {
                "id": "REQ-9",
                "title": "Business Analyst",
                "company": "Example Inc.",
                "location": "San Francisco, CA",
                "url": "https://example.com/jobs/REQ-9",
                "board": "Career site",
                "source": "Greenhouse",
            }
            _, is_new_again = record_job(
                run_one, same_career_job, company, "Business Analyst", db
            )
            self.assertFalse(is_new_again)
            finish_search_run(run_one, 1, 0, 1, 1, db)
            self.assertEqual(1, len(run_jobs(run_one, new_only=True, db_path=db)))

            run_two = start_search_run("", "any", ["LinkedIn"], 1, db)
            _, tomorrow_new = record_job(
                run_two, linked_in, company, "Business Analyst", db
            )
            self.assertFalse(tomorrow_new)
            finish_search_run(run_two, 1, 0, 1, 0, db)
            self.assertEqual([], run_jobs(run_two, new_only=True, db_path=db))
            self.assertEqual(1, len(run_jobs(run_two, db_path=db)))

    def test_supported_career_site_api_is_parsed(self):
        response = json.dumps({
            "jobs": [{
                "id": 123,
                "title": "Business Operations Analyst",
                "updated_at": "2026-07-25T10:00:00-07:00",
                "location": {"name": "San Francisco, CA"},
                "absolute_url": (
                    "https://boards.greenhouse.io/example/jobs/123"
                ),
                "content": "Support strategy and operations.",
            }]
        }).encode("utf-8")
        with patch("target_companies._request", return_value=response):
            jobs, status, provider = fetch_career_jobs(
                "Example",
                "https://boards.greenhouse.io/example",
            )
        self.assertEqual("ok", status)
        self.assertEqual("greenhouse", provider)
        self.assertEqual(1, len(jobs))
        self.assertEqual("123", jobs[0]["id"])
        self.assertEqual("Business Operations Analyst", jobs[0]["title"])


if __name__ == "__main__":
    unittest.main()
