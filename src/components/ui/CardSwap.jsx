import React, {
  Children,
  cloneElement,
  forwardRef,
  isValidElement,
  useEffect,
  useMemo,
  useRef,
  useState,
  useCallback
} from 'react'
import gsap from 'gsap'
import './CardSwap.css'

export const Card = forwardRef(({ customClass, className, style, ...rest }, ref) => (
  <div
    ref={ref}
    {...rest}
    style={style}
    className={`card-swap-item ${customClass ?? ''} ${className ?? ''}`.trim()}
  />
))
Card.displayName = 'Card'

const makeSlot = (i, distX, distY, total) => {
  // Center the stack horizontally and vertically so it never clips or overflows
  const centerOffsetX = -((total - 1) * distX) / 2
  const centerOffsetY = ((total - 1) * distY) / 2
  return {
    x: centerOffsetX + i * distX,
    y: centerOffsetY - i * distY,
    z: -i * distX * 1.5,
    zIndex: total - i
  }
}

const placeNow = (el, slot, skew) => {
  if (!el) return
  gsap.set(el, {
    x: slot.x,
    y: slot.y,
    z: slot.z,
    xPercent: -50,
    yPercent: -50,
    skewY: skew,
    transformOrigin: 'center center',
    zIndex: slot.zIndex,
    force3D: true
  })
}

export const CardSwap = ({
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
  children
}) => {
  const [windowWidth, setWindowWidth] = useState(() =>
    typeof window !== 'undefined' ? window.innerWidth : 1200
  )

  useEffect(() => {
    let timer
    const handleResize = () => {
      clearTimeout(timer)
      timer = setTimeout(() => {
        setWindowWidth(window.innerWidth)
      }, 80)
    }
    window.addEventListener('resize', handleResize)
    return () => {
      clearTimeout(timer)
      window.removeEventListener('resize', handleResize)
    }
  }, [])

  const isMobile = windowWidth < 640
  const isTablet = windowWidth >= 640 && windowWidth < 1024

  // Compute responsive dimensions dynamically so mobile screens never clip
  const effectiveWidth = useMemo(() => {
    if (isMobile) return Math.min(windowWidth - 36, 350)
    if (isTablet) return Math.min(windowWidth - 80, 500)
    return width
  }, [width, windowWidth, isMobile, isTablet])

  const effectiveHeight = useMemo(() => {
    if (isMobile) return Math.min(Math.round(effectiveWidth * 1.25), 450)
    if (isTablet) return 420
    return height
  }, [height, effectiveWidth, isMobile, isTablet])

  const effectiveCardDist = useMemo(() => {
    if (isMobile) return 12
    if (isTablet) return 24
    return cardDistance
  }, [cardDistance, isMobile, isTablet])

  const effectiveVertDist = useMemo(() => {
    if (isMobile) return 16
    if (isTablet) return 26
    return verticalDistance
  }, [verticalDistance, isMobile, isTablet])

  const effectiveSkew = useMemo(() => {
    if (isMobile) return 1.5
    if (isTablet) return 2.5
    return skewAmount
  }, [skewAmount, isMobile, isTablet])

  const childArr = useMemo(() => Children.toArray(children), [children])
  const refs = useMemo(() => childArr.map(() => React.createRef()), [childArr.length])

  const order = useRef(Array.from({ length: childArr.length }, (_, i) => i))
  const tlRef = useRef(null)
  const intervalRef = useRef(0)
  const container = useRef(null)
  const isAnimatingRef = useRef(false)

  // Fast, crisp animation timing
  const config = useMemo(() => ({
    ease: 'power3.out',
    durDrop: 0.55,
    durMove: 0.55,
    durReturn: 0.55,
    promoteOverlap: 0.75,
    returnDelay: 0.08
  }), [])

  // Position all elements on mount or responsive dimension changes
  useEffect(() => {
    const total = refs.length
    if (total === 0) return

    order.current.forEach((originalIdx, slotIdx) => {
      const el = refs[originalIdx]?.current
      if (el) {
        placeNow(el, makeSlot(slotIdx, effectiveCardDist, effectiveVertDist, total), effectiveSkew)
      }
    })
  }, [effectiveCardDist, effectiveVertDist, effectiveSkew, refs])

  // Core fast swap animation
  const swap = useCallback(() => {
    if (order.current.length < 2 || isAnimatingRef.current) return
    isAnimatingRef.current = true

    const [front, ...rest] = order.current
    const elFront = refs[front]?.current
    if (!elFront) {
      isAnimatingRef.current = false
      return
    }

    const tl = gsap.timeline({
      onComplete: () => {
        isAnimatingRef.current = false
      }
    })
    tlRef.current = tl

    // Drop front card down
    tl.to(elFront, {
      y: '+=420',
      duration: config.durDrop,
      ease: config.ease
    })

    tl.addLabel('promote', `-=${config.durDrop * config.promoteOverlap}`)
    
    // Move remaining cards forward by one slot
    rest.forEach((idx, i) => {
      const el = refs[idx]?.current
      if (!el) return
      const slot = makeSlot(i, effectiveCardDist, effectiveVertDist, refs.length)
      tl.set(el, { zIndex: slot.zIndex }, 'promote')
      tl.to(
        el,
        {
          x: slot.x,
          y: slot.y,
          z: slot.z,
          duration: config.durMove,
          ease: config.ease
        },
        `promote+=${i * 0.04}`
      )
    })

    // Slide front card into back slot
    const backSlot = makeSlot(refs.length - 1, effectiveCardDist, effectiveVertDist, refs.length)
    tl.addLabel('return', `promote+=${config.durMove * config.returnDelay}`)
    tl.call(
      () => {
        if (elFront) {
          gsap.set(elFront, { zIndex: backSlot.zIndex })
        }
      },
      undefined,
      'return'
    )
    tl.to(
      elFront,
      {
        x: backSlot.x,
        y: backSlot.y,
        z: backSlot.z,
        duration: config.durReturn,
        ease: config.ease
      },
      'return'
    )

    tl.call(() => {
      order.current = [...rest, front]
      onActiveChange?.(rest[0])
    })
  }, [config, effectiveCardDist, effectiveVertDist, refs, onActiveChange])

  // Instant smooth jump to target card
  const jumpTo = useCallback((targetIdx) => {
    if (order.current.length < 2 || targetIdx === order.current[0] || isAnimatingRef.current) return
    const pos = order.current.indexOf(targetIdx)
    if (pos === -1) return

    isAnimatingRef.current = true
    const newOrder = [
      ...order.current.slice(pos),
      ...order.current.slice(0, pos)
    ]
    order.current = newOrder

    const tl = gsap.timeline({
      onComplete: () => {
        isAnimatingRef.current = false
      }
    })
    tlRef.current = tl

    newOrder.forEach((idx, slotIdx) => {
      const el = refs[idx]?.current
      if (!el) return
      const slot = makeSlot(slotIdx, effectiveCardDist, effectiveVertDist, refs.length)
      tl.set(el, { zIndex: slot.zIndex })
      tl.to(
        el,
        {
          x: slot.x,
          y: slot.y,
          z: slot.z,
          duration: 0.45,
          ease: 'power3.out'
        },
        0
      )
    })

    onActiveChange?.(targetIdx)
  }, [effectiveCardDist, effectiveVertDist, refs, onActiveChange])

  // External sync from activeCardIndex prop
  useEffect(() => {
    if (activeCardIndex !== undefined && activeCardIndex !== order.current[0]) {
      jumpTo(activeCardIndex)
    }
  }, [activeCardIndex, jumpTo])

  // Interval timer for auto-swap
  useEffect(() => {
    if (delay <= 0) return

    intervalRef.current = window.setInterval(swap, delay)

    const node = container.current
    if (pauseOnHover && node) {
      const pause = () => {
        tlRef.current?.pause()
        clearInterval(intervalRef.current)
      }
      const resume = () => {
        tlRef.current?.play()
        clearInterval(intervalRef.current)
        intervalRef.current = window.setInterval(swap, delay)
      }
      node.addEventListener('mouseenter', pause)
      node.addEventListener('mouseleave', resume)
      return () => {
        node.removeEventListener('mouseenter', pause)
        node.removeEventListener('mouseleave', resume)
        clearInterval(intervalRef.current)
        tlRef.current?.kill()
      }
    }

    return () => {
      clearInterval(intervalRef.current)
      tlRef.current?.kill()
    }
  }, [delay, pauseOnHover, swap])

  const rendered = childArr.map((child, i) =>
    isValidElement(child)
      ? cloneElement(child, {
          key: i,
          ref: refs[i],
          style: {
            width: effectiveWidth,
            height: effectiveHeight,
            ...(child.props.style ?? {})
          },
          onClick: (e) => {
            child.props.onClick?.(e)
            onCardClick?.(i)
            if (i !== order.current[0]) {
              jumpTo(i)
            } else {
              swap()
            }
          }
        })
      : child
  )

  return (
    <div
      ref={container}
      className="card-swap-container"
      style={{
        width: effectiveWidth,
        height: effectiveHeight
      }}
    >
      {rendered}
    </div>
  )
}

export default CardSwap
