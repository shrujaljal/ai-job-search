from __future__ import annotations

import unittest
from unittest.mock import patch

import company_jobs


class CompanyJobsTests(unittest.TestCase):
    @patch("company_jobs._get_json")
    def test_greenhouse_adapter_normalizes_job(self, get_json) -> None:
        get_json.return_value = {"jobs": [{
            "id": 42,
            "title": "Business Operations Analyst",
            "location": {"name": "California"},
            "absolute_url": "https://boards.greenhouse.io/acme/jobs/42",
            "updated_at": "2026-07-24T12:00:00Z",
            "content": "<p>Build KPI dashboards.</p>",
        }]}

        jobs = company_jobs.fetch_source({
            "name": "Acme",
            "url": "https://boards.greenhouse.io/acme",
        })

        self.assertEqual(jobs[0]["company"], "Acme")
        self.assertEqual(jobs[0]["source"], "Greenhouse")
        self.assertEqual(jobs[0]["jd_text"], "Build KPI dashboards.")

    def test_tracker_matches_url_or_company_and_title(self) -> None:
        jobs = [
            {"company": "Acme", "title": "Analyst", "url": "https://acme.com/jobs/1?src=feed"},
            {"company": "Beta Inc.", "title": "Program Manager", "url": ""},
        ]
        applications = [
            {"id": 1, "company": "Other", "role": "Other", "url": "https://acme.com/jobs/1",
             "status": "Applied"},
            {"id": 2, "company": "Beta Inc", "role": "Program Manager", "url": "",
             "status": "To Apply"},
        ]

        company_jobs.annotate_tracker(jobs, applications)

        self.assertTrue(jobs[0]["already_applied"])
        self.assertEqual(jobs[0]["application_status"], "Applied")
        self.assertTrue(jobs[1]["tracked"])
        self.assertFalse(jobs[1]["already_applied"])

    def test_generic_parser_keeps_unique_job_links(self) -> None:
        html = b"""
        <a href="/jobs/123">Operations Analyst</a>
        <a href="/jobs/123">Operations Analyst</a>
        <a href="/about">About us</a>
        """
        with patch("company_jobs._request", return_value=(html, "https://acme.com/careers")):
            jobs = company_jobs.fetch_source({
                "name": "Acme",
                "url": "https://acme.com/careers",
            })

        self.assertEqual(len(jobs), 1)
        self.assertEqual(jobs[0]["url"], "https://acme.com/jobs/123")


if __name__ == "__main__":
    unittest.main()
