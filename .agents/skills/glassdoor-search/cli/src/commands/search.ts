import { defineCommand, option } from "@bunli/core"
import { z } from "zod"
import {
  BASE_URL,
  writeError,
  htmlFetch,
  parseNextData,
  isCloudflareChallenge,
  formatTable,
} from "../helpers.js"

// Glassdoor fromAge values
const DAYS_MAP: Record<string, string> = {
  "1": "1",
  "3": "3",
  "7": "7",
  "14": "14",
  "30": "30",
}

export const search = defineCommand({
  name: "search",
  description: "Search Glassdoor job listings",
  options: {
    query: option(z.string().optional(), {
      short: "q",
      description: "Search keywords (job title, skill, company)",
    }),
    location: option(z.string().optional(), {
      short: "l",
      description: "Job location (city, state) — leave blank for 'Anywhere'",
    }),
    days: option(z.enum(["1", "3", "7", "14", "30", "any"]).default("any"), {
      description: "Max posting age in days: 1, 3, 7, 14, 30, any (default)",
    }),
    remote: option(z.boolean().default(false), {
      argumentKind: "flag",
      description: "Remote jobs only",
    }),
    page: option(z.coerce.number().int().min(1).default(1), {
      description: "Page number (30 results per page on Glassdoor)",
    }),
    limit: option(z.coerce.number().int().min(1).optional(), {
      description: "Cap total results returned by the CLI",
    }),
    format: option(z.enum(["json", "table", "plain"]).default("json"), {
      description: "Output format: json (default), table, plain",
    }),
  },
  handler: async ({ flags }) => {
    const { query, location, days, remote, page, limit, format } = flags

    if (!query && !location && !remote) {
      writeError("--query or --location is required", "MISSING_REQUIRED")
      process.exit(1)
    }

    // Glassdoor job search URL
    const params = new URLSearchParams()
    params.set("suggestCount", "0")
    params.set("suggestChosen", "false")
    params.set("clickSource", "searchBtn")
    if (query) {
      params.set("typedKeyword", query)
      params.set("sc.keyword", query)
    }
    if (location) params.set("locT", "S") // S = city/metro
    if (remote) {
      params.set("remoteWorkType", "1")
    }
    if (days !== "any" && DAYS_MAP[days]) params.set("fromAge", DAYS_MAP[days])
    if (page > 1) params.set("p", String(page))

    const url = `${BASE_URL}/Job/jobs.htm?${params.toString()}`

    let html: string
    try {
      html = await htmlFetch(url)
    } catch (err) {
      writeError(String(err), "API_ERROR")
      process.exit(1)
    }

    if (isCloudflareChallenge(html)) {
      writeError(
        "Glassdoor returned a Cloudflare challenge page. Scraping is blocked. Use WebSearch with site:glassdoor.com instead.",
        "BLOCKED"
      )
      process.exit(1)
    }

    const totalRef = { value: 0 }
    let results = parseNextData(html, totalRef)

    if (results.length === 0) {
      writeError(
        "No job data found in page response. Glassdoor may have changed their page structure or is blocking requests. Try WebSearch with site:glassdoor.com instead.",
        "PARSE_ERROR"
      )
      process.exit(1)
    }

    if (limit !== undefined) results = results.slice(0, limit)

    if (format === "json") {
      process.stdout.write(
        JSON.stringify(
          {
            meta: {
              page,
              perPage: 30,
              total: totalRef.value || null,
              query: query ?? null,
              location: location ?? null,
            },
            results,
          },
          null,
          2
        ) + "\n"
      )
    } else if (format === "table") {
      const label = [query && `"${query}"`, location && `in ${location}`]
        .filter(Boolean)
        .join(" ")
      process.stdout.write(`Glassdoor Jobs${label ? " — " + label : ""} (page ${page}):\n`)
      process.stdout.write(formatTable(results) + "\n")
    } else {
      // plain
      for (const job of results) {
        process.stdout.write(`${job.title}\n`)
        if (job.company) process.stdout.write(`  Company:  ${job.company}\n`)
        if (job.location) process.stdout.write(`  Location: ${job.location}\n`)
        if (job.date) process.stdout.write(`  Posted:   ${job.date}\n`)
        if (job.description) process.stdout.write(`  Snippet:  ${job.description.substring(0, 120)}\n`)
        process.stdout.write(`  URL:      ${job.url}\n`)
        process.stdout.write("\n")
      }
    }
  },
})
