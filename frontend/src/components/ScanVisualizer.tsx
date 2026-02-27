import { useState, useEffect, useRef, useCallback } from 'react'
import { SCAN_STAGES, SCAN_SEVERITY_DATA, STAGE_DURATIONS } from '../data/scanStages'
import type { ScanStage } from '../data/scanStages'

/* ─────────────────────────────────────────────────
   Sub-components
   ───────────────────────────────────────────────── */

/** Radar ring animation for active stage */
function RadarRing({ stage, active }: { stage: ScanStage; active: boolean }) {
  const rings = [1, 2, 3]
  return (
    <div className="relative w-[160px] h-[160px] shrink-0">
      {rings.map((r, i) => (
        <div
          key={r}
          className="absolute top-1/2 left-1/2 rounded-full"
          style={{
            width: 50 * r,
            height: 50 * r,
            transform: 'translate(-50%, -50%)',
            border: `1px solid ${active ? stage.color : 'var(--color-border-subtle)'}`,
            opacity: active ? 1 - i * 0.25 : 0.15,
            animation: active ? `radar-pulse ${1.5 + i * 0.5}s ease-out infinite` : 'none',
            animationDelay: `${i * 0.3}s`,
            transition: 'all 0.5s ease',
            boxShadow: active ? `0 0 ${8 + i * 4}px ${stage.glow}` : 'none',
          }}
        />
      ))}
      {/* Sweep line */}
      {active && (
        <div
          className="absolute top-1/2 left-1/2"
          style={{
            width: '50%',
            height: 1,
            background: `linear-gradient(90deg, transparent, ${stage.color})`,
            transformOrigin: 'left center',
            animation: 'radar-sweep 2s linear infinite',
          }}
        />
      )}
      {/* Center dot */}
      <div
        className="absolute top-1/2 left-1/2 rounded-full"
        style={{
          width: 8,
          height: 8,
          transform: 'translate(-50%, -50%)',
          background: active ? stage.color : 'var(--color-border-subtle)',
          boxShadow: active ? `0 0 12px ${stage.color}` : 'none',
          transition: 'all 0.5s',
        }}
      />
    </div>
  )
}

/** Terminal log with typewriter effect — remounted via key={stageId} */
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
    if (line.includes('CRITICAL') || line.includes('⚠ CRITICAL')) return '#FF3B3B'
    if (line.includes('HIGH') || line.includes('⚠ HIGH')) return '#FF6B35'
    if (line.includes('MEDIUM')) return '#FFB800'
    if (line.includes('✓')) return 'var(--color-success)'
    if (line.startsWith('$') || line.startsWith('[')) return stageColor
    if (line.startsWith('::')) return '#A78BFA'
    if (line === '') return 'var(--color-border-subtle)'
    if (line.startsWith('━')) return stageColor
    if (line.includes('COMPLETED')) return 'var(--color-success)'
    return 'var(--color-text-muted)'
  }

  return (
    <div
      className="font-mono text-[0.72rem] leading-[1.7] h-[280px] overflow-y-auto p-3 bg-bg-surface border border-border-subtle"
      style={{ borderTop: `1px solid ${stageColor}33` }}
    >
      {displayedLogs.map((line, i) => (
        <div key={i} style={{ color: colorize(line), whiteSpace: 'pre' }}>
          {line || '\u00A0'}
        </div>
      ))}
      {currentTyping !== null && (
        <div style={{ color: colorize(logs[currentLine] || ''), whiteSpace: 'pre' }}>
          {currentTyping}
          <span
            className="inline-block w-[7px] h-[13px] ml-px align-middle"
            style={{
              background: stageColor,
              animation: 'cursor-blink 0.7s step-end infinite',
            }}
          />
        </div>
      )}
      <div ref={bottomRef} />
    </div>
  )
}

/** Stage node in the vertical pipeline */
function StageNode({
  stage,
  status,
  isLast,
  nextStage,
}: {
  stage: ScanStage
  status: 'pending' | 'active' | 'done'
  isLast: boolean
  nextStage?: ScanStage
}) {
  const isDone = status === 'done'
  const isActive = status === 'active'

  return (
    <div className="flex flex-col items-center">
      <div className="flex flex-col items-center gap-1.5">
        {/* Circle */}
        <div
          className="w-11 h-11 rounded-full flex items-center justify-center relative transition-all duration-400"
          style={{
            border: `2px solid ${isDone || isActive ? stage.color : 'var(--color-border-subtle)'}`,
            background: isDone
              ? `${stage.color}22`
              : isActive
                ? `${stage.color}15`
                : 'transparent',
            boxShadow: isActive
              ? `0 0 20px ${stage.glow}, 0 0 40px ${stage.glow}`
              : isDone
                ? `0 0 10px ${stage.glow}`
                : 'none',
            animation: isActive ? 'active-node-pulse 2s ease-in-out infinite' : 'none',
          }}
        >
          {isDone ? (
            <svg width="16" height="16" viewBox="0 0 18 18">
              <polyline
                points="3,9 7,13 15,5"
                fill="none"
                stroke={stage.color}
                strokeWidth="2.5"
                strokeLinecap="round"
              />
            </svg>
          ) : (
            <span
              className="font-mono text-[0.65rem] font-bold transition-colors duration-300"
              style={{ color: isActive ? stage.color : 'var(--color-text-dim)' }}
            >
              {stage.code}
            </span>
          )}
          {isActive && (
            <div
              className="absolute rounded-full"
              style={{
                inset: -4,
                border: `1px solid ${stage.color}`,
                opacity: 0.5,
                animation: 'scan-ripple 1.5s ease-out infinite',
              }}
            />
          )}
        </div>
        {/* Label */}
        <span
          className="font-mono text-[0.5rem] font-bold tracking-[0.12em] text-center max-w-[72px] transition-colors duration-300"
          style={{
            color: isDone || isActive ? stage.color : 'var(--color-text-dim)',
          }}
        >
          {stage.label}
        </span>
      </div>
      {/* Connector */}
      {!isLast && (
        <div
          className="w-px h-7 mt-1 relative overflow-hidden transition-all duration-500"
          style={{
            background: isDone
              ? `linear-gradient(180deg, ${stage.color}, ${nextStage?.color || stage.color})`
              : 'var(--color-border-subtle)',
          }}
        >
          {isDone && (
            <div
              className="absolute inset-0 opacity-40"
              style={{
                background: 'linear-gradient(180deg, transparent, white, transparent)',
                animation: 'flow-down 1.5s linear infinite',
              }}
            />
          )}
        </div>
      )}
    </div>
  )
}

/** Severity bar with animated fill */
function SeverityBar({
  item,
  animate,
  delay,
}: {
  item: { label: string; count: number; color: string }
  animate: boolean
  delay: number
}) {
  const [width, setWidth] = useState(0)
  const max = 11

  useEffect(() => {
    if (animate) {
      const t = setTimeout(() => setWidth((item.count / max) * 100), delay)
      return () => clearTimeout(t)
    }
  }, [animate, item.count, delay, max])

  return (
    <div className="mb-2.5">
      <div className="flex justify-between mb-1">
        <span
          className="font-mono text-[0.6rem] tracking-[0.1em]"
          style={{ color: item.color }}
        >
          {item.label}
        </span>
        <span className="font-mono text-[0.6rem] text-text-dim">
          {animate ? item.count : 0}
        </span>
      </div>
      <div className="h-1 bg-bg-deep rounded-sm overflow-hidden">
        <div
          className="h-full rounded-sm"
          style={{
            width: `${width}%`,
            background: item.color,
            boxShadow: `0 0 8px ${item.color}`,
            transition: 'width 1s cubic-bezier(0.34, 1.56, 0.64, 1)',
          }}
        />
      </div>
    </div>
  )
}

/* ─────────────────────────────────────────────────
   Main Visualizer
   ───────────────────────────────────────────────── */

interface ScanVisualizerProps {
  targetUrl: string
  onBack: () => void
}

export default function ScanVisualizer({ targetUrl, onBack }: ScanVisualizerProps) {
  const [currentStageIdx, setCurrentStageIdx] = useState(0)
  const [stageStatuses, setStageStatuses] = useState<('pending' | 'active' | 'done')[]>(
    SCAN_STAGES.map((_, i) => (i === 0 ? 'active' : 'pending'))
  )
  const [elapsed, setElapsed] = useState(0)
  const [isRunning, setIsRunning] = useState(true)
  const [showReport, setShowReport] = useState(false)
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null)
  const stageTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  // Extract repo path from URL
  const repoPath = targetUrl.replace(/^https?:\/\/(www\.)?github\.com\//, '').replace(/\/$/, '') || 'target/repo'

  const advanceStageRef = useRef<(idx: number) => void>(null)

  const advanceStage = useCallback((idx: number) => {
    if (idx >= SCAN_STAGES.length - 1) {
      setStageStatuses(SCAN_STAGES.map(() => 'done'))
      setIsRunning(false)
      setTimeout(() => setShowReport(true), 800)
      return
    }
    setStageStatuses(prev => {
      const next = [...prev]
      next[idx] = 'done'
      next[idx + 1] = 'active'
      return next
    })
    setCurrentStageIdx(idx + 1)
    stageTimerRef.current = setTimeout(() => advanceStageRef.current?.(idx + 1), STAGE_DURATIONS[idx + 1])
  }, [])

  useEffect(() => {
    advanceStageRef.current = advanceStage
  }, [advanceStage])

  useEffect(() => {
    stageTimerRef.current = setTimeout(() => advanceStage(0), STAGE_DURATIONS[0])
    return () => {
      if (stageTimerRef.current) clearTimeout(stageTimerRef.current)
    }
  }, [advanceStage])

  useEffect(() => {
    if (!isRunning) return
    timerRef.current = setInterval(() => setElapsed(e => e + 1), 1000)
    return () => {
      if (timerRef.current) clearInterval(timerRef.current)
    }
  }, [isRunning])

  const activeStage = SCAN_STAGES[currentStageIdx]
  const formatTime = (s: number) =>
    `${String(Math.floor(s / 60)).padStart(2, '0')}:${String(s % 60).padStart(2, '0')}`

  const handleReset = () => {
    if (stageTimerRef.current) clearTimeout(stageTimerRef.current)
    if (timerRef.current) clearInterval(timerRef.current)
    setCurrentStageIdx(0)
    setStageStatuses(SCAN_STAGES.map((_, i) => (i === 0 ? 'active' : 'pending')))
    setElapsed(0)
    setIsRunning(true)
    setShowReport(false)
    stageTimerRef.current = setTimeout(() => advanceStage(0), STAGE_DURATIONS[0])
  }

  return (
    <div className="fixed inset-0 z-50 bg-bg-deep flex flex-col" style={{ animation: 'scan-view-enter 0.5s cubic-bezier(0.16, 1, 0.3, 1) both' }}>

      {/* ── TOP BAR ── */}
      <div className="shrink-0 border-b border-border-subtle px-5 md:px-8 py-3 flex items-center justify-between bg-bg-deep/95 backdrop-blur-sm">
        <div className="flex items-center gap-4">
          {/* Back button */}
          <button
            onClick={onBack}
            className="font-mono text-[0.7rem] text-text-dim hover:text-accent transition-colors tracking-wider cursor-crosshair"
          >
            ← ABORT
          </button>
          <div className="w-px h-4 bg-border-subtle" />
          <span className="font-display text-lg text-accent tracking-[0.15em]" style={{ textShadow: '0 0 20px rgba(0,229,255,0.3)' }}>
            REDSHELL
          </span>
          <span className="text-text-dim text-[0.6rem] tracking-[0.1em] hidden sm:inline">
            ENGAGEMENT // <span className="text-redshell">
              {repoPath.slice(0, 24)}{repoPath.length > 24 ? '...' : ''}
            </span>
          </span>
        </div>
        <div className="flex items-center gap-5">
          <div className="text-right hidden sm:block">
            <div className="font-label text-[0.5rem] text-text-dim tracking-[0.1em]">ELAPSED</div>
            <div
              className="font-mono text-base font-bold"
              style={{ color: isRunning ? activeStage.color : 'var(--color-success)' }}
            >
              {formatTime(elapsed)}
            </div>
          </div>
          <div className="flex items-center gap-2">
            <div
              className="w-2 h-2 rounded-full"
              style={{
                background: isRunning ? '#FF3B3B' : 'var(--color-success)',
                boxShadow: isRunning ? '0 0 12px #FF3B3B' : '0 0 12px var(--color-success)',
                animation: isRunning ? 'dot-blink 1s ease-in-out infinite' : 'none',
              }}
            />
            <span
              className="font-label text-[0.55rem] tracking-[0.15em]"
              style={{ color: isRunning ? '#FF3B3B' : 'var(--color-success)' }}
            >
              {isRunning ? 'LIVE' : 'COMPLETE'}
            </span>
          </div>
        </div>
      </div>

      {/* ── TARGET URL BAR ── */}
      <div className="shrink-0 px-5 md:px-8 py-2.5 border-b border-border-subtle/50 bg-bg-surface/50 flex items-center gap-3">
        <span className="font-label text-[0.5rem] text-text-dim tracking-[0.1em]">TARGET</span>
        <span className="text-text-dim text-[0.6rem]">→</span>
        <span className="font-mono text-[0.68rem] text-text-dim">https://github.com/</span>
        <span className="font-mono text-[0.68rem] text-text-primary font-bold">{repoPath}</span>
        <div className="ml-auto font-label text-[0.5rem] text-text-dim tracking-[0.1em]">
          {SCAN_STAGES.filter((_, i) => stageStatuses[i] === 'done').length}/{SCAN_STAGES.length} PHASES
        </div>
      </div>

      {/* ── MAIN 3-COL LAYOUT ── */}
      <div className="flex-1 grid grid-cols-[72px_1fr_260px] min-h-0 overflow-hidden">

        {/* LEFT — STAGE PIPELINE */}
        <div className="border-r border-border-subtle/50 py-6 flex flex-col items-center gap-0 overflow-y-auto bg-bg-deep/60">
          {SCAN_STAGES.map((stage, i) => (
            <StageNode
              key={stage.id}
              stage={stage}
              status={stageStatuses[i]}
              isLast={i === SCAN_STAGES.length - 1}
              nextStage={SCAN_STAGES[i + 1]}
            />
          ))}
        </div>

        {/* CENTER — MAIN DISPLAY */}
        <div className="p-5 md:p-7 flex flex-col gap-5 overflow-y-auto">
          {/* Stage Header */}
          <div style={{ animation: 'fade-slide-up 0.4s ease' }} key={showReport ? 'report' : activeStage.id}>
            <div className="flex items-baseline gap-3 mb-1">
              <span
                className="font-display text-[2.2rem] sm:text-[2.8rem] leading-none tracking-[0.08em]"
                style={{
                  color: showReport ? 'var(--color-success)' : activeStage.color,
                  textShadow: `0 0 30px ${showReport ? 'rgba(0,255,136,0.3)' : activeStage.glow}`,
                }}
              >
                {showReport ? 'OPERATION COMPLETE' : activeStage.label}
              </span>
              {!showReport && (
                <span className="font-label text-[0.5rem] text-text-dim tracking-[0.15em] pl-2 border-l border-border-subtle">
                  PHASE {activeStage.code} / 06
                </span>
              )}
            </div>
            <div className="font-mono text-[0.7rem] text-text-dim tracking-[0.08em]">
              {showReport ? 'All containers stopped. Report ready.' : activeStage.sublabel}
            </div>
          </div>

          {/* Radar + Status Row */}
          {!showReport && (
            <div
              className="flex items-center gap-6 p-5 border border-border-subtle"
              style={{
                borderColor: `${activeStage.color}22`,
                background: `${activeStage.color}08`,
                borderLeft: `3px solid ${activeStage.color}`,
              }}
            >
              <RadarRing stage={activeStage} active />
              <div className="flex-1 min-w-0">
                <div className="mb-3">
                  <div className="font-label text-[0.5rem] text-text-dim tracking-[0.1em] mb-1">
                    CURRENT OPERATION
                  </div>
                  <div
                    className="font-mono text-sm font-bold tracking-[0.05em]"
                    style={{ color: activeStage.color }}
                  >
                    {activeStage.sublabel.toUpperCase()}
                  </div>
                </div>
                {/* Animated progress bar */}
                <div className="h-[2px] bg-bg-deep rounded-sm overflow-hidden">
                  <div
                    className="h-full"
                    style={{
                      background: `linear-gradient(90deg, ${activeStage.color}, ${activeStage.color}88)`,
                      boxShadow: `0 0 8px ${activeStage.color}`,
                      animation: 'scan-progress-flow 2s ease-in-out infinite alternate',
                    }}
                  />
                </div>
              </div>
            </div>
          )}

          {/* Terminal */}
          {!showReport && (
            <div className="flex flex-col">
              {/* Terminal header */}
              <div
                className="flex items-center gap-2 px-4 py-2 bg-bg-card border border-border-subtle border-b-0"
                style={{ borderTop: `1px solid ${activeStage.color}44` }}
              >
                <div className="flex gap-1.5">
                  <div className="w-2.5 h-2.5 rounded-full bg-redshell opacity-60" />
                  <div className="w-2.5 h-2.5 rounded-full bg-warning opacity-40" />
                  <div className="w-2.5 h-2.5 rounded-full bg-success opacity-40" />
                </div>
                <span className="font-label text-[0.55rem] text-text-dim tracking-wider ml-2">
                  kali@redshell-{activeStage.id.toLowerCase()} ~ %
                </span>
                <span
                  className="ml-auto font-label text-[0.5rem] tracking-[0.1em]"
                  style={{ color: activeStage.color }}
                >
                  LIVE OUTPUT
                </span>
              </div>
              <TerminalLog
                key={activeStage.id}
                logs={activeStage.logs}
                stageColor={activeStage.color}
              />
            </div>
          )}

          {/* REPORT PANEL */}
          {showReport && (
            <div style={{ animation: 'scan-report-reveal 0.6s cubic-bezier(0.34,1.56,0.64,1)' }}>
              <div className="border border-border-subtle bg-bg-card/60 p-6" style={{ borderTop: '2px solid var(--color-redshell)' }}>
                {/* Report header */}
                <div className="mb-5">
                  <div className="font-label text-[0.5rem] text-text-dim tracking-[0.15em] mb-1.5">
                    SECURITY ASSESSMENT REPORT // RS-2026-a3f9
                  </div>
                  <div className="font-display text-xl text-text-primary tracking-[0.1em]">
                    TARGET: {repoPath.toUpperCase()}
                  </div>
                  <div className="flex gap-4 mt-2">
                    <span className="font-mono text-[0.6rem] text-text-dim">Duration: {formatTime(elapsed)}</span>
                    <span className="text-border-subtle">·</span>
                    <span className="font-mono text-[0.6rem] text-text-dim">Scan ID: a3f9e7c2</span>
                    <span className="text-border-subtle">·</span>
                    <span className="font-mono text-[0.6rem] text-text-dim">28 Findings</span>
                  </div>
                </div>

                {/* Severity summary grid */}
                <div className="grid grid-cols-4 gap-2 mb-5">
                  {SCAN_SEVERITY_DATA.map(s => (
                    <div
                      key={s.label}
                      className="p-3 text-center border"
                      style={{
                        borderColor: `${s.color}33`,
                        background: `${s.color}0a`,
                      }}
                    >
                      <div className="font-display text-2xl leading-none" style={{ color: s.color }}>
                        {s.count}
                      </div>
                      <div
                        className="font-label text-[0.5rem] tracking-[0.12em] mt-1"
                        style={{ color: s.color }}
                      >
                        {s.label}
                      </div>
                    </div>
                  ))}
                </div>

                {/* Sample finding */}
                <div className="border-t border-border-subtle pt-5">
                  <div className="font-label text-[0.5rem] text-text-dim tracking-[0.1em] mb-3">
                    TOP FINDING PREVIEW
                  </div>
                  <div
                    className="p-4 border"
                    style={{
                      background: 'rgba(255,59,59,0.04)',
                      borderColor: 'rgba(255,59,59,0.2)',
                      borderLeft: '3px solid #FF3B3B',
                    }}
                  >
                    <div className="flex justify-between items-start mb-2">
                      <span className="font-mono text-[0.75rem] text-text-primary font-bold">
                        RS-001 — SQL Injection in /api/search
                      </span>
                      <span
                        className="font-label text-[0.5rem] px-2 py-0.5 tracking-[0.1em]"
                        style={{
                          background: 'rgba(255,59,59,0.2)',
                          color: '#FF3B3B',
                          animation: 'severity-pulse 2s ease-in-out infinite',
                        }}
                      >
                        CRITICAL
                      </span>
                    </div>
                    <div className="font-mono text-[0.65rem] text-text-dim mb-2.5">
                      The parameter 'q' in /api/search is vulnerable to error-based SQL injection allowing full database extraction.
                    </div>
                    <div className="p-2 bg-bg-deep border border-border-subtle font-mono text-[0.65rem] text-success">
                      GET /api/search?q=1'+AND+EXTRACTVALUE(1,CONCAT(0x7e,version()))--
                    </div>
                  </div>
                </div>

                {/* CTA Buttons */}
                <div className="flex gap-3 mt-5">
                  <button
                    onClick={handleReset}
                    className="flex-1 py-3 font-mono text-[0.68rem] font-bold tracking-[0.15em] border border-accent text-accent bg-transparent hover:bg-accent/10 transition-all cursor-crosshair"
                  >
                    ↩ RUN NEW SCAN
                  </button>
                  <button className="flex-[2] py-3 font-mono text-[0.68rem] font-bold tracking-[0.15em] bg-accent text-bg-deep border-none hover:shadow-[0_0_30px_rgba(0,229,255,0.4)] transition-all cursor-crosshair">
                    VIEW FULL REPORT →
                  </button>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* RIGHT PANEL */}
        <div className="border-l border-border-subtle/50 p-4 flex flex-col gap-5 overflow-y-auto bg-bg-deep/60">

          {/* Phase status list */}
          <div>
            <div className="font-label text-[0.5rem] text-text-dim tracking-[0.15em] mb-3">
              OPERATION LOG
            </div>
            {SCAN_STAGES.map((stage, i) => {
              const status = stageStatuses[i]
              return (
                <div
                  key={stage.id}
                  className="flex items-center gap-2.5 px-2.5 py-2 mb-0.5 transition-all duration-300"
                  style={{
                    background: status === 'active' ? `${stage.color}0a` : 'transparent',
                    borderLeft: status === 'active' ? `2px solid ${stage.color}` : '2px solid transparent',
                  }}
                >
                  <div
                    className="w-1.5 h-1.5 rounded-full shrink-0"
                    style={{
                      background: status === 'done' || status === 'active' ? stage.color : 'var(--color-border-subtle)',
                      boxShadow: status === 'active' ? `0 0 8px ${stage.color}` : 'none',
                      animation: status === 'active' ? 'dot-blink 1s infinite' : 'none',
                    }}
                  />
                  <span
                    className="font-mono text-[0.55rem] tracking-[0.08em] font-bold flex-1"
                    style={{
                      color:
                        status === 'done'
                          ? 'var(--color-text-dim)'
                          : status === 'active'
                            ? stage.color
                            : 'var(--color-text-dim)',
                      opacity: status === 'pending' ? 0.3 : 1,
                    }}
                  >
                    {stage.label}
                  </span>
                  <span
                    className="font-mono text-[0.5rem] tracking-[0.1em]"
                    style={{
                      color:
                        status === 'done'
                          ? 'var(--color-success)'
                          : status === 'active'
                            ? stage.color
                            : 'var(--color-border-subtle)',
                    }}
                  >
                    {status === 'done' ? '✓' : status === 'active' ? '●' : '○'}
                  </span>
                </div>
              )
            })}
          </div>

          {/* Severity bars — visible from Attacking stage onward */}
          {(currentStageIdx >= 2 || showReport) && (
            <div>
              <div className="font-label text-[0.5rem] text-text-dim tracking-[0.15em] mb-3">
                FINDINGS SEVERITY
              </div>
              {SCAN_SEVERITY_DATA.map((item, i) => (
                <SeverityBar
                  key={item.label}
                  item={item}
                  animate={currentStageIdx >= 3 || showReport}
                  delay={i * 200}
                />
              ))}
            </div>
          )}

          {/* System telemetry */}
          <div>
            <div className="font-label text-[0.5rem] text-text-dim tracking-[0.15em] mb-3">
              SYSTEM TELEMETRY
            </div>
            {[
              ['CONTAINERS', currentStageIdx >= 1 ? '2 ACTIVE' : '0 ACTIVE', currentStageIdx >= 1 ? 'var(--color-success)' : 'var(--color-text-dim)'],
              ['NETWORK', currentStageIdx >= 0 ? 'rs-net-a3f9' : '—', 'var(--color-text-muted)'],
              ['ENDPOINTS', currentStageIdx >= 2 ? '247 FOUND' : currentStageIdx >= 1 ? 'SCANNING...' : '—', currentStageIdx >= 2 ? '#FFB800' : 'var(--color-text-dim)'],
              ['FINDINGS', currentStageIdx >= 3 ? '28 TOTAL' : currentStageIdx >= 2 ? 'ANALYZING...' : '—', currentStageIdx >= 3 ? '#FF3B3B' : 'var(--color-text-dim)'],
              ['REPORT', showReport ? 'READY' : 'PENDING', showReport ? 'var(--color-success)' : 'var(--color-text-dim)'],
            ].map(([key, val, color]) => (
              <div key={key} className="flex justify-between py-1.5 border-b border-border-subtle/30">
                <span className="font-label text-[0.5rem] text-text-dim tracking-[0.1em]">{key}</span>
                <span className="font-mono text-[0.55rem] font-bold tracking-[0.08em]" style={{ color }}>{val}</span>
              </div>
            ))}
          </div>

          {/* Tool status — visible from Attacking stage */}
          {currentStageIdx >= 2 && (
            <div>
              <div className="font-label text-[0.5rem] text-text-dim tracking-[0.15em] mb-3">
                TOOLS DEPLOYED
              </div>
              {[
                ['nmap', currentStageIdx >= 3, '#FFB800'],
                ['ffuf', currentStageIdx >= 3, '#A78BFA'],
                ['nuclei', currentStageIdx >= 3, '#00E5FF'],
                ['sqlmap', currentStageIdx >= 3, '#FF3B3B'],
              ].map(([tool, done, color]) => (
                <div key={tool as string} className="flex items-center gap-2 py-1.5 border-b border-border-subtle/30">
                  <div
                    className="w-1.5 h-1.5 rounded-full"
                    style={{
                      background: done || currentStageIdx === 2 ? color as string : 'var(--color-border-subtle)',
                      animation: currentStageIdx === 2 && !done ? 'dot-blink 1s infinite' : 'none',
                      boxShadow: done ? `0 0 6px ${color}` : 'none',
                    }}
                  />
                  <span
                    className="font-mono text-[0.62rem] font-bold tracking-[0.05em]"
                    style={{ color: done || currentStageIdx === 2 ? (color as string) : 'var(--color-text-dim)' }}
                  >
                    {tool as string}
                  </span>
                  <span className="ml-auto font-label text-[0.45rem]" style={{ color: done ? 'var(--color-success)' : 'var(--color-text-dim)' }}>
                    {done ? 'COMPLETE' : currentStageIdx === 2 ? 'RUNNING' : 'QUEUED'}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
