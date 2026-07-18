"""Regression tests for deterministic JD-to-resume catalog selection."""

import json
from pathlib import Path
import re
import sys
import unittest

from docx import Document

sys.path.insert(0, str(Path(__file__).parent.parent))

from fit import detect_family
from resume_engine import generate, tailor_for_job
from resume_engine.catalog import load_catalog


ROOT = Path(__file__).parent
FIXTURES = json.loads(
    (ROOT / "fixtures" / "representative_jds.json").read_text(encoding="utf-8")
)
OUTPUT = ROOT.parent / "output" / "catalog_test"
UNSUPPORTED_SENIORITY = re.compile(
    r"\b(senior|sr\.?|lead|manager|director|principal|head|chief|vp)\b", re.I
)


class CatalogTailoringTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        OUTPUT.mkdir(parents=True, exist_ok=True)

    def test_representative_jds(self):
        for fixture in FIXTURES:
            with self.subTest(fixture=fixture["name"]):
                family, _ = detect_family(fixture["title"], fixture["jd_text"])
                self.assertEqual(fixture["expected_family"], family)

                data, report = tailor_for_job(
                    family, fixture["title"], fixture["jd_text"]
                )
                self.assertEqual(5, len(data.experiences))
                self.assertLessEqual(
                    sum("intern" in exp.role.casefold() for exp in data.experiences),
                    2,
                )
                for exp in data.experiences:
                    self.assertIsNone(UNSUPPORTED_SENIORITY.search(exp.role), exp.role)
                self.assertEqual([4, 3, 4, 3, 1], [len(exp.bullets) for exp in data.experiences])

                skill_text = " | ".join(category.skills for category in data.skills)
                for expected in fixture["expected_skills"]:
                    self.assertIn(expected, skill_text)
                for expected in fixture["expected_gaps"]:
                    self.assertIn(expected, report["unapproved_jd_terms"])

                self.assertEqual(4, len(data.skills))
                for category in data.skills:
                    self.assertLessEqual(len(category.skills), 160)

                out = OUTPUT / f"{fixture['name']}.docx"
                _, warnings = generate(data, str(out))
                self.assertEqual([], warnings)
                doc = Document(out)
                self.assertEqual(1, len(doc.tables))
                self.assertEqual(21, len(doc.tables[0].rows))

    def test_catalog_safety(self):
        catalog = load_catalog()
        categories = {item["name"] for item in catalog["skill_categories"]}
        companies = set()
        for experience in catalog["experiences"]:
            self.assertNotIn(experience["company"], companies)
            companies.add(experience["company"])
            for title in experience["titles"]:
                self.assertIsNone(UNSUPPORTED_SENIORITY.search(title["text"]), title["text"])
            for bullet in experience["bullets"]:
                self.assertLessEqual(len(bullet["text"]), 250, bullet["text"])

        skill_names = set()
        for skill in catalog["skills"]:
            self.assertIn(skill["category"], categories)
            self.assertNotIn(skill["name"].casefold(), skill_names)
            skill_names.add(skill["name"].casefold())


if __name__ == "__main__":
    unittest.main()
