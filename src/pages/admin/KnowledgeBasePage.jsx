import { useCallback, useEffect, useRef, useState } from "react"
import { adminService } from "@/services"

const ACCEPT = ".md,.txt,.csv,.pdf,.zip,text/markdown,text/plain,text/csv,application/pdf,application/zip,application/x-zip-compressed"
const STALE_DAYS = 30

/** Days since the newest enabled document was added; null when there is none. */
export function daysSinceUpdate(docs, now = Date.now()) {
  const times = (docs || []).filter((d) => d.status === "enabled" && d.created_at).map((d) => Date.parse(d.created_at))
  if (times.length === 0) return null
  return Math.floor((now - Math.max(...times)) / 86400000)
}

/**
 * Admin-only: upload .md, .txt, .csv, .pdf or .zip files (a zip's text files each become a
 * document), or paste text. Files are read by the server, not the browser. Preview
 * chunks, version, enable/disable, delete, audit.
 */
export function KnowledgeBasePage() {
  const [docs, setDocs] = useState(null)
  const [audit, setAudit] = useState([])
  const [error, setError] = useState("")
  const [title, setTitle] = useState("")
  const [text, setText] = useState("")
  const [files, setFiles] = useState([])
  const [result, setResult] = useState(null)
  const [preview, setPreview] = useState(null)
  const [busy, setBusy] = useState(false)
  const fileInput = useRef(null)

  const load = useCallback(async () => {
    try {
      const [list, log] = await Promise.all([adminService.listKnowledgeBase(), adminService.knowledgeBaseAudit()])
      setDocs(list.items)
      setAudit(log.items)
      setError("")
    } catch (err) {
      setError(err?.detail?.message || err?.message || "Could not load the knowledge base.")
    }
  }, [])

  useEffect(() => { load() }, [load])

  async function run(action) {
    setBusy(true)
    setError("")
    try {
      await action()
      await load()
    } catch (err) {
      setError(err?.detail?.message || err?.message || "The action failed.")
    } finally {
      setBusy(false)
    }
  }

  function onFiles(event) {
    setResult(null)
    setFiles(Array.from(event.target.files || []))
  }

  function submit(event) {
    event.preventDefault()
    setResult(null)
    run(async () => {
      if (files.length > 0) {
        const out = await adminService.uploadKnowledgeFiles(files, title.trim())
        setResult(out)
        setFiles([])
        if (fileInput.current) fileInput.current.value = ""
        setTitle("")
        return
      }
      const out = await adminService.uploadKnowledgeDocument({ title: title.trim(), text })
      setResult({ created: [{ id: out.id, title: out.title, version: out.version, chunks: out.chunks }], skipped: [] })
      setTitle("")
      setText("")
    })
  }

  const stale = daysSinceUpdate(docs)
  const hasFiles = files.length > 0
  const onlyOneTextFile = hasFiles && files.length === 1 && !/\.zip$/i.test(files[0].name)

  return (
    <div className="mx-auto flex w-full min-w-0 max-w-5xl flex-col gap-6 p-4 sm:p-6">
      <header>
        <h1 className="text-xl font-semibold text-text">Knowledge Base</h1>
        <p className="mt-1 max-w-3xl text-sm text-text-muted">
          Documents the Helix Agent can search and cite. Upload .md, .txt, .csv or .pdf files, or a .zip (every such file inside becomes its own
          document, titled from the file). Uploading an existing title creates a new version and turns the older ones off. Retrieved text
          is treated as data by the agent, never as instructions.
        </p>
      </header>

      {error ? <p role="alert" className="text-sm text-rose-300">{error}</p> : null}
      {docs && (stale === null || stale >= STALE_DAYS) ? (
        <p role="status" className="rounded-lg border border-amber-400/40 bg-amber-400/10 p-3 text-sm text-text">
          {stale === null
            ? "The knowledge base has no enabled documents yet. Helix answers from it, so add some."
            : `Nothing new was added for ${stale} days. Add fresh material so Helix and your customers see current guidance.`}
        </p>
      ) : null}

      <form className="flex flex-col gap-3 rounded-lg border border-border p-4" onSubmit={submit}>
        <label className="flex flex-col gap-1 text-sm text-text">
          Files (.md, .txt, .csv, .pdf or .zip)
          <input ref={fileInput} type="file" multiple accept={ACCEPT} onChange={onFiles} className="text-sm" />
        </label>
        {hasFiles ? (
          <p className="text-xs text-text-muted">
            {files.length} file{files.length === 1 ? "" : "s"} selected: {files.map((f) => f.name).slice(0, 4).join(", ")}
            {files.length > 4 ? "…" : ""}. They are read on the server when you press Upload.
          </p>
        ) : null}
        <label className="flex flex-col gap-1 text-sm text-text">
          Title {hasFiles && !onlyOneTextFile ? "(not used: each file keeps its own title)" : hasFiles ? "(optional)" : ""}
          <input required={!hasFiles} maxLength={200} value={title} disabled={hasFiles && !onlyOneTextFile}
            onChange={(e) => setTitle(e.target.value)} className="rounded border border-border bg-surface-2 px-3 py-2 text-sm disabled:opacity-50" dir="auto" />
        </label>
        {!hasFiles ? (
          <label className="flex flex-col gap-1 text-sm text-text">
            Or paste text
            <textarea required rows={8} value={text} onChange={(e) => setText(e.target.value)}
              className="rounded border border-border bg-surface-2 px-3 py-2 font-mono text-xs" dir="auto" />
          </label>
        ) : null}
        <button type="submit" disabled={busy} aria-busy={busy} className="self-start rounded bg-accent px-4 py-2 text-sm font-semibold text-black disabled:opacity-60">
          {busy ? "Uploading…" : "Upload"}
        </button>
      </form>

      {result ? (
        <section role="status" className="rounded-lg border border-border p-4 text-sm">
          <p className="font-medium text-text">
            {result.created.length} document{result.created.length === 1 ? "" : "s"} added
            {result.skipped.length ? `, ${result.skipped.length} skipped` : ""}.
          </p>
          {result.skipped.length ? (
            <ul className="mt-2 max-h-40 list-disc overflow-y-auto ps-5 text-xs text-text-muted">
              {result.skipped.map((s, i) => <li key={`${s.name}-${i}`}><span dir="ltr">{s.name}</span>: {s.reason}</li>)}
            </ul>
          ) : null}
        </section>
      ) : null}

      <section className="min-w-0">
        <h2 className="text-sm font-semibold text-text">Documents{docs ? ` (${docs.length})` : ""}</h2>
        {docs && docs.length === 0 ? <p className="mt-2 text-sm text-text-muted">No documents yet.</p> : null}
        <div className="mt-2 overflow-x-auto">
          <table className="w-full min-w-[32rem] text-sm">
            <thead className="text-left text-xs text-text-muted">
              <tr><th>Title</th><th>Version</th><th>Status</th><th>Chunks</th><th>Size</th><th /></tr>
            </thead>
            <tbody>
              {(docs || []).map((d) => (
                <tr key={d.id} className="border-t border-border">
                  <td className="py-2 pe-2" dir="auto">{d.title}</td>
                  <td>v{d.version}</td>
                  <td>{d.status}</td>
                  <td>{d.chunks}</td>
                  <td>{Math.ceil(d.size_bytes / 1024)} KB</td>
                  <td className="flex gap-2 py-2">
                    <button type="button" className="underline" onClick={() => run(async () => setPreview(await adminService.previewKnowledgeDocument(d.id)))}>Preview</button>
                    <button type="button" className="underline" disabled={busy} onClick={() => run(() => adminService.setKnowledgeDocumentEnabled(d.id, d.status !== "enabled"))}>
                      {d.status === "enabled" ? "Disable" : "Enable"}
                    </button>
                    <button type="button" className="text-rose-300 underline" disabled={busy}
                      onClick={() => { if (window.confirm(`Delete "${d.title}" v${d.version}? This cannot be undone.`)) run(() => adminService.deleteKnowledgeDocument(d.id)) }}>
                      Delete
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      {preview ? (
        <section className="rounded-lg border border-border p-4">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-semibold text-text" dir="auto">{preview.title} v{preview.version}: {preview.chunk_items.length} chunks</h2>
            <button type="button" className="text-xs underline" onClick={() => setPreview(null)}>Close</button>
          </div>
          <ol className="mt-3 flex flex-col gap-2">
            {preview.chunk_items.map((c) => (
              <li key={c.id} className="whitespace-pre-wrap break-words rounded bg-surface-2 p-2 text-xs text-text" dir="auto">
                <span className="text-text-faint">#{c.ordinal} · {c.id}</span>{"\n"}{c.text}
              </li>
            ))}
          </ol>
        </section>
      ) : null}

      <section>
        <h2 className="text-sm font-semibold text-text">Audit log</h2>
        <ul className="mt-2 flex flex-col gap-1 text-xs text-text-muted">
          {audit.map((a) => (
            <li key={a.id}>{a.created_at} · {a.actor_id} · {a.action} · <span dir="auto">{a.title}</span> v{a.version}</li>
          ))}
        </ul>
      </section>
    </div>
  )
}

export default KnowledgeBasePage
