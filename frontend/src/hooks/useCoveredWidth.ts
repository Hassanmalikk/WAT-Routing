import { type RefObject, useLayoutEffect, useState } from 'react'

export function useCoveredWidth(
  cover: RefObject<HTMLElement | null>,
  target: RefObject<HTMLElement | null>,
): number {
  const [width, setWidth] = useState(0)

  useLayoutEffect(() => {
    const coverElement = cover.current
    const targetElement = target.current
    if (!coverElement || !targetElement) return
    const observer = new ResizeObserver(() => {
      const covering = coverElement.getBoundingClientRect()
      const covered = targetElement.getBoundingClientRect()
      const overlaps = covering.top < covered.bottom && covering.bottom > covered.top
      setWidth(overlaps ? Math.max(0, Math.round(covering.right - covered.left)) : 0)
    })
    observer.observe(coverElement)
    observer.observe(targetElement)
    return () => observer.disconnect()
  }, [cover, target])

  return width
}
