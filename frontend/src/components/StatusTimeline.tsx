import { useState, useEffect, useCallback } from 'react'
import { useInView } from '../hooks/useInView'
import { STATUS_PHASES } from '../data/mockData'

export default function StatusTimeline() {
  const { ref, isInView } = useInView({ threshold: 0.2 })
  const [activeStep, setActiveStep] = useState(-1)

  const totalPhases = STATUS_PHASES?.length ?? 0

  // Auto-progress through timeline phases when visible
  const tick = useCallback(() => {
    setActiveStep(prev => {
      if (prev >= totalPhases - 1) return totalPhases - 1 // stay on final
      return prev + 1
    })
  }, [totalPhases])

  useEffect(() => {
    if (!isInView || totalPhases === 0) return

    // Kick off the first step immediately
    const initialDelay = setTimeout(() => setActiveStep(0), 400)

    // Then advance every 2s
    const interval = setInterval(tick, 2000)

    return () => {
      clearTimeout(initialDelay)
      clearInterval(interval)
    }
  }, [isInView, tick, totalPhases])

  return (
    <section ref={ref} className={`relative py-28 px-6 md:px-12 section-reveal ${isInView ? 'in-view' : ''}`}>
      {/* Accent line separator */}
      <div className="absolute top-0 left-1/2 -translate-x-1/2 w-24 h-px bg-accent opacity-30" />

      <div className="max-w-[800px] mx-auto">
        {/* Section header */}
        <div className="text-center mb-16">
          <div className="font-label text-[0.6rem] text-accent uppercase tracking-[0.3em] mb-3">
            [ ENGAGEMENT PROTOCOL ]
          </div>
          <h2 className="font-display text-[3rem] sm:text-[4rem] text-text-primary leading-none m-0">
            LIVE OPERATION STATUS
          </h2>
          <p className="font-mono text-[0.8rem] text-text-muted mt-3 max-w-[520px] mx-auto">
            After submitting your URL, this is what happens inside RedShell — in real time.
          </p>
        </div>

        {/* Vertical timeline */}
        <div className="relative ml-4 sm:ml-8">
          {/* Vertical line track */}
          <div className="absolute left-3 top-0 bottom-0 w-px bg-border-subtle">
            <div
              className="w-full bg-accent origin-top"
              style={{
                height: activeStep >= 0
                  ? `${Math.min(((activeStep + 0.5) / Math.max(totalPhases - 1, 1)) * 100, 100)}%`
                  : '0%',
                transition: 'height 0.8s cubic-bezier(0.16, 1, 0.3, 1)',
              }}
            />
          </div>

          {/* Phase rows */}
          <div className="flex flex-col gap-0">
            {(STATUS_PHASES ?? []).map((phase, i) => {
              const isCompleted = i < activeStep
              const isActive = i === activeStep
              const isPending = i > activeStep

              return (
                <div
                  key={phase.status}
                  className="relative pl-10 pb-8 last:pb-0"
                  style={{
                    animation: isInView
                      ? `slide-in-left 0.5s ${0.2 + i * 0.1}s both`
                      : 'none',
                    opacity: isInView ? undefined : 0,
                  }}
                >
                  {/* Dot */}
                  <div
                    className={`absolute left-0 top-1 w-[25px] h-[25px] rounded-full border-2 flex items-center justify-center transition-all duration-500 ${
                      isCompleted
                        ? 'border-success bg-success/10'
                        : isActive
                          ? 'border-accent bg-accent/10'
                          : 'border-border-subtle bg-bg-card'
                    }`}
                    style={isActive ? { animation: 'timeline-dot-pulse 2s ease-in-out infinite' } : undefined}
                  >
                    {isCompleted && (
                      <svg width="12" height="12" viewBox="0 0 12 12" fill="none" stroke="var(--color-success)" strokeWidth="2">
                        <polyline points="2,6 5,9 10,3" />
                      </svg>
                    )}
                    {isActive && (
                      <div
                        className="w-2 h-2 rounded-full bg-accent"
                        style={{ animation: 'dot-blink 1.2s ease-in-out infinite' }}
                      />
                    )}
                    {isPending && (
                      <div className="w-1.5 h-1.5 rounded-full bg-border-subtle" />
                    )}
                  </div>

                  {/* Content card */}
                  <div
                    className={`border p-4 transition-all duration-500 ${
                      isActive
                        ? 'bg-bg-card border-accent/40 shadow-[0_0_20px_rgba(0,229,255,0.06)]'
                        : isCompleted
                          ? 'bg-bg-card/50 border-success/20'
                          : 'bg-bg-card/30 border-border-subtle'
                    }`}
                  >
                    {/* Status badge */}
                    <div className="flex items-center gap-3 mb-1.5">
                      <span
                        className={`font-mono text-[0.65rem] font-bold tracking-[0.15em] ${
                          isActive
                            ? 'text-accent'
                            : isCompleted
                              ? 'text-success'
                              : 'text-text-dim'
                        }`}
                      >
                        [ {phase.status} ]
                      </span>
                      <span
                        className={`font-label text-[0.6rem] tracking-wider uppercase ${
                          isPending ? 'text-text-dim' : 'text-text-muted'
                        }`}
                      >
                        {phase.label}
                      </span>
                    </div>

                    {/* Detail text */}
                    <p
                      className={`font-mono text-[0.7rem] leading-relaxed m-0 transition-colors duration-500 ${
                        isActive
                          ? 'text-text-muted'
                          : isCompleted
                            ? 'text-text-dim'
                            : 'text-text-dim/50'
                      }`}
                    >
                      {phase.detail}
                    </p>

                    {/* Active state blinking cursor */}
                    {isActive && (
                      <span
                        className="inline-block w-1.5 h-3.5 bg-accent ml-0.5 mt-1 align-middle"
                        style={{ animation: 'cursor-blink 1s step-end infinite' }}
                      />
                    )}
                  </div>
                </div>
              )
            })}
          </div>

          {/* Summary line after completion */}
          {activeStep >= totalPhases - 1 && (
            <div
              className="mt-8 ml-10 flex items-center gap-3"
              style={{ animation: 'fade-slide-up 0.5s 0.3s both' }}
            >
              <span
                className="inline-block w-2 h-2 rounded-full bg-accent"
                style={{ animation: 'dot-blink 2s ease-in-out infinite' }}
              />
              <span className="font-mono text-[0.8rem] text-accent font-bold">
                28 findings documented — Report ready for review
              </span>
            </div>
          )}
        </div>
      </div>
    </section>
  )
}
