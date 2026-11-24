import { useCallback, useEffect, useState } from "react"
import { adminService } from "@/services"

/** Admin-only: upload .md/.txt (or paste text), preview chunks, version, enable/disable, delete, audit. */
export function KnowledgeBasePage() {
  const [docs, setDocs] = useState(null)
  const [audit, setAudit] = useState([])
  const [error, setError] = useState("")
  const [title, setTitle] = useState("")
  const [text, setText] = useState("")
  const [filename, setFilename] = useState("")
  const [preview, setPreview] = useState(null)
  const [busy, setBusy] = useState(false)

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

  async function onFile(event) {
    const file = event.target.files?.[0]
    if (!file) return
    if (!/\.(md|txt)$/i.test(file.name)) {
      setError("Upload a .md or .txt file.")
      return
    }
    setFilename(file.name)
    setTitle((t) => t || file.name.replace(/\.(md|txt)$/i, ""))
    setText(await file.text())
  }

  return (
    <div className="flex flex-col gap-6 p-6">
      <header>
        <h1 className="text-xl font-semibold text-text">Knowledge Base</h1>
        <p className="mt-1 max-w-3xl text-sm text-text-muted">
          Documents the Helix Agent can search and cite. Uploading an existing title creates a new version and turns the older ones off.
          Retrieved text is treated as data by the agent, never as instructions.
        </p>
      </header>

      {error ? <p role="alert" className="text-sm text-rose-300">{error}</p> : null}

      <form
        className="flex flex-col gap-3 rounded-lg border border-border p-4"
        onSubmit={(e) => {
          e.preventDefault()
          run(async () => {
            await adminService.uploadKnowledgeDocument({ title: title.trim(), text, filename: filename || undefined })
            setTitle("")
            setText("")
            setFilename("")
          })
        }}
      >
        <label className="flex flex-col gap-1 text-sm text-text">
          Title
          <input required maxLength={200} value={title} onChange={(e) => setTitle(e.target.value)}
            className="rounded border border-border bg-surface-2 px-3 py-2 text-sm" dir="auto" />
        </label>
        <label className="flex flex-col gap-1 text-sm text-text">
          File (.md or .txt)
          <input type="file" accept=".md,.txt,text/markdown,text/plain" onChange={onFile} className="text-sm" />
        </label>
        <label className="flex flex-col gap-1 text-sm text-text">
          Or paste text
          <textarea required rows={8} value={text} onChange={(e) => setText(e.target.value)}
            className="rounded border border-border bg-surface-2 px-3 py-2 font-mono text-xs" dir="auto" />
        </label>
        <button type="submit" disabled={busy} className="self-start rounded bg-accent px-4 py-2 text-sm font-semibold text-black disabled:opacity-60">
          Upload
        </button>
      </form>

      <section>
        <h2 className="text-sm font-semibold text-text">Documents</h2>
        {docs && docs.length === 0 ? <p className="mt-2 text-sm text-text-muted">No documents yet.</p> : null}
        <table className="mt-2 w-full text-sm">
          <thead className="text-left text-xs text-text-muted">
            <tr><th>Title</th><th>Version</th><th>Status</th><th>Chunks</th><th>Size</th><th /></tr>
          </thead>
          <tbody>
            {(docs || []).map((d) => (
              <tr key={d.id} className="border-t border-border">
                <td className="py-2" dir="auto">{d.title}</td>
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
      </section>

      {preview ? (
        <section className="rounded-lg border border-border p-4">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-semibold text-text" dir="auto">{preview.title} v{preview.version}: {preview.chunk_items.length} chunks</h2>
            <button type="button" className="text-xs underline" onClick={() => setPreview(null)}>Close</button>
          </div>
          <ol className="mt-3 flex flex-col gap-2">
            {preview.chunk_items.map((c) => (
              <li key={c.id} className="whitespace-pre-wrap rounded bg-surface-2 p-2 text-xs text-text" dir="auto">
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
