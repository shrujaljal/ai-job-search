# Job Scraper

**name:** job-scraper
**description:** Scrapes US job sites for new positions matching your profile. Deduplicates across runs. Triggers on: job scrape, find jobs, search jobs, new jobs, job search, scrape jobs, /scrape
**allowed-tools:** Read, Write, Edit, Glob, Grep, WebFetch, WebSearch, Bash, Agent, AskUserQuestion

---

## How It Works

This skill searches multiple US job sites using targeted queries based on your profile, deduplicates against previously seen jobs and the application tracker, and presents new matches with a quick fit assessment.

## Invocation

The user triggers this skill by saying things like:
- "Find new jobs"
- "Scrape for jobs"
- "Any new positions?"
- "/scrape"

Optional arguments:
- A focus area, e.g. "/scrape data science" or "/scrape machine learning"
- "broad" to run all search categories, e.g. "/scrape broad"

---

## Execution Steps

### Step 0: Load State

1. Read `job_scraper/seen_jobs.json` (create if missing - start with `{"seen": {}}`)
2. Read `job_search_tracker.csv` to extract already-applied companies+roles
3. Read `search-queries.md` (this directory) for the search strategy

### Step 1: Search

Run searches using the CLI scrapers and/or WebSearch from `search-queries.md`. By default, run the top 3 priority categories. If the user said "broad", run all categories.

If the user specified a focus area (e.g. "machine learning"), prioritize queries from that category.

#### Primary: Use the CLI scrapers

Run the CLI tools for more structured results. Use Bash to invoke them from the `.agents/` directory:

**LinkedIn** (most reliable):
```bash
cd .agents && bun run skills/linkedin-search/cli/src/cli.ts search \
  --query "YOUR_QUERY" --location "YOUR_CITY" --date-posted week --format json
```

**Indeed** (may be blocked by Cloudflare):
```bash
cd .agents && bun run skills/indeed-search/cli/src/cli.ts search \
  --query "YOUR_QUERY" --location "YOUR_CITY" --days 7 --format json
```

**Glassdoor** (strong anti-bot protection — use as fallback or with WebSearch):
```bash
cd .agents && bun run skills/glassdoor-search/cli/src/cli.ts search \
  --query "YOUR_QUERY" --location "YOUR_CITY" --days 7 --format json
```

If a CLI tool returns a `BLOCKED` or `PARSE_ERROR` exit code, fall back to WebSearch for that portal:
```
WebSearch: site:indeed.com "data scientist" "New York" posted:7d
WebSearch: site:glassdoor.com "data engineer" "Seattle" posted:14d
```

#### Fallback: WebSearch

For any portal where the CLI is blocked, or for company career pages:
- Use `WebSearch` with site-specific queries (see `search-queries.md`)
- Target your configured geographic area
- Look for postings from the last 14 days

### Step 2: Fetch & Parse

For results returned by the CLI scrapers:
- The structured JSON output already contains title, company, location, date, URL, and description snippet
- Use `detail` subcommand for full description when needed

For WebSearch results:
- Use `WebFetch` to retrieve the job posting page
- Extract: **job title**, **company**, **location**, **posting date** (or "recent"), **URL**, **key requirements** (brief), **application deadline** (if listed)

In both cases:
- Skip if the URL or company+title combo already exists in `seen_jobs.json`
- Skip if the company+role already appears in `job_search_tracker.csv`

### Step 3: Quick Fit Assessment

For each new job, do a rapid fit check (NOT the full evaluation from `04-job-evaluation.md` - just a quick signal):

- **High match**: Role directly involves your core skills
- **Medium match**: Role is adjacent to your experience
- **Low match**: Role requires significant skills you lack

### Step 4: Deduplicate & Store

1. Add ALL fetched jobs (new and skipped) to `seen_jobs.json` with structure:
```json
{
  "seen": {
    "<url_or_company_title_key>": {
      "title": "...",
      "company": "...",
      "url": "...",
      "first_seen": "YYYY-MM-DD",
      "fit": "high/medium/low",
      "status": "new/skipped/evaluated"
    }
  }
}
```
2. Only present jobs NOT already in the seen list or tracker.

### Step 5: Present Results

Present new jobs in a table sorted by fit (high first):

```
## New Job Matches - YYYY-MM-DD

Found X new positions (Y high, Z medium, W low match).

| # | Fit | Title | Company | Location | Deadline | URL |
|---|-----|-------|---------|----------|----------|-----|
| 1 | High | ... | ... | ... | ... | [Link](...) |

### High-Match Highlights
For each high-match job, add 2-3 bullet points:
- Why it matches your profile
- Key requirements to check
- Any red flags
```

After presenting, ask:
> "Want me to evaluate any of these in detail? Just give me the number(s)."

If the user picks a number, invoke the **job-application-assistant** skill workflow (fit evaluation first, then CV + cover letter if approved).

### Step 6: Update Tracker (Optional)

If the user decides to apply to any job, add a row to `job_search_tracker.csv`.

---

## Important Rules

1. **Never fabricate job postings.** Only present jobs found via actual CLI scraper or WebSearch/WebFetch results.
2. **Respect deduplication.** Always check seen_jobs.json AND job_search_tracker.csv before presenting.
3. **Focus on configured geographic area.** Skip jobs that require relocation or are clearly outside commute range.
4. **Only open positions.** Skip postings with expired deadlines or those marked as closed.
5. **Be efficient with fetching.** Use the structured JSON from CLI scrapers when available; fall back to WebFetch for full descriptions when needed.
6. **Handle blocks gracefully.** If a CLI scraper is blocked (BLOCKED/PARSE_ERROR exit code), immediately fall back to WebSearch for that portal — don't retry.
7. **Parallel searches.** Use the Agent tool or parallel calls to speed up the search phase.
