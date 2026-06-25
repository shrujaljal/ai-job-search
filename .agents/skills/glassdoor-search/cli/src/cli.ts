import { createCLI } from "@bunli/core"
import { search } from "./commands/search.js"
import { detail } from "./commands/detail.js"

const cli = await createCLI({
  name: "glassdoor-cli",
  version: "1.0.0",
  description: "CLI for searching jobs on Glassdoor.com (extracts __NEXT_DATA__ JSON)",
})

cli.command(search)
cli.command(detail)

await cli.run()
