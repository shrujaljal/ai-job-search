import { defineCommand, option } from "@bunli/core"
import { z } from "zod"
import { writeError, htmlFetch, parseJobCards, formatTable } from "../helpers.js"

// LinkedIn f_TPR (time posted range) parameter values
const DATE_POSTED_PARAM: Record<string, string> = {
  day: "r86400",
  week: "r604800",
  month: "r2592000",
}

// LinkedIn f_JT (job type) parameter values
const JOB_TYPE_PARAM: Record<string, string> = {
  fulltime: "F",
  parttime: "P",
  contract: "C",
  temporary: "T",
  internship: "I",
  other: "O",
}

export const search = defineCommand({
  name: "search",
  description: "Search LinkedIn job listings",
  options: {
    query: option(z.string().optional(), {
      short: "q",
      description: "Search keywords (job title, skill, company)",
    }),
    location: option(z.string().optional(), {
      short: "l",
      description: "Job location (city, state, country) or 'Remote'",
    }),
    datePosted: option(z.enum(["day", "week", "month", "any"]).default("any"), {
      description: "Filter by posting date: day (24h), week, month, any (default)",
    }),
    remote: option(z.boolean().default(false), {
      argumentKind: "flag",
      description: "Remote jobs only (f_WT=2)",
    }),
    hybrid: option(z.boolean().default(false), {
      argumentKind: "flag",
      description: "Hybrid jobs only (f_WT=3)",
    }),
    jobType: option(
      z
        .enum(["fulltime", "parttime", "contract", "temporary", "internship", "other"])
        .optional(),
      { description: "Job type filter" }
    ),
    page: option(z.coerce.number().int().min(1).default(1), {
      description: "Page number (25 results per page)",
    }),
    limit: option(z.coerce.number().int().min(1).optional(), {
      description: "Cap total results returned by the CLI",
    }),
    format: option(z.enum(["json", "table", "plain"]).default("json"), {
      description: "Output format: json (default), table, plain",
    }),
  },
  handler: async ({ flags }) => {
    const { query, location, datePosted, remote, hybrid, jobType, page, limit, format } = flags

    if (!query && !location) {
      writeError("--query or --location is required", "MISSING_REQUIRED")
      process.exit(1)
    }

    const start = (page - 1) * 25
    const params: Record<string, string> = { start: String(start) }
    if (query) params.keywords = query
    if (location) params.location = location
    if (datePosted !== "any") params.f_TPR = DATE_POSTED_PARAM[datePosted]
    if (remote) params.f_WT = "2"
    else if (hybrid) params.f_WT = "3"
    if (jobType) params.f_JT = JOB_TYPE_PARAM[jobType]

    let html: string
    try {
      html = await htmlFetch("/jobs-guest/jobs/api/seeMoreJobPostings/search", params)
    } catch (err) {
      writeError(String(err), "API_ERROR")
      process.exit(1)
    }

    let results = parseJobCards(html)
    if (limit !== undefined) results = results.slice(0, limit)

    if (format === "json") {
      process.stdout.write(
        JSON.stringify(
          {
            meta: { page, perPage: 25, query: query ?? null, location: location ?? null },
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
      process.stdout.write(`LinkedIn Jobs${label ? " — " + label : ""} (page ${page}):\n`)
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
        process.stdout.write(`  URL:      ${job.url}\n`)
        process.stdout.write("\n")
      }
    }
  },
})
