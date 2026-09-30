import fs from "node:fs"
import path from "node:path"
import { execSync } from "node:child_process"
import { fileURLToPath } from "node:url"

const __dirname = path.dirname(fileURLToPath(import.meta.url))
const rootDir = path.resolve(__dirname, "..")
const docsDir = path.join(rootDir, "docs")
const outputFile = path.join(rootDir, "src", "features", "docs", "docsGitMeta.json")

function getFilesRecursively(dir) {
  let results = []
  if (!fs.existsSync(dir)) return results
  const list = fs.readdirSync(dir)
  for (const file of list) {
    const filePath = path.join(dir, file)
    const stat = fs.statSync(filePath)
    if (stat && stat.isDirectory()) {
      results = results.concat(getFilesRecursively(filePath))
    } else if (file.endsWith(".md")) {
      results.push(filePath)
    }
  }
  return results
}

const files = getFilesRecursively(docsDir)
const meta = {}

for (const filePath of files) {
  const relPath = path.relative(rootDir, filePath).replace(/\\/g, "/")
  const docKey = path.relative(docsDir, filePath).replace(/\\/g, "/")
  try {
    const gitDate = execSync(`git log -1 --format=%cs "${relPath}"`, { cwd: rootDir })
      .toString()
      .trim()
    const gitHash = execSync(`git log -1 --format=%h "${relPath}"`, { cwd: rootDir })
      .toString()
      .trim()
    if (gitDate) {
      meta[docKey] = {
        lastUpdated: gitDate,
        commitHash: gitHash,
      }
    } else {
      const stat = fs.statSync(filePath)
      meta[docKey] = {
        lastUpdated: stat.mtime.toISOString().split("T")[0],
        commitHash: "local",
      }
    }
  } catch (err) {
    const stat = fs.statSync(filePath)
    meta[docKey] = {
      lastUpdated: stat.mtime.toISOString().split("T")[0],
      commitHash: "local",
    }
  }
}

fs.writeFileSync(outputFile, JSON.stringify(meta, null, 2) + "\n")
console.log(`Generated docs git metadata for ${Object.keys(meta).length} files -> ${outputFile}`)
