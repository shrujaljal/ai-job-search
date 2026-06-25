# indeed-cli

CLI for searching jobs on [Indeed.com](https://www.indeed.com/).

**Base URL**: `https://www.indeed.com`
**Authentication**: None required.
**Format**: The CLI extracts job data from Indeed's embedded JSON (`window.mosaic.providerData`) and falls back to HTML parsing. Detail pages use JSON-LD (`application/ld+json`).

> **Important**: Indeed uses Cloudflare bot protection. Requests may be blocked with a 403 or a challenge page. If this happens, the CLI exits with code `BLOCKED` and suggests using WebSearch instead.

---

## Installation

```bash
cd skills/indeed-search/cli
bun install
```

---

## Commands

| Command | Description |
|---------|-------------|
| `search` | Search Indeed job listings |
| `detail` | Fetch full detail for a single job posting |

All commands accept `--format json|table|plain` (default: `json`).
All errors are written to **stderr** as `{ "error": "...", "code": "..." }` and the process exits with code `1`.

---

## `search` — Search Indeed job listings

**URL**: `GET https://www.indeed.com/jobs?q={q}&l={location}&sort=date`

```bash
bun run src/cli.ts search [flags]
```

### Flags

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `--query` / `-q` | string | — | Keywords (job title, skill, company) |
| `--location` / `-l` | string | — | Location (city, state) or `remote` |
| `--days` | enum | `any` | Max posting age: `1`, `3`, `7`, `14`, `any` |
| `--remote` | flag | false | Remote jobs only (sets location to `remote`) |
| `--job-type` | enum | — | `fulltime`, `parttime`, `contract`, `internship`, `temporary` |
| `--radius` | number | — | Search radius in miles |
| `--page` | number | `1` | Page number (10 results per page) |
| `--limit` | number | — | Cap total results returned by CLI |
| `--format` | string | `json` | `json`, `table`, `plain` |

### Examples

```bash
# Software engineer jobs in New York posted in the last week
bun run src/cli.ts search --query "software engineer" --location "New York, NY" --days 7

# Remote Python jobs (table view)
bun run src/cli.ts search --query python --remote --format table

# Data analyst jobs, full-time only
bun run src/cli.ts search --query "data analyst" --job-type fulltime --days 14

# Page 2 of results
bun run src/cli.ts search --query "product manager" --location "Seattle, WA" --page 2
```

### Response shape (`--format json`)

```json
{
  "meta": {
    "page": 1,
    "perPage": 10,
    "total": 1500,
    "query": "software engineer",
    "location": "New York, NY"
  },
  "results": [
    {
      "id": "abc123def456abc1",
      "title": "Software Engineer",
      "company": "Acme Corp",
      "companyUrl": null,
      "location": "New York, NY",
      "date": "2026-06-20",
      "url": "https://www.indeed.com/viewjob?jk=abc123def456abc1",
      "description": "Brief job snippet from the listing..."
    }
  ]
}
```

**Field notes:**
- `id` — 16-character hex job key (`jk`). Pass to `detail`.
- `date` — ISO date derived from `pubDate` Unix timestamp in mosaic data; `null` in HTML fallback mode.
- `description` — short snippet (up to 300 chars) from mosaic data; `null` in HTML fallback mode.
- `companyUrl` — always `null` from search; available from `detail` via JSON-LD.
- `total` — total result count from mosaic data; `null` if not available.

---

## `detail` — Fetch full job detail

**URL**: `GET https://www.indeed.com/viewjob?jk={id}`

```bash
bun run src/cli.ts detail <id-or-url> [--format json|plain]
```

`id` is the 16-character hex job key from `search` results. You may also pass the full `viewjob?jk=...` URL.

### Examples

```bash
# Using job key from search results
bun run src/cli.ts detail abc123def456abc1

# Using full URL
bun run src/cli.ts detail "https://www.indeed.com/viewjob?jk=abc123def456abc1"

# Plain text output
bun run src/cli.ts detail abc123def456abc1 --format plain
```

### Response shape (`--format json`)

```json
{
  "id": "abc123def456abc1",
  "title": "Software Engineer",
  "company": "Acme Corp",
  "companyUrl": "https://www.acme.com",
  "location": "New York, NY",
  "date": "2026-06-20",
  "url": "https://www.indeed.com/viewjob?jk=abc123def456abc1",
  "description": "Full plain-text job description...",
  "employmentType": "FULL_TIME",
  "deadline": "2026-07-31",
  "applyUrl": "https://www.indeed.com/viewjob?jk=abc123def456abc1"
}
```

**Field notes:**
- `date` — ISO date from JSON-LD `datePosted`; `null` if not in JSON-LD.
- `deadline` — from JSON-LD `validThrough`; `null` if not set.
- `employmentType` — from JSON-LD (e.g. `FULL_TIME`, `CONTRACTOR`); may be an array joined with `, `.
- `description` — full plain-text description stripped of HTML.
- `applyUrl` — the `viewjob` URL itself (Indeed applies are on-site).

---

## Error handling

```json
{ "error": "...", "code": "API_ERROR" }
{ "error": "Job not found", "code": "NOT_FOUND" }
{ "error": "Indeed returned a Cloudflare challenge page. ...", "code": "BLOCKED" }
{ "error": "--query, --location, or --remote is required", "code": "MISSING_REQUIRED" }
```

---

## Notes

- Indeed uses Cloudflare protection. The CLI may fail with `BLOCKED` on cloud IPs. If so, use `WebSearch` with `site:indeed.com` as a fallback.
- The primary data source is `window.mosaic.providerData["mosaic-provider-jobcards"]` JSON. If this is absent, the CLI attempts HTML parsing (less reliable).
- Detail pages use `application/ld+json` (schema.org `JobPosting`), which is more stable than Indeed's HTML.
- Pagination: 10 results per page (Indeed server default). Use `--page` to navigate.
- `total` in meta may be `null` when the mosaic JSON data is absent.
