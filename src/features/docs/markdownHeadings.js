export function slugify(text) {
  return text.toLowerCase().replace(/[^\w\s-]/g, '').replace(/\s+/g, '-').replace(/^-+|-+$/g, '')
}

/** Keep article anchors and the table of contents in sync, including repeats. */
export function getMarkdownHeadings(content) {
  const used = new Set()
  let inCode = false
  return content.split('\n').flatMap((line, index) => {
    if (line.trim().startsWith('```')) {
      inCode = !inCode
      return []
    }
    if (inCode) return []
    const match = line.match(/^(#{1,4})\s+(.+)$/)
    if (!match) return []
    const text = match[2].trim()
    const base = slugify(text) || 'section'
    let id = base
    let suffix = 2
    while (used.has(id)) id = `${base}-${suffix++}`
    used.add(id)
    return [{ line: index, level: match[1].length, text, id }]
  })
}
