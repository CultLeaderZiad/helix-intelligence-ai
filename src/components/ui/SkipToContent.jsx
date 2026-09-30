import React from 'react'
import { cn } from '@/lib/utils'

export function SkipToContent({ targetId = 'main-content', label = 'Skip to main content', className }) {
  const handleClick = (e) => {
    const target = document.getElementById(targetId)
    if (target) {
      e.preventDefault()
      target.tabIndex = -1
      target.focus({ preventScroll: false })
      target.scrollIntoView({ behavior: 'smooth', block: 'start' })
    }
  }

  return (
    <a
      href={`#${targetId}`}
      onClick={handleClick}
      className={cn(
        "sr-only focus:not-sr-only focus:fixed focus:top-3 focus:left-3 focus:z-50 focus:inline-flex focus:items-center focus:gap-2 focus:px-4 focus:py-2 focus:rounded-md focus:bg-accent focus:text-black focus:font-mono focus:text-xs focus:font-bold focus:shadow-2xl focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-accent",
        className
      )}
    >
      <span>{label}</span>
    </a>
  )
}

export default SkipToContent
