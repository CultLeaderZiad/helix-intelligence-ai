import React, { useState, useEffect } from 'react'
import { ArrowUp } from 'lucide-react'
import { cn } from '@/lib/utils'

export function ScrollToTopButton({ threshold = 350, className, containerRef = null }) {
  const [visible, setVisible] = useState(false)

  useEffect(() => {
    const target = containerRef?.current || window

    const checkScroll = () => {
      const scrollY = containerRef?.current ? containerRef.current.scrollTop : window.scrollY
      setVisible(scrollY > threshold)
    }

    target.addEventListener('scroll', checkScroll, { passive: true })
    checkScroll()

    return () => target.removeEventListener('scroll', checkScroll)
  }, [threshold, containerRef])

  const scrollToTop = () => {
    if (containerRef?.current) {
      containerRef.current.scrollTo({ top: 0, behavior: 'smooth' })
    } else {
      window.scrollTo({ top: 0, behavior: 'smooth' })
    }
  }

  if (!visible) return null

  return (
    <button
      type="button"
      onClick={scrollToTop}
      aria-label="Scroll to top"
      title="Scroll to top"
      className={cn(
        "fixed bottom-20 right-4 sm:right-6 z-40 flex h-9 w-9 items-center justify-center rounded-full border border-border bg-surface-2/90 text-text-muted hover:text-accent hover:bg-surface-3 shadow-xl backdrop-blur-md transition-all duration-200 hover:scale-105 active:scale-95 focus:outline-none focus:ring-2 focus:ring-accent/50",
        className
      )}
    >
      <ArrowUp className="h-4 w-4" aria-hidden="true" />
    </button>
  )
}

export default ScrollToTopButton
