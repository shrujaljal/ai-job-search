export const BASE_URL = "https://www.indeed.com"

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
        Referer: "https://www.indeed.com/",
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
        "Access denied (403) — Indeed is blocking this request (likely Cloudflare). Try again later."
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
 * Check if the page is a Cloudflare challenge page.
 */
export function isCloudflareChallenge(html: string): boolean {
  return (
    html.includes("Just a moment") ||
    html.includes("Checking if the site connection is secure") ||
    html.includes("cf-browser-verification") ||
    html.includes("challenge-platform")
  )
}

/**
 * Extract job tiles from the window.mosaic.providerData JSON embedded in the page.
 * Indeed embeds structured job data in a <script> tag.
 */
function extractMosaicTiles(html: string): MosaicTile[] {
  // Look for the mosaic-provider-jobcards data block
  const scriptMatch = html.match(
    /window\.mosaic\.providerData\["mosaic-provider-jobcards"\]\s*=\s*(\{)/
  )
  if (!scriptMatch || scriptMatch.index === undefined) return []

  // Walk forward from the opening brace to find the matching close brace
  const start = scriptMatch.index + scriptMatch[0].length - 1
  let depth = 0
  let i = start
  while (i < html.length) {
    if (html[i] === "{") depth++
    else if (html[i] === "}") {
      depth--
      if (depth === 0) break
    }
    i++
  }

  const jsonStr = html.substring(start, i + 1)
  try {
    const data = JSON.parse(jsonStr) as {
      metaData?: {
        mosaicProviderJobCardsModel?: {
          tiles?: MosaicTile[]
          queryResultSize?: number
        }
      }
    }
    return data?.metaData?.mosaicProviderJobCardsModel?.tiles ?? []
  } catch {
    return []
  }
}

/**
 * Extract total result count from mosaic data.
 */
export function extractMosaicTotal(html: string): number {
  const scriptMatch = html.match(
    /window\.mosaic\.providerData\["mosaic-provider-jobcards"\]\s*=\s*(\{)/
  )
  if (!scriptMatch || scriptMatch.index === undefined) return 0
  const start = scriptMatch.index + scriptMatch[0].length - 1
  let depth = 0
  let i = start
  while (i < html.length) {
    if (html[i] === "{") depth++
    else if (html[i] === "}") {
      depth--
      if (depth === 0) break
    }
    i++
  }
  try {
    const data = JSON.parse(html.substring(start, i + 1)) as {
      metaData?: {
        mosaicProviderJobCardsModel?: { queryResultSize?: number }
      }
    }
    return data?.metaData?.mosaicProviderJobCardsModel?.queryResultSize ?? 0
  } catch {
    return 0
  }
}

interface MosaicTile {
  jobkey?: string
  displayTitle?: string
  company?: string
  formattedLocation?: string
  formattedRelativeTime?: string
  pubDate?: number
  snippet?: string
  link?: string
  jobTypes?: string[]
  companyBrandingAttributes?: { logoUrl?: string }
}

function mosaicTileToJobCard(tile: MosaicTile): JobCard | null {
  const id = tile.jobkey
  if (!id) return null
  const title = tile.displayTitle || ""
  if (!title) return null

  const url = `${BASE_URL}/viewjob?jk=${id}`
  const company = tile.company || null
  const location = tile.formattedLocation || null

  // Indeed pubDate is Unix ms timestamp
  let date: string | null = null
  if (tile.pubDate) {
    try {
      date = new Date(tile.pubDate).toISOString().split("T")[0]
    } catch {
      date = null
    }
  }

  const description = tile.snippet ? stripTags(tile.snippet).substring(0, 300) : null

  return { id, title, company, companyUrl: null, location, date, url, description }
}

/**
 * Parse job cards from Indeed's HTML using the embedded mosaic JSON data.
 * Falls back to HTML parsing if the JSON is not found.
 */
export function parseJobCards(html: string, total?: { value: number }): JobCard[] {
  // Primary: extract from embedded JSON
  const tiles = extractMosaicTiles(html)
  if (tiles.length > 0) {
    if (total) total.value = extractMosaicTotal(html)
    return tiles.map(mosaicTileToJobCard).filter((c): c is JobCard => c !== null)
  }

  // Fallback: parse HTML job cards (less reliable, structure changes frequently)
  return parseJobCardsFromHtml(html)
}

function parseJobCardsFromHtml(html: string): JobCard[] {
  const results: JobCard[] = []

  // Each job card has a data-jk attribute with the job key
  const cardPattern = /data-jk="([a-f0-9]+)"([\s\S]*?)(?=data-jk="|<\/ul>|$)/g

  let match: RegExpExecArray | null
  while ((match = cardPattern.exec(html)) !== null) {
    const id = match[1]
    const cardHtml = match[2]

    // Title from span with id="jobTitle-{id}" or similar
    const titleMatch =
      cardHtml.match(new RegExp(`<span[^>]+id="jobTitle-${id}"[^>]*>([\\s\\S]*?)<\\/span>`, "i")) ||
      cardHtml.match(/<h2[^>]*class="[^"]*jobTitle[^"]*"[^>]*>[\s\S]*?<span[^>]*>([\s\S]*?)<\/span>/i)
    const title = titleMatch ? stripTags(titleMatch[1]) : ""
    if (!title) continue

    const url = `${BASE_URL}/viewjob?jk=${id}`

    const companyMatch = cardHtml.match(
      /data-testid="company-name"[^>]*>([\s\S]*?)<\/(?:span|div|a)>/i
    )
    const company = companyMatch ? stripTags(companyMatch[1]) || null : null

    const locMatch = cardHtml.match(
      /data-testid="text-location"[^>]*>([\s\S]*?)<\/(?:div|span)>/i
    )
    const location = locMatch ? stripTags(locMatch[1]) || null : null

    const dateMatch = cardHtml.match(/class="[^"]*date[^"]*"[^>]*>([\s\S]*?)<\/(?:span|div)>/i)
    const date = dateMatch ? stripTags(dateMatch[1]) || null : null

    results.push({ id, title, company, companyUrl: null, location, date, url, description: null })
  }

  return results
}

/**
 * Parse a job detail page from Indeed.
 * Prefers JSON-LD (schema.org JobPosting) over HTML parsing.
 */
export function parseJobDetail(html: string, id: string): JobDetail {
  const url = `${BASE_URL}/viewjob?jk=${id}`

  // Try JSON-LD first
  const ldMatch = html.match(/<script[^>]+type="application\/ld\+json"[^>]*>([\s\S]*?)<\/script>/gi)
  if (ldMatch) {
    for (const block of ldMatch) {
      const content = block.replace(/<script[^>]*>/, "").replace(/<\/script>/, "")
      try {
        const ld = JSON.parse(content) as {
          "@type"?: string
          title?: string
          hiringOrganization?: { name?: string; sameAs?: string }
          jobLocation?: { address?: { addressLocality?: string; addressRegion?: string } }
          datePosted?: string
          validThrough?: string
          employmentType?: string | string[]
          description?: string
          url?: string
        }
        if (ld["@type"] === "JobPosting") {
          const title = ld.title || ""
          const company = ld.hiringOrganization?.name || null
          const companyUrl = ld.hiringOrganization?.sameAs || null
          const addr = ld.jobLocation?.address
          const location = addr
            ? [addr.addressLocality, addr.addressRegion].filter(Boolean).join(", ") || null
            : null
          const date = ld.datePosted || null
          const deadline = ld.validThrough || null
          const empType = Array.isArray(ld.employmentType)
            ? ld.employmentType.join(", ")
            : ld.employmentType || null
          const description = ld.description ? stripTags(ld.description) : null

          return {
            id,
            title,
            company,
            companyUrl,
            location,
            date,
            url: ld.url || url,
            description,
            employmentType: empType,
            deadline,
            applyUrl: url,
          }
        }
      } catch {
        // continue to next block
      }
    }
  }

  // HTML fallback
  const titleMatch = html.match(/<h1[^>]*class="[^"]*jobsearch-JobInfoHeader-title[^"]*"[^>]*>([\s\S]*?)<\/h1>/i)
  const title = titleMatch ? stripTags(titleMatch[1]) : ""

  const companyMatch = html.match(/data-testid="inlineHeader-companyName"[^>]*>([\s\S]*?)<\/(?:span|div|a)>/i)
  const company = companyMatch ? stripTags(companyMatch[1]) || null : null

  const locMatch = html.match(/data-testid="inlineHeader-companyLocation"[^>]*>([\s\S]*?)<\/(?:span|div)>/i)
  const location = locMatch ? stripTags(locMatch[1]) || null : null

  const descMatch = html.match(/<div[^>]+id="jobDescriptionText"[^>]*>([\s\S]*?)<\/div>/i)
  const description = descMatch ? stripTags(descMatch[1]) || null : null

  return {
    id,
    title,
    company,
    companyUrl: null,
    location,
    date: null,
    url,
    description,
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
