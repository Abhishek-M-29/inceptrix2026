import { useInView } from '../hooks/useInView'
import { ARSENAL_TOOLS } from '../data/mockData'

/* ─── Inline SVG icons — one per tool ─── */

function ToolIcon({ icon }: { icon: string }) {
  const base = 'transition-colors duration-300'
  switch (icon) {
    /* nmap — sonar wave rings */
    case 'sonar':
      return (
        <svg className={base} width="36" height="36" viewBox="0 0 36 36" fill="none" stroke="currentColor" strokeWidth="1.4">
          <circle cx="18" cy="18" r="4" />
          <path d="M18 8a10 10 0 0 1 0 20" strokeDasharray="3 3" opacity="0.5" />
          <path d="M18 4a14 14 0 0 1 0 28" strokeDasharray="4 4" opacity="0.3" />
          <circle cx="18" cy="18" r="1.5" fill="currentColor" />
          <line x1="18" y1="14" x2="18" y2="6" strokeDasharray="2 2" opacity="0.4" />
          <line x1="22" y1="18" x2="30" y2="18" strokeDasharray="2 2" opacity="0.4" />
        </svg>
      )
    /* ffuf — fuzz / scatter pulse */
    case 'fuzz':
      return (
        <svg className={base} width="36" height="36" viewBox="0 0 36 36" fill="none" stroke="currentColor" strokeWidth="1.4">
          <rect x="4" y="10" width="28" height="16" rx="2" strokeDasharray="4 2" />
          <line x1="10" y1="16" x2="14" y2="16" opacity="0.8" />
          <line x1="16" y1="16" x2="26" y2="16" opacity="0.4" />
          <line x1="10" y1="20" x2="20" y2="20" opacity="0.6" />
          <line x1="22" y1="20" x2="26" y2="20" opacity="0.3" />
          <line x1="10" y1="24" x2="12" y2="24" opacity="0.9" />
          <line x1="14" y1="24" x2="26" y2="24" opacity="0.3" />
          <circle cx="7" cy="16" r="1" fill="currentColor" opacity="0.7" />
          <circle cx="7" cy="20" r="1" fill="currentColor" opacity="0.7" />
          <circle cx="7" cy="24" r="1" fill="currentColor" opacity="0.7" />
        </svg>
      )
    /* nuclei — atom orbits */
    case 'atom':
      return (
        <svg className={base} width="36" height="36" viewBox="0 0 36 36" fill="none" stroke="currentColor" strokeWidth="1.3">
          <circle cx="18" cy="18" r="3" fill="currentColor" opacity="0.6" />
          <ellipse cx="18" cy="18" rx="14" ry="5" />
          <ellipse cx="18" cy="18" rx="14" ry="5" transform="rotate(60 18 18)" />
          <ellipse cx="18" cy="18" rx="14" ry="5" transform="rotate(120 18 18)" />
          <circle cx="31" cy="15" r="1.5" fill="currentColor" opacity="0.8" />
          <circle cx="10" cy="25" r="1.5" fill="currentColor" opacity="0.5" />
        </svg>
      )
    /* sqlmap — syringe / injection */
    case 'syringe':
      return (
        <svg className={base} width="36" height="36" viewBox="0 0 36 36" fill="none" stroke="currentColor" strokeWidth="1.4">
          <path d="M26 4l-4 4 6 6 4-4z" />
          <path d="M22 8L10 20l-2 6 6-2 12-12z" />
          <line x1="14" y1="12" x2="16" y2="14" opacity="0.5" />
          <line x1="12" y1="14" x2="14" y2="16" opacity="0.5" />
          <line x1="10" y1="16" x2="12" y2="18" opacity="0.5" />
          <line x1="4" y1="30" x2="8" y2="26" strokeLinecap="round" opacity="0.6" />
          <path d="M8 24l-2 6" strokeLinecap="round" />
        </svg>
      )
    /* Kali — terminal / skull */
    case 'kali':
      return (
        <svg className={base} width="36" height="36" viewBox="0 0 36 36" fill="none" stroke="currentColor" strokeWidth="1.4">
          <rect x="3" y="6" width="30" height="22" rx="3" />
          <line x1="3" y1="12" x2="33" y2="12" opacity="0.4" />
          <circle cx="7" cy="9" r="1" fill="currentColor" opacity="0.5" />
          <circle cx="10.5" cy="9" r="1" fill="currentColor" opacity="0.5" />
          <text x="8" y="23" fill="currentColor" fontSize="8" fontFamily="monospace" opacity="0.8">root@kali</text>
          <line x1="8" y1="25.5" x2="20" y2="25.5" opacity="0.3" />
        </svg>
      )
    default:
      return null
  }
}

function ToolCard({
  tool,
  index,
  isInView,
}: {
  tool: { name: string; description: string; icon: string }
  index: number
  isInView: boolean
}) {
  return (
    <div
      className="group relative bg-bg-card border border-border-subtle p-6 h-full
        transition-all duration-500
        hover:border-accent/30 hover:bg-bg-card-hover hover:-translate-y-1
        hover:shadow-[0_0_24px_rgba(0,229,255,0.08)]"
      style={{
        animation: isInView
          ? `fade-slide-down 0.55s ${0.15 + index * 0.12}s both`
          : 'none',
        opacity: isInView ? undefined : 0,
      }}
    >
      {/* Tool icon */}
      <div className="text-text-dim mb-4 group-hover:text-accent transition-colors duration-300">
        <ToolIcon icon={tool.icon} />
      </div>

      {/* Name */}
      <h3 className="font-mono text-base text-text-primary tracking-[0.08em] mb-2 font-bold">
        {tool.name}
      </h3>

      {/* Description */}
      <p className="font-mono text-[0.7rem] text-text-muted leading-relaxed m-0">
        {tool.description}
      </p>

      {/* Corner accents */}
      <div className="absolute top-0 right-0 w-3 h-3 border-t border-r border-accent/20 group-hover:border-accent/50 transition-colors" />
      <div className="absolute bottom-0 left-0 w-3 h-3 border-b border-l border-accent/20 group-hover:border-accent/50 transition-colors" />
    </div>
  )
}

export default function ArsenalSection() {
  const { ref, isInView } = useInView({ threshold: 0.1 })

  return (
    <section ref={ref} className={`relative py-28 px-6 md:px-12 section-reveal ${isInView ? 'in-view' : ''}`}>
      {/* Accent line separator */}
      <div className="absolute top-0 left-1/2 -translate-x-1/2 w-24 h-px bg-accent opacity-30" />

      <div className="max-w-[1200px] mx-auto">
        {/* Section header */}
        <div className="text-center mb-16">
          <div className="font-label text-[0.6rem] text-accent uppercase tracking-[0.3em] mb-3">
            [ TACTICAL LOADOUT ]
          </div>
          <h2 className="font-display text-[3rem] sm:text-[4rem] text-text-primary leading-none m-0">
            THE ARSENAL
          </h2>
          <p className="font-mono text-[0.8rem] text-text-muted mt-3 max-w-[500px] mx-auto">
            We deploy the same tools elite penetration testers use. Automated. Targeted. Relentless.
          </p>
        </div>

        {/* Tool cards — top row of 3, bottom row of 2 centered */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">
          {(ARSENAL_TOOLS ?? []).slice(0, 3).map((tool, i) => (
            <ToolCard key={tool.name} tool={tool} index={i} isInView={isInView} />
          ))}
        </div>
        <div className="flex flex-col sm:flex-row gap-5 justify-center mt-5">
          {(ARSENAL_TOOLS ?? []).slice(3).map((tool, i) => (
            <div key={tool.name} className="w-full sm:w-[calc(50%-10px)] lg:w-[calc(33.333%-14px)]">
              <ToolCard tool={tool} index={i + 3} isInView={isInView} />
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}
