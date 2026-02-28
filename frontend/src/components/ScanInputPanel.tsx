import { useState, useEffect, useRef } from 'react'
import { useInView } from '../hooks/useInView'
import { MOCK_TERMINAL_LINES } from '../data/mockData'

interface ScanInputPanelProps {
  onScan?: (url: string) => void
  isLoading?: boolean
}

export default function ScanInputPanel({ onScan, isLoading }: ScanInputPanelProps) {
  const { ref, isInView } = useInView({ threshold: 0.2 })
  const [url, setUrl] = useState('')
  const [validationStep, setValidationStep] = useState(0)
  const [terminalLines, setTerminalLines] = useState<string[]>([])
  const terminalRef = useRef<HTMLDivElement>(null)
  const lineIndexRef = useRef(0)

  // Auto-scroll terminal
  useEffect(() => {
    if (!isInView) return
    const interval = setInterval(() => {
      if (lineIndexRef.current < MOCK_TERMINAL_LINES.length) {
        setTerminalLines(prev => [...prev, MOCK_TERMINAL_LINES[lineIndexRef.current]])
        lineIndexRef.current++
      } else {
        // Reset and loop
        lineIndexRef.current = 0
        setTerminalLines([])
      }
    }, 120)
    return () => clearInterval(interval)
  }, [isInView])

  // Auto-scroll terminal div
  useEffect(() => {
    if (terminalRef.current) {
      terminalRef.current.scrollTop = terminalRef.current.scrollHeight
    }
  }, [terminalLines])

  // Validation hints on typing
  useEffect(() => {
    if (url.length === 0) return
    const t1 = setTimeout(() => setValidationStep(1), 400)
    const t2 = setTimeout(() => {
      if (url.includes('github.com')) setValidationStep(2)
    }, 1000)
    const t3 = setTimeout(() => {
      if (url.includes('github.com/')) setValidationStep(3)
    }, 1800)
    return () => {
      clearTimeout(t1)
      clearTimeout(t2)
      clearTimeout(t3)
    }
  }, [url])

  const handleUrlChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const newUrl = e.target.value
    if (newUrl.length === 0) setValidationStep(0)
    setUrl(newUrl)
  }

  const handleScan = () => {
    if (url.includes('github.com/') && onScan && !isLoading) {
      onScan(url)
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') handleScan()
  }

  return (
    <section
      id="scan-input"
      ref={ref}
      className={`relative py-24 px-6 md:px-12 section-reveal ${isInView ? 'in-view' : ''}`}
    >
      {/* Accent line separator */}
      <div className="absolute top-0 left-1/2 -translate-x-1/2 w-24 h-px bg-accent opacity-30" />

      <div className="max-w-[1200px] mx-auto">
        {/* Section label */}
        <div className="font-label text-[0.6rem] text-accent uppercase tracking-[0.3em] mb-2">
          [ TARGET ACQUISITION ]
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          {/* Left: Input */}
          <div className="flex flex-col gap-4">
            {/* Input bar */}
            <div className="flex gap-0 w-full">
              <div className="flex items-center px-4 bg-bg-card border border-border-subtle border-r-0 font-mono text-accent text-sm shrink-0">
                $&nbsp;target&nbsp;——
              </div>
              <input
                type="text"
                className="terminal-input flex-1"
                placeholder="https://github.com/your-org/your-repo"
                value={url}
                onChange={handleUrlChange}
                onKeyDown={handleKeyDown}
                style={{ borderLeft: 'none' }}
              />
              <button
                className="redshell-btn-sm shrink-0 border-l-0"
                style={{ animation: 'none' }}
                onClick={handleScan}
              >
                {isLoading ? '⏳ STARTING...' : '▶ RUN REDSHELL'}
              </button>
            </div>

            {/* Validation hints */}
            <div className="flex flex-col gap-1.5 min-h-[60px] ml-1">
              <ValidationHint
                visible={validationStep >= 1}
                type="check"
                text="Analyzing URL format..."
                complete={validationStep >= 2}
                completeText="✓ Valid GitHub URL"
              />
              <ValidationHint
                visible={validationStep >= 2}
                type="check"
                text="Checking repository..."
                complete={validationStep >= 3}
                completeText="✓ Public repository detected"
              />
              <ValidationHint
                visible={validationStep >= 3}
                type="loading"
                text="⏳ Provisioning environment..."
                complete={false}
                completeText=""
              />
            </div>
          </div>

          {/* Right: Live Terminal Preview */}
          <div className="relative bg-bg-card border border-border-subtle overflow-hidden">
            {/* Terminal header bar */}
            <div className="flex items-center gap-2 px-4 py-2 border-b border-border-subtle bg-bg-surface">
              <div className="flex gap-1.5">
                <div className="w-2.5 h-2.5 rounded-full bg-redshell opacity-60" />
                <div className="w-2.5 h-2.5 rounded-full bg-warning opacity-40" />
                <div className="w-2.5 h-2.5 rounded-full bg-success opacity-40" />
              </div>
              <span className="font-label text-[0.6rem] text-text-dim tracking-wider ml-2">
                redshell — live scan output
              </span>
            </div>

            {/* Terminal content */}
            <div
              ref={terminalRef}
              className="p-4 h-[280px] overflow-y-auto font-mono text-[0.72rem] leading-relaxed"
              style={{ scrollBehavior: 'smooth' }}
            >
              {terminalLines.map((line, i) => (
                <div key={i} className={getLineClass(line ?? '')}>
                  {line ?? ''}
                </div>
              ))}
              {/* Blinking cursor */}
              <span
                className="inline-block w-2 h-4 bg-accent ml-0.5 align-middle"
                style={{ animation: 'cursor-blink 1s step-end infinite' }}
              />
            </div>
          </div>
        </div>
      </div>
    </section>
  )
}

function ValidationHint({
  visible,
  type,
  text,
  complete,
  completeText,
}: {
  visible: boolean
  type: 'check' | 'loading'
  text: string
  complete: boolean
  completeText: string
}) {
  if (!visible) return null
  return (
    <div
      className={`font-mono text-[0.7rem] transition-all duration-300 ${
        complete ? 'text-success' : type === 'loading' ? 'text-warning' : 'text-text-muted'
      }`}
      style={{ animation: 'fade-slide-left 0.3s ease both' }}
    >
      {complete ? completeText : text}
    </div>
  )
}

function getLineClass(line: string): string {
  if (!line) return 'text-text-muted'
  if (line.startsWith('[critical]')) return 'text-redshell font-bold'
  if (line.startsWith('[high]')) return 'text-redshell opacity-80'
  if (line.startsWith('[medium]')) return 'text-warning'
  if (line.startsWith('[low]')) return 'text-text-muted'
  if (line.startsWith('[info]')) return 'text-text-dim'
  if (line.startsWith('[+]')) return 'text-success'
  if (line.startsWith('[*]')) return 'text-text-muted'
  if (line.startsWith('[★]')) return 'text-accent font-bold mt-2'
  if (line.startsWith('────')) return 'text-border-subtle mt-1'
  if (line.startsWith('$')) return 'text-accent'
  if (line.startsWith('Starting') || line.startsWith('PORT')) return 'text-text-dim'
  return 'text-text-muted'
}
