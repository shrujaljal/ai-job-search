# Job Scraper

**name:** job-scraper
**description:** Searches LinkedIn and target-company career sites for new US
positions, deduplicates them, and presents profile-aligned matches. Triggers on:
job scrape, find jobs, search jobs, new jobs, job search, scrape jobs, /scrape
**allowed-tools:** Read, Write, Edit, Glob, Grep, WebFetch, WebSearch, Bash,
Agent, AskUserQuestion

---

## Invocation

Examples:

- "Find new jobs"
- "Scrape for jobs"
- "/scrape"
- "/scrape strategy operations"
- "/scrape broad"

## Execution

### 1. Load State

1. Read `job_scraper/seen_jobs.json`, creating `{"seen": {}}` if missing.
2. Read `job_search_tracker.csv` for jobs already being pursued.
3. Read `search-queries.md` in this directory.

### 2. Search LinkedIn

Use the structured LinkedIn CLI from the project root:

```bash
cd .agents && bun run skills/linkedin-search/cli/src/cli.ts search \
  --query "YOUR_QUERY" --location "YOUR_CITY" \
  --date-posted week --format json
```

Run the top three query categories by default. Run every category for a broad
search. Prioritize the requested focus area when one is supplied.

### 3. Search Target-Company Career Sites

Use saved company career URLs and the app's supported Greenhouse, Lever, and
SmartRecruiters readers. For other career pages, use company-specific WebSearch
queries from `search-queries.md`. Do not invoke Indeed or Glassdoor.

### 4. Fetch and Assess

- Use the LinkedIn `detail` command when a full job description is needed.
- Extract title, company, location, date, URL, requirements, and deadline.
- Skip jobs already present by URL or normalized company and title.
- Skip jobs already represented in the application tracker.
- Mark each new job as high, medium, or low match.

### 5. Persist and Present

Store every fetched job in `seen_jobs.json` with first-seen date, fit, URL, and
status. Present only new jobs in a table sorted by fit, followed by concise
high-match notes.

## Rules

1. Never fabricate postings.
2. Respect seen-job and application-tracker deduplication.
3. Apply the configured geography and recency filters.
4. Include only open roles.
5. Do not repeatedly retry a blocked source.
6. Use target-company career pages when LinkedIn coverage is incomplete.
