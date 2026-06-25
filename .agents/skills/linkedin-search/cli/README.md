# linkedin-cli

CLI for searching jobs on [LinkedIn Jobs](https://www.linkedin.com/jobs/) using the public guest API.

**Base URL**: `https://www.linkedin.com/jobs-guest/jobs/api/`
**Authentication**: None required (guest API).
**Format**: Returns HTML fragments; the CLI parses them and emits clean JSON.

> **Note**: LinkedIn may throttle or block requests from non-browser IPs. If you receive a 403 error, try again later or use `--format table` to spot-check results.

---

## Installation

```bash
cd skills/linkedin-search/cli
bun install
```

---

## Commands

| Command | Description |
|---------|-------------|
| `search` | Search LinkedIn job listings |
| `detail` | Fetch full detail for a single job posting |

All commands accept `--format json|table|plain` (default: `json`).
All errors are written to **stderr** as `{ "error": "...", "code": "..." }` and the process exits with code `1`.

---

## `search` — Search LinkedIn job listings

**Endpoint**: `GET /jobs-guest/jobs/api/seeMoreJobPostings/search`

```bash
bun run src/cli.ts search [flags]
```

### Flags

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `--query` / `-q` | string | — | Keywords (job title, skill, company) |
| `--location` / `-l` | string | — | Location (city, state, country) or `Remote` |
| `--date-posted` | enum | `any` | `day` (24h), `week`, `month`, `any` |
| `--remote` | flag | false | Remote jobs only |
| `--hybrid` | flag | false | Hybrid jobs only |
| `--job-type` | enum | — | `fulltime`, `parttime`, `contract`, `temporary`, `internship`, `other` |
| `--page` | number | `1` | Page number (25 results per page) |
| `--limit` | number | — | Cap total results returned by the CLI |
| `--format` | string | `json` | `json`, `table`, `plain` |

### Examples

```bash
# Software engineer jobs in San Francisco posted this week
bun run src/cli.ts search --query "software engineer" --location "San Francisco, CA" --date-posted week

# Remote Python jobs, newest first (table view)
bun run src/cli.ts search --query python --remote --date-posted month --format table

# Page 2 of data engineer results in New York
bun run src/cli.ts search --query "data engineer" --location "New York" --page 2

# Full-time machine learning jobs (cap at 10)
bun run src/cli.ts search --query "machine learning" --job-type fulltime --limit 10
```

### Response shape (`--format json`)

```json
{
  "meta": {
    "page": 1,
    "perPage": 25,
    "query": "software engineer",
    "location": "San Francisco, CA"
  },
  "results": [
    {
      "id": "3912345678",
      "title": "Software Engineer",
      "company": "Acme Corp",
      "companyUrl": "https://www.linkedin.com/company/acme-corp",
      "location": "San Francisco, CA",
      "date": "2026-06-20",
      "url": "https://www.linkedin.com/jobs/view/software-engineer-at-acme-corp-3912345678",
      "description": null
    }
  ]
}
```

**Field notes:**
- `id` — numeric LinkedIn job posting ID. Pass to `detail`.
- `date` — ISO date from `<time datetime="...">`. May be `null` if absent.
- `description` — always `null` in search results; use `detail` to get the full text.
- `companyUrl` — LinkedIn company page URL; `null` if not linked.

---

## `detail` — Fetch full job detail

**Endpoint**: `GET /jobs-guest/jobs/api/jobPosting/{id}`

```bash
bun run src/cli.ts detail <id-or-url> [--format json|plain]
```

`id` is the numeric job ID from `search` results. You may also pass the full LinkedIn job URL.

### Examples

```bash
# Using numeric ID from search results
bun run src/cli.ts detail 3912345678

# Using full URL
bun run src/cli.ts detail "https://www.linkedin.com/jobs/view/software-engineer-3912345678"

# Plain text output
bun run src/cli.ts detail 3912345678 --format plain
```

### Response shape (`--format json`)

```json
{
  "id": "3912345678",
  "title": "Software Engineer",
  "company": "Acme Corp",
  "companyUrl": "https://www.linkedin.com/company/acme-corp",
  "location": "San Francisco, CA",
  "date": null,
  "url": "https://www.linkedin.com/jobs/view/3912345678",
  "description": "Full plain-text job description...",
  "employmentType": "Full-time",
  "deadline": null,
  "applyUrl": "https://www.linkedin.com/jobs/apply/3912345678"
}
```

**Field notes:**
- `date` — not available from the detail page; always `null`.
- `deadline` — LinkedIn does not expose application deadlines; always `null`.
- `applyUrl` — the direct apply URL; `null` if not found (e.g. external apply).
- `description` — full plain-text description (HTML stripped).

---

## Error handling

```json
{ "error": "...", "code": "API_ERROR" }
{ "error": "Job not found", "code": "NOT_FOUND" }
{ "error": "Access denied (403) — LinkedIn is blocking this request.", "code": "API_ERROR" }
{ "error": "--query or --location is required", "code": "MISSING_REQUIRED" }
{ "error": "<id> or <url> is required", "code": "MISSING_REQUIRED" }
```

---

## Notes

- LinkedIn's guest API returns 25 results per page. Use `--page` to paginate.
- LinkedIn may block scraping with a 403 when accessed from cloud/VPN IPs. Retry after a delay.
- `date` in search results is an ISO date string; the detail page does not expose it.
- LinkedIn does not expose application deadlines via the guest API.
- The guest API (`/jobs-guest/`) does not require a login or API key.
