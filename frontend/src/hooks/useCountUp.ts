import { useEffect, useState } from 'react'

export function useCountUp(
  target: number,
  duration: number = 2000,
  shouldStart: boolean = true
) {
  const [value, setValue] = useState(0)

  useEffect(() => {
    if (!shouldStart) return

    let startTime: number | null = null
    let animationId: number

    const easeOutCubic = (t: number) => 1 - Math.pow(1 - t, 3)

    const animate = (timestamp: number) => {
      if (startTime === null) startTime = timestamp
      const elapsed = timestamp - startTime
      const progress = Math.min(elapsed / duration, 1)
      const easedProgress = easeOutCubic(progress)

      setValue(Math.floor(easedProgress * target))

      if (progress < 1) {
        animationId = requestAnimationFrame(animate)
      }
    }

    animationId = requestAnimationFrame(animate)
    return () => cancelAnimationFrame(animationId)
  }, [target, duration, shouldStart])

  return value
}
