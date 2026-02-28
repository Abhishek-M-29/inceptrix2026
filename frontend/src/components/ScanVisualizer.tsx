import { useState, useEffect, useRef } from 'react'
import { SCAN_STAGES, SCAN_SEVERITY_DATA, JOB_STATE_TO_STAGE_INDEX } from '../data/scanStages'
import type { ScanStage } from '../data/scanStages'
import type { JobState, StateHistoryEntry, Report, QueueItem } from '../api/types'
import { useQueue } from '../hooks/useQueue'
import ReportView from './ReportView'

/* ─────────────────────────────────────────────────
   Sub-components
   ───────────────────────────────────────────────── */

function StageIndicator({ stage, active }: { stage: ScanStage; active: boolean }) {
  return (
    <div className="relative w-[120px] h-[120px] shrink-0 flex items-center justify-center">
      <div className="absolute inset-0 rounded-full transition-all duration-700" style={{ border: `2px solid ${active ? stage.color : 'var(--color-border-subtle)'}`, opacity: active ? 0.25 : 0.1 }} />
      <div className="absolute rounded-full transition-all duration-700" style={{ inset: 14, border: `2px solid ${active ? stage.color : 'var(--color-border-subtle)'}`, opacity: active ? 0.5 : 0.1 }} />
      <div className="relative w-14 h-14 rounded-full flex items-center justify-center transition-all duration-700" style={{ background: active ? `${stage.color}18` : 'transparent', border: `2px solid ${active ? stage.color : 'var(--color-border-subtle)'}`, boxShadow: active ? `0 0 24px ${stage.glow}` : 'none' }}>
        <span className="font-display text-xl tracking-wider transition-colors duration-500" style={{ color: active ? stage.color : 'var(--color-text-dim)' }}>{stage.code}</span>
      </div>
      {active && (
        <svg className="absolute inset-0 w-full h-full" style={{ animation: 'scan-slow-rotate 12s linear infinite' }}>
          <circle cx="60" cy="60" r="56" fill="none" stroke={stage.color} strokeWidth="1.5" strokeDasharray="8 16" opacity="0.35" />
        </svg>
      )}
    </div>
  )
}

function TerminalLog({ logs, stageColor }: { logs: string[]; stageColor: string }) {
  const bottomRef = useRef<HTMLDivElement>(null)
  const [displayedLogs, setDisplayedLogs] = useState<string[]>([])
  const [currentLine, setCurrentLine] = useState(0)
  const [currentChar, setCurrentChar] = useState(0)

  useEffect(() => {
    if (currentLine >= logs.length) return
    const line = logs[currentLine]
    if (currentChar < line.length) {
      const t = setTimeout(() => setCurrentChar(c => c + 1), 18)
      return () => clearTimeout(t)
    } else {
      const t = setTimeout(() => {
        setDisplayedLogs(prev => [...prev, line])
        setCurrentLine(l => l + 1)
        setCurrentChar(0)
      }, 60)
      return () => clearTimeout(t)
    }
  }, [currentLine, currentChar, logs])

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [displayedLogs, currentChar])

  const currentTyping = currentLine < logs.length ? logs[currentLine].slice(0, currentChar) : null

  const colorize = (line: string) => {
    if (line.includes('CRITICAL') || line.includes('\u26a0 CRITICAL')) return '#FF3B3B'
    if (line.includes('HIGH') || line.includes('\u26a0 HIGH')) return '#FF6B35'
    if (line.includes('MEDIUM')) return '#FFB800'
    if (line.includes('\u2713')) return 'var(--color-success)'
    if (line.startsWith('$') || line.startsWith('[')) return stageColor
    if (line.startsWith('::')) return '#A78BFA'
    if (line === '') return 'var(--color-border-subtle)'
    if (line.startsWith('\u2501')) return stageColor
    if (line.includes('COMPLETED')) return 'var(--color-success)'
    return 'var(--color-text-muted)'
  }

  return (
    <div className="font-mono text-[0.72rem] leading-[1.7] h-[280px] overflow-y-auto p-3 bg-bg-surface border border-border-subtle" style={{ borderTop: `1px solid ${stageColor}33` }}>
      {displayedLogs.map((line, i) => (
        <div key={i} style={{ color: colorize(line), whiteSpace: 'pre' }}>{line || '\u00A0'}</div>
      ))}
      {currentTyping !== null && (
        <div style={{ color: colorize(logs[currentLine] || ''), whiteSpace: 'pre' }}>
          {currentTyping}
          <span className="inline-block w-[7px] h-[13px] ml-px align-middle" style={{ background: stageColor, animation: 'cursor-blink 0.7s step-end infinite' }} />
        </div>
      )}
      <div ref={bottomRef} />
    </div>
  )
}

function LiveTerminal({ items, stageColor }: { items: QueueItem[]; stageColor: string }) {
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [items.length])

  const colorize = (item: QueueItem) => {
    if (item.status === 'ended') return 'var(--color-success)'
    if (item.tool === 'nmap') return '#FFB800'
    if (item.tool === 'ffuf') return '#A78BFA'
    if (item.tool === 'nuclei') return '#00E5FF'
    if (item.tool === 'sqlmap') return '#FF3B3B'
    if (item.tool === 'shell') return 'var(--color-text-muted)'
    if (item.tool === 'preflight') return stageColor
    return 'var(--color-text-muted)'
  }

  const formatLine = (item: QueueItem) => {
    const time = new Date(item.received_at).toLocaleTimeString('en-US', { hour12: false })
    const statusIcon = item.status === 'ended' ? '\u2713' : '\u25b6'
    return `[${time}] ${statusIcon} [${item.tool}] ${item.command_used}`
  }

  return (
    <div className="font-mono text-[0.72rem] leading-[1.7] h-[280px] overflow-y-auto p-3 bg-bg-surface border border-border-subtle" style={{ borderTop: `1px solid ${stageColor}33` }}>
      {items.length === 0 && <div className="text-text-dim">Waiting for tool output...</div>}
      {items.map((item, i) => (
        <div key={`${item.received_at}-${i}`} style={{ color: colorize(item), whiteSpace: 'pre' }}>{formatLine(item)}</div>
      ))}
      <span className="inline-block w-[7px] h-[13px] ml-px align-middle" style={{ background: stageColor, animation: 'cursor-blink 0.7s step-end infinite' }} />
      <div ref={bottomRef} />
    </div>
  )
}

function StageNode({ stage, status, isLast }: { stage: ScanStage; status: 'pending' | 'active' | 'done'; isLast: boolean }) {
  const isDone = status === 'done'
  const isActive = status === 'active'
  return (
    <div className="flex flex-col items-center">
      <div className="flex flex-col items-center gap-1.5">
        <div className="w-10 h-10 rounded-full flex items-center justify-center relative transition-all duration-500" style={{ border: `2px solid ${isDone || isActive ? stage.color : 'var(--color-border-subtle)'}`, background: isDone ? `${stage.color}20` : isActive ? `${stage.color}12` : 'transparent', boxShadow: isActive ? `0 0 16px ${stage.glow}` : 'none' }}>
          {isDone ? (
            <svg width="14" height="14" viewBox="0 0 18 18"><polyline points="3,9 7,13 15,5" fill="none" stroke={stage.color} strokeWidth="2.5" strokeLinecap="round" /></svg>
          ) : (
            <span className="font-mono text-[0.65rem] font-bold transition-colors duration-300" style={{ color: isActive ? stage.color : 'var(--color-text-dim)' }}>{stage.code}</span>
          )}
        </div>
        <span className="font-mono text-[0.55rem] font-bold tracking-[0.1em] text-center max-w-[72px] transition-colors duration-300" style={{ color: isDone || isActive ? stage.color : 'var(--color-text-dim)' }}>{stage.label}</span>
      </div>
      {!isLast && (
        <div className="h-6 mt-1 transition-all duration-500" style={{ width: 2, background: isDone ? stage.color : 'var(--color-border-subtle)', opacity: isDone ? 0.6 : 0.3 }} />
      )}
    </div>
  )
}

function SeverityBar({ item, animate, delay, maxCount }: { item: { label: string; count: number; color: string }; animate: boolean; delay: number; maxCount: number }) {
  const [width, setWidth] = useState(0)
  useEffect(() => {
    if (animate && maxCount > 0) {
      const t = setTimeout(() => setWidth((item.count / maxCount) * 100), delay)
      return () => clearTimeout(t)
    }
  }, [animate, item.count, delay, maxCount])
  return (
    <div className="mb-3">
      <div className="flex justify-between mb-1.5">
        <span className="font-mono text-[0.7rem] tracking-[0.08em]" style={{ color: item.color }}>{item.label}</span>
        <span className="font-mono text-[0.7rem] text-text-muted">{animate ? item.count : 0}</span>
      </div>
      <div className="h-1.5 bg-bg-surface rounded-sm overflow-hidden">
        <div className="h-full rounded-sm" style={{ width: `${width}%`, background: item.color, transition: 'width 0.8s cubic-bezier(0.16, 1, 0.3, 1)' }} />
      </div>
    </div>
  )
}

/* ─────────────────────────────────────────────────
   Main Visualizer — API-driven
   ───────────────────────────────────────────────── */

interface ScanVisualizerProps {
  targetUrl: string
  engagementId: string | null
  status: JobState | null
  history: StateHistoryEntry[]
  report: Report | null
  error: string | null
  isLoading: boolean
  onBack: () => void
}

function getStageIndex(status: JobState | null): number {
  if (!status) return 0
  return JOB_STATE_TO_STAGE_INDEX[status] ?? 0
}

function deriveStageStatuses(status: JobState | null): ('pending' | 'active' | 'done')[] {
  const idx = getStageIndex(status)
  if (status === 'Completed') return SCAN_STAGES.map(() => 'done')
  if (status === 'Failed') return SCAN_STAGES.map((_, i) => (i < idx ? 'done' : 'pending'))
  return SCAN_STAGES.map((_, i) => {
    if (i < idx) return 'done'
    if (i === idx) return 'active'
    return 'pending'
  })
}

function extractSeverityData(report: Report | null) {
  if (!report) return SCAN_SEVERITY_DATA
  const findings = report.findings
  if (Array.isArray(findings) && findings.length > 0) {
    const counts: Record<string, number> = { Critical: 0, High: 0, Medium: 0, Low: 0 }
    for (const f of findings) {
      const sev = f.severity ?? 'Low'
      if (counts[sev] !== undefined) counts[sev]++
    }
    const mapped = []
    if (counts.Critical > 0) mapped.push({ label: 'CRITICAL', count: counts.Critical, color: '#FF3B3B' })
    if (counts.High > 0) mapped.push({ label: 'HIGH', count: counts.High, color: '#FF6B35' })
    if (counts.Medium > 0) mapped.push({ label: 'MEDIUM', count: counts.Medium, color: '#FFB800' })
    if (counts.Low > 0) mapped.push({ label: 'LOW', count: counts.Low, color: '#00B8D4' })
    if (mapped.length > 0) return mapped
  }
  return SCAN_SEVERITY_DATA
}

function extractTools(queueItems: QueueItem[]): { tool: string; done: boolean; color: string }[] {
  const TOOL_COLORS: Record<string, string> = {
    nmap: '#FFB800', ffuf: '#A78BFA', nuclei: '#00E5FF', sqlmap: '#FF3B3B',
    dalfox: '#FF6B35', whatweb: '#00FF88', shell: 'var(--color-text-muted)', preflight: 'var(--color-accent)',
  }
  const toolMap = new Map<string, boolean>()
  for (const item of queueItems) {
    const toolName = item.tool.toLowerCase()
    if (toolName === 'preflight' || toolName === 'shell') continue
    const wasEnded = toolMap.get(toolName) || false
    if (item.status === 'ended') toolMap.set(toolName, true)
    else if (!wasEnded) toolMap.set(toolName, false)
  }
  return Array.from(toolMap.entries()).map(([tool, done]) => ({
    tool, done, color: TOOL_COLORS[tool] ?? 'var(--color-text-muted)',
  }))
}

export default function ScanVisualizer({ targetUrl, engagementId, status, history, report, error, isLoading, onBack }: ScanVisualizerProps) {
  const [elapsed, setElapsed] = useState(0)
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null)
  const repoPath = targetUrl.replace(/^https?:\/\/(www\.)?github\.com\//, '').replace(/\/$/, '') || 'target/repo'

  const currentStageIdx = Math.max(0, getStageIndex(status))
  const stageStatuses = deriveStageStatuses(status)
  const isRunning = status !== null && status !== 'Completed' && status !== 'Failed'
  const showReport = status === 'Completed'
  const isFailed = status === 'Failed'
  const activeStage = SCAN_STAGES[Math.min(currentStageIdx, SCAN_STAGES.length - 1)]

  const { items: queueItems } = useQueue(isRunning)
  const deployedTools = extractTools(queueItems)
  const severityData = extractSeverityData(report)
  const maxSeverityCount = Math.max(...severityData.map(s => s.count), 1)

  const hasLiveData = queueItems.length > 0

  useEffect(() => {
    if (!isRunning && !isLoading) {
      if (timerRef.current) clearInterval(timerRef.current)
      return
    }
    timerRef.current = setInterval(() => setElapsed(e => e + 1), 1000)
    return () => { if (timerRef.current) clearInterval(timerRef.current) }
  }, [isRunning, isLoading])

  useEffect(() => { setElapsed(0) }, [engagementId])

  const formatTime = (s: number) => `${String(Math.floor(s / 60)).padStart(2, '0')}:${String(s % 60).padStart(2, '0')}`

  const serverElapsed = (() => {
    if (history.length < 2) return null
    const first = new Date(history[0].timestamp).getTime()
    const last = new Date(history[history.length - 1].timestamp).getTime()
    return Math.floor((last - first) / 1000)
  })()
  const displayElapsed = (showReport || isFailed) && serverElapsed !== null ? serverElapsed : elapsed

  return (
    <div className="fixed inset-0 z-50 bg-bg-deep flex flex-col" style={{ animation: 'scan-view-enter 0.5s cubic-bezier(0.16, 1, 0.3, 1) both' }}>

      {/* TOP BAR */}
      <div className="shrink-0 border-b border-border-subtle px-6 md:px-8 py-3.5 flex items-center justify-between bg-bg-deep/95 backdrop-blur-sm">
        <div className="flex items-center gap-4">
          <button onClick={onBack} className="font-mono text-xs text-text-muted hover:text-accent transition-colors tracking-wider cursor-crosshair">\u2190 ABORT</button>
          <div className="w-px h-5 bg-border-subtle" />
          <span className="font-display text-xl text-accent tracking-[0.15em]" style={{ textShadow: '0 0 20px rgba(0,229,255,0.3)' }}>REDSHELL</span>
          <span className="text-text-muted text-xs tracking-[0.08em] hidden sm:inline">
            ENGAGEMENT // <span className="text-redshell font-bold">{engagementId ? engagementId.slice(0, 8) : repoPath.slice(0, 28)}{repoPath.length > 28 && !engagementId ? '\u2026' : ''}</span>
          </span>
        </div>
        <div className="flex items-center gap-6">
          <div className="text-right hidden sm:block">
            <div className="font-label text-[0.6rem] text-text-muted tracking-[0.1em]">ELAPSED</div>
            <div className="font-mono text-lg font-bold tabular-nums" style={{ color: isRunning ? activeStage.color : 'var(--color-success)' }}>{formatTime(displayElapsed)}</div>
          </div>
          <div className="flex items-center gap-2.5">
            <div className="w-2 h-2 rounded-full" style={{ background: isFailed ? '#FF3B3B' : isRunning || isLoading ? '#FF3B3B' : 'var(--color-success)', boxShadow: isFailed ? '0 0 8px #FF3B3B' : isRunning || isLoading ? '0 0 8px #FF3B3B' : '0 0 8px var(--color-success)' }} />
            <span className="font-label text-xs tracking-[0.15em] font-bold" style={{ color: isFailed ? '#FF3B3B' : isRunning || isLoading ? '#FF3B3B' : 'var(--color-success)' }}>
              {isLoading ? 'STARTING' : isFailed ? 'FAILED' : isRunning ? 'LIVE' : 'COMPLETE'}
            </span>
          </div>
        </div>
      </div>

      {/* TARGET URL BAR */}
      <div className="shrink-0 px-6 md:px-8 py-2.5 border-b border-border-subtle/50 bg-bg-surface/50 flex items-center gap-3">
        <span className="font-label text-[0.65rem] text-text-muted tracking-[0.1em]">TARGET</span>
        <span className="text-text-muted">\u2192</span>
        <span className="font-mono text-[0.8rem] text-text-muted">https://github.com/</span>
        <span className="font-mono text-[0.8rem] text-text-primary font-bold">{repoPath}</span>
        <div className="ml-auto font-label text-[0.65rem] text-text-muted tracking-[0.1em]">
          {SCAN_STAGES.filter((_, i) => stageStatuses[i] === 'done').length}/{SCAN_STAGES.length} PHASES
        </div>
      </div>

      {/* ERROR BANNER */}
      {(error || isFailed) && (
        <div className="shrink-0 px-6 md:px-8 py-3 bg-[#FF3B3B12] border-b border-[#FF3B3B33] flex items-center gap-3">
          <span className="font-mono text-xs text-[#FF3B3B] font-bold">\u26a0 ERROR</span>
          <span className="font-mono text-xs text-text-muted">{error || 'Scan failed. The server encountered an error processing this engagement.'}</span>
          <button onClick={onBack} className="ml-auto font-mono text-xs text-accent hover:text-text-primary transition-colors tracking-wider">\u2190 TRY AGAIN</button>
        </div>
      )}

      {/* LOADING STATE */}
      {isLoading && !status && (
        <div className="flex-1 flex items-center justify-center">
          <div className="text-center">
            <div className="font-display text-[2.5rem] text-accent tracking-[0.1em] mb-4" style={{ textShadow: '0 0 40px rgba(0,229,255,0.3)' }}>INITIALIZING</div>
            <div className="font-mono text-sm text-text-muted">Contacting Red Team Engine...</div>
            <div className="mt-6 h-1 w-48 mx-auto bg-bg-surface rounded-full overflow-hidden">
              <div className="h-full rounded-full bg-accent" style={{ animation: 'scan-progress-flow 1.5s ease-in-out infinite alternate' }} />
            </div>
          </div>
        </div>
      )}

      {/* REPORT VIEW (full-width when completed) */}
      {status && !isLoading && showReport && (
        <div className="flex-1 min-h-0 flex flex-col" style={{ animation: 'fade-slide-up 0.4s ease' }}>
          {report ? (
            <ReportView
              report={report}
              engagementId={engagementId}
              targetUrl={targetUrl}
              elapsed={formatTime(displayElapsed)}
              onBack={onBack}
            />
          ) : (
            <div className="flex-1 flex items-center justify-center">
              <div className="font-mono text-sm text-text-muted">Loading report data...</div>
            </div>
          )}
        </div>
      )}

      {/* MAIN 3-COL LAYOUT (scanning / failed states) */}
      {status && !isLoading && !showReport && (
        <div className="flex-1 grid grid-cols-[72px_1fr_260px] min-h-0 overflow-hidden">

          {/* LEFT \u2014 STAGE PIPELINE */}
          <div className="border-r border-border-subtle/50 py-6 flex flex-col items-center gap-0 overflow-y-auto bg-bg-deep/60">
            {SCAN_STAGES.map((stage, i) => (
              <StageNode key={stage.id} stage={stage} status={stageStatuses[i]} isLast={i === SCAN_STAGES.length - 1} />
            ))}
          </div>

          {/* CENTER \u2014 MAIN DISPLAY */}
          <div className="p-5 md:p-7 flex flex-col gap-5 overflow-y-auto">
            <div style={{ animation: 'fade-slide-up 0.4s ease' }} key={isFailed ? 'failed' : activeStage.id}>
              <div className="flex items-baseline gap-4 mb-2">
                <span className="font-display text-[2.8rem] sm:text-[3.5rem] leading-none tracking-[0.06em]" style={{ color: isFailed ? '#FF3B3B' : activeStage.color, textShadow: `0 0 40px ${isFailed ? 'rgba(255,59,59,0.2)' : activeStage.glow}` }}>
                  {isFailed ? 'OPERATION FAILED' : activeStage.label}
                </span>
                {!isFailed && (
                  <span className="font-label text-xs text-text-muted tracking-[0.15em] pl-3 border-l border-border-subtle">PHASE {activeStage.code} / {String(SCAN_STAGES.length).padStart(2, '0')}</span>
                )}
              </div>
              <div className="font-mono text-sm text-text-muted tracking-[0.04em]">
                {isFailed ? (error || 'The scan could not be completed.') : activeStage.sublabel}
              </div>
            </div>

            {!isFailed && (
              <div className="flex items-center gap-8 p-6" style={{ border: `1px solid ${activeStage.color}18`, background: `${activeStage.color}06`, borderLeft: `3px solid ${activeStage.color}` }}>
                <StageIndicator stage={activeStage} active />
                <div className="flex-1 min-w-0">
                  <div className="mb-4">
                    <div className="font-label text-[0.7rem] text-text-muted tracking-[0.12em] mb-1.5">CURRENT OPERATION</div>
                    <div className="font-mono text-base font-bold tracking-[0.04em]" style={{ color: activeStage.color }}>{activeStage.sublabel.toUpperCase()}</div>
                  </div>
                  <div className="h-1 bg-bg-surface rounded-full overflow-hidden">
                    <div className="h-full rounded-full" style={{ background: activeStage.color, opacity: 0.7, animation: 'scan-progress-flow 3s ease-in-out infinite alternate' }} />
                  </div>
                </div>
              </div>
            )}

            {!isFailed && (
              <div className="flex flex-col">
                <div className="flex items-center gap-2 px-4 py-2.5 bg-bg-card border border-border-subtle border-b-0" style={{ borderTop: `2px solid ${activeStage.color}55` }}>
                  <div className="flex gap-1.5">
                    <div className="w-2.5 h-2.5 rounded-full bg-redshell opacity-60" />
                    <div className="w-2.5 h-2.5 rounded-full bg-warning opacity-40" />
                    <div className="w-2.5 h-2.5 rounded-full bg-success opacity-40" />
                  </div>
                  <span className="font-label text-[0.65rem] text-text-muted tracking-wider ml-2">kali@redshell-{activeStage.id.toLowerCase()} ~ %</span>
                  <span className="ml-auto font-label text-[0.6rem] tracking-[0.1em]" style={{ color: activeStage.color }}>{hasLiveData ? 'LIVE OUTPUT' : 'SIMULATED OUTPUT'}</span>
                </div>
                {hasLiveData ? (
                  <LiveTerminal items={queueItems} stageColor={activeStage.color} />
                ) : (
                  <TerminalLog key={activeStage.id} logs={activeStage.logs} stageColor={activeStage.color} />
                )}
              </div>
            )}

            {isFailed && (
              <div className="flex flex-col gap-5">
                <div className="p-6 border" style={{ borderColor: '#FF3B3B33', background: '#FF3B3B08', borderLeft: '3px solid #FF3B3B' }}>
                  <div className="font-mono text-sm text-[#FF3B3B] font-bold mb-2">Scan terminated with errors</div>
                  <div className="font-mono text-xs text-text-muted leading-relaxed">{error || 'The engagement could not be completed. Check the target URL and try again.'}</div>
                  {history.length > 0 && (
                    <div className="mt-4 pt-4 border-t border-[#FF3B3B22]">
                      <div className="font-label text-[0.6rem] text-text-dim tracking-[0.12em] mb-2">STATE HISTORY</div>
                      {history.map((h, i) => (
                        <div key={i} className="font-mono text-xs text-text-muted py-0.5">
                          {new Date(h.timestamp).toLocaleTimeString('en-US', { hour12: false })} \u2014 {h.state}
                        </div>
                      ))}
                    </div>
                  )}
                </div>
                <button onClick={onBack} className="self-start py-3.5 px-8 font-mono text-xs font-bold tracking-[0.12em] border border-accent text-accent bg-transparent hover:bg-accent/10 transition-all cursor-crosshair">\u21a9 TRY AGAIN</button>
              </div>
            )}
          </div>

          {/* RIGHT PANEL */}
          <div className="border-l border-border-subtle/50 p-4 flex flex-col gap-5 overflow-y-auto bg-bg-deep/60">
            <div>
              <div className="font-label text-[0.65rem] text-text-muted tracking-[0.15em] mb-3">OPERATION LOG</div>
              {SCAN_STAGES.map((stage, i) => {
                const stStatus = stageStatuses[i]
                return (
                  <div key={stage.id} className="flex items-center gap-2.5 px-2.5 py-2 mb-0.5 transition-all duration-300" style={{ background: stStatus === 'active' ? `${stage.color}0a` : 'transparent', borderLeft: stStatus === 'active' ? `2px solid ${stage.color}` : '2px solid transparent' }}>
                    <div className="w-1.5 h-1.5 rounded-full shrink-0" style={{ background: stStatus === 'done' || stStatus === 'active' ? stage.color : 'var(--color-border-subtle)', boxShadow: stStatus === 'active' ? `0 0 6px ${stage.color}` : 'none' }} />
                    <span className="font-mono text-[0.68rem] tracking-[0.06em] font-bold flex-1" style={{ color: stStatus === 'done' ? 'var(--color-text-muted)' : stStatus === 'active' ? stage.color : 'var(--color-text-dim)', opacity: stStatus === 'pending' ? 0.35 : 1 }}>{stage.label}</span>
                    <span className="font-mono text-[0.6rem] tracking-[0.1em]" style={{ color: stStatus === 'done' ? 'var(--color-success)' : stStatus === 'active' ? stage.color : 'var(--color-border-subtle)' }}>
                      {stStatus === 'done' ? '\u2713' : stStatus === 'active' ? '\u25cf' : '\u25cb'}
                    </span>
                  </div>
                )
              })}
            </div>

            {history.length > 0 && (
              <div>
                <div className="font-label text-[0.65rem] text-text-muted tracking-[0.15em] mb-3">STATE TRANSITIONS</div>
                {history.map((h, i) => (
                  <div key={i} className="flex justify-between py-1.5 border-b border-border-subtle/20">
                    <span className="font-mono text-[0.65rem] text-text-muted">{h.state.replace('_', ' ')}</span>
                    <span className="font-mono text-[0.6rem] text-text-dim">{new Date(h.timestamp).toLocaleTimeString('en-US', { hour12: false })}</span>
                  </div>
                ))}
              </div>
            )}

            {(currentStageIdx >= 2) && (
              <div>
                <div className="font-label text-[0.65rem] text-text-muted tracking-[0.15em] mb-3">FINDINGS SEVERITY</div>
                {severityData.map((item, i) => (
                  <SeverityBar key={item.label} item={item} animate={currentStageIdx >= 3} delay={i * 200} maxCount={maxSeverityCount} />
                ))}
              </div>
            )}

            <div>
              <div className="font-label text-[0.65rem] text-text-muted tracking-[0.15em] mb-3">SYSTEM TELEMETRY</div>
              {([
                ['CONTAINERS', currentStageIdx >= 1 ? '2 ACTIVE' : isLoading ? 'STARTING...' : '0 ACTIVE', currentStageIdx >= 1 ? 'var(--color-success)' : 'var(--color-text-dim)'],
                ['NETWORK', engagementId ? `rs-net-${engagementId.slice(0, 4)}` : '\u2014', 'var(--color-text-muted)'],
                ['QUEUE ITEMS', `${queueItems.length} TOTAL`, queueItems.length > 0 ? '#00E5FF' : 'var(--color-text-dim)'],
                ['REPORT', isFailed ? 'N/A' : 'PENDING', isFailed ? '#FF3B3B' : 'var(--color-text-dim)'],
              ] as const).map(([key, val, color]) => (
                <div key={key} className="flex justify-between py-2 border-b border-border-subtle/30">
                  <span className="font-label text-[0.65rem] text-text-muted tracking-[0.08em]">{key}</span>
                  <span className="font-mono text-[0.68rem] font-bold tracking-[0.06em]" style={{ color }}>{val}</span>
                </div>
              ))}
            </div>

            {(deployedTools.length > 0 || currentStageIdx >= 2) && (
              <div>
                <div className="font-label text-[0.65rem] text-text-muted tracking-[0.15em] mb-3">TOOLS DEPLOYED</div>
                {deployedTools.length > 0 ? (
                  deployedTools.map(({ tool, done, color }) => (
                    <div key={tool} className="flex items-center gap-2.5 py-2 border-b border-border-subtle/30">
                      <div className="w-2 h-2 rounded-full" style={{ background: color, boxShadow: done ? `0 0 6px ${color}` : 'none' }} />
                      <span className="font-mono text-[0.75rem] font-bold tracking-[0.04em]" style={{ color }}>{tool}</span>
                      <span className="ml-auto font-label text-[0.6rem]" style={{ color: done ? 'var(--color-success)' : 'var(--color-text-muted)' }}>{done ? 'COMPLETE' : 'RUNNING'}</span>
                    </div>
                  ))
                ) : (
                  ['nmap', 'ffuf', 'nuclei', 'sqlmap'].map(tool => (
                    <div key={tool} className="flex items-center gap-2.5 py-2 border-b border-border-subtle/30">
                      <div className="w-2 h-2 rounded-full" style={{ background: 'var(--color-border-subtle)' }} />
                      <span className="font-mono text-[0.75rem] font-bold tracking-[0.04em] text-text-dim">{tool}</span>
                      <span className="ml-auto font-label text-[0.6rem] text-text-muted">QUEUED</span>
                    </div>
                  ))
                )}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}