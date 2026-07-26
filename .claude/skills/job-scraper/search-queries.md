# Search Queries for Job Scraper

The automated board search uses LinkedIn only. Target-company career sites are
searched separately through saved URLs and supported ATS readers. Do not invoke
Indeed or Glassdoor.

## LinkedIn Command

Run from the project root:

```bash
cd .agents && bun run skills/linkedin-search/cli/src/cli.ts search \
  --query "[ROLE_OR_KEYWORDS]" \
  --location "[LOCATION]" \
  --date-posted week \
  --format json
```

Use `--remote` for fully remote searches and `--job-type fulltime` when needed.

## Priority Queries

### Strategy and Operations

- Strategy & Operations Analyst
- Business Operations Analyst
- Strategy Analyst
- Corporate Strategy Analyst
- Operational Excellence Analyst
- Chief of Staff Analyst

### GTM and Revenue

- GTM Strategy Analyst
- Revenue Operations Analyst
- Sales Strategy Analyst
- Commercial Strategy Analyst
- Growth Operations Analyst

### Marketing

- Marketing Strategy Analyst
- Marketing Operations Analyst
- Product Marketing
- Growth Strategy Analyst
- Customer Insights Analyst

### Data and Business Analytics

- Business Analyst
- Data Analyst
- Business Intelligence Analyst
- Analytics & Insights Analyst
- Operations Analytics

### Program and Transformation

- Program Manager
- Business Program Manager
- Transformation Analyst
- Implementation Analyst
- Process Improvement Analyst

## Geography

Default to United States roles with remote-friendly options. For the current
target-company catalog, prioritize the San Francisco Bay Area and broader
California when the user has not selected another scope.

## Target-Company Career Pages

When a career URL is saved, search it through the app. Supported ATS formats:

- Greenhouse
- Lever
- SmartRecruiters

For an unsupported site, use a company-specific query:

```text
site:company-domain.com/careers ("strategy" OR "operations" OR "analyst")
site:company-domain.com/jobs ("business analyst" OR "data analyst")
```

## Filtering

- Include closely related functional titles.
- Exclude Director, Head, VP, Principal, Chief, and clearly senior roles.
- Prefer jobs posted within the selected recency window.
- Preserve all seen jobs for deduplication, but present a job as new only once.
