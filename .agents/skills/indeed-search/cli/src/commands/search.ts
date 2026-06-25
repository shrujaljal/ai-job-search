import { defineCommand, option } from "@bunli/core"
import { z } from "zod"
import {
  BASE_URL,
  writeError,
  htmlFetch,
  parseJobCards,
  isCloudflareChallenge,
  formatTable,
} from "../helpers.js"

// Indeed fromage (days) values
const DAYS_MAP: Record<string, string> = {
  "1": "1",
  "3": "3",
  "7": "7",
  "14": "14",
}

// Indeed job type parameter values
const JOB_TYPE_MAP: Record<string, string> = {
  fulltime: "fulltime",
  parttime: "parttime",
  contract: "contract",
  internship: "internship",
  temporary: "temporary",
}

export const search = defineCommand({
  name: "search",
  description: "Search Indeed job listings",
  options: {
    query: option(z.string().optional(), {
      short: "q",
      description: "Search keywords (job title, skill, company)",
    }),
    location: option(z.string().optional(), {
      short: "l",
      description: "Job location (city, state) or 'remote'",
    }),
    days: option(
      z
        .enum(["1", "3", "7", "14", "any"])
        .default("any"),
      {
        description: "Max posting age in days: 1, 3, 7, 14, any (default)",
      }
    ),
    remote: option(z.boolean().default(false), {
      argumentKind: "flag",
      description: "Remote jobs only (adds 'remote' to location)",
    }),
    jobType: option(
      z.enum(["fulltime", "parttime", "contract", "internship", "temporary"]).optional(),
      { description: "Job type filter" }
    ),
    radius: option(z.coerce.number().int().optional(), {
      description: "Search radius in miles from location (default: Indeed default ~25mi)",
    }),
    page: option(z.coerce.number().int().min(1).default(1), {
      description: "Page number (10 results per page on Indeed)",
    }),
    limit: option(z.coerce.number().int().min(1).optional(), {
      description: "Cap total results returned by the CLI",
    }),
    format: option(z.enum(["json", "table", "plain"]).default("json"), {
      description: "Output format: json (default), table, plain",
    }),
  },
  handler: async ({ flags }) => {
    const { query, location, days, remote, jobType, radius, page, limit, format } = flags

    if (!query && !location && !remote) {
      writeError("--query, --location, or --remote is required", "MISSING_REQUIRED")
      process.exit(1)
    }

    // Indeed uses `start` for pagination (0-indexed, 10 per page)
    const start = (page - 1) * 10
    const params = new URLSearchParams()
    if (query) params.set("q", query)

    const loc = remote ? "remote" : location || ""
    if (loc) params.set("l", loc)

    if (days !== "any" && DAYS_MAP[days]) params.set("fromage", DAYS_MAP[days])
    if (jobType && JOB_TYPE_MAP[jobType]) params.set("jt", JOB_TYPE_MAP[jobType])
    if (radius !== undefined) params.set("radius", String(radius))
    if (start > 0) params.set("start", String(start))
    params.set("sort", "date")

    const url = `${BASE_URL}/jobs?${params.toString()}`

    let html: string
    try {
      html = await htmlFetch(url)
    } catch (err) {
      writeError(String(err), "API_ERROR")
      process.exit(1)
    }

    if (isCloudflareChallenge(html)) {
      writeError(
        "Indeed returned a Cloudflare challenge page. Scraping is blocked. Try again later or use WebSearch instead.",
        "BLOCKED"
      )
      process.exit(1)
    }

    const totalRef = { value: 0 }
    let results = parseJobCards(html, totalRef)
    if (limit !== undefined) results = results.slice(0, limit)

    if (format === "json") {
      process.stdout.write(
        JSON.stringify(
          {
            meta: {
              page,
              perPage: 10,
              total: totalRef.value || null,
              query: query ?? null,
              location: loc || null,
            },
            results,
          },
          null,
          2
        ) + "\n"
      )
    } else if (format === "table") {
      const label = [query && `"${query}"`, loc && `in ${loc}`].filter(Boolean).join(" ")
      process.stdout.write(`Indeed Jobs${label ? " — " + label : ""} (page ${page}):\n`)
      process.stdout.write(formatTable(results) + "\n")
    } else {
      // plain
      if (results.length === 0) {
        process.stdout.write("No results found.\n")
        return
      }
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
