import React, { useState } from 'react'
import { Link } from 'react-router-dom'
import { Check, Copy, Info, AlertTriangle, AlertCircle, Lightbulb, ShieldAlert } from 'lucide-react'

// Helper to convert header text into anchor id
export function slugify(text) {
  return text
    .toLowerCase()
    .replace(/[^\w\s-]/g, '')
    .replace(/\s+/g, '-')
    .replace(/^-+|-+$/g, '')
}

function CodeBlock({ code, language }) {
  const [copied, setCopied] = useState(false)

  const handleCopy = () => {
    navigator.clipboard.writeText(code)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <div className="my-5 overflow-hidden rounded-md border border-border bg-[#0d0f12] text-xs">
      <div className="flex items-center justify-between border-b border-border/80 bg-surface-2 px-3 py-1.5 font-mono text-[11px] text-text-muted">
        <span className="uppercase tracking-wider text-text-faint">{language || 'code'}</span>
        <button
          onClick={handleCopy}
          type="button"
          className="flex items-center gap-1 text-[11px] text-text-muted hover:text-accent transition-colors"
        >
          {copied ? (
            <>
              <Check className="h-3 w-3 text-accent" />
              <span className="text-accent font-medium">Copied</span>
            </>
          ) : (
            <>
              <Copy className="h-3 w-3" />
              <span>Copy</span>
            </>
          )}
        </button>
      </div>
      <pre className="overflow-x-auto p-4 font-mono text-[12.5px] leading-relaxed text-text">
        <code>{code}</code>
      </pre>
    </div>
  )
}

function Callout({ type, title, children }) {
  const configs = {
    NOTE: {
      border: 'border-blue-500/40 bg-blue-500/5 text-blue-300',
      icon: <Info className="h-4 w-4 shrink-0 text-blue-400 mt-0.5" />,
      badge: 'NOTE',
    },
    TIP: {
      border: 'border-accent/40 bg-accent/5 text-accent-dim',
      icon: <Lightbulb className="h-4 w-4 shrink-0 text-accent mt-0.5" />,
      badge: 'TIP',
    },
    IMPORTANT: {
      border: 'border-amber-500/40 bg-amber-500/5 text-amber-300',
      icon: <AlertTriangle className="h-4 w-4 shrink-0 text-amber-400 mt-0.5" />,
      badge: 'IMPORTANT',
    },
    WARNING: {
      border: 'border-orange-500/40 bg-orange-500/5 text-orange-300',
      icon: <AlertCircle className="h-4 w-4 shrink-0 text-orange-400 mt-0.5" />,
      badge: 'WARNING',
    },
    CAUTION: {
      border: 'border-red-500/40 bg-red-500/5 text-red-300',
      icon: <ShieldAlert className="h-4 w-4 shrink-0 text-red-400 mt-0.5" />,
      badge: 'CAUTION',
    },
  }

  const cfg = configs[type] || configs.NOTE

  return (
    <div className={`my-5 rounded-md border p-4 ${cfg.border}`}>
      <div className="flex items-start gap-2.5">
        {cfg.icon}
        <div className="min-w-0 flex-1">
          <p className="font-mono text-[11px] font-bold uppercase tracking-wider mb-1 opacity-90">
            {title || cfg.badge}
          </p>
          <div className="text-[13px] leading-relaxed text-text-muted">{children}</div>
        </div>
      </div>
    </div>
  )
}

/**
 * Format inline markdown text: links, bold, code, italics
 */
function renderInline(text) {
  if (!text) return null

  // Split by inline code first: `code`
  const codeParts = text.split(/(`[^`]+`)/g)
  return codeParts.map((codePart, i) => {
    if (codePart.startsWith('`') && codePart.endsWith('`')) {
      return (
        <code
          key={i}
          className="rounded bg-surface-2 px-1.5 py-0.5 font-mono text-[12px] text-accent-dim border border-border/80"
        >
          {codePart.slice(1, -1)}
        </code>
      )
    }

    // Process bold, italic, and links inside plain text
    // Replace markdown links [label](url)
    const linkRegex = /\[([^\]]+)\]\(([^)]+)\)/g
    const elements = []
    let lastIdx = 0
    let match

    while ((match = linkRegex.exec(codePart)) !== null) {
      if (match.index > lastIdx) {
        elements.push(parseFormatting(codePart.slice(lastIdx, match.index), `${i}-${lastIdx}`))
      }
      const label = match[1]
      const url = match[2]
      if (url.startsWith('/')) {
        elements.push(
          <Link
            key={`${i}-${match.index}`}
            to={url}
            className="text-accent underline underline-offset-2 hover:text-accent-bright"
          >
            {label}
          </Link>
        )
      } else {
        elements.push(
          <a
            key={`${i}-${match.index}`}
            href={url}
            target="_blank"
            rel="noopener noreferrer"
            className="text-accent underline underline-offset-2 hover:text-accent-bright"
          >
            {label}
          </a>
        )
      }
      lastIdx = linkRegex.lastIndex
    }

    if (lastIdx < codePart.length) {
      elements.push(parseFormatting(codePart.slice(lastIdx), `${i}-${lastIdx}`))
    }

    return <React.Fragment key={i}>{elements}</React.Fragment>
  })
}

function parseFormatting(text, keyPrefix) {
  // Bold **bold**
  const boldParts = text.split(/(\*\*[^*]+\*\*)/g)
  return boldParts.map((bPart, bi) => {
    if (bPart.startsWith('**') && bPart.endsWith('**')) {
      return (
        <strong key={`${keyPrefix}-b-${bi}`} className="font-semibold text-text">
          {bPart.slice(2, -2)}
        </strong>
      )
    }
    // Italic *italic*
    const itParts = bPart.split(/(\*[^*]+\*)/g)
    return itParts.map((itPart, iti) => {
      if (itPart.startsWith('*') && itPart.endsWith('*')) {
        return (
          <em key={`${keyPrefix}-it-${iti}`} className="italic text-text-muted">
            {itPart.slice(1, -1)}
          </em>
        )
      }
      return itPart
    })
  })
}

export function MarkdownRenderer({ content }) {
  if (!content) return null

  const lines = content.split('\n')
  const elements = []
  let i = 0

  while (i < lines.length) {
    const line = lines[i]

    // 1. Code blocks ```lang ... ```
    if (line.trim().startsWith('```')) {
      const lang = line.trim().replace(/^```/, '').trim()
      const codeLines = []
      i++
      while (i < lines.length && !lines[i].trim().startsWith('```')) {
        codeLines.push(lines[i])
        i++
      }
      elements.push(
        <CodeBlock key={`code-${i}`} language={lang} code={codeLines.join('\n')} />
      )
      i++
      continue
    }

    // 2. GitHub-style alerts: > [!NOTE] or > blockquote
    if (line.trim().startsWith('>')) {
      const alertMatch = line.trim().match(/^>\s*\[!(NOTE|TIP|IMPORTANT|WARNING|CAUTION)\]/i)
      if (alertMatch) {
        const type = alertMatch[1].toUpperCase()
        const alertLines = []
        i++
        while (i < lines.length && lines[i].trim().startsWith('>')) {
          alertLines.push(lines[i].replace(/^>\s?/, ''))
          i++
        }
        elements.push(
          <Callout key={`alert-${i}`} type={type}>
            {alertLines.map((al, idx) => (
              <p key={idx} className={idx > 0 ? 'mt-2' : ''}>
                {renderInline(al)}
              </p>
            ))}
          </Callout>
        )
        continue
      } else {
        // Standard blockquote
        const bqLines = [line.replace(/^>\s?/, '')]
        i++
        while (i < lines.length && lines[i].trim().startsWith('>')) {
          bqLines.push(lines[i].replace(/^>\s?/, ''))
          i++
        }
        elements.push(
          <blockquote
            key={`bq-${i}`}
            className="my-4 border-l-2 border-accent/60 pl-4 py-1 italic text-text-muted text-[13.5px]"
          >
            {bqLines.map((bl, bidx) => (
              <p key={bidx}>{renderInline(bl)}</p>
            ))}
          </blockquote>
        )
        continue
      }
    }

    // 3. Tables | header | header |
    if (line.trim().startsWith('|') && line.trim().endsWith('|')) {
      const tableLines = []
      while (i < lines.length && lines[i].trim().startsWith('|') && lines[i].trim().endsWith('|')) {
        tableLines.push(lines[i].trim())
        i++
      }

      if (tableLines.length >= 2) {
        const headers = tableLines[0]
          .split('|')
          .slice(1, -1)
          .map((h) => h.trim())
        const rows = tableLines.slice(2).map((r) =>
          r
            .split('|')
            .slice(1, -1)
            .map((c) => c.trim())
        )

        elements.push(
          <div key={`tbl-${i}`} className="my-5 overflow-x-auto rounded border border-border bg-surface text-xs">
            <table className="w-full border-collapse text-left">
              <thead>
                <tr className="border-b border-border bg-surface-2">
                  {headers.map((h, hi) => (
                    <th key={hi} className="px-3.5 py-2.5 font-mono font-medium text-text uppercase tracking-wider text-[11px]">
                      {renderInline(h)}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-border/60">
                {rows.map((row, ri) => (
                  <tr key={ri} className="hover:bg-surface-2/40 transition-colors">
                    {row.map((cell, ci) => (
                      <td key={ci} className="px-3.5 py-2 text-text-muted leading-relaxed">
                        {renderInline(cell)}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )
      }
      continue
    }

    // 4. Horizontal rule ---
    if (line.trim() === '---' || line.trim() === '***') {
      elements.push(<hr key={`hr-${i}`} className="my-8 border-border" />)
      i++
      continue
    }

    // 5. Headings
    if (line.startsWith('# ')) {
      const title = line.replace(/^#\s+/, '').trim()
      elements.push(
        <h1
          key={`h1-${i}`}
          id={slugify(title)}
          className="scroll-mt-20 text-2xl md:text-3xl font-bold tracking-tight text-text mb-4 mt-2"
        >
          {renderInline(title)}
        </h1>
      )
      i++
      continue
    }

    if (line.startsWith('## ')) {
      const title = line.replace(/^##\s+/, '').trim()
      elements.push(
        <h2
          key={`h2-${i}`}
          id={slugify(title)}
          className="scroll-mt-20 text-xl font-semibold tracking-tight text-text mt-8 mb-3 pb-1 border-b border-border/50"
        >
          {renderInline(title)}
        </h2>
      )
      i++
      continue
    }

    if (line.startsWith('### ')) {
      const title = line.replace(/^###\s+/, '').trim()
      elements.push(
        <h3
          key={`h3-${i}`}
          id={slugify(title)}
          className="scroll-mt-20 text-base font-semibold text-text mt-6 mb-2"
        >
          {renderInline(title)}
        </h3>
      )
      i++
      continue
    }

    if (line.startsWith('#### ')) {
      const title = line.replace(/^####\s+/, '').trim()
      elements.push(
        <h4
          key={`h4-${i}`}
          id={slugify(title)}
          className="scroll-mt-20 text-sm font-semibold font-mono text-accent-dim uppercase tracking-wider mt-5 mb-2"
        >
          {renderInline(title)}
        </h4>
      )
      i++
      continue
    }

    // 6. Unordered lists: - item or * item
    if (line.trim().startsWith('- ') || line.trim().startsWith('* ')) {
      const listItems = []
      while (i < lines.length && (lines[i].trim().startsWith('- ') || lines[i].trim().startsWith('* '))) {
        listItems.push(lines[i].trim().replace(/^[-*]\s+/, ''))
        i++
      }
      elements.push(
        <ul key={`ul-${i}`} className="my-3 space-y-1.5 pl-5 list-disc text-[13.5px] leading-relaxed text-text-muted">
          {listItems.map((item, li) => (
            <li key={li}>{renderInline(item)}</li>
          ))}
        </ul>
      )
      continue
    }

    // 7. Ordered lists: 1. item
    if (/^\d+\.\s+/.test(line.trim())) {
      const listItems = []
      while (i < lines.length && /^\d+\.\s+/.test(lines[i].trim())) {
        listItems.push(lines[i].trim().replace(/^\d+\.\s+/, ''))
        i++
      }
      elements.push(
        <ol key={`ol-${i}`} className="my-3 space-y-1.5 pl-5 list-decimal text-[13.5px] leading-relaxed text-text-muted">
          {listItems.map((item, li) => (
            <li key={li}>{renderInline(item)}</li>
          ))}
        </ol>
      )
      continue
    }

    // 8. Empty lines
    if (!line.trim()) {
      i++
      continue
    }

    // 9. Standard paragraphs
    elements.push(
      <p key={`p-${i}`} className="my-3 text-[13.5px] leading-relaxed text-text-muted">
        {renderInline(line)}
      </p>
    )
    i++
  }

  return <div className="docs-prose max-w-none">{elements}</div>
}
