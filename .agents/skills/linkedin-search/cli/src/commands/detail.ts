import { defineCommand, option } from "@bunli/core"
import { z } from "zod"
import { writeError, htmlFetch, parseJobDetail } from "../helpers.js"

function extractId(idOrUrl: string): string {
  // Full view URL: https://www.linkedin.com/jobs/view/title-at-company-3912345678
  const viewMatch = idOrUrl.match(/\/jobs\/view\/[^/?]+-(\d{7,})/)
  if (viewMatch) return viewMatch[1]
  // Numeric ID directly
  if (/^\d{7,}$/.test(idOrUrl.trim())) return idOrUrl.trim()
  // Fall back to returning as-is (may be a slug or other format)
  return idOrUrl
}

export const detail = defineCommand({
  name: "detail",
  description: "Fetch full detail for a LinkedIn job posting",
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

    const id = extractId(idOrUrl)

    let html: string
    try {
      html = await htmlFetch(`/jobs-guest/jobs/api/jobPosting/${id}`)
    } catch (err) {
      const msg = String(err)
      if (msg.includes("404") || msg.toLowerCase().includes("not found")) {
        writeError("Job not found", "NOT_FOUND")
      } else {
        writeError(msg, "API_ERROR")
      }
      process.exit(1)
    }

    const job = parseJobDetail(html, id)

    if (format === "json") {
      process.stdout.write(JSON.stringify(job, null, 2) + "\n")
    } else {
      // plain
      process.stdout.write(`${job.title}\n`)
      process.stdout.write("=".repeat(Math.min(job.title.length, 60)) + "\n\n")
      if (job.company) process.stdout.write(`Company:         ${job.company}\n`)
      if (job.location) process.stdout.write(`Location:        ${job.location}\n`)
      if (job.employmentType) process.stdout.write(`Employment type: ${job.employmentType}\n`)
      process.stdout.write(`URL:             ${job.url}\n`)
      if (job.applyUrl) process.stdout.write(`Apply:           ${job.applyUrl}\n`)
      if (job.description) {
        process.stdout.write("\nDescription:\n")
        process.stdout.write("-".repeat(40) + "\n")
        process.stdout.write(job.description + "\n")
      }
    }
  },
})
