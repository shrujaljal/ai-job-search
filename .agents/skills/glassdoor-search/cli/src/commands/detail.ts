import { defineCommand, option } from "@bunli/core"
import { z } from "zod"
import { BASE_URL, writeError, htmlFetch, parseJobDetail, isCloudflareChallenge } from "../helpers.js"

function extractIdAndUrl(idOrUrl: string): { id: string; url: string } {
  // Full Glassdoor job URL: https://www.glassdoor.com/job-listing/...?jl=1234567890
  const jlMatch = idOrUrl.match(/[?&]jl=(\d+)/)
  if (jlMatch) {
    const id = jlMatch[1]
    const url = idOrUrl.startsWith("http") ? idOrUrl : `${BASE_URL}${idOrUrl}`
    return { id, url }
  }
  // /job-listing/slug-SLCH_IC..._KO...,....htm patterns with ID at end
  const slugMatch = idOrUrl.match(/\/job-listing\/[^?]+jl(\d+)/)
  if (slugMatch) {
    return { id: slugMatch[1], url: idOrUrl.startsWith("http") ? idOrUrl : `${BASE_URL}${idOrUrl}` }
  }
  // Pure numeric ID
  if (/^\d{7,}$/.test(idOrUrl.trim())) {
    return { id: idOrUrl.trim(), url: `${BASE_URL}/job-listing/jl${idOrUrl.trim()}` }
  }
  // Assume it's a full URL
  return { id: idOrUrl, url: idOrUrl.startsWith("http") ? idOrUrl : `${BASE_URL}${idOrUrl}` }
}

export const detail = defineCommand({
  name: "detail",
  description: "Fetch full detail for a Glassdoor job posting",
  options: {
    format: option(z.enum(["json", "plain"]).default("json"), {
      description: "Output format: json (default), plain",
    }),
  },
  handler: async ({ flags, positional }) => {
    const { format } = flags
    const idOrUrl = positional[0]

    if (!idOrUrl) {
      writeError("<id> or <url> is required", "MISSING_REQUIRED")
      process.exit(1)
    }

    const { id, url } = extractIdAndUrl(idOrUrl)

    let html: string
    try {
      html = await htmlFetch(url)
    } catch (err) {
      const msg = String(err)
      if (msg.includes("404") || msg.toLowerCase().includes("not found")) {
        writeError("Job not found", "NOT_FOUND")
      } else {
        writeError(msg, "API_ERROR")
      }
      process.exit(1)
    }

    if (isCloudflareChallenge(html)) {
      writeError(
        "Glassdoor returned a Cloudflare challenge page. Scraping is blocked. Try again later.",
        "BLOCKED"
      )
      process.exit(1)
    }

    const job = parseJobDetail(html, id, url)

    if (format === "json") {
      process.stdout.write(JSON.stringify(job, null, 2) + "\n")
    } else {
      // plain
      process.stdout.write(`${job.title}\n`)
      process.stdout.write("=".repeat(Math.min(job.title.length, 60)) + "\n\n")
      if (job.company) process.stdout.write(`Company:         ${job.company}\n`)
      if (job.companyUrl) process.stdout.write(`Company URL:     ${job.companyUrl}\n`)
      if (job.location) process.stdout.write(`Location:        ${job.location}\n`)
      if (job.employmentType) process.stdout.write(`Employment type: ${job.employmentType}\n`)
      if (job.date) process.stdout.write(`Date posted:     ${job.date}\n`)
      process.stdout.write(`URL:             ${job.url}\n`)
      if (job.applyUrl && job.applyUrl !== job.url) {
        process.stdout.write(`Apply:           ${job.applyUrl}\n`)
      }
      if (job.description) {
        process.stdout.write("\nDescription:\n")
        process.stdout.write("-".repeat(40) + "\n")
        process.stdout.write(job.description + "\n")
      }
    }
  },
})
