from __future__ import annotations

import json
import unittest

import tailoring
from llm.base import LLMProvider, ProviderError
from llm.prompts import build_user_prompt


PROFILE = {
    "identity": {"name": "Candidate"},
    "summary": "Operations analyst",
    "experience": [{
        "company": "Acme",
        "role": "Analyst",
        "date": "2024",
        "bullets": ["Built 20 weekly reports using Excel", "Documented reporting workflows"],
    }],
    "education": [],
    "projects": [],
    "leadership": [],
    "skills": [{"name": "Tools", "items": "Excel, SQL"}],
}
CONTENT = {
    "default_family": "General",
    "families": {"General": {"summary": "Operations analyst", "skill_categories": []}},
}
SETTINGS = {"llm": {"enabled": True}}


class FakeProvider(LLMProvider):
    name = "fake"
    model = "fake-model"

    def __init__(self, response: dict | None = None, error: str = "") -> None:
        self.response = response or {}
        self.error = error

    def complete_json(self, system_prompt: str, user_prompt: str) -> str:
        if self.error:
            raise ProviderError(self.error)
        return json.dumps(self.response)


def proposal(bullet: str = "Built 20 weekly Excel reports") -> dict:
    return {
        "summary": "Operations analyst experienced in Excel reporting",
        "summary_source_evidence": ["Operations analyst", "Excel"],
        "experiences": [{
            "index": 0,
            "bullets": [{"text": bullet, "source_indices": [0]}],
        }],
        "skill_names": ["Excel"],
    }


class TailoringTests(unittest.TestCase):
    def run_tailor(self, provider: LLMProvider, use_llm: bool | None = None):
        return tailoring.build_tailored_context(
            profile=PROFILE,
            content=CONTENT,
            family="General",
            jd_text="Need Excel reporting experience",
            role="Operations Analyst",
            company="Target",
            settings=SETTINGS,
            use_llm=use_llm,
            provider=provider,
        )

    def test_valid_grounded_response_uses_ai(self) -> None:
        context, meta = self.run_tailor(FakeProvider(proposal()))

        self.assertEqual(meta["engine"], "ai")
        self.assertEqual(context["experiences"][0]["bullets"], ["Built 20 weekly Excel reports"])
        self.assertEqual(context["skills"], [{"name": "Tools", "items": "Excel"}])

    def test_invented_number_falls_back_to_rules(self) -> None:
        context, meta = self.run_tailor(FakeProvider(proposal("Built 99 weekly Excel reports")))

        self.assertEqual(meta["engine"], "rules")
        self.assertTrue(meta["ai_fallback"])
        self.assertIn("99", meta["ai_warning"])
        self.assertEqual(context["experiences"][0]["bullets"][0], PROFILE["experience"][0]["bullets"][0])

    def test_unsupported_plus_claim_falls_back_to_rules(self) -> None:
        _, meta = self.run_tailor(FakeProvider(proposal("Built 20+ weekly Excel reports")))

        self.assertEqual(meta["engine"], "rules")
        self.assertIn("20+", meta["ai_warning"])

    def test_provider_failure_falls_back_to_rules(self) -> None:
        _, meta = self.run_tailor(FakeProvider(error="provider offline"))

        self.assertEqual(meta["engine"], "rules")
        self.assertIn("provider offline", meta["ai_warning"])

    def test_explicit_disable_uses_rules_without_calling_provider(self) -> None:
        _, meta = self.run_tailor(FakeProvider(error="must not be called"), use_llm=False)

        self.assertEqual(meta, {"engine": "rules", "ai_requested": False})

    def test_prompt_excludes_identity_and_contact_details(self) -> None:
        context, _ = self.run_tailor(FakeProvider(proposal()), use_llm=False)
        prompt = build_user_prompt(PROFILE, context, "JD", "Role", "Company")

        self.assertNotIn('"identity"', prompt)
        self.assertNotIn('"name": "Candidate"', prompt)


if __name__ == "__main__":
    unittest.main()
