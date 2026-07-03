"""End-to-end test: scrape -> score -> queue -> tailor (headless, no Streamlit)."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import json
import subprocess
from fit import score_job
from tailoring import tailor_job

ROOT = Path(__file__).parent.parent
LI = ROOT / ".agents/skills/linkedin-search/cli"

# 1. Scrape LinkedIn
print("1. Scraping LinkedIn…")
res = subprocess.run(
    ["bun", "run", "src/cli.ts", "search", "--query", "Strategy Operations Analyst",
     "--location", "California", "--format", "json", "--limit", "6"],
    cwd=str(LI), capture_output=True, text=True, timeout=40,
)
jobs = json.loads(res.stdout)["results"]
for j in jobs:
    j["board"] = "LinkedIn"
print(f"   got {len(jobs)} jobs")

# 2. Score
print("\n2. Scoring:")
for j in jobs:
    fit = score_job(j["title"], j["company"], j.get("location", ""))
    j.update(fit)
    print(f"   [{fit['score']:>3}] {fit['tier']:<8} {j['title'][:45]:<45} @ {j['company']}")
    print(f"         -> {fit['reason']}")

# 3. Tailor the top-scoring job
jobs.sort(key=lambda j: j["score"], reverse=True)
top = jobs[0]
print(f"\n3. Tailoring top job: {top['title']} @ {top['company']}")
result = tailor_job(top)
if result["ok"]:
    print(f"   [OK] family={result['family']}")
    print(f"   resume: {result['resume_path']}")
    print(f"   jd:     {result['jd_path']}")
    if result["warnings"]:
        print(f"   warnings: {result['warnings']}")
else:
    print(f"   [FAIL] {result['error']}")
