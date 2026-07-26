"""Build the committed target-company seed from an Excel workbook."""

from argparse import ArgumentParser
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from target_companies import (  # noqa: E402
    import_records,
    list_companies,
    records_from_workbook,
)


def main() -> None:
    parser = ArgumentParser()
    parser.add_argument("workbook", type=Path)
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "data" / "target_companies_seed.json",
    )
    parser.add_argument(
        "--temp-db",
        type=Path,
        default=ROOT / "output" / "target_seed_build.sqlite3",
    )
    args = parser.parse_args()

    if args.temp_db.exists():
        args.temp_db.unlink()
    raw_records = records_from_workbook(args.workbook.read_bytes())
    import_records(raw_records, args.temp_db)

    seed = []
    for company in list_companies(args.temp_db):
        seed.append({
            "company_name": company["company_name"],
            "aliases": company["aliases"],
            "location": company["location"],
            "roles": company["roles"],
            "career_url": company["career_url"],
            "category": company["category"],
            "source_tabs": company["source_tabs"],
            "notes": company["notes"],
        })

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(seed, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(
        f"{len(raw_records)} workbook rows merged into "
        f"{len(seed)} unique companies."
    )


if __name__ == "__main__":
    main()
