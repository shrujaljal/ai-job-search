"""Quick smoke test - generates the current base resume."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from resume_engine import base_resume, generate


data = base_resume()
out = Path(__file__).parent.parent / "output" / "test_resume.docx"
out.parent.mkdir(exist_ok=True)

path, warnings = generate(data, str(out))
print(f"Generated: {path}")
if warnings:
    print("Warnings:")
    for warning in warnings:
        print(f"  - {warning}")
else:
    print("No content warnings - all within limits.")
