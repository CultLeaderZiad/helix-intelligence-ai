import React, { useEffect } from 'react'
import { useParams, Link, Navigate } from 'react-router-dom'
import { DocsLayout } from '@/features/docs/DocsLayout'
import { MarkdownRenderer } from '@/features/docs/MarkdownRenderer'
import { getDoc, getDefaultDocForSection } from '@/features/docs/docsData'
import { AlertCircle, ArrowLeft } from 'lucide-react'

export function DocsDetailPage() {
  const { section, slug } = useParams()

  // Find corresponding doc in static registry
  const doc = getDoc(section, slug)

  useEffect(() => {
    if (doc) {
      document.title = `${doc.title} · Helix Documentation`
    }
  }, [doc])

  if (!doc) {
    const fallback = getDefaultDocForSection(section)
    if (fallback) {
      return <Navigate to={`/docs/${fallback.section}/${fallback.slug}`} replace />
    }

    return (
      <DocsLayout activeDoc={null}>
        <div className="py-16 text-center max-w-md mx-auto">
          <div className="h-12 w-12 rounded-full bg-amber-500/10 border border-amber-500/30 flex items-center justify-center mx-auto text-amber-400 mb-4">
            <AlertCircle className="h-6 w-6" />
          </div>
          <h1 className="text-xl font-bold text-text mb-2">Documentation Page Not Found</h1>
          <p className="text-xs text-text-muted mb-6 leading-relaxed">
            The page you are looking for does not exist in our static documentation registry.
          </p>
          <Link
            to="/docs"
            className="inline-flex items-center gap-2 px-4 py-2 rounded-md bg-surface-2 border border-border text-xs font-mono text-text hover:text-accent transition-colors"
          >
            <ArrowLeft className="h-3.5 w-3.5" />
            Back to Docs Home
          </Link>
        </div>
      </DocsLayout>
    )
  }

  return (
    <DocsLayout activeDoc={doc}>
      <MarkdownRenderer content={doc.content} />
    </DocsLayout>
  )
}
