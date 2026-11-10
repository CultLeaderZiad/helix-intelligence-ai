import React, {
  Children,
  cloneElement,
  forwardRef,
  isValidElement,
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react"
import { gsap } from "gsap"
import "./CardSwap.css"

/**
 * Stacked, auto-swapping cards (React Bits "CardSwap"), restored from the
 * landing page that ships on main. GSAP is imported only here, so it loads
 * with the lazy landing chunk and never with the app shell. Auto-swap pauses
 * off-screen, on hover, and entirely under prefers-reduced-motion.
 */

/** @type {React.ForwardRefExoticComponent<React.HTMLAttributes<HTMLDivElement> & { customClass?: string } & React.RefAttributes<HTMLDivElement>>} */
export const Card = forwardRef(function Card({ customClass, className, ...rest }, ref) {
  return (
    <div
      ref={ref}
      {...rest}
      className={`card-swap-item ${customClass ?? ""} ${className ?? ""}`.trim()}
    />
  )
})

/** @param {number} i @param {number} distX @param {number} distY @param {number} total */
const makeSlot = (i, distX, distY, total) => {
  const centerOffsetX = -((total - 1) * distX) / 2
  const centerOffsetY = ((total - 1) * distY) / 2
  return {
    x: centerOffsetX + i * distX,
    y: centerOffsetY - i * distY,
    z: -i * distX * 1.5,
    zIndex: total - i,
  }
}

/** @param {Element | null} el @param {ReturnType<typeof makeSlot>} slot @param {number} skew */
const placeNow = (el, slot, skew) => {
  if (!el) return
  gsap.set(el, {
    x: slot.x,
    y: slot.y,
    z: slot.z,
    xPercent: -50,
    yPercent: -50,
    skewY: skew,
    transformOrigin: "center center",
    zIndex: slot.zIndex,
    force3D: true,
  })
}

function prefersReducedMotion() {
  return typeof window !== "undefined" && window.matchMedia?.("(prefers-reduced-motion: reduce)").matches === true
}

/**
 * @param {{
 *   width?: number, height?: number, cardDistance?: number, verticalDistance?: number,
 *   delay?: number, pauseOnHover?: boolean, skewAmount?: number,
 *   activeCardIndex?: number, onActiveChange?: (index: number) => void,
 *   onCardClick?: (index: number) => void, children?: React.ReactNode
 * }} props
 */
export function CardSwap({
  width = 580,
  height = 450,
  cardDistance = 38,
  verticalDistance = 40,
  delay = 2800,
  pauseOnHover = true,
  onCardClick,
  onActiveChange,
  activeCardIndex,
  skewAmount = 3.5,
  children,
}) {
  const [windowWidth, setWindowWidth] = useState(() => (typeof window !== "undefined" ? window.innerWidth : 1200))

  useEffect(() => {
    /** @type {ReturnType<typeof setTimeout> | undefined} */
    let timer
    const handleResize = () => {
      clearTimeout(timer)
      timer = setTimeout(() => setWindowWidth(window.innerWidth), 80)
    }
    window.addEventListener("resize", handleResize)
    return () => {
      clearTimeout(timer)
      window.removeEventListener("resize", handleResize)
    }
  }, [])

  const isMobile = windowWidth < 640
  const isTablet = windowWidth >= 640 && windowWidth < 1024
  const effectiveWidth = isMobile ? Math.min(windowWidth - 36, 350) : isTablet ? Math.min(windowWidth - 80, 500) : width
  const effectiveHeight = isMobile ? Math.min(Math.round(effectiveWidth * 1.25), 450) : isTablet ? 420 : height
  const effectiveCardDist = isMobile ? 12 : isTablet ? 24 : cardDistance
  const effectiveVertDist = isMobile ? 16 : isTablet ? 26 : verticalDistance
  const effectiveSkew = isMobile ? 1.5 : isTablet ? 2.5 : skewAmount

  const childArr = useMemo(() => Children.toArray(children), [children])
  const count = childArr.length
  /** @type {React.RefObject<HTMLDivElement | null>[]} */
  const refs = useMemo(() => Array.from({ length: count }, () => React.createRef()), [count])

  const order = useRef(Array.from({ length: count }, (_, i) => i))
  /** @type {React.MutableRefObject<gsap.core.Timeline | null>} */
  const tlRef = useRef(null)
  /** @type {React.MutableRefObject<number | undefined>} */
  const intervalRef = useRef(undefined)
  /** @type {React.RefObject<HTMLDivElement | null>} */
  const container = useRef(null)
  const isAnimatingRef = useRef(false)
  const [isInView, setIsInView] = useState(false)

  useEffect(() => {
    const node = container.current
    if (!node || typeof IntersectionObserver === "undefined") {
      setIsInView(true)
      return
    }
    const observer = new IntersectionObserver(([entry]) => setIsInView(entry.isIntersecting), { threshold: 0.15 })
    observer.observe(node)
    return () => observer.disconnect()
  }, [])

  useEffect(() => {
    order.current.forEach((originalIdx, slotIdx) => {
      placeNow(refs[originalIdx]?.current ?? null, makeSlot(slotIdx, effectiveCardDist, effectiveVertDist, refs.length), effectiveSkew)
    })
  }, [effectiveCardDist, effectiveVertDist, effectiveSkew, refs])

  const swap = useCallback(() => {
    if (order.current.length < 2 || isAnimatingRef.current) return
    const [front, ...rest] = order.current
    const elFront = refs[front]?.current
    if (!elFront) return
    isAnimatingRef.current = true

    const tl = gsap.timeline({ onComplete: () => { isAnimatingRef.current = false } })
    tlRef.current = tl
    tl.to(elFront, { y: "+=420", duration: 0.5, ease: "power3.out" })
    tl.addLabel("promote", `-=${0.5 * 0.75}`)
    rest.forEach((idx, i) => {
      const el = refs[idx]?.current
      if (!el) return
      const slot = makeSlot(i, effectiveCardDist, effectiveVertDist, refs.length)
      tl.set(el, { zIndex: slot.zIndex }, "promote")
      tl.to(el, { x: slot.x, y: slot.y, z: slot.z, duration: 0.5, ease: "power3.out" }, `promote+=${i * 0.04}`)
    })
    const backSlot = makeSlot(refs.length - 1, effectiveCardDist, effectiveVertDist, refs.length)
    tl.addLabel("return", `promote+=${0.5 * 0.08}`)
    tl.call(() => { gsap.set(elFront, { zIndex: backSlot.zIndex }) }, undefined, "return")
    tl.to(elFront, { x: backSlot.x, y: backSlot.y, z: backSlot.z, duration: 0.5, ease: "power3.out" }, "return")
    tl.call(() => {
      order.current = [...rest, front]
      onActiveChange?.(rest[0])
    })
  }, [effectiveCardDist, effectiveVertDist, refs, onActiveChange])

  const jumpTo = useCallback((/** @type {number} */ targetIdx) => {
    if (order.current.length < 2 || targetIdx === order.current[0]) return
    // An explicit choice always wins: finish any running swap at its end
    // state, then rebuild the order from the settled stack.
    if (tlRef.current?.isActive()) tlRef.current.progress(1)
    tlRef.current?.kill()
    isAnimatingRef.current = false
    const pos = order.current.indexOf(targetIdx)
    if (pos === -1) return
    const newOrder = [...order.current.slice(pos), ...order.current.slice(0, pos)]
    order.current = newOrder
    const reduced = prefersReducedMotion()
    const tl = reduced ? null : gsap.timeline()
    tlRef.current = tl
    newOrder.forEach((idx, slotIdx) => {
      const el = refs[idx]?.current
      if (!el) return
      const slot = makeSlot(slotIdx, effectiveCardDist, effectiveVertDist, refs.length)
      if (!tl) {
        gsap.set(el, { x: slot.x, y: slot.y, z: slot.z, zIndex: slot.zIndex })
        return
      }
      tl.set(el, { zIndex: slot.zIndex }, 0)
      tl.to(el, { x: slot.x, y: slot.y, z: slot.z, duration: 0.45, ease: "power3.out" }, 0)
    })
    onActiveChange?.(targetIdx)
  }, [effectiveCardDist, effectiveVertDist, refs, onActiveChange])

  useEffect(() => {
    if (activeCardIndex !== undefined && activeCardIndex !== order.current[0]) jumpTo(activeCardIndex)
  }, [activeCardIndex, jumpTo])

  useEffect(() => {
    if (delay <= 0 || !isInView || prefersReducedMotion()) {
      tlRef.current?.pause()
      window.clearInterval(intervalRef.current)
      return
    }
    intervalRef.current = window.setInterval(swap, delay)
    const node = container.current
    const pause = () => {
      tlRef.current?.pause()
      window.clearInterval(intervalRef.current)
    }
    const resume = () => {
      tlRef.current?.play()
      window.clearInterval(intervalRef.current)
      intervalRef.current = window.setInterval(swap, delay)
    }
    if (pauseOnHover && node) {
      node.addEventListener("mouseenter", pause)
      node.addEventListener("mouseleave", resume)
      node.addEventListener("focusin", pause)
      node.addEventListener("focusout", resume)
    }
    return () => {
      if (pauseOnHover && node) {
        node.removeEventListener("mouseenter", pause)
        node.removeEventListener("mouseleave", resume)
        node.removeEventListener("focusin", pause)
        node.removeEventListener("focusout", resume)
      }
      window.clearInterval(intervalRef.current)
      tlRef.current?.kill()
    }
  }, [delay, pauseOnHover, swap, isInView])

  const rendered = childArr.map((child, i) => {
    if (!isValidElement(child)) return child
    /** @type {React.ReactElement<{ style?: React.CSSProperties, onClick?: (e: React.MouseEvent) => void }>} */
    const element = /** @type {any} */ (child)
    return cloneElement(element, {
      key: i,
      // @ts-expect-error ref is forwarded by Card
      ref: refs[i],
      style: { width: effectiveWidth, height: effectiveHeight, ...(element.props.style ?? {}) },
      onClick: (/** @type {React.MouseEvent} */ e) => {
        element.props.onClick?.(e)
        onCardClick?.(i)
        if (i !== order.current[0]) jumpTo(i)
        else if (prefersReducedMotion()) jumpTo(order.current[1] ?? i)
        else swap()
      },
    })
  })

  return (
    <div ref={container} className="card-swap-container" style={{ width: effectiveWidth, height: effectiveHeight }}>
      {rendered}
    </div>
  )
}

export default CardSwap
