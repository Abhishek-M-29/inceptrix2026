import { useState, useRef, useCallback } from 'react'
import type { Report, Finding } from '../api/types'

/* ─── Severity helpers ─── */

const SEVERITY_ORDER: Record<string, number> = {
  Critical: 0,
  High: 1,
  Medium: 2,
  Low: 3,
  Info: 4,
}

const SEVERITY_CONFIG: Record<string, { color: string; bg: string; border: string }> = {
  Critical: { color: '#FF3B3B', bg: 'rgba(255,59,59,0.08)', border: 'rgba(255,59,59,0.25)' },
  High:     { color: '#FF6B35', bg: 'rgba(255,107,53,0.08)', border: 'rgba(255,107,53,0.25)' },
  Medium:   { color: '#FFB800', bg: 'rgba(255,184,0,0.08)', border: 'rgba(255,184,0,0.25)' },
  Low:      { color: '#00B8D4', bg: 'rgba(0,184,212,0.08)', border: 'rgba(0,184,212,0.25)' },
  Info:     { color: '#7080A0', bg: 'rgba(112,128,160,0.06)', border: 'rgba(112,128,160,0.2)' },
}

function getSeverityConfig(severity: string) {
  return SEVERITY_CONFIG[severity] ?? SEVERITY_CONFIG.Info
}

function stripAnsi(str: string): string {
  // eslint-disable-next-line no-control-regex
  return str.replace(/\u001b\[[0-9;]*m/g, '')
}

/* ─── Severity summary counts ─── */

function countBySeverity(findings: Finding[]) {
  const counts: Record<string, number> = { Critical: 0, High: 0, Medium: 0, Low: 0, Info: 0 }
  for (const f of findings) {
    const sev = f.severity ?? 'Info'
    if (counts[sev] !== undefined) counts[sev]++
    else counts.Info++
  }
  return counts
}

/* ─── Sub-components ─── */

function SeverityBadge({ severity }: { severity: string }) {
  const cfg = getSeverityConfig(severity)
  return (
    <span
      className="inline-flex items-center gap-1.5 font-mono text-[0.65rem] font-semibold tracking-[0.08em] uppercase px-2.5 py-1 rounded-sm"
      style={{ color: cfg.color, background: cfg.bg, border: `1px solid ${cfg.border}` }}
    >
      <span className="w-1.5 h-1.5 rounded-full" style={{ background: cfg.color }} />
      {severity}
    </span>
  )
}

function SeveritySummaryBar({ findings }: { findings: Finding[] }) {
  const counts = countBySeverity(findings)
  const total = findings.length
  const entries = Object.entries(counts).filter(([, count]) => count > 0)

  return (
    <div className="flex flex-col gap-4">
      {/* Visual bar */}
      <div className="flex h-2 rounded-sm overflow-hidden bg-bg-surface">
        {entries.map(([sev, count]) => {
          const cfg = getSeverityConfig(sev)
          const pct = (count / total) * 100
          return (
            <div
              key={sev}
              style={{ width: `${pct}%`, background: cfg.color, minWidth: count > 0 ? 4 : 0 }}
              title={`${sev}: ${count}`}
            />
          )
        })}
      </div>

      {/* Counts */}
      <div className="flex gap-5 flex-wrap">
        {Object.entries(counts).map(([sev, count]) => {
          const cfg = getSeverityConfig(sev)
          return (
            <div key={sev} className="flex items-center gap-2">
              <span className="w-2.5 h-2.5 rounded-sm" style={{ background: count > 0 ? cfg.color : 'var(--color-border-subtle)' }} />
              <span className="font-mono text-[0.72rem] text-text-muted">{sev}</span>
              <span className="font-mono text-[0.82rem] font-bold tabular-nums" style={{ color: count > 0 ? cfg.color : 'var(--color-text-dim)' }}>
                {count}
              </span>
            </div>
          )
        })}
      </div>
    </div>
  )
}

function FindingCard({ finding, index, isExpanded, onToggle }: {
  finding: Finding
  index: number
  isExpanded: boolean
  onToggle: () => void
}) {
  const cfg = getSeverityConfig(finding.severity)
  const cleanedEvidence = stripAnsi(finding.evidence)

  return (
    <div
      className="border rounded-sm transition-all duration-200"
      style={{
        borderColor: isExpanded ? cfg.border : 'var(--color-border-subtle)',
        background: isExpanded ? cfg.bg : 'transparent',
      }}
    >
      {/* Header — always visible */}
      <button
        onClick={onToggle}
        className="w-full flex items-start gap-4 px-5 py-4 text-left bg-transparent border-none cursor-pointer group"
      >
        <span className="font-mono text-[0.7rem] text-text-dim tabular-nums pt-0.5 shrink-0 w-10">
          {finding.id || `F-${String(index + 1).padStart(3, '0')}`}
        </span>

        <div className="flex-1 min-w-0">
          <div className="font-mono text-[0.82rem] text-text-primary leading-snug group-hover:text-accent transition-colors">
            {finding.title}
          </div>
          <div className="flex items-center gap-3 mt-2">
            <SeverityBadge severity={finding.severity} />
            {finding.category && (
              <span className="font-mono text-[0.62rem] text-text-dim tracking-[0.05em]">
                {finding.category}
              </span>
            )}
            {finding.tool && (
              <span className="font-mono text-[0.62rem] text-text-dim tracking-[0.05em]">
                via {finding.tool.replace(/^run_/, '')}
              </span>
            )}
          </div>
        </div>

        <span className="text-text-dim text-sm pt-1 transition-transform duration-200 shrink-0" style={{
          transform: isExpanded ? 'rotate(180deg)' : 'rotate(0deg)',
        }}>
          ▾
        </span>
      </button>

      {/* Expandable detail */}
      {isExpanded && (
        <div className="px-5 pb-5 pt-0 ml-14 flex flex-col gap-4 border-t" style={{ borderColor: cfg.border }}>
          {/* Description */}
          {finding.description && (
            <div>
              <div className="font-mono text-[0.62rem] text-text-dim uppercase tracking-[0.12em] mb-1.5">Description</div>
              <p className="font-mono text-[0.78rem] text-text-muted leading-relaxed m-0">
                {finding.description}
              </p>
            </div>
          )}

          {/* Impact */}
          {finding.impact && (
            <div>
              <div className="font-mono text-[0.62rem] text-text-dim uppercase tracking-[0.12em] mb-1.5">Impact</div>
              <p className="font-mono text-[0.78rem] text-text-muted leading-relaxed m-0">
                {finding.impact}
              </p>
            </div>
          )}

          {/* Evidence */}
          {cleanedEvidence && (
            <div>
              <div className="font-mono text-[0.62rem] text-text-dim uppercase tracking-[0.12em] mb-1.5">Evidence</div>
              <pre className="font-mono text-[0.68rem] text-text-muted leading-relaxed p-4 bg-bg-deep border border-border-subtle rounded-sm overflow-x-auto max-h-[260px] overflow-y-auto whitespace-pre-wrap break-all m-0">
                {cleanedEvidence}
              </pre>
            </div>
          )}

          {/* Remediation */}
          {finding.remediation && (
            <div>
              <div className="font-mono text-[0.62rem] text-text-dim uppercase tracking-[0.12em] mb-1.5">Remediation</div>
              <div className="p-3 rounded-sm" style={{ background: 'rgba(0,255,136,0.05)', border: '1px solid rgba(0,255,136,0.15)' }}>
                <p className="font-mono text-[0.78rem] leading-relaxed m-0" style={{ color: 'rgba(0,255,136,0.85)' }}>
                  {finding.remediation}
                </p>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

function MetadataRow({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="flex justify-between py-2.5 border-b border-border-subtle/40">
      <span className="font-mono text-[0.72rem] text-text-dim">{label}</span>
      <span className="font-mono text-[0.72rem] text-text-muted font-medium">{String(value)}</span>
    </div>
  )
}

/* ─── PDF styles (injected into the PDF-target element for printing) ─── */

const PDF_PRINT_STYLES = `
  .report-pdf-target {
    --color-bg-deep: #020210;
    --color-bg-surface: #080820;
    --color-bg-card: #0A0A24;
    --color-border-subtle: #1A1A3A;
    --color-text-primary: #E4E8F0;
    --color-text-muted: #7080A0;
    --color-text-dim: #3A4468;
    --color-accent: #00E5FF;
    --color-success: #00FF88;
  }
  @media print {
    body { background: #020210 !important; }
    .report-pdf-target { padding: 40px !important; }
    .no-print { display: none !important; }
  }
`

/* ─── Main Report View ─── */

interface ReportViewProps {
  report: Report
  engagementId: string | null
  targetUrl: string
  elapsed: string
  onBack: () => void
}

export default function ReportView({ report, engagementId, targetUrl, elapsed, onBack }: ReportViewProps) {
  const [expandedIds, setExpandedIds] = useState<Set<string>>(new Set())
  const [isGeneratingPdf, setIsGeneratingPdf] = useState(false)
  const [filterSeverity, setFilterSeverity] = useState<string | null>(null)
  const reportRef = useRef<HTMLDivElement>(null)

  const repoPath = targetUrl.replace(/^https?:\/\/(www\.)?github\.com\//, '').replace(/\/$/, '') || targetUrl

  const toggleFinding = useCallback((id: string) => {
    setExpandedIds(prev => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }, [])

  const expandAll = useCallback(() => {
    const allIds = (report.findings ?? []).map(f => f.id)
    setExpandedIds(new Set(allIds))
  }, [report.findings])

  const collapseAll = useCallback(() => {
    setExpandedIds(new Set())
  }, [])

  // Sort findings by severity
  const sortedFindings = [...(report.findings ?? [])].sort(
    (a, b) => (SEVERITY_ORDER[a.severity] ?? 4) - (SEVERITY_ORDER[b.severity] ?? 4)
  )

  const filteredFindings = filterSeverity
    ? sortedFindings.filter(f => f.severity === filterSeverity)
    : sortedFindings

  const totalFindings = report.scan_summary?.total_findings ?? report.findings?.length ?? 0
  const generatedAt = report.metadata?.generated_at
    ? new Date(report.metadata.generated_at).toLocaleString('en-US', {
        year: 'numeric', month: 'short', day: 'numeric',
        hour: '2-digit', minute: '2-digit', timeZoneName: 'short',
      })
    : '—'

  const handleDownloadPdf = async () => {
    if (!reportRef.current || isGeneratingPdf) return
    setIsGeneratingPdf(true)

    // Expand all findings for PDF
    const prevExpanded = new Set(expandedIds)
    setExpandedIds(new Set(sortedFindings.map(f => f.id)))
    const prevFilter = filterSeverity
    setFilterSeverity(null)

    // Small delay to let React re-render with all expanded
    await new Promise(r => setTimeout(r, 150))

    try {
      // html2pdf.js is CJS — handle both default and direct export
      const mod = await import('html2pdf.js')
      const html2pdf = (mod as unknown as { default?: unknown }).default ?? mod
      if (typeof html2pdf !== 'function') {
        throw new Error('html2pdf.js did not export a callable function')
      }
      const element = reportRef.current

      const opt = {
        margin: [10, 10, 10, 10] as [number, number, number, number],
        filename: `redshell-report-${engagementId?.slice(0, 8) ?? 'scan'}.pdf`,
        image: { type: 'jpeg' as const, quality: 0.95 },
        html2canvas: {
          scale: 2,
          useCORS: true,
          backgroundColor: '#020210',
          logging: false,
          scrollY: 0,
          windowHeight: element.scrollHeight,
        },
        jsPDF: {
          unit: 'mm' as const,
          format: 'a4' as const,
          orientation: 'portrait' as const,
        },
        pagebreak: { mode: ['avoid-all', 'css', 'legacy'] as string[] },
      }

      await (html2pdf as CallableFunction)()
        .set(opt)
        .from(element)
        .save()
    } catch (err) {
      console.error('PDF generation failed:', err)
    } finally {
      // Restore previous state
      setExpandedIds(prevExpanded)
      setFilterSeverity(prevFilter)
      setIsGeneratingPdf(false)
    }
  }

  return (
    <div className="flex-1 min-h-0 overflow-y-auto">
      <style>{PDF_PRINT_STYLES}</style>

      <div ref={reportRef} className="report-pdf-target max-w-[900px] mx-auto p-6 md:p-10">

        {/* ── Report Header ── */}
        <header className="mb-10">
          <div className="flex items-start justify-between mb-6 flex-wrap gap-4">
            <div>
              <div className="font-mono text-[0.65rem] text-text-dim tracking-[0.08em] mb-2">
                SECURITY ASSESSMENT REPORT
              </div>
              <h1 className="font-mono text-[1.4rem] sm:text-[1.7rem] text-text-primary font-bold leading-tight m-0 tracking-tight">
                {repoPath}
              </h1>
            </div>
            <div className="flex gap-2 no-print shrink-0">
              <button
                onClick={handleDownloadPdf}
                disabled={isGeneratingPdf}
                className="flex items-center gap-2 px-4 py-2.5 font-mono text-[0.72rem] font-semibold tracking-[0.06em] border border-border-subtle text-text-muted bg-bg-surface hover:bg-bg-card hover:text-text-primary hover:border-accent/40 transition-all rounded-sm cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {isGeneratingPdf ? (
                  <>
                    <svg className="w-3.5 h-3.5 animate-spin" viewBox="0 0 16 16" fill="none">
                      <circle cx="8" cy="8" r="6" stroke="currentColor" strokeWidth="2" opacity="0.3" />
                      <path d="M14 8a6 6 0 00-6-6" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
                    </svg>
                    Generating…
                  </>
                ) : (
                  <>
                    <svg className="w-3.5 h-3.5" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5">
                      <path d="M8 2v8m0 0l-3-3m3 3l3-3M3 12v1.5h10V12" strokeLinecap="round" strokeLinejoin="round" />
                    </svg>
                    Download PDF
                  </>
                )}
              </button>
              <button
                onClick={onBack}
                className="flex items-center gap-2 px-4 py-2.5 font-mono text-[0.72rem] font-semibold tracking-[0.06em] border border-accent/30 text-accent bg-transparent hover:bg-accent/10 transition-all rounded-sm cursor-pointer"
              >
                ← New Scan
              </button>
            </div>
          </div>

          {/* Meta details */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-px bg-border-subtle/50 border border-border-subtle rounded-sm overflow-hidden">
            {[
              { label: 'Findings', value: String(totalFindings) },
              { label: 'Duration', value: report.metadata?.elapsed_seconds ? `${Math.round(report.metadata.elapsed_seconds)}s` : elapsed },
              { label: 'Scan ID', value: engagementId?.slice(0, 8) ?? report.job_id?.slice(0, 8) ?? '—' },
              { label: 'Generated', value: generatedAt },
            ].map(item => (
              <div key={item.label} className="px-4 py-3 bg-bg-card">
                <div className="font-mono text-[0.58rem] text-text-dim tracking-[0.1em] uppercase mb-1">{item.label}</div>
                <div className="font-mono text-[0.82rem] text-text-primary font-semibold truncate">{item.value}</div>
              </div>
            ))}
          </div>
        </header>

        {/* ── Severity Overview ── */}
        <section className="mb-10">
          <h2 className="font-mono text-[0.72rem] text-text-dim tracking-[0.1em] uppercase font-semibold mb-4 m-0">
            Severity Overview
          </h2>
          <div className="p-5 bg-bg-card border border-border-subtle rounded-sm">
            <SeveritySummaryBar findings={report.findings ?? []} />
          </div>
        </section>

        {/* ── Scan Info ── */}
        <section className="mb-10">
          <h2 className="font-mono text-[0.72rem] text-text-dim tracking-[0.1em] uppercase font-semibold mb-4 m-0">
            Engagement Details
          </h2>
          <div className="bg-bg-card border border-border-subtle rounded-sm px-5 py-1">
            <MetadataRow label="Target" value={report.target ?? '—'} />
            <MetadataRow label="Repository" value={report.sandbox?.github_url ?? targetUrl} />
            <MetadataRow label="Agent" value={report.metadata?.agent ?? '—'} />
            <MetadataRow label="Actions Executed" value={report.metadata?.total_actions ?? '—'} />
            <MetadataRow label="Status" value={report.status ?? '—'} />
            {report.scan_summary?.open_ports?.length > 0 && (
              <MetadataRow label="Open Ports" value={report.scan_summary.open_ports.join(', ')} />
            )}
            {report.scan_summary?.services_detected?.length > 0 && (
              <MetadataRow label="Services" value={report.scan_summary.services_detected.join(', ')} />
            )}
          </div>
        </section>

        {/* ── Findings ── */}
        <section className="mb-10">
          <div className="flex items-center justify-between mb-4 flex-wrap gap-3">
            <h2 className="font-mono text-[0.72rem] text-text-dim tracking-[0.1em] uppercase font-semibold m-0">
              Findings ({filteredFindings.length}{filterSeverity ? ` ${filterSeverity}` : ''})
            </h2>

            <div className="flex items-center gap-3 no-print">
              {/* Severity filter pills */}
              <div className="flex gap-1">
                <button
                  onClick={() => setFilterSeverity(null)}
                  className={`font-mono text-[0.62rem] px-2.5 py-1 rounded-sm border transition-all cursor-pointer ${
                    !filterSeverity
                      ? 'border-accent/40 text-accent bg-accent/10'
                      : 'border-border-subtle text-text-dim bg-transparent hover:text-text-muted'
                  }`}
                >
                  All
                </button>
                {Object.entries(countBySeverity(report.findings ?? [])).map(([sev, count]) =>
                  count > 0 ? (
                    <button
                      key={sev}
                      onClick={() => setFilterSeverity(filterSeverity === sev ? null : sev)}
                      className="font-mono text-[0.62rem] px-2.5 py-1 rounded-sm border transition-all cursor-pointer"
                      style={{
                        borderColor: filterSeverity === sev
                          ? getSeverityConfig(sev).border
                          : 'var(--color-border-subtle)',
                        color: filterSeverity === sev
                          ? getSeverityConfig(sev).color
                          : 'var(--color-text-dim)',
                        background: filterSeverity === sev
                          ? getSeverityConfig(sev).bg
                          : 'transparent',
                      }}
                    >
                      {sev} ({count})
                    </button>
                  ) : null
                )}
              </div>

              {/* Expand/Collapse */}
              <div className="flex gap-1 border-l border-border-subtle pl-3 ml-1">
                <button
                  onClick={expandAll}
                  className="font-mono text-[0.62rem] text-text-dim hover:text-text-muted px-2 py-1 bg-transparent border border-border-subtle rounded-sm transition-colors cursor-pointer"
                >
                  Expand all
                </button>
                <button
                  onClick={collapseAll}
                  className="font-mono text-[0.62rem] text-text-dim hover:text-text-muted px-2 py-1 bg-transparent border border-border-subtle rounded-sm transition-colors cursor-pointer"
                >
                  Collapse all
                </button>
              </div>
            </div>
          </div>

          <div className="flex flex-col gap-2">
            {filteredFindings.length > 0 ? (
              filteredFindings.map((finding, i) => (
                <FindingCard
                  key={finding.id}
                  finding={finding}
                  index={i}
                  isExpanded={expandedIds.has(finding.id)}
                  onToggle={() => toggleFinding(finding.id)}
                />
              ))
            ) : (
              <div className="py-8 text-center font-mono text-[0.78rem] text-text-dim">
                No findings match the selected filter.
              </div>
            )}
          </div>
        </section>

        {/* ── Activity Log (collapsed by default) ── */}
        {report.logs && report.logs.length > 0 && (
          <ActivityLog logs={report.logs} />
        )}

        {/* ── Footer ── */}
        <footer className="mt-8 pt-6 border-t border-border-subtle/40">
          <div className="flex justify-between items-center text-text-dim font-mono text-[0.62rem] tracking-[0.05em]">
            <span>{report.metadata?.agent ?? 'RedShell'} — Automated Security Assessment</span>
            <span>{generatedAt}</span>
          </div>
        </footer>
      </div>
    </div>
  )
}

/* ─── Activity Log (collapsible) ─── */

function ActivityLog({ logs }: { logs: Report['logs'] }) {
  const [isOpen, setIsOpen] = useState(false)

  const toolLogs = logs.filter(l =>
    l.event === 'tool_started' || l.event === 'tool_completed' || l.event === 'tool_failed'
  )

  return (
    <section className="mb-10">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center gap-2 mb-4 bg-transparent border-none p-0 cursor-pointer group"
      >
        <h2 className="font-mono text-[0.72rem] text-text-dim tracking-[0.1em] uppercase font-semibold m-0 group-hover:text-text-muted transition-colors">
          Activity Log ({toolLogs.length} events)
        </h2>
        <span className="text-text-dim text-xs transition-transform duration-200" style={{
          transform: isOpen ? 'rotate(180deg)' : 'rotate(0deg)',
        }}>▾</span>
      </button>

      {isOpen && (
        <div className="bg-bg-card border border-border-subtle rounded-sm overflow-hidden">
          <div className="max-h-[400px] overflow-y-auto">
            <table className="w-full border-collapse">
              <thead>
                <tr className="border-b border-border-subtle bg-bg-surface sticky top-0">
                  <th className="text-left font-mono text-[0.6rem] text-text-dim tracking-[0.08em] uppercase font-semibold px-4 py-2.5">Time</th>
                  <th className="text-left font-mono text-[0.6rem] text-text-dim tracking-[0.08em] uppercase font-semibold px-4 py-2.5">Tool</th>
                  <th className="text-left font-mono text-[0.6rem] text-text-dim tracking-[0.08em] uppercase font-semibold px-4 py-2.5">Event</th>
                  <th className="text-right font-mono text-[0.6rem] text-text-dim tracking-[0.08em] uppercase font-semibold px-4 py-2.5">Duration</th>
                </tr>
              </thead>
              <tbody>
                {toolLogs.map((log, i) => {
                  const time = new Date(log.ts).toLocaleTimeString('en-US', { hour12: false })
                  const isFailure = log.event === 'tool_failed'
                  const isComplete = log.event === 'tool_completed'
                  return (
                    <tr key={i} className="border-b border-border-subtle/30 last:border-none">
                      <td className="font-mono text-[0.68rem] text-text-dim px-4 py-2 tabular-nums">{time}</td>
                      <td className="font-mono text-[0.68rem] text-text-muted px-4 py-2">{log.tool ?? '—'}</td>
                      <td className="px-4 py-2">
                        <span
                          className="font-mono text-[0.65rem] font-medium"
                          style={{
                            color: isFailure ? '#FF3B3B' : isComplete ? 'var(--color-success)' : 'var(--color-text-muted)',
                          }}
                        >
                          {log.event.replace('tool_', '')}
                          {log.error && ` — ${log.error}`}
                        </span>
                      </td>
                      <td className="font-mono text-[0.68rem] text-text-dim px-4 py-2 text-right tabular-nums">
                        {log.elapsed != null ? `${log.elapsed.toFixed(1)}s` : '—'}
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </section>
  )
}
