import React, { useRef, useState, useEffect, useLayoutEffect } from "react"
import { Link } from "react-router-dom"
import { cn } from "@/lib/utils"

export function PillNav({
  logo,
  logoAlt = "Logo",
  items = [],
  activeHref,
  className,
  ease = "power2.easeOut",
  baseColor = "#000000",
  pillColor = "#ffffff",
  hoveredPillTextColor = "#ffffff",
  pillTextColor = "#000000",
}) {
  const [hoveredIndex, setHoveredIndex] = useState(null)
  const [activeIndex, setActiveIndex] = useState(0)
  const [pillStyle, setPillStyle] = useState({ left: 0, width: 0 })

  const itemRefs = useRef([])

  // Sync activeIndex with activeHref prop
  useEffect(() => {
    const index = items.findIndex(
      (item) => item.href === activeHref || item.path === activeHref
    )
    if (index !== -1) {
      setActiveIndex(index)
    }
  }, [activeHref, items])

  const currentHighlightIndex = hoveredIndex !== null ? hoveredIndex : activeIndex

  // Measure and update the pill's absolute styling (left and width offsets)
  const updatePillPosition = () => {
    const activeEl = itemRefs.current[currentHighlightIndex]
    if (activeEl) {
      setPillStyle({
        left: activeEl.offsetLeft,
        width: activeEl.offsetWidth,
      })
    } else {
      setPillStyle({ left: 0, width: 0 })
    }
  }

  // Recalculate on highlight index change or window resize
  useLayoutEffect(() => {
    updatePillPosition()
    window.addEventListener("resize", updatePillPosition)
    return () => window.removeEventListener("resize", updatePillPosition)
  }, [currentHighlightIndex])

  // Simple fallback since useLayoutEffect may run before children fully mount/render
  useEffect(() => {
    updatePillPosition()
  }, [items, activeHref])

  // Map easing function from GSAP style to CSS transition-timing-function
  const getCssEase = (gsapEase) => {
    if (gsapEase === "power2.easeOut") {
      return "cubic-bezier(0.25, 0.46, 0.45, 0.94)" // easeOutQuad
    }
    return "cubic-bezier(0.4, 0, 0.2, 1)" // easeInOut
  }

  return (
    <div
      className={cn(
        "inline-flex items-center gap-2 rounded-full border border-border p-1 shadow-lg",
        className
      )}
      style={{ backgroundColor: baseColor }}
    >
      {/* Logo container */}
      {logo && (
        <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-black/40 border border-border p-1 ml-1">
          {typeof logo === "string" ? (
            <img src={logo} alt={logoAlt} className="h-full w-full object-contain" />
          ) : (
            logo
          )}
        </div>
      )}

      {/* Navigation items wrapper */}
      <div className="relative flex items-center gap-1.5 pr-1.5">
        {/* Animated Sliding Pill Background */}
        <div
          className="absolute top-0 bottom-0 rounded-full transition-all duration-300"
          style={{
            transform: `translateX(${pillStyle.left}px)`,
            width: `${pillStyle.width}px`,
            backgroundColor: pillColor,
            transitionTimingFunction: getCssEase(ease),
          }}
        />

        {/* Navigation items */}
        {items.map((item, index) => {
          const isActive = index === activeIndex
          const isHovered = index === hoveredIndex
          const isHighlighted = index === currentHighlightIndex

          const isExternal = item.href?.startsWith("http") || item.href?.startsWith("#")
          const Comp = isExternal ? "a" : Link
          const toProp = isExternal ? { href: item.href } : { to: item.href || item.path }

          return (
            <Comp
              key={item.label}
              ref={(el) => (itemRefs.current[index] = el)}
              {...toProp}
              onMouseEnter={() => setHoveredIndex(index)}
              onMouseLeave={() => setHoveredIndex(null)}
              className={cn(
                "relative z-10 rounded-full px-4 py-1 text-[11px] font-mono font-medium uppercase tracking-[0.08em] transition-colors duration-200 select-none cursor-pointer"
              )}
              style={{
                color: isHighlighted
                  ? isHovered
                    ? hoveredPillTextColor
                    : pillTextColor
                  : "var(--color-text-muted)", // use tailwind design token text-muted
              }}
            >
              {item.label}
            </Comp>
          )
        })}
      </div>
    </div>
  )
}

export default PillNav
