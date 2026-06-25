export const BASE_URL = "https://www.glassdoor.com"

export const USER_AGENT =
  "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

export function writeError(error: string, code: string): void {
  process.stderr.write(JSON.stringify({ error, code }) + "\n")
}

export async function htmlFetch(url: string): Promise<string> {
  const maxRetries = 6
  let delay = 500
  for (let attempt = 0; attempt <= maxRetries; attempt++) {
    const response = await fetch(url, {
      headers: {
        "User-Agent": USER_AGENT,
        Accept: "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        Referer: "https://www.glassdoor.com/",
        "Cache-Control": "no-cache",
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
        "Access denied (403) — Glassdoor is blocking this request (Cloudflare). Try again later or use WebSearch instead."
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

export function isCloudflareChallenge(html: string): boolean {
  return (
    html.includes("Just a moment") ||
    html.includes("Checking if the site connection is secure") ||
    html.includes("cf-browser-verification") ||
    html.includes("challenge-platform") ||
    html.includes("_cf_chl_")
  )
}

// ─── __NEXT_DATA__ extraction ────────────────────────────────────────────────

interface GlassdoorJobListing {
  jobview?: {
    header?: {
      jobTitleText?: string
      normalizedJobTitle?: string
      employerNameFromSearch?: string
      locationName?: string
      easyApply?: boolean
      indeedJobAttribute?: { jobTypes?: string[] }
    }
    job?: {
      listingId?: number
      description?: string
      discoveryDate?: string
      jobLink?: string
      descriptionFragments?: string[]
    }
    overview?: {
      employer?: {
        name?: string
        website?: string
      }
    }
  }
}

interface GlassdoorNextData {
  props?: {
    pageProps?: {
      jobListings?: {
        jobListings?: GlassdoorJobListing[]
        totalJobsCount?: number
      }
      // Glassdoor also uses Apollo cache sometimes
      apolloCache?: Record<string, unknown>
    }
  }
}

function listingToJobCard(listing: GlassdoorJobListing): JobCard | null {
  const header = listing.jobview?.header
  const job = listing.jobview?.job
  const overview = listing.jobview?.overview

  const id = String(job?.listingId ?? "")
  if (!id) return null

  const title = header?.jobTitleText || header?.normalizedJobTitle || ""
  if (!title) return null

  const company = header?.employerNameFromSearch || overview?.employer?.name || null
  const companyUrl = overview?.employer?.website
    ? `https://${overview.employer.website.replace(/^https?:\/\//, "")}`
    : null
  const location = header?.locationName || null

  // discoveryDate is like "2026-06-01 00:00:00.0"
  let date: string | null = null
  if (job?.discoveryDate) {
    const d = job.discoveryDate.split(" ")[0]
    if (/^\d{4}-\d{2}-\d{2}$/.test(d)) date = d
  }

  // Build canonical Glassdoor job URL
  const url = job?.jobLink
    ? job.jobLink.startsWith("http")
      ? job.jobLink
      : `${BASE_URL}${job.jobLink}`
    : `${BASE_URL}/job-listing/jl${id}`

  const description = job?.description
    ? stripTags(job.description).substring(0, 300)
    : job?.descriptionFragments?.join(" ").substring(0, 300) || null

  return { id, title, company, companyUrl, location, date, url, description }
}

/**
 * Extract job listings from __NEXT_DATA__ embedded JSON on Glassdoor search pages.
 */
export function parseNextData(html: string, total?: { value: number }): JobCard[] {
  const match = html.match(/<script id="__NEXT_DATA__" type="application\/json">([\s\S]*?)<\/script>/)
  if (!match) return []

  let data: GlassdoorNextData
  try {
    data = JSON.parse(match[1]) as GlassdoorNextData
  } catch {
    return []
  }

  const pageProps = data?.props?.pageProps
  const jobListings = pageProps?.jobListings

  if (jobListings?.jobListings) {
    if (total) total.value = jobListings.totalJobsCount ?? 0
    return jobListings.jobListings
      .map(listingToJobCard)
      .filter((c): c is JobCard => c !== null)
  }

  // Try Apollo cache path
  if (pageProps?.apolloCache) {
    return parseFromApolloCache(pageProps.apolloCache, total)
  }

  return []
}

function parseFromApolloCache(cache: Record<string, unknown>, total?: { value: number }): JobCard[] {
  // Apollo cache keys for job listings look like:
  // jobListings({"keyword":"...","numPerPage":30,...})
  for (const [key, value] of Object.entries(cache)) {
    if (key.startsWith("jobListings(") && typeof value === "object" && value !== null) {
      const v = value as { jobListings?: GlassdoorJobListing[]; totalJobsCount?: number }
      if (Array.isArray(v.jobListings)) {
        if (total) total.value = v.totalJobsCount ?? 0
        return v.jobListings.map(listingToJobCard).filter((c): c is JobCard => c !== null)
      }
    }
  }
  return []
}

/**
 * Parse job detail from a Glassdoor job detail page.
 * Tries __NEXT_DATA__ first, then JSON-LD, then HTML fallback.
 */
export function parseJobDetail(html: string, id: string, url: string): JobDetail {
  // Try __NEXT_DATA__ for the detail page
  const nextDataMatch = html.match(
    /<script id="__NEXT_DATA__" type="application\/json">([\s\S]*?)<\/script>/
  )
  if (nextDataMatch) {
    try {
      const data = JSON.parse(nextDataMatch[1]) as GlassdoorNextData
      const listing = data?.props?.pageProps?.jobListings?.jobListings?.[0]
      if (listing) {
        const card = listingToJobCard(listing)
        if (card) {
          return { ...card, employmentType: null, deadline: null, applyUrl: url }
        }
      }
    } catch {
      // fall through
    }
  }

  // Try JSON-LD
  const ldMatches = html.matchAll(/<script[^>]+type="application\/ld\+json"[^>]*>([\s\S]*?)<\/script>/gi)
  for (const ldMatch of ldMatches) {
    try {
      const ld = JSON.parse(ldMatch[1]) as {
        "@type"?: string
        title?: string
        hiringOrganization?: { name?: string; sameAs?: string }
        jobLocation?: { address?: { addressLocality?: string; addressRegion?: string } }
        datePosted?: string
        validThrough?: string
        employmentType?: string | string[]
        description?: string
      }
      if (ld["@type"] === "JobPosting") {
        const addr = ld.jobLocation?.address
        const location = addr
          ? [addr.addressLocality, addr.addressRegion].filter(Boolean).join(", ") || null
          : null
        const empType = Array.isArray(ld.employmentType)
          ? ld.employmentType.join(", ")
          : ld.employmentType || null
        return {
          id,
          title: ld.title || "",
          company: ld.hiringOrganization?.name || null,
          companyUrl: ld.hiringOrganization?.sameAs || null,
          location,
          date: ld.datePosted || null,
          url,
          description: ld.description ? stripTags(ld.description) : null,
          employmentType: empType,
          deadline: ld.validThrough || null,
          applyUrl: url,
        }
      }
    } catch {
      // continue
    }
  }

  // HTML fallback
  const titleMatch = html.match(
    /<div[^>]*class="[^"]*css-[a-z0-9]+-title[^"]*"[^>]*>([\s\S]*?)<\/div>/i
  )
  const title = titleMatch ? stripTags(titleMatch[1]) : ""

  const companyMatch = html.match(
    /<span[^>]*class="[^"]*EmployerProfile_employerName[^"]*"[^>]*>([\s\S]*?)<\/span>/i
  )
  const company = companyMatch ? stripTags(companyMatch[1]) || null : null

  const locMatch = html.match(
    /<div[^>]*class="[^"]*SalaryEstimate_location[^"]*"[^>]*>([\s\S]*?)<\/div>/i
  )
  const location = locMatch ? stripTags(locMatch[1]) || null : null

  return {
    id,
    title,
    company,
    companyUrl: null,
    location,
    date: null,
    url,
    description: null,
    employmentType: null,
    deadline: null,
    applyUrl: url,
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
