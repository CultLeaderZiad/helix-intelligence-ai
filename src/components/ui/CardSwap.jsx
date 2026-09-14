import React, {
  Children,
  cloneElement,
  forwardRef,
  isValidElement,
  useEffect,
  useMemo,
  useRef
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

const makeSlot = (i, distX, distY, total) => ({
  x: i * distX,
  y: -i * distY,
  z: -i * distX * 1.5,
  zIndex: total - i
})

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
  width = 540,
  height = 420,
  cardDistance = 60,
  verticalDistance = 55,
  delay = 4500,
  pauseOnHover = true,
  onCardClick,
  skewAmount = 4,
  easing = 'elastic',
  children
}) => {
  const config =
    easing === 'elastic'
      ? {
          ease: 'elastic.out(0.6,0.9)',
          durDrop: 1.8,
          durMove: 1.8,
          durReturn: 1.8,
          promoteOverlap: 0.9,
          returnDelay: 0.05
        }
      : {
          ease: 'power1.inOut',
          durDrop: 0.8,
          durMove: 0.8,
          durReturn: 0.8,
          promoteOverlap: 0.45,
          returnDelay: 0.2
        }

  const childArr = useMemo(() => Children.toArray(children), [children])
  const refs = useMemo(() => childArr.map(() => React.createRef()), [childArr.length])

  const order = useRef(Array.from({ length: childArr.length }, (_, i) => i))
  const tlRef = useRef(null)
  const intervalRef = useRef(0)
  const container = useRef(null)

  useEffect(() => {
    const total = refs.length
    if (total === 0) return

    refs.forEach((r, i) => {
      if (r.current) {
        placeNow(r.current, makeSlot(i, cardDistance, verticalDistance, total), skewAmount)
      }
    })

    const swap = () => {
      if (order.current.length < 2) return

      const [front, ...rest] = order.current
      const elFront = refs[front]?.current
      if (!elFront) return

      const tl = gsap.timeline()
      tlRef.current = tl

      tl.to(elFront, {
        y: '+=500',
        duration: config.durDrop,
        ease: config.ease
      })

      tl.addLabel('promote', `-=${config.durDrop * config.promoteOverlap}`)
      rest.forEach((idx, i) => {
        const el = refs[idx]?.current
        if (!el) return
        const slot = makeSlot(i, cardDistance, verticalDistance, refs.length)
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
          `promote+=${i * 0.15}`
        )
      })

      const backSlot = makeSlot(refs.length - 1, cardDistance, verticalDistance, refs.length)
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
      })
    }

    intervalRef.current = window.setInterval(swap, delay)

    const node = container.current
    if (pauseOnHover && node) {
      const pause = () => {
        tlRef.current?.pause()
        clearInterval(intervalRef.current)
      }
      const resume = () => {
        tlRef.current?.play()
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
  }, [cardDistance, verticalDistance, delay, pauseOnHover, skewAmount, easing, refs])

  const rendered = childArr.map((child, i) =>
    isValidElement(child)
      ? cloneElement(child, {
          key: i,
          ref: refs[i],
          style: { width, height, ...(child.props.style ?? {}) },
          onClick: (e) => {
            child.props.onClick?.(e)
            onCardClick?.(i)
          }
        })
      : child
  )

  return (
    <div ref={container} className="card-swap-container" style={{ width, height }}>
      {rendered}
    </div>
  )
}

export default CardSwap
