import { defineCommand, option } from "@bunli/core"
import { z } from "zod"
import { BASE_URL, writeError, htmlFetch, parseJobDetail, isCloudflareChallenge } from "../helpers.js"

function extractId(idOrUrl: string): string {
  // URL: https://www.indeed.com/viewjob?jk=abc123 or rc/clk?jk=abc123
  const jkMatch = idOrUrl.match(/[?&]jk=([a-f0-9]+)/)
  if (jkMatch) return jkMatch[1]
  // Raw alphanumeric ID
  if (/^[a-f0-9]{16}$/.test(idOrUrl.trim())) return idOrUrl.trim()
  return idOrUrl
}

export const detail = defineCommand({
  name: "detail",
  description: "Fetch full detail for an Indeed job posting",
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
    const url = `${BASE_URL}/viewjob?jk=${id}`

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
        "Indeed returned a Cloudflare challenge page. Scraping is blocked. Try again later.",
        "BLOCKED"
      )
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
      if (job.date) process.stdout.write(`Date posted:     ${job.date}\n`)
      if (job.deadline) process.stdout.write(`Apply by:        ${job.deadline}\n`)
      process.stdout.write(`URL:             ${job.url}\n`)
      if (job.description) {
        process.stdout.write("\nDescription:\n")
        process.stdout.write("-".repeat(40) + "\n")
        process.stdout.write(job.description + "\n")
      }
    }
  },
})
