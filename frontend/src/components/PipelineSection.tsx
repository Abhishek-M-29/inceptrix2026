import { useInView } from '../hooks/useInView'
import { PIPELINE_PHASES } from '../data/mockData'

function PhaseIcon({ icon }: { icon: string }) {
  switch (icon) {
    case 'crosshair':
      return (
        <svg width="32" height="32" viewBox="0 0 32 32" fill="none" stroke="currentColor" strokeWidth="1.5">
          <circle cx="16" cy="16" r="10" />
          <circle cx="16" cy="16" r="4" />
          <line x1="16" y1="2" x2="16" y2="8" />
          <line x1="16" y1="24" x2="16" y2="30" />
          <line x1="2" y1="16" x2="8" y2="16" />
          <line x1="24" y1="16" x2="30" y2="16" />
        </svg>
      )
    case 'container':
      return (
        <svg width="32" height="32" viewBox="0 0 32 32" fill="none" stroke="currentColor" strokeWidth="1.5">
          <rect x="4" y="8" width="24" height="18" rx="2" />
          <line x1="4" y1="14" x2="28" y2="14" />
          <circle cx="8" cy="11" r="1" fill="currentColor" />
          <circle cx="12" cy="11" r="1" fill="currentColor" />
          <line x1="8" y1="18" x2="24" y2="18" opacity="0.5" />
          <line x1="8" y1="22" x2="18" y2="22" opacity="0.3" />
        </svg>
      )
    case 'lightning':
      return (
        <svg width="32" height="32" viewBox="0 0 32 32" fill="none" stroke="currentColor" strokeWidth="1.5">
          <path d="M18 2L8 18h6l-2 12 12-16h-6l2-12z" />
          <circle cx="16" cy="16" r="14" strokeDasharray="4 4" opacity="0.3" />
        </svg>
      )
    case 'document':
      return (
        <svg width="32" height="32" viewBox="0 0 32 32" fill="none" stroke="currentColor" strokeWidth="1.5">
          <path d="M8 4h12l6 6v18H8V4z" />
          <path d="M20 4v6h6" />
          <line x1="12" y1="16" x2="24" y2="16" opacity="0.5" />
          <line x1="12" y1="20" x2="20" y2="20" opacity="0.3" />
          <line x1="12" y1="24" x2="22" y2="24" opacity="0.3" />
          <rect x="11" y="12" width="6" height="3" rx="1" fill="currentColor" opacity="0.8" />
        </svg>
      )
    default:
      return null
  }
}

export default function PipelineSection() {
  const { ref, isInView } = useInView({ threshold: 0.15 })

  return (
    <section ref={ref} className={`relative py-28 px-6 md:px-12 section-reveal ${isInView ? 'in-view' : ''}`}>
      <div className="max-w-[1200px] mx-auto">
        {/* Section header */}
        <div className="text-center mb-16">
          <div className="font-label text-[0.6rem] text-accent uppercase tracking-[0.3em] mb-3">
            [ OPERATIONAL SEQUENCE ]
          </div>
          <h2 className="font-display text-[3rem] sm:text-[4rem] text-text-primary leading-none m-0">
            THE PIPELINE
          </h2>
          <p className="font-mono text-[0.8rem] text-text-muted mt-3">
            Four phases. One command. Full coverage.
          </p>
        </div>

        {/* Pipeline cards */}
        <div className="relative">
          {/* Connecting line */}
          <div className="absolute top-1/2 left-0 h-px w-full bg-border-subtle -translate-y-1/2 hidden lg:block">
            <div
              className="h-full bg-accent"
              style={{
                width: isInView ? '100%' : '0%',
                transition: 'width 1.5s cubic-bezier(0.16, 1, 0.3, 1) 0.3s',
              }}
            />
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6 relative z-10">
            {PIPELINE_PHASES.map((phase, i) => (
              <div
                key={phase.number}
                className="group relative bg-bg-card border border-border-subtle p-6 transition-all duration-500 hover:border-accent/30 hover:bg-bg-card-hover"
                style={{
                  animation: isInView
                    ? `fade-slide-up 0.6s ${0.3 + i * 0.15}s both`
                    : 'none',
                  opacity: isInView ? undefined : 0,
                }}
              >
                {/* Phase number */}
                <div className="font-display text-[2.5rem] text-accent leading-none mb-4 opacity-30 group-hover:opacity-70 transition-opacity">
                  {phase.number}
                </div>

                {/* Icon */}
                <div className="text-text-dim mb-3 group-hover:text-accent transition-colors">
                  <PhaseIcon icon={phase.icon} />
                </div>

                {/* Title */}
                <h3 className="font-label text-sm text-text-primary tracking-[0.15em] mb-2">
                  {phase.title}
                </h3>

                {/* Description */}
                <p className="font-mono text-[0.7rem] text-text-muted leading-relaxed m-0">
                  {phase.description}
                </p>

                {/* Corner accent */}
                <div className="absolute top-0 right-0 w-3 h-3 border-t border-r border-accent/20 group-hover:border-accent/50 transition-colors" />
                <div className="absolute bottom-0 left-0 w-3 h-3 border-b border-l border-accent/20 group-hover:border-accent/50 transition-colors" />
              </div>
            ))}
          </div>
        </div>
      </div>
    </section>
  )
}
