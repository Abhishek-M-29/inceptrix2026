import { useInView } from '../hooks/useInView'

export default function FooterCTA() {
  const { ref: ctaRef, isInView: ctaInView } = useInView({ threshold: 0.2 })
  const { ref: footerRef, isInView: footerInView } = useInView({ threshold: 0.3 })

  return (
    <>
      {/* ──── Final CTA ──── */}
      <section
        ref={ctaRef}
        className={`relative py-32 px-6 md:px-12 text-center section-reveal ${ctaInView ? 'in-view' : ''}`}
      >
        {/* Background glow */}
        <div
          className="absolute inset-0 pointer-events-none"
          style={{
            background:
              'radial-gradient(ellipse at 50% 60%, rgba(0,229,255,0.04) 0%, transparent 60%)',
          }}
        />

        <div className="relative z-10 max-w-[700px] mx-auto flex flex-col items-center gap-6">
          <div className="font-label text-[0.6rem] text-accent uppercase tracking-[0.3em]">
            [ FINAL BRIEFING ]
          </div>

          <h2 className="font-display text-[3rem] sm:text-[4rem] lg:text-[5rem] text-text-primary leading-[0.9] m-0">
            Your code is already live.
            <br />
            <span className="text-accent">Is it safe?</span>
          </h2>

          <p className="font-mono text-[0.8rem] text-text-muted max-w-[500px] leading-relaxed">
            Most frontend applications have at least one HIGH severity vulnerability
            discoverable in minutes. Find yours before someone else does.
          </p>

          {/* Input + button */}
          <div className="flex gap-0 w-full max-w-[600px] mt-4">
            <div className="flex items-center px-4 bg-bg-card border border-border-subtle border-r-0 font-mono text-accent text-sm shrink-0">
              $
            </div>
            <input
              type="text"
              className="terminal-input flex-1"
              placeholder="https://github.com/your-org/your-repo"
              style={{ borderLeft: 'none' }}
            />
            <button className="redshell-btn-sm shrink-0 border-l-0 whitespace-nowrap" style={{ animation: 'none' }}>
              SCAN NOW
            </button>
          </div>

          <p className="font-label text-[0.55rem] text-text-dim tracking-wider">
            No account required · Public GitHub repos only · Results in minutes
          </p>
        </div>
      </section>

      {/* ──── Footer ──── */}
      <footer
        ref={footerRef}
        className={`relative border-t border-border-subtle py-6 px-6 md:px-12 section-reveal ${
          footerInView ? 'in-view' : ''
        }`}
      >
        <div className="max-w-[1200px] mx-auto flex flex-col md:flex-row items-center justify-between gap-4 text-center md:text-left">
          {/* Left: Branding */}
          <div>
            <span className="font-display text-xl text-text-primary tracking-wider">
              REDSHELL
            </span>
            <span className="block font-mono text-[0.6rem] text-text-dim mt-0.5">
              Automated red-teaming for the modern developer.
            </span>
          </div>

          {/* Center: Hackathon credit */}
          <div className="font-label text-[0.6rem] text-text-dim tracking-wider">
            Built at{' '}
            <span className="text-text-muted">Inceptrix 2026</span>{' '}
            ·{' '}
            <a
              href="https://github.com"
              target="_blank"
              rel="noopener noreferrer"
              className="text-text-muted hover:text-accent transition-colors no-underline"
            >
              GitHub ↗
            </a>
          </div>

          {/* Right: Status */}
          <div className="flex items-center gap-2">
            <span className="font-label text-[0.6rem] text-text-dim tracking-wider uppercase">
              System Status:
            </span>
            <span className="font-label text-[0.6rem] text-success tracking-wider uppercase">
              Operational
            </span>
            <span
              className="inline-block w-2 h-2 rounded-full bg-success"
              style={{ animation: 'dot-blink 2s ease-in-out infinite' }}
            />
          </div>
        </div>
      </footer>
    </>
  )
}
