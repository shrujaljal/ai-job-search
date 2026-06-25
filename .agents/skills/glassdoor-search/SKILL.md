---
name: glassdoor-search
version: 1.0.0
description: >
  Make sure to use this skill whenever the user wants to search for jobs on Glassdoor,
  find Glassdoor job listings, look up company reviews alongside job postings, or asks
  about job opportunities with salary data on Glassdoor — even if they don't mention
  glassdoor.com explicitly. Invoke this skill for questions about open positions with
  salary ranges, company ratings, employee reviews combined with job search, or when
  the user specifically mentions Glassdoor. Also trigger for: "glassdoor jobs",
  "jobs on glassdoor", "glassdoor job search", "glassdoor job listings", "find job
  glassdoor". Trigger phrases include: glassdoor, glassdoor jobs, jobs with salary,
  job with reviews, company reviews jobs, glassdoor.com, glassdoor listings,
  software engineer glassdoor, data scientist glassdoor, product manager glassdoor,
  glassdoor remote jobs, glassdoor salary, glassdoor hiring, jobs glassdoor usa,
  company ratings jobs, employer reviews.

  NOTE: Glassdoor uses strong Cloudflare bot protection. If this skill's CLI returns
  a BLOCKED error, immediately fall back to WebSearch with site:glassdoor.com queries.
context: fork
allowed-tools: Bash(bun run skills/glassdoor-search/cli/src/cli.ts *)
---

# Glassdoor Search Skill

Search live US job listings from [Glassdoor.com](https://www.glassdoor.com/). No authentication required. Extracts structured data from Glassdoor's embedded `__NEXT_DATA__` JSON.

> **Important**: Glassdoor uses strong Cloudflare bot protection. If the CLI returns a `BLOCKED` or `PARSE_ERROR` code, **immediately fall back to WebSearch** with `site:glassdoor.com` queries instead of retrying.

## When to use this skill

Invoke this skill when the user wants to:

- Search for job openings on Glassdoor (often valued for salary transparency and company reviews context)
- Find jobs by keyword, title, or skill on Glassdoor
- Filter by posting date or remote work type
- Get full job descriptions from Glassdoor postings

## Commands

### Search job listings

```bash
bun run skills/glassdoor-search/cli/src/cli.ts search [flags]
```

Key flags:
- `--query <text>` / `-q <text>` — keyword search (job title, skill, company). **Required** unless `--location` is provided.
- `--location <text>` / `-l <text>` — location (e.g. `"San Francisco, CA"`, `"New York"`)
- `--days <n>` — max posting age: `1`, `3`, `7`, `14`, `30`, `any` (default)
- `--remote` — remote jobs only (flag)
- `--page <n>` — page number (30 results per page)
- `--limit <n>` — cap results returned
- `--format json|table|plain`

### Fetch full job detail

```bash
bun run skills/glassdoor-search/cli/src/cli.ts detail <id> [--format json|plain]
```

`id` is the numeric listing ID from `search` results. You may also pass the full Glassdoor job URL.

---

## How to use effectively

**If the CLI is blocked, fall back immediately to WebSearch:**
```
WebSearch: site:glassdoor.com "software engineer" "San Francisco" posted:7d
```

**Natural workflow: `search` → `detail`.**
1. `search` returns job IDs and quick summaries.
2. `detail <id>` returns the full job description.

---

## Usage examples

### Software engineer jobs in San Francisco

```bash
bun run skills/glassdoor-search/cli/src/cli.ts search \
  --query "software engineer" \
  --location "San Francisco, CA" \
  --days 7 \
  --format table
```

### Remote DevOps jobs posted in the last 2 weeks

```bash
bun run skills/glassdoor-search/cli/src/cli.ts search \
  --query "devops engineer" \
  --remote \
  --days 14 \
  --format table
```

### Full details for a specific job

```bash
bun run skills/glassdoor-search/cli/src/cli.ts detail 1234567890 --format plain
```

### WebSearch fallback (when CLI is blocked)

```
site:glassdoor.com/job-listing "software engineer" "San Francisco"
```

---

## Output formats

| Format | Best for |
|--------|----------|
| `json` | Default — programmatic use, passing IDs to `detail` |
| `table` | Quick human-readable overview |
| `plain` | Reading a single job's full details (`detail` command) |

All errors are written to **stderr** as `{ "error": "...", "code": "..." }` and the process exits with code `1`.

---

## Notes

- Glassdoor uses strong Cloudflare protection. **Use WebSearch as fallback when `BLOCKED`.**
- Data comes from `__NEXT_DATA__` JSON (Glassdoor is a Next.js app).
- Detail pages also try JSON-LD which may have more complete structured data.
- Page size is 30 results per page.
- No salary data is available via scraping; use WebSearch for pages that include salary estimates.
