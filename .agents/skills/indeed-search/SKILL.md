---
name: indeed-search
version: 1.0.0
description: >
  Make sure to use this skill whenever the user wants to search for jobs on Indeed,
  find Indeed job listings, look up a specific job posting on Indeed, or asks about
  job opportunities in the US via Indeed — even if they don't mention indeed.com
  explicitly. Invoke this skill for questions about open positions, job vacancies,
  hiring, salary ranges, job opportunities by city or sector, or when the user wants
  to find work using Indeed. Also trigger for: "search indeed for jobs", "indeed jobs",
  "jobs on indeed", "find job indeed", "indeed job search", "entry level jobs indeed",
  "jobs near me indeed", "remote jobs indeed", "full time jobs indeed", "part time
  jobs indeed", "contract jobs indeed". Trigger phrases include: indeed jobs,
  indeed.com, job listings indeed, software developer jobs, data engineer jobs,
  project manager jobs, business analyst jobs, marketing jobs, accounting jobs,
  finance jobs, nursing jobs, teaching jobs, warehouse jobs, customer service jobs,
  entry level jobs, jobs hiring today, jobs hiring immediately, jobs in new york,
  jobs in los angeles, jobs in chicago, jobs in houston, jobs in phoenix, jobs near me,
  remote jobs usa, hybrid jobs, contract jobs usa, temp jobs, internship usa.
context: fork
allowed-tools: Bash(bun run skills/indeed-search/cli/src/cli.ts *)
---

# Indeed Search Skill

Search live US job listings from [Indeed.com](https://www.indeed.com/). No authentication required. Extracts structured data from Indeed's embedded JSON and JSON-LD.

> **Note**: Indeed uses Cloudflare bot protection. If requests are blocked, the CLI exits with a `BLOCKED` error and you should fall back to `WebSearch` with `site:indeed.com` queries.

## When to use this skill

Invoke this skill when the user wants to:

- Search for job openings on Indeed by keyword, title, or skill
- Find jobs in a specific US city or region
- Filter jobs by recency (posted today, last 3 days, last week, etc.)
- Filter by job type (full-time, contract, internship, etc.)
- Get the full description and requirements of a specific Indeed job

## Commands

### Search job listings

```bash
bun run skills/indeed-search/cli/src/cli.ts search [flags]
```

Key flags:
- `--query <text>` / `-q <text>` — keyword search. **Required** unless `--location` or `--remote` is provided.
- `--location <text>` / `-l <text>` — location (e.g. `"New York, NY"`, `"Seattle, WA"`, `"remote"`)
- `--days <n>` — max posting age: `1`, `3`, `7`, `14`, `any` (default)
- `--remote` — remote jobs only (flag)
- `--job-type <type>` — `fulltime`, `parttime`, `contract`, `internship`, `temporary`
- `--page <n>` — page number (10 results per page)
- `--limit <n>` — cap results returned
- `--format json|table|plain`

### Fetch full job detail

```bash
bun run skills/indeed-search/cli/src/cli.ts detail <id> [--format json|plain]
```

`id` is the 16-character hex job key from `search` results. You may also pass the full `viewjob?jk=...` URL.

---

## How to use effectively

**Start with `search`.** Use `--query` with a job title or skill and `--location` to narrow by city.

**Use `--days 7` for fresh listings.** Default includes all ages.

**Fall back to WebSearch if blocked.** If the CLI returns a `BLOCKED` error, use:
```
WebSearch: site:indeed.com "software engineer" "New York" posted:7d
```

**Natural workflow: `search` → `detail`.**
1. `search` returns job IDs and quick summaries.
2. `detail <id>` returns the full description, deadline, and employer info from JSON-LD.

---

## Usage examples

### Software engineer jobs in Seattle, posted last week

```bash
bun run skills/indeed-search/cli/src/cli.ts search \
  --query "software engineer" \
  --location "Seattle, WA" \
  --days 7 \
  --format table
```

### Remote data scientist jobs

```bash
bun run skills/indeed-search/cli/src/cli.ts search \
  --query "data scientist" \
  --remote \
  --days 14 \
  --format table
```

### Full-time product manager jobs in Austin

```bash
bun run skills/indeed-search/cli/src/cli.ts search \
  --query "product manager" \
  --location "Austin, TX" \
  --job-type fulltime \
  --format json
```

### Full details for a specific job

```bash
bun run skills/indeed-search/cli/src/cli.ts detail abc123def456abc1 --format plain
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

- Indeed uses Cloudflare. If blocked, fall back to `WebSearch`.
- Primary data is from `window.mosaic.providerData` JSON; HTML parsing is the fallback.
- Detail pages parse `application/ld+json` (schema.org `JobPosting`) which is more reliable.
- Page size is 10 results per page (Indeed default).
- `total` count in meta may be `null` when JSON data is unavailable.
