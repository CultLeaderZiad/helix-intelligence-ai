import React, { useEffect } from 'react'
import { useParams, Link, Navigate } from 'react-router-dom'
import { DocsLayout } from '@/features/docs/DocsLayout'
import { MarkdownRenderer } from '@/features/docs/MarkdownRenderer'
import { getDoc, getDefaultDocForSection } from '@/features/docs/docsData'
import { getDocsReferenceCopy } from '@/features/docs/docsReferenceCopy'
import { useLanguage } from '@/context/LanguageContext'
import { AlertCircle, ArrowLeft } from 'lucide-react'

export function DocsDetailPage() {
  const { section, slug } = useParams()
  const { lang, t } = useLanguage()
  const referenceCopy = getDocsReferenceCopy(lang)

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
          <h1 className="text-xl font-bold text-text mb-2">{t('docsNotFound')}</h1>
          <p className="text-xs text-text-muted mb-6 leading-relaxed">
            {lang === 'ar'
              ? 'الصفحة المطلوبة غير موجودة ضمن صفحات التوثيق.'
              : 'The page you are looking for does not exist in the documentation.'}
          </p>
          <Link
            to="/docs"
            className="inline-flex items-center gap-2 px-4 py-2 rounded-md bg-surface-2 border border-border text-xs font-mono text-text hover:text-accent transition-colors"
          >
            <ArrowLeft className="h-3.5 w-3.5" />
            {t('docsBackToHome')}
          </Link>
        </div>
      </DocsLayout>
    )
  }

  return (
    <DocsLayout activeDoc={doc}>
      <aside
        role="note"
        dir={lang === 'ar' ? 'rtl' : 'ltr'}
        className="mb-6 rounded-lg border border-border bg-surface-2/60 p-4 text-sm"
      >
        <h2 className="font-semibold text-text">{referenceCopy.title}</h2>
        <p className="mt-1 leading-relaxed text-text-muted">{referenceCopy.message}</p>
        <p className="mt-1 leading-relaxed text-text-muted">{referenceCopy.usage}</p>
        {lang === 'ar' && <p className="mt-2 text-xs leading-relaxed text-text-faint">{t('docsEnglishNotice')}</p>}
      </aside>
      <MarkdownRenderer content={doc.content} />
    </DocsLayout>
  )
}
