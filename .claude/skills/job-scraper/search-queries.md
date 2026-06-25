# Search Queries for Job Scraper

<!-- SETUP: Customize these queries based on your skills, target roles, and location -->

## Search Sites

Primary (US job market):
- **linkedin.com/jobs** — LinkedIn job listings (use the linkedin-search CLI or site: search)
- **indeed.com** — largest US job board (use the indeed-search CLI or site: search)
- **glassdoor.com** — job listings with salary and review data (use glassdoor-search CLI or site: search)

Secondary (company career pages via Google):
- Direct Google searches with `site:` filters for known target companies

## CLI Scraper Commands

The following CLI tools are available via Bash. Run from the project root (they require `cd .agents` first):

### LinkedIn (most reliable, no auth required)
```bash
cd .agents && bun run skills/linkedin-search/cli/src/cli.ts search \
  --query "[YOUR_PRIMARY_JOB_TITLE]" \
  --location "[YOUR_CITY]" \
  --date-posted week \
  --format json
```

### Indeed (may be blocked by Cloudflare)
```bash
cd .agents && bun run skills/indeed-search/cli/src/cli.ts search \
  --query "[YOUR_PRIMARY_JOB_TITLE]" \
  --location "[YOUR_CITY]" \
  --days 7 \
  --format json
```

### Glassdoor (strong anti-bot — fall back to WebSearch if blocked)
```bash
cd .agents && bun run skills/glassdoor-search/cli/src/cli.ts search \
  --query "[YOUR_PRIMARY_JOB_TITLE]" \
  --location "[YOUR_CITY]" \
  --days 7 \
  --format json
```

If any CLI tool returns a BLOCKED or PARSE_ERROR exit code, fall back to WebSearch:
```
WebSearch: site:indeed.com "[YOUR_PRIMARY_JOB_TITLE]" "[YOUR_CITY]" posted:7d
WebSearch: site:glassdoor.com "[YOUR_PRIMARY_JOB_TITLE]" "[YOUR_CITY]" posted:14d
```

## Query Categories

Queries are grouped by priority. Each query should be combined with your location terms (e.g. "[YOUR_CITY]", "[YOUR_STATE]") where the site supports it.

### Priority 1: [YOUR_PRIMARY_ROLE_TYPE]

These match your strongest and most desired career direction.

**LinkedIn CLI:**
```bash
cd .agents && bun run skills/linkedin-search/cli/src/cli.ts search \
  --query "[YOUR_PRIMARY_JOB_TITLE]" \
  --location "[YOUR_CITY]" \
  --date-posted week --format json
```

**WebSearch fallback:**
```
site:linkedin.com/jobs "[YOUR_PRIMARY_JOB_TITLE]" "[YOUR_CITY]"
site:indeed.com "[YOUR_PRIMARY_JOB_TITLE]" "[YOUR_CITY]" posted:7d
site:glassdoor.com/job-listing "[YOUR_PRIMARY_JOB_TITLE]" "[YOUR_CITY]"
```

### Priority 2: [YOUR_DOMAIN_EXPERTISE]

These match your domain expertise.

**LinkedIn CLI:**
```bash
cd .agents && bun run skills/linkedin-search/cli/src/cli.ts search \
  --query "[YOUR_DOMAIN_KEYWORD_1]" \
  --location "[YOUR_CITY]" \
  --date-posted month --format json
```

**WebSearch fallback:**
```
site:linkedin.com/jobs "[YOUR_DOMAIN_KEYWORD_1]" "[YOUR_CITY]"
site:indeed.com "[YOUR_DOMAIN_KEYWORD_2]" "[YOUR_CITY]" posted:14d
```

### Priority 3: [YOUR_ADJACENT_ROLE_TYPE]

Adjacent roles you could pivot into.

```
site:linkedin.com/jobs "[YOUR_ADJACENT_TITLE_1]" "[YOUR_KEY_SKILL]" "[YOUR_CITY]"
site:indeed.com "[YOUR_ADJACENT_TITLE_2]" "[YOUR_KEY_SKILL]" "[YOUR_CITY]" posted:14d
```

### Priority 4: Broader Technical / Consulting

Wider net for general technical roles.

**LinkedIn CLI:**
```bash
cd .agents && bun run skills/linkedin-search/cli/src/cli.ts search \
  --query "[YOUR_KEY_SKILL] developer" \
  --location "[YOUR_CITY]" \
  --job-type fulltime --format json
```

**WebSearch fallback:**
```
site:indeed.com "[YOUR_KEY_SKILL] developer" "[YOUR_CITY]" posted:30d
site:glassdoor.com "technical consultant" "[YOUR_DOMAIN]" "[YOUR_CITY]"
```

### Priority 5: Remote jobs

Remote-only opportunities across the US.

**LinkedIn CLI:**
```bash
cd .agents && bun run skills/linkedin-search/cli/src/cli.ts search \
  --query "[YOUR_PRIMARY_JOB_TITLE]" \
  --remote \
  --date-posted week --format json
```

**Indeed CLI:**
```bash
cd .agents && bun run skills/indeed-search/cli/src/cli.ts search \
  --query "[YOUR_PRIMARY_JOB_TITLE]" \
  --remote \
  --days 7 --format json
```

## Location Filter

When evaluating results, verify the job location is within reasonable commute distance or is remote. Define acceptable areas:
- [YOUR_CITY] and surrounding areas
- [ACCEPTABLE_AREA_1]
- [ACCEPTABLE_AREA_2]
- Remote (fully remote positions)
- [BORDERLINE_AREA] (borderline - ~X min by transit)
- [TOO_FAR_AREA] (too far)

## Date Filter

Only include jobs posted within the last 14 days, or with an application deadline that has not yet passed. If a posting date cannot be determined, include it but flag as "date unknown".

## Adapting Queries

If the user specifies a focus area, select queries from the matching category and also generate 2-3 custom queries for that focus. For example:
- "/scrape [focus_area]" -> relevant category queries + custom focus-specific queries
- "/scrape remote" -> run all Priority 5 remote queries plus primary role queries with --remote flag
- "/scrape broad" -> run queries from all priority categories

## CLI vs WebSearch Decision Tree

1. **Start with LinkedIn CLI** — most reliable, no bot protection
2. **Try Indeed CLI** — good structured data if not blocked
3. **Try Glassdoor CLI** — if blocked (exit code 1 + BLOCKED error), fall back immediately to WebSearch
4. **WebSearch fallback** — always works, less structured, requires WebFetch to get full details
5. **Company career pages** — use WebSearch `site:company.com/careers` for target companies
