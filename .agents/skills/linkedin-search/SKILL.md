---
name: linkedin-search
version: 1.0.0
description: >
  Make sure to use this skill whenever the user wants to search for jobs on LinkedIn,
  find LinkedIn job listings, look up a specific job posting on LinkedIn, or asks about
  job opportunities in the US or globally on LinkedIn — even if they don't mention
  linkedin.com explicitly. Invoke this skill for questions about open positions, job
  vacancies, hiring, job opportunities by city or sector, or when the user wants to
  find work using LinkedIn. Also trigger for phrases like "find me a job on LinkedIn",
  "LinkedIn jobs", "are there any jobs for X on LinkedIn", or "what positions are on
  LinkedIn". Trigger phrases include: linkedin jobs, jobs on linkedin, linkedin job search,
  job listings linkedin, find job linkedin, software engineer jobs, data scientist jobs,
  product manager jobs, machine learning jobs, remote jobs, jobs in new york, jobs in
  san francisco, jobs in seattle, jobs in austin, jobs in boston, us jobs, jobs usa,
  tech jobs, engineering jobs, jobs hiring now, entry level jobs, senior jobs, internship
  linkedin, contract jobs, full time jobs, part time jobs, linkedin hiring, job openings,
  job vacancies, job opportunities.
context: fork
allowed-tools: Bash(bun run skills/linkedin-search/cli/src/cli.ts *)
---

# LinkedIn Search Skill

Search live US job listings from [LinkedIn Jobs](https://www.linkedin.com/jobs/) using the public guest API. No authentication required.

## When to use this skill

Invoke this skill when the user wants to:

- Search for job openings on LinkedIn by keyword, job title, or technology
- Find jobs in a specific US city or region
- Filter jobs by recency (posted today, last week, last month)
- Filter by remote, hybrid, or on-site work type
- Filter by job type (full-time, contract, internship, etc.)
- Get the full description of a specific LinkedIn job listing

## Commands

### Search job listings

```bash
bun run skills/linkedin-search/cli/src/cli.ts search [flags]
```

Key flags:
- `--query <text>` / `-q <text>` — keyword search (job title, skill, company). **Required** unless `--location` is provided.
- `--location <text>` / `-l <text>` — location filter (e.g. `"San Francisco, CA"`, `"New York"`, `"Remote"`)
- `--date-posted <period>` — `day` (24h), `week`, `month`, `any` (default)
- `--remote` — remote jobs only (flag)
- `--hybrid` — hybrid jobs only (flag)
- `--job-type <type>` — `fulltime`, `parttime`, `contract`, `temporary`, `internship`, `other`
- `--page <n>` — page number (25 results per page)
- `--limit <n>` — cap results returned
- `--format json|table|plain`

### Fetch full job detail

```bash
bun run skills/linkedin-search/cli/src/cli.ts detail <id> [--format json|plain]
```

`id` is the numeric job ID from `search` results. You may also pass the full LinkedIn job URL.

---

## How to use effectively

**Always start with `search`.** Use `--query` with a job title or skill. Add `--location` to narrow by geography.

**Use `--date-posted week` for fresh listings.** Without it, results include older postings.

**Use `--remote` for remote-only positions.** Combine with `--query` for best results.

**Natural workflow: `search` → `detail`.**
1. Use `search` to find matching jobs and their `id` values.
2. Call `detail <id>` to get the full description and apply link.

---

## Usage examples

### Software engineer jobs in San Francisco, posted this week

```bash
bun run skills/linkedin-search/cli/src/cli.ts search \
  --query "software engineer" \
  --location "San Francisco, CA" \
  --date-posted week \
  --format table
```

### Remote data scientist jobs

```bash
bun run skills/linkedin-search/cli/src/cli.ts search \
  --query "data scientist" \
  --remote \
  --date-posted month \
  --format table
```

### Machine learning engineer jobs in New York

```bash
bun run skills/linkedin-search/cli/src/cli.ts search \
  --query "machine learning engineer" \
  --location "New York" \
  --job-type fulltime \
  --format table
```

### Product manager internships

```bash
bun run skills/linkedin-search/cli/src/cli.ts search \
  --query "product manager" \
  --job-type internship \
  --date-posted month \
  --format json
```

### Get full details for a specific job

```bash
bun run skills/linkedin-search/cli/src/cli.ts detail 3912345678 --format plain
```

---

## Output formats

| Format | Best for |
|--------|----------|
| `json` | Default — programmatic use, data processing, passing IDs to `detail` |
| `table` | Quick human-readable overview |
| `plain` | Reading a single job's full detail (`detail` command) |

All errors are written to **stderr** as `{ "error": "...", "code": "..." }` and the process exits with code `1`.

---

## Notes

- Uses LinkedIn's public guest API — no credentials required.
- LinkedIn may return 403 from cloud/VPN IPs. Retry after a delay if blocked.
- Page size is fixed at 25 results per page.
- Application deadlines are not exposed by LinkedIn's guest API.
- The `description` field is always `null` in `search` results — use `detail` to retrieve it.
