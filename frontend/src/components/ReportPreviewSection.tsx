import { useInView } from '../hooks/useInView'
import { MOCK_REPORT_FINDING, SEVERITY_BREAKDOWN } from '../data/mockData'

/* ─── Severity bar chart (no chart library — pure divs) ─── */

function SeverityBars({ isInView }: { isInView: boolean }) {
  const maxCount = Math.max(...(SEVERITY_BREAKDOWN ?? []).map(s => s.count), 1)

  return (
    <div className="flex flex-col gap-4">
      {(SEVERITY_BREAKDOWN ?? []).map((item, i) => {
        const pct = Math.round((item.count / maxCount) * 100)
        return (
          <div key={item.label} className="flex items-center gap-3">
            {/* Label */}
            <span className="font-label text-[0.65rem] text-text-muted tracking-wider uppercase w-20 text-right shrink-0">
              {item.label}
            </span>

            {/* Bar track */}
            <div className="flex-1 h-4 bg-bg-surface border border-border-subtle relative overflow-hidden">
              <div
                className="h-full origin-left"
                style={{
                  backgroundColor: item.color,
                  width: `${pct}%`,
                  transform: isInView ? 'scaleX(1)' : 'scaleX(0)',
                  transition: `transform 0.8s cubic-bezier(0.16, 1, 0.3, 1) ${0.3 + i * 0.12}s`,
                  boxShadow: `0 0 12px ${item.color}44`,
                }}
              />
            </div>

            {/* Count */}
            <span
              className="font-mono text-sm tabular-nums w-6 text-right"
              style={{ color: item.color }}
            >
              {item.count}
            </span>
          </div>
        )
      })}

      {/* Total */}
      <div className="flex items-center gap-3 mt-2 pt-3 border-t border-border-subtle">
        <span className="font-label text-[0.65rem] text-text-muted tracking-wider uppercase w-20 text-right">
          Total
        </span>
        <span className="font-mono text-sm text-text-primary font-bold">
          {(SEVERITY_BREAKDOWN ?? []).reduce((a, b) => a + b.count, 0)} findings
        </span>
      </div>
    </div>
  )
}

/* ─── Severity badge ─── */

function SeverityBadge({ severity }: { severity: string }) {
  const isCritical = severity === 'CRITICAL'
  return (
    <span
      className={`inline-block font-label text-[0.6rem] tracking-[0.2em] uppercase px-3 py-1
        ${isCritical
          ? 'bg-redshell/20 text-redshell border border-redshell/40'
          : 'bg-warning/20 text-warning border border-warning/40'
        }`}
      style={isCritical ? { animation: 'severity-pulse 2.5s ease-in-out infinite' } : undefined}
    >
      {severity}
    </span>
  )
}

export default function ReportPreviewSection() {
  const { ref, isInView } = useInView({ threshold: 0.1 })
  const finding = MOCK_REPORT_FINDING

  return (
    <section ref={ref} className={`relative py-28 px-6 md:px-12 section-reveal ${isInView ? 'in-view' : ''}`}>
      {/* Accent line separator */}
      <div className="absolute top-0 left-1/2 -translate-x-1/2 w-24 h-px bg-accent opacity-30" />

      <div className="max-w-[1200px] mx-auto">
        {/* Section header */}
        <div className="text-center mb-16">
          <div className="font-label text-[0.6rem] text-accent uppercase tracking-[0.3em] mb-3">
            [ INTELLIGENCE OUTPUT ]
          </div>
          <h2 className="font-display text-[3rem] sm:text-[4rem] text-text-primary leading-none m-0">
            SEE WHAT WE FIND
          </h2>
          <p className="font-mono text-[0.8rem] text-text-muted mt-3 max-w-[520px] mx-auto">
            A real finding. Real evidence. Real remediation. Every vulnerability is documented and actionable.
          </p>
        </div>

        {/* Two-column layout */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          {/* Left — Report card */}
          <div
            className="bg-bg-card border border-border-subtle overflow-hidden"
            style={{
              animation: isInView ? 'rise-in 0.7s 0.2s both' : 'none',
              opacity: isInView ? undefined : 0,
            }}
          >
            {/* Card header */}
            <div className="flex items-center justify-between px-5 py-3 border-b border-border-subtle bg-bg-surface">
              <span className="font-label text-[0.6rem] text-text-dim tracking-wider uppercase">
                Finding Report
              </span>
              <SeverityBadge severity={finding?.severity ?? 'UNKNOWN'} />
            </div>

            <div className="p-5 flex flex-col gap-5">
              {/* Title */}
              <h3 className="font-label text-sm text-text-primary tracking-[0.1em] m-0">
                {finding?.title ?? 'Untitled Finding'}
              </h3>

              {/* Evidence block */}
              <div>
                <div className="font-label text-[0.55rem] text-text-dim tracking-[0.2em] uppercase mb-2">
                  Evidence
                </div>
                <div className="bg-bg-surface border border-border-subtle p-4 font-mono text-[0.68rem] leading-relaxed overflow-x-auto max-h-[220px] overflow-y-auto">
                  {(finding?.evidence ?? []).map((line, i) => (
                    <div key={i} className={getEvidenceLineClass(line)}>
                      {line || '\u00A0'}
                    </div>
                  ))}
                </div>
              </div>

              {/* Impact */}
              <div>
                <div className="font-label text-[0.55rem] text-text-dim tracking-[0.2em] uppercase mb-2">
                  Impact
                </div>
                <p className="font-mono text-[0.72rem] text-text-muted leading-relaxed m-0">
                  {finding?.impact ?? '—'}
                </p>
              </div>

              {/* Remediation */}
              <div>
                <div className="font-label text-[0.55rem] text-text-dim tracking-[0.2em] uppercase mb-2">
                  Remediation
                </div>
                <p className="font-mono text-[0.72rem] text-success/80 leading-relaxed m-0">
                  {finding?.remediation ?? '—'}
                </p>
              </div>
            </div>
          </div>

          {/* Right — Severity breakdown */}
          <div
            className="bg-bg-card border border-border-subtle overflow-hidden"
            style={{
              animation: isInView ? 'rise-in 0.7s 0.4s both' : 'none',
              opacity: isInView ? undefined : 0,
            }}
          >
            {/* Card header */}
            <div className="flex items-center px-5 py-3 border-b border-border-subtle bg-bg-surface">
              <span className="font-label text-[0.6rem] text-text-dim tracking-wider uppercase">
                Severity Breakdown
              </span>
            </div>

            <div className="p-5">
              <SeverityBars isInView={isInView} />
            </div>
          </div>
        </div>

        {/* CTA below panes */}
        <div
          className="text-center mt-12"
          style={{
            animation: isInView ? 'fade-slide-up 0.6s 0.8s both' : 'none',
            opacity: isInView ? undefined : 0,
          }}
        >
          <p className="font-mono text-[0.8rem] text-text-muted mb-4">
            Want to see your report?
          </p>
          <a href="#scan-input">
            <button className="redshell-btn">
              SCAN YOUR REPO →
            </button>
          </a>
        </div>
      </div>
    </section>
  )
}

/* ─── Evidence line coloring (reuses ScanInputPanel pattern) ─── */

function getEvidenceLineClass(line: string): string {
  if (!line) return ''
  if (line.startsWith('[+]')) return 'text-success'
  if (line.startsWith('[*]')) return 'text-text-muted'
  if (line.startsWith('$')) return 'text-accent'
  if (line.includes('VULNERABLE') || line.includes('vulnerable')) return 'text-redshell font-bold'
  if (line.includes('Payload:')) return 'text-warning'
  return 'text-text-muted'
}
