# glassdoor-cli

CLI for searching jobs on [Glassdoor.com](https://www.glassdoor.com/).

**Base URL**: `https://www.glassdoor.com`
**Authentication**: None required.
**Format**: Extracts job data from `__NEXT_DATA__` JSON embedded in Next.js pages. Falls back to JSON-LD (`application/ld+json`) on detail pages.

> **Important**: Glassdoor uses strong Cloudflare bot protection. Requests are frequently blocked. If you get a `BLOCKED` error, use `WebSearch` with `site:glassdoor.com` instead.

---

## Installation

```bash
cd skills/glassdoor-search/cli
bun install
```

---

## Commands

| Command | Description |
|---------|-------------|
| `search` | Search Glassdoor job listings |
| `detail` | Fetch full detail for a single job posting |

All commands accept `--format json|table|plain` (default: `json`).
All errors are written to **stderr** as `{ "error": "...", "code": "..." }` and the process exits with code `1`.

---

## `search` — Search Glassdoor job listings

**URL**: `GET https://www.glassdoor.com/Job/jobs.htm?sc.keyword={q}&locT=S&fromAge={days}`

```bash
bun run src/cli.ts search [flags]
```

### Flags

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `--query` / `-q` | string | — | Keywords (job title, skill, company) |
| `--location` / `-l` | string | — | Job location (city, state) |
| `--days` | enum | `any` | Max posting age: `1`, `3`, `7`, `14`, `30`, `any` |
| `--remote` | flag | false | Remote jobs only |
| `--page` | number | `1` | Page number (30 results per page) |
| `--limit` | number | — | Cap total results returned by CLI |
| `--format` | string | `json` | `json`, `table`, `plain` |

### Examples

```bash
# Software engineer jobs in San Francisco
bun run src/cli.ts search --query "software engineer" --location "San Francisco, CA" --days 7

# Remote data analyst jobs (table view)
bun run src/cli.ts search --query "data analyst" --remote --format table

# DevOps engineer jobs posted in the last 14 days
bun run src/cli.ts search --query "devops engineer" --days 14 --format json
```

### Response shape (`--format json`)

```json
{
  "meta": {
    "page": 1,
    "perPage": 30,
    "total": 500,
    "query": "software engineer",
    "location": "San Francisco, CA"
  },
  "results": [
    {
      "id": "1234567890",
      "title": "Software Engineer",
      "company": "Acme Corp",
      "companyUrl": "https://acme.com",
      "location": "San Francisco, CA",
      "date": "2026-06-20",
      "url": "https://www.glassdoor.com/job-listing/software-engineer-jl1234567890",
      "description": "Brief description fragment..."
    }
  ]
}
```

**Field notes:**
- `id` — Glassdoor `listingId`. Pass to `detail`.
- `date` — from `discoveryDate` in `__NEXT_DATA__`; format `YYYY-MM-DD`.
- `description` — up to 300 chars from `descriptionFragments`; `null` if absent.
- `total` — total result count from Glassdoor; `null` if not available.

---

## `detail` — Fetch full job detail

```bash
bun run src/cli.ts detail <id-or-url> [--format json|plain]
```

`id` is the numeric listing ID from `search` results. You may also pass the full Glassdoor job URL (with `?jl=...` or `/jl...`).

### Examples

```bash
# Using numeric ID
bun run src/cli.ts detail 1234567890

# Using full URL
bun run src/cli.ts detail "https://www.glassdoor.com/job-listing/software-engineer-jl1234567890"

# Plain text output
bun run src/cli.ts detail 1234567890 --format plain
```

---

## Error handling

```json
{ "error": "...", "code": "API_ERROR" }
{ "error": "Job not found", "code": "NOT_FOUND" }
{ "error": "Glassdoor returned a Cloudflare challenge page. ...", "code": "BLOCKED" }
{ "error": "No job data found in page response. ...", "code": "PARSE_ERROR" }
{ "error": "--query or --location is required", "code": "MISSING_REQUIRED" }
```

When the CLI exits with `BLOCKED` or `PARSE_ERROR`, fall back to:
```
WebSearch: site:glassdoor.com "software engineer" "San Francisco" posted:7d
```

---

## Notes

- Glassdoor uses strong Cloudflare protection. Expect frequent `BLOCKED` errors on cloud/non-browser IPs.
- When unblocked, data comes from `__NEXT_DATA__` JSON (Glassdoor uses Next.js).
- Detail pages also try JSON-LD (`application/ld+json`) which may contain more structured data.
- Page size is 30 results per page (Glassdoor default).
- Application deadlines are not exposed by Glassdoor's public pages.
