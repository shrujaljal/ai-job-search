export const BASE_URL = "https://www.linkedin.com"

export const USER_AGENT =
  "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

export function writeError(error: string, code: string): void {
  process.stderr.write(JSON.stringify({ error, code }) + "\n")
}

export async function htmlFetch(
  path: string,
  params?: Record<string, string>
): Promise<string> {
  let url = `${BASE_URL}${path}`
  if (params && Object.keys(params).length > 0) {
    url += `?${new URLSearchParams(params).toString()}`
  }

  const maxRetries = 6
  let delay = 500
  for (let attempt = 0; attempt <= maxRetries; attempt++) {
    const response = await fetch(url, {
      headers: {
        "User-Agent": USER_AGENT,
        Accept: "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        Referer: "https://www.linkedin.com/jobs/search/",
      },
    })
    if (response.status === 429 || response.status >= 500) {
      if (attempt === maxRetries) {
        throw new Error(`Request failed: ${response.status} ${response.statusText}`)
      }
      const jitter = Math.floor(Math.random() * 500)
      await new Promise((resolve) => setTimeout(resolve, delay + jitter))
      delay = Math.min(delay * 2, 5000)
      continue
    }
    if (response.status === 403) {
      throw new Error(
        "Access denied (403) — LinkedIn is blocking this request. Try again later or use a different IP."
      )
    }
    if (!response.ok) {
      throw new Error(`Request failed: ${response.status} ${response.statusText}`)
    }
    return response.text()
  }
  throw new Error("Request failed after max retries")
}

export interface JobCard {
  id: string
  title: string
  company: string | null
  companyUrl: string | null
  location: string | null
  date: string | null
  url: string
  description: string | null
}

export interface JobDetail extends JobCard {
  employmentType: string | null
  deadline: string | null
  applyUrl: string | null
}

export function stripTags(html: string): string {
  return html
    .replace(/<[^>]*>/g, " ")
    .replace(/&amp;/g, "&")
    .replace(/&lt;/g, "<")
    .replace(/&gt;/g, ">")
    .replace(/&quot;/g, '"')
    .replace(/&#39;/g, "'")
    .replace(/&apos;/g, "'")
    .replace(/&nbsp;/g, " ")
    .replace(/&#(\d+);/g, (_, code) => String.fromCharCode(parseInt(code, 10)))
    .replace(/\s+/g, " ")
    .trim()
}

function truncate(s: string, max: number): string {
  return s.length <= max ? s : s.substring(0, max - 1) + "…"
}

/**
 * Parse job cards from the HTML fragment returned by LinkedIn's guest search API.
 * Each card is a <li> containing a div with data-entity-urn="urn:li:jobPosting:{id}".
 */
export function parseJobCards(html: string): JobCard[] {
  const results: JobCard[] = []

  // Split on each job posting URN to get card sections
  const urnPattern = /data-entity-urn="urn:li:jobPosting:(\d+)"([\s\S]*?)(?=data-entity-urn="urn:li:jobPosting:|$)/g

  let match: RegExpExecArray | null
  while ((match = urnPattern.exec(html)) !== null) {
    const id = match[1]
    const cardHtml = match[2]

    // Title from h3.base-search-card__title
    const titleMatch = cardHtml.match(
      /<h3[^>]*class="[^"]*base-search-card__title[^"]*"[^>]*>([\s\S]*?)<\/h3>/i
    )
    const title = titleMatch ? stripTags(titleMatch[1]) : ""
    if (!title) continue

    // Canonical job URL — strip query params so IDs are stable
    const urlMatch = cardHtml.match(
      /href="(https:\/\/www\.linkedin\.com\/jobs\/view\/[^"?]+)/
    )
    const url = urlMatch ? urlMatch[1] : `${BASE_URL}/jobs/view/${id}`

    // Company from h4.base-search-card__subtitle > a
    const subtitleMatch = cardHtml.match(
      /<h4[^>]*class="[^"]*base-search-card__subtitle[^"]*"[^>]*>([\s\S]*?)<\/h4>/i
    )
    let company: string | null = null
    let companyUrl: string | null = null
    if (subtitleMatch) {
      const linkMatch = subtitleMatch[1].match(
        /<a[^>]+href="([^"]+)"[^>]*>([\s\S]*?)<\/a>/i
      )
      if (linkMatch) {
        company = stripTags(linkMatch[2]) || null
        companyUrl = linkMatch[1].split("?")[0] || null
      }
    }

    // Location from span.job-search-card__location
    const locMatch = cardHtml.match(
      /<span[^>]*class="[^"]*job-search-card__location[^"]*"[^>]*>([\s\S]*?)<\/span>/i
    )
    const location = locMatch ? stripTags(locMatch[1]) || null : null

    // Date from <time datetime="...">
    const dateMatch = cardHtml.match(/<time[^>]+datetime="([^"]+)"/)
    const date = dateMatch ? dateMatch[1] : null

    results.push({ id, title, company, companyUrl, location, date, url, description: null })
  }

  return results
}

/**
 * Parse full job detail from the HTML returned by LinkedIn's guest jobPosting API.
 */
export function parseJobDetail(html: string, id: string): JobDetail {
  const url = `${BASE_URL}/jobs/view/${id}`

  // Title — h1 or h2 with top-card-layout__title class
  const titleMatch = html.match(
    /<h[12][^>]*class="[^"]*top-card-layout__title[^"]*"[^>]*>([\s\S]*?)<\/h[12]>/i
  )
  const title = titleMatch ? stripTags(titleMatch[1]) : ""

  // Company link
  const companyMatch = html.match(
    /<a[^>]*class="[^"]*topcard__org-name-link[^"]*"[^>]+href="([^"]+)"[^>]*>([\s\S]*?)<\/a>/i
  )
  const company = companyMatch ? stripTags(companyMatch[2]) || null : null
  const companyUrl = companyMatch ? companyMatch[1].split("?")[0] : null

  // Location — first topcard__flavor--bullet span
  const locMatch = html.match(
    /<span[^>]*class="[^"]*topcard__flavor--bullet[^"]*"[^>]*>([\s\S]*?)<\/span>/i
  )
  const location = locMatch ? stripTags(locMatch[1]) || null : null

  // Employment type from criteria list
  const empTypeMatch = html.match(
    /Employment type[\s\S]{0,200}?<span[^>]*class="[^"]*description__job-criteria-text[^"]*"[^>]*>\s*([\w\s-]+?)\s*<\/span>/i
  )
  const employmentType = empTypeMatch ? empTypeMatch[1].trim() || null : null

  // Description from show-more-less-html__markup
  const descMatch = html.match(
    /<div[^>]*class="[^"]*show-more-less-html__markup[^"]*"[^>]*>([\s\S]*?)(?=<\/div>\s*(?:<button|<\/section))/i
  )
  const description = descMatch ? stripTags(descMatch[1]) || null : null

  // Apply URL
  const applyMatch = html.match(
    /<a[^>]+href="(https?:\/\/[^"]+)"[^>]*>\s*(?:<span[^>]*>)?\s*(?:Easy\s+)?Apply\b/i
  )
  const applyUrl = applyMatch ? applyMatch[1] : null

  return {
    id,
    title,
    company,
    companyUrl,
    location,
    date: null,
    url,
    description,
    employmentType,
    deadline: null,
    applyUrl,
  }
}

export function formatTable(cards: JobCard[]): string {
  if (cards.length === 0) return "(no results)"
  const headers = ["#", "Title", "Company", "Location", "Date"]
  const MAXW = [4, 48, 28, 24, 10]
  const rows = cards.map((c, i) => [
    String(i + 1),
    truncate(c.title || "", MAXW[1]),
    truncate(c.company || "—", MAXW[2]),
    truncate(c.location || "—", MAXW[3]),
    c.date || "—",
  ])
  const widths = headers.map((h, i) =>
    Math.min(MAXW[i], Math.max(h.length, ...rows.map((r) => r[i].length)))
  )
  const sep = "+" + widths.map((w) => "-".repeat(w + 2)).join("+") + "+"
  const fmtRow = (row: string[]) =>
    "| " + row.map((c, i) => c.padEnd(widths[i])).join(" | ") + " |"
  return [sep, fmtRow(headers), sep, ...rows.map(fmtRow), sep].join("\n")
}
