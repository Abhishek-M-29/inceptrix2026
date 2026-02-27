import { lazy, Suspense, useState, useMemo, useEffect, useRef, Component, type ReactNode } from 'react'

const Spline = lazy(() => import('@splinetool/react-spline'))

// Error boundary to catch Spline runtime crashes
class SplineErrorBoundary extends Component<{ children: ReactNode; onError: () => void }, { hasError: boolean }> {
  state = { hasError: false }
  static getDerivedStateFromError() { return { hasError: true } }
  componentDidCatch() { this.props.onError() }
  render() { return this.state.hasError ? null : this.props.children }
}

interface SplineGlobeProps {
  sceneUrl: string
  className?: string
}

function checkSplineCapability(): boolean {
  if (typeof window === 'undefined') return false
  if (window.innerWidth < 768) return false
  if (navigator.hardwareConcurrency <= 2) return false
  const canvas = document.createElement('canvas')
  const gl = canvas.getContext('webgl2') || canvas.getContext('webgl')
  return !!gl
}

export default function SplineGlobe({ sceneUrl, className = '' }: SplineGlobeProps) {
  const [loaded, setLoaded] = useState(false)
  const [failed, setFailed] = useState(false)
  const canLoad = useMemo(() => checkSplineCapability(), [])
  const timeoutRef = useRef<ReturnType<typeof setTimeout>>(undefined)

  useEffect(() => {
    if (!canLoad) return
    timeoutRef.current = setTimeout(() => {
      if (!loaded) setFailed(true)
    }, 10000)
    return () => clearTimeout(timeoutRef.current)
  }, [canLoad, loaded])

  const onLoad = () => {
    clearTimeout(timeoutRef.current)
    setLoaded(true)
  }

  const showSpline = canLoad && !failed && sceneUrl && !sceneUrl.includes('REPLACE_ME')

  return (
    <div className={`relative w-full h-full ${className}`} style={{ contain: 'strict' }}>
      {/* Fallback: CSS wireframe globe */}
      <div
        className="absolute inset-0 flex items-center justify-center transition-opacity duration-700"
        style={{ opacity: loaded ? 0 : 1 }}
      >
        <div className="relative">
          {/* Outer ring */}
          <div
            className="rounded-full border border-border-subtle"
            style={{
              width: 'min(440px, 80vw)',
              height: 'min(440px, 80vw)',
              animation: 'spin 60s linear infinite',
              borderStyle: 'dashed',
            }}
          />
          {/* Inner cross lines */}
          <div
            className="absolute top-1/2 left-0 w-full border-t border-border-subtle"
            style={{ opacity: 0.3 }}
          />
          <div
            className="absolute left-1/2 top-0 h-full border-l border-border-subtle"
            style={{ opacity: 0.3 }}
          />
          {/* Tilted ellipse */}
          <div
            className="absolute inset-[15%] rounded-full border border-border-subtle"
            style={{
              transform: 'rotateX(60deg)',
              opacity: 0.3,
              borderStyle: 'dashed',
            }}
          />
          {/* Second tilted ellipse */}
          <div
            className="absolute inset-[15%] rounded-full border border-border-subtle"
            style={{
              transform: 'rotateY(60deg)',
              opacity: 0.2,
              borderStyle: 'dashed',
            }}
          />
          {/* Cyan target dot */}
          <div
            className="absolute top-[30%] right-[25%] w-3 h-3 rounded-full bg-accent"
            style={{ animation: 'dot-blink 2s ease-in-out infinite', boxShadow: '0 0 12px rgba(0,229,255,0.6)' }}
          />
          {/* Reticle around target */}
          <div
            className="absolute top-[30%] right-[25%] w-8 h-8 -mt-2.5 -mr-2.5 border border-accent rounded-full"
            style={{
              animation: 'dot-blink 2s ease-in-out infinite',
              opacity: 0.5,
              transform: 'translate(50%, -50%)',
            }}
          />
          {/* Scattered dots */}
          {[
            { top: '20%', left: '40%' },
            { top: '55%', left: '25%' },
            { top: '45%', left: '65%' },
            { top: '70%', left: '45%' },
            { top: '35%', left: '55%' },
            { top: '60%', left: '70%' },
          ].map((pos, i) => (
            <div
              key={i}
              className="absolute w-1 h-1 rounded-full bg-text-dim"
              style={{ ...pos, animationDelay: `${i * 0.4}s`, animation: 'dot-blink 3s ease-in-out infinite' }}
            />
          ))}
        </div>
      </div>

      {/* Spline scene — interactive, scroll hijacking blocked */}
      {showSpline && (
        <div
          className="spline-globe-wrapper"
          style={{
            position: 'absolute',
            inset: 0,
            overflow: 'hidden',
            pointerEvents: 'auto',
            isolation: 'isolate',
            zIndex: 1,
          }}
          onWheel={(e) => e.stopPropagation()}
          onScroll={(e) => e.stopPropagation()}
          onKeyDown={(e) => e.stopPropagation()}
        >
          <SplineErrorBoundary onError={() => setFailed(true)}>
            <Suspense fallback={null}>
              <Spline
                scene={sceneUrl}
                onLoad={onLoad}
                style={{
                  position: 'absolute',
                  top: 0,
                  left: 0,
                  width: '100%',
                  height: '100%',
                  opacity: loaded ? 1 : 0,
                  transition: 'opacity 0.8s ease',
                  pointerEvents: 'auto',
                }}
              />
            </Suspense>
          </SplineErrorBoundary>
        </div>
      )}
    </div>
  )
}
