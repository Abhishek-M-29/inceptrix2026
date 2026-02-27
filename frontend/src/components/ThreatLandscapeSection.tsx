import { useState, useEffect, useRef, useCallback } from 'react'
import { useInView } from '../hooks/useInView'

/* ═══════════════════════════════════════════════════
   THREAT LANDSCAPE SECTION — 3 Data Graphs
   Growth → Risk → Consequence → Solution
   ═══════════════════════════════════════════════════ */

/* ─── Shared tooltip ─── */
function Tooltip({
  x,
  y,
  label,
  value,
  visible,
  color = 'var(--color-accent)',
}: {
  x: number
  y: number
  label: string
  value: string
  visible: boolean
  color?: string
}) {
  if (!visible) return null
  return (
    <g style={{ pointerEvents: 'none' }}>
      <rect
        x={x - 60}
        y={y - 52}
        width={120}
        height={40}
        rx={2}
        fill="var(--color-bg-card)"
        stroke={color}
        strokeWidth={1}
        opacity={0.95}
      />
      <text
        x={x}
        y={y - 36}
        textAnchor="middle"
        fill="var(--color-text-muted)"
        fontSize={9}
        fontFamily="var(--font-label)"
      >
        {label}
      </text>
      <text
        x={x}
        y={y - 22}
        textAnchor="middle"
        fill={color}
        fontSize={12}
        fontFamily="var(--font-mono)"
        fontWeight={700}
      >
        {value}
      </text>
    </g>
  )
}



/* ═══════════════════════════════════════════════════
   GRAPH 1 — .ai Domain Registration Growth
   ═══════════════════════════════════════════════════ */
function DomainGrowthChart({ isInView }: { isInView: boolean }) {
  const [hoveredPoint, setHoveredPoint] = useState<number | null>(null)
  const [pathLength, setPathLength] = useState(0)
  const pathRef = useRef<SVGPathElement>(null)

  const W = 500
  const H = 280
  const PAD = { top: 30, right: 40, bottom: 50, left: 70 }
  const plotW = W - PAD.left - PAD.right
  const plotH = H - PAD.top - PAD.bottom

  const data = [
    { year: '2022', value: 148000, label: '148,000' },
    { year: '2024', value: 598000, label: '598,000' },
    { year: '2025 Q3', value: 864500, label: '864,500' },
  ]

  const maxVal = 1000000
  const xPos = data.map((_, i) => PAD.left + (i / (data.length - 1)) * plotW)
  const yPos = data.map((d) => PAD.top + plotH - (d.value / maxVal) * plotH)

  const pathD = `M ${xPos[0]} ${yPos[0]} C ${xPos[0] + 60} ${yPos[0]}, ${xPos[1] - 40} ${yPos[1] + 20}, ${xPos[1]} ${yPos[1]} C ${xPos[1] + 40} ${yPos[1] - 20}, ${xPos[2] - 60} ${yPos[2]}, ${xPos[2]} ${yPos[2]}`
  const areaD = `${pathD} L ${xPos[2]} ${PAD.top + plotH} L ${xPos[0]} ${PAD.top + plotH} Z`

  useEffect(() => {
    if (pathRef.current) {
      setPathLength(pathRef.current.getTotalLength())
    }
  }, [])

  return (
    <div className="graph-panel group">
      {/* Header */}
      <div className="graph-header">
        <div className="graph-phase-label">[ SECTION 01: EXPLOSION ]</div>
        <h3 className="graph-title">
          .ai Domain Registrations:
          <span className="text-accent"> 10× Growth</span> in 3 Years
        </h3>
        <p className="graph-subtitle">
          The AI application boom has triggered unprecedented web deployment velocity.
        </p>
      </div>

      {/* SVG Chart */}
      <div className="graph-svg-wrap">
        <svg viewBox={`0 0 ${W} ${H}`} className="graph-svg">
          {/* Grid lines */}
          {[0, 250000, 500000, 750000, 1000000].map((tick) => {
            const y = PAD.top + plotH - (tick / maxVal) * plotH
            return (
              <g key={tick}>
                <line
                  x1={PAD.left}
                  y1={y}
                  x2={W - PAD.right}
                  y2={y}
                  stroke="var(--color-border-subtle)"
                  strokeWidth={0.5}
                  strokeDasharray={tick === 0 ? 'none' : '3 3'}
                />
                <text
                  x={PAD.left - 8}
                  y={y + 3}
                  textAnchor="end"
                  fill="var(--color-text-dim)"
                  fontSize={8}
                  fontFamily="var(--font-mono)"
                >
                  {tick === 0 ? '0' : `${tick / 1000}K`}
                </text>
              </g>
            )
          })}

          {/* X-axis labels */}
          {data.map((d, i) => (
            <text
              key={d.year}
              x={xPos[i]}
              y={H - 10}
              textAnchor="middle"
              fill="var(--color-text-muted)"
              fontSize={10}
              fontFamily="var(--font-label)"
            >
              {d.year}
            </text>
          ))}

          {/* Area fill */}
          <path
            d={areaD}
            fill="url(#domainGradient)"
            opacity={isInView ? 0.15 : 0}
            style={{ transition: 'opacity 1.5s ease 0.6s' }}
          />

          {/* Line */}
          <path
            ref={pathRef}
            d={pathD}
            fill="none"
            stroke="var(--color-accent)"
            strokeWidth={2.5}
            strokeLinecap="round"
            style={{
              strokeDasharray: pathLength || 800,
              strokeDashoffset: isInView ? 0 : pathLength || 800,
              transition: 'stroke-dashoffset 2s cubic-bezier(0.16, 1, 0.3, 1) 0.3s',
              filter: 'drop-shadow(0 0 6px rgba(0, 229, 255, 0.5))',
            }}
          />

          {/* Glow line duplicate */}
          <path
            d={pathD}
            fill="none"
            stroke="var(--color-accent-glow)"
            strokeWidth={1}
            strokeLinecap="round"
            opacity={0.4}
            style={{
              strokeDasharray: pathLength || 800,
              strokeDashoffset: isInView ? 0 : pathLength || 800,
              transition: 'stroke-dashoffset 2s cubic-bezier(0.16, 1, 0.3, 1) 0.3s',
              filter: 'drop-shadow(0 0 12px rgba(0, 229, 255, 0.3))',
            }}
          />

          {/* Data points */}
          {data.map((_d, i) => (
            <g key={i}>
              {/* Pulse ring on hover */}
              <circle
                cx={xPos[i]}
                cy={yPos[i]}
                r={hoveredPoint === i ? 16 : 0}
                fill="none"
                stroke="var(--color-accent)"
                strokeWidth={1}
                opacity={hoveredPoint === i ? 0.3 : 0}
                style={{ transition: 'all 0.3s ease' }}
              />
              {/* Outer ring */}
              <circle
                cx={xPos[i]}
                cy={yPos[i]}
                r={6}
                fill="var(--color-bg-deep)"
                stroke="var(--color-accent)"
                strokeWidth={1.5}
                style={{
                  opacity: isInView ? 1 : 0,
                  transition: `opacity 0.4s ease ${0.8 + i * 0.3}s`,
                  filter:
                    hoveredPoint === i
                      ? 'drop-shadow(0 0 8px rgba(0, 229, 255, 0.8))'
                      : 'none',
                }}
              />
              {/* Inner dot */}
              <circle
                cx={xPos[i]}
                cy={yPos[i]}
                r={3}
                fill="var(--color-accent)"
                style={{
                  opacity: isInView ? 1 : 0,
                  transition: `opacity 0.4s ease ${0.8 + i * 0.3}s`,
                }}
              />
              {/* Hover hitbox */}
              <circle
                cx={xPos[i]}
                cy={yPos[i]}
                r={20}
                fill="transparent"
                style={{ cursor: 'crosshair' }}
                onMouseEnter={() => setHoveredPoint(i)}
                onMouseLeave={() => setHoveredPoint(null)}
              />
            </g>
          ))}

          {/* Tooltips */}
          {data.map((d, i) => (
            <Tooltip
              key={`tip-${i}`}
              x={xPos[i]}
              y={yPos[i]}
              label={d.year}
              value={d.label}
              visible={hoveredPoint === i}
            />
          ))}

          {/* Gradient definition */}
          <defs>
            <linearGradient id="domainGradient" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="var(--color-accent)" stopOpacity={0.4} />
              <stop offset="100%" stopColor="var(--color-accent)" stopOpacity={0} />
            </linearGradient>
          </defs>
        </svg>
      </div>

      {/* Highlight annotation */}
      <div className="graph-annotation">
        <div className="graph-annotation-marker" />
        <span>Over <strong className="text-accent">20,000</strong> new .ai domains registered every month (~700 per day)</span>
      </div>

      {/* Caption */}
      <p className="graph-caption">
        Since the launch of generative AI tools, .ai domain registrations have surged
        nearly 10× in three years. This growth reflects a massive acceleration in
        AI-driven web application deployment, often without proportional security
        validation.
      </p>
    </div>
  )
}

/* ═══════════════════════════════════════════════════
   GRAPH 2 — eCrime Breakout Time
   ═══════════════════════════════════════════════════ */
function BreakoutTimeChart({ isInView }: { isInView: boolean }) {
  const [hoveredPoint, setHoveredPoint] = useState<number | null>(null)
  const [pathLength, setPathLength] = useState(0)
  const pathRef = useRef<SVGPathElement>(null)

  const W = 500
  const H = 280
  const PAD = { top: 30, right: 40, bottom: 50, left: 70 }
  const plotW = W - PAD.left - PAD.right
  const plotH = H - PAD.top - PAD.bottom

  // Representing time in seconds for logarithmic-ish visual drama
  // 2024 baseline ~84 min = 5040s; 2025 avg = 29 min = 1740s; 2026 fastest = 27s
  const data = [
    { year: '2024', value: 5040, display: '~84 min', label: 'Baseline' },
    { year: '2025', value: 1740, display: '29 min', label: '65% faster' },
    { year: '2026', value: 27, display: '27 sec', label: 'Fastest recorded' },
  ]

  const maxVal = 5400
  const xPos = data.map((_, i) => PAD.left + (i / (data.length - 1)) * plotW)
  const yPos = data.map((d) => PAD.top + (1 - d.value / maxVal) * plotH)

  const pathD = `M ${xPos[0]} ${yPos[0]} C ${xPos[0] + 60} ${yPos[0] + 30}, ${xPos[1] - 30} ${yPos[1]}, ${xPos[1]} ${yPos[1]} C ${xPos[1] + 50} ${yPos[1] + 20}, ${xPos[2] - 40} ${yPos[2]}, ${xPos[2]} ${yPos[2]}`

  useEffect(() => {
    if (pathRef.current) {
      setPathLength(pathRef.current.getTotalLength())
    }
  }, [])

  return (
    <div className="graph-panel group">
      {/* Header */}
      <div className="graph-header">
        <div className="graph-phase-label text-redshell">[ SECTION 02: ACCELERATION ]</div>
        <h3 className="graph-title">
          eCrime Breakout Time Has Collapsed to
          <span className="text-redshell"> Seconds</span>
        </h3>
        <p className="graph-subtitle">
          The window between initial compromise and lateral movement is shrinking.
        </p>
      </div>

      {/* SVG Chart */}
      <div className="graph-svg-wrap">
        <svg viewBox={`0 0 ${W} ${H}`} className="graph-svg">
          {/* Grid lines */}
          {[0, 1350, 2700, 4050, 5400].map((tick, idx) => {
            const y = PAD.top + (1 - tick / maxVal) * plotH
            const timeLabels = ['0s', '~22 min', '~45 min', '~67 min', '~90 min']
            return (
              <g key={tick}>
                <line
                  x1={PAD.left}
                  y1={y}
                  x2={W - PAD.right}
                  y2={y}
                  stroke="var(--color-border-subtle)"
                  strokeWidth={0.5}
                  strokeDasharray={tick === 0 ? 'none' : '3 3'}
                />
                <text
                  x={PAD.left - 8}
                  y={y + 3}
                  textAnchor="end"
                  fill="var(--color-text-dim)"
                  fontSize={8}
                  fontFamily="var(--font-mono)"
                >
                  {timeLabels[idx]}
                </text>
              </g>
            )
          })}

          {/* X-axis labels */}
          {data.map((d, i) => (
            <text
              key={d.year}
              x={xPos[i]}
              y={H - 10}
              textAnchor="middle"
              fill="var(--color-text-muted)"
              fontSize={10}
              fontFamily="var(--font-label)"
            >
              {d.year}
            </text>
          ))}

          {/* Danger zone — bottom area fill */}
          <rect
            x={PAD.left}
            y={yPos[2] - 4}
            width={plotW}
            height={PAD.top + plotH - yPos[2] + 4}
            fill="url(#dangerGradient)"
            opacity={isInView ? 0.12 : 0}
            style={{ transition: 'opacity 1.5s ease 1s' }}
          />
          <line
            x1={PAD.left}
            y1={yPos[2]}
            x2={W - PAD.right}
            y2={yPos[2]}
            stroke="var(--color-redshell)"
            strokeWidth={0.5}
            strokeDasharray="4 4"
            opacity={isInView ? 0.5 : 0}
            style={{ transition: 'opacity 1s ease 1.2s' }}
          />
          {/* "DANGER ZONE" label */}
          <text
            x={W - PAD.right - 4}
            y={yPos[2] + 14}
            textAnchor="end"
            fill="var(--color-redshell)"
            fontSize={7}
            fontFamily="var(--font-label)"
            letterSpacing="0.15em"
            opacity={isInView ? 0.6 : 0}
            style={{ transition: 'opacity 1s ease 1.4s' }}
          >
            DANGER ZONE
          </text>

          {/* Line */}
          <path
            ref={pathRef}
            d={pathD}
            fill="none"
            stroke="var(--color-redshell)"
            strokeWidth={2.5}
            strokeLinecap="round"
            style={{
              strokeDasharray: pathLength || 800,
              strokeDashoffset: isInView ? 0 : pathLength || 800,
              transition: 'stroke-dashoffset 2s cubic-bezier(0.16, 1, 0.3, 1) 0.3s',
              filter: 'drop-shadow(0 0 6px rgba(255, 59, 59, 0.5))',
            }}
          />

          {/* Glow duplicate */}
          <path
            d={pathD}
            fill="none"
            stroke="#FF6B6B"
            strokeWidth={1}
            strokeLinecap="round"
            opacity={0.3}
            style={{
              strokeDasharray: pathLength || 800,
              strokeDashoffset: isInView ? 0 : pathLength || 800,
              transition: 'stroke-dashoffset 2s cubic-bezier(0.16, 1, 0.3, 1) 0.3s',
              filter: 'drop-shadow(0 0 12px rgba(255, 59, 59, 0.3))',
            }}
          />

          {/* Data points */}
          {data.map((_d, i) => (
            <g key={i}>
              <circle
                cx={xPos[i]}
                cy={yPos[i]}
                r={hoveredPoint === i ? 16 : 0}
                fill="none"
                stroke="var(--color-redshell)"
                strokeWidth={1}
                opacity={hoveredPoint === i ? 0.3 : 0}
                style={{ transition: 'all 0.3s ease' }}
              />
              <circle
                cx={xPos[i]}
                cy={yPos[i]}
                r={6}
                fill="var(--color-bg-deep)"
                stroke="var(--color-redshell)"
                strokeWidth={1.5}
                style={{
                  opacity: isInView ? 1 : 0,
                  transition: `opacity 0.4s ease ${0.8 + i * 0.3}s`,
                  filter:
                    hoveredPoint === i
                      ? 'drop-shadow(0 0 8px rgba(255, 59, 59, 0.8))'
                      : 'none',
                }}
              />
              <circle
                cx={xPos[i]}
                cy={yPos[i]}
                r={3}
                fill="var(--color-redshell)"
                style={{
                  opacity: isInView ? 1 : 0,
                  transition: `opacity 0.4s ease ${0.8 + i * 0.3}s`,
                }}
              />
              <circle
                cx={xPos[i]}
                cy={yPos[i]}
                r={20}
                fill="transparent"
                style={{ cursor: 'crosshair' }}
                onMouseEnter={() => setHoveredPoint(i)}
                onMouseLeave={() => setHoveredPoint(null)}
              />
            </g>
          ))}

          {/* Tooltips */}
          {data.map((d, i) => (
            <Tooltip
              key={`tip-${i}`}
              x={xPos[i]}
              y={yPos[i]}
              label={d.label}
              value={d.display}
              visible={hoveredPoint === i}
              color="var(--color-redshell)"
            />
          ))}

          {/* Danger gradient */}
          <defs>
            <linearGradient id="dangerGradient" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#FF3B3B" stopOpacity={0.3} />
              <stop offset="100%" stopColor="#FF3B3B" stopOpacity={0} />
            </linearGradient>
          </defs>
        </svg>
      </div>

      {/* Annotation */}
      <div className="graph-annotation graph-annotation--red">
        <div className="graph-annotation-marker graph-annotation-marker--red" />
        <span>AI-enabled adversary attacks increased by <strong className="text-redshell">89%</strong></span>
      </div>

      {/* Caption */}
      <p className="graph-caption">
        Threat actors now weaponize vulnerabilities at machine speed. The fastest
        recorded breakout time in 2026 was just 27 seconds, leaving virtually no
        margin for delayed security validation.
      </p>
    </div>
  )
}

/* ═══════════════════════════════════════════════════
   GRAPH 3 — Vulnerability Density Bar Chart
   ═══════════════════════════════════════════════════ */
function VulnerabilityChart({ isInView }: { isInView: boolean }) {
  const [hoveredBar, setHoveredBar] = useState<number | null>(null)

  const W = 500
  const H = 280
  const PAD = { top: 30, right: 40, bottom: 50, left: 70 }
  const plotH = H - PAD.top - PAD.bottom

  const data = [
    { year: '2025', value: 290, label: '~290', color: 'var(--color-warning)' },
    { year: '2026', value: 581, label: '581', color: 'var(--color-redshell)' },
  ]

  const maxVal = 700
  const barWidth = 80
  const gap = 60
  const totalBarsWidth = data.length * barWidth + (data.length - 1) * gap
  const startX = PAD.left + (W - PAD.left - PAD.right - totalBarsWidth) / 2

  return (
    <div className="graph-panel group">
      {/* Header */}
      <div className="graph-header">
        <div className="graph-phase-label text-warning">[ SECTION 03: FRAGILITY ]</div>
        <h3 className="graph-title">
          Average Application Contains
          <span className="text-redshell"> 581 Vulnerabilities</span>
        </h3>
        <p className="graph-subtitle">
          AI-assisted development is increasing vulnerability density.
        </p>
      </div>

      {/* SVG Chart */}
      <div className="graph-svg-wrap">
        <svg viewBox={`0 0 ${W} ${H}`} className="graph-svg">
          {/* Grid lines */}
          {[0, 175, 350, 525, 700].map((tick) => {
            const y = PAD.top + plotH - (tick / maxVal) * plotH
            return (
              <g key={tick}>
                <line
                  x1={PAD.left}
                  y1={y}
                  x2={W - PAD.right}
                  y2={y}
                  stroke="var(--color-border-subtle)"
                  strokeWidth={0.5}
                  strokeDasharray={tick === 0 ? 'none' : '3 3'}
                />
                <text
                  x={PAD.left - 8}
                  y={y + 3}
                  textAnchor="end"
                  fill="var(--color-text-dim)"
                  fontSize={8}
                  fontFamily="var(--font-mono)"
                >
                  {tick}
                </text>
              </g>
            )
          })}

          {/* Bars */}
          {data.map((d, i) => {
            const x = startX + i * (barWidth + gap)
            const barH = (d.value / maxVal) * plotH
            const y = PAD.top + plotH - barH
            const isHovered = hoveredBar === i

            return (
              <g key={d.year}>
                {/* Bar glow background */}
                <rect
                  x={x - 2}
                  y={y - 2}
                  width={barWidth + 4}
                  height={barH + 4}
                  rx={2}
                  fill={d.color}
                  opacity={isHovered ? 0.15 : 0}
                  style={{ transition: 'opacity 0.3s ease' }}
                />
                {/* Bar body */}
                <rect
                  x={x}
                  y={PAD.top + plotH}
                  width={barWidth}
                  height={0}
                  rx={2}
                  fill={`url(#barGrad${i})`}
                  stroke={d.color}
                  strokeWidth={isHovered ? 1.5 : 0.5}
                  style={{
                    transform: isInView ? `translateY(-${barH}px)` : 'translateY(0)',
                    height: isInView ? barH : 0,
                    transition: `all 1s cubic-bezier(0.16, 1, 0.3, 1) ${0.5 + i * 0.3}s`,
                    filter: isHovered
                      ? `drop-shadow(0 0 12px ${i === 1 ? 'rgba(255,59,59,0.4)' : 'rgba(255,184,0,0.4)'})`
                      : 'none',
                    cursor: 'crosshair',
                  }}
                  onMouseEnter={() => setHoveredBar(i)}
                  onMouseLeave={() => setHoveredBar(null)}
                />

                {/* Value on top */}
                <text
                  x={x + barWidth / 2}
                  y={y - 10}
                  textAnchor="middle"
                  fill={d.color}
                  fontSize={16}
                  fontFamily="var(--font-display)"
                  fontWeight={700}
                  style={{
                    opacity: isInView ? 1 : 0,
                    transition: `opacity 0.5s ease ${1 + i * 0.3}s`,
                  }}
                >
                  {d.label}
                </text>

                {/* Year label */}
                <text
                  x={x + barWidth / 2}
                  y={H - 10}
                  textAnchor="middle"
                  fill="var(--color-text-muted)"
                  fontSize={11}
                  fontFamily="var(--font-label)"
                >
                  {d.year}
                </text>

                {/* Gradient defs */}
                <defs>
                  <linearGradient id={`barGrad${i}`} x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor={i === 0 ? '#FFB800' : '#FF3B3B'} stopOpacity={0.9} />
                    <stop offset="100%" stopColor={i === 0 ? '#FFB800' : '#FF3B3B'} stopOpacity={0.3} />
                  </linearGradient>
                </defs>
              </g>
            )
          })}

          {/* 100% increase connector */}
          {isInView && (
            <g
              style={{
                opacity: isInView ? 1 : 0,
                transition: 'opacity 0.5s ease 1.6s',
              }}
            >
              <line
                x1={startX + barWidth + 12}
                y1={PAD.top + plotH - (290 / maxVal) * plotH}
                x2={startX + barWidth + gap - 12}
                y2={PAD.top + plotH - (290 / maxVal) * plotH}
                stroke="var(--color-text-dim)"
                strokeWidth={0.5}
                strokeDasharray="3 3"
              />
              <line
                x1={startX + barWidth + gap / 2}
                y1={PAD.top + plotH - (290 / maxVal) * plotH}
                x2={startX + barWidth + gap / 2}
                y2={PAD.top + plotH - (581 / maxVal) * plotH + 12}
                stroke="var(--color-text-dim)"
                strokeWidth={0.5}
                strokeDasharray="3 3"
              />
              {/* Arrow tip */}
              <polygon
                points={`${startX + barWidth + gap / 2 - 3},${PAD.top + plotH - (581 / maxVal) * plotH + 16} ${startX + barWidth + gap / 2 + 3},${PAD.top + plotH - (581 / maxVal) * plotH + 16} ${startX + barWidth + gap / 2},${PAD.top + plotH - (581 / maxVal) * plotH + 10}`}
                fill="var(--color-redshell)"
                opacity={0.7}
              />
              {/* Label */}
              <text
                x={startX + barWidth + gap / 2}
                y={PAD.top + plotH - (430 / maxVal) * plotH}
                textAnchor="middle"
                fill="var(--color-redshell)"
                fontSize={10}
                fontFamily="var(--font-display)"
                letterSpacing="0.05em"
              >
                +100%
              </text>
            </g>
          )}
        </svg>
      </div>

      {/* Context stats */}
      <div className="vuln-stats-row">
        <VulnStat value="19%" label="high-risk" icon="shield" />
        <VulnStat value="84%" label="companies affected" icon="building" />
        <VulnStat value="60%" label="breaches from unpatched" icon="bug" />
      </div>

      {/* Annotation */}
      <div className="graph-annotation graph-annotation--red">
        <div className="graph-annotation-marker graph-annotation-marker--red" />
        <span>100% year-over-year increase in vulnerability density</span>
      </div>

      {/* Caption */}
      <p className="graph-caption">
        The average application in 2026 contains 581 vulnerabilities — a 100%
        increase year-over-year — largely driven by AI-generated code and
        unchecked open-source dependencies.
      </p>
    </div>
  )
}

/* ─── Vulnerability stat pill ─── */
function VulnStat({
  value,
  label,
  icon,
}: {
  value: string
  label: string
  icon: string
}) {
  return (
    <div className="vuln-stat">
      <VulnIcon type={icon} />
      <span className="vuln-stat-value">{value}</span>
      <span className="vuln-stat-label">{label}</span>
    </div>
  )
}

function VulnIcon({ type }: { type: string }) {
  const cls = 'shrink-0'
  switch (type) {
    case 'shield':
      return (
        <svg className={cls} width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.2">
          <path d="M8 1L2 4v4c0 3.3 2.6 6.4 6 7 3.4-.6 6-3.7 6-7V4L8 1z" />
          <path d="M6 8l1.5 1.5L10 6" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
      )
    case 'building':
      return (
        <svg className={cls} width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.2">
          <rect x="3" y="2" width="10" height="13" rx="1" />
          <line x1="6" y1="5" x2="6" y2="5.5" />
          <line x1="8" y1="5" x2="8" y2="5.5" />
          <line x1="10" y1="5" x2="10" y2="5.5" />
          <line x1="6" y1="8" x2="6" y2="8.5" />
          <line x1="8" y1="8" x2="8" y2="8.5" />
          <line x1="10" y1="8" x2="10" y2="8.5" />
          <rect x="6.5" y="11" width="3" height="4" />
        </svg>
      )
    case 'bug':
      return (
        <svg className={cls} width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.2">
          <ellipse cx="8" cy="10" rx="4" ry="4.5" />
          <circle cx="8" cy="5" r="2" />
          <path d="M2 8H4M12 8h2M3 12l1.5-1M13 12l-1.5-1M3 5l2 1.5M13 5l-2 1.5" />
        </svg>
      )
    default:
      return null
  }
}

/* ═══════════════════════════════════════════════════
   GLITCH TEXT EFFECT
   ═══════════════════════════════════════════════════ */
function GlitchText({ text, className = '' }: { text: string; className?: string }) {
  return (
    <span className={`glitch-text ${className}`} data-text={text}>
      {text}
    </span>
  )
}

/* ═══════════════════════════════════════════════════
   PARTICLE CANVAS — ambient floating particles
   ═══════════════════════════════════════════════════ */
function ParticleField() {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const animRef = useRef<number>(0)

  const initParticles = useCallback(() => {
    const canvas = canvasRef.current
    if (!canvas) return
    const ctx = canvas.getContext('2d')
    if (!ctx) return

    const resize = () => {
      canvas.width = canvas.offsetWidth * 2
      canvas.height = canvas.offsetHeight * 2
      ctx.scale(2, 2)
    }
    resize()
    window.addEventListener('resize', resize)

    const particles: { x: number; y: number; vx: number; vy: number; r: number; o: number }[] = []
    const count = 40
    const w = canvas.offsetWidth
    const h = canvas.offsetHeight

    for (let i = 0; i < count; i++) {
      particles.push({
        x: Math.random() * w,
        y: Math.random() * h,
        vx: (Math.random() - 0.5) * 0.3,
        vy: (Math.random() - 0.5) * 0.2,
        r: Math.random() * 1.5 + 0.5,
        o: Math.random() * 0.4 + 0.1,
      })
    }

    const draw = () => {
      ctx.clearRect(0, 0, w, h)
      for (const p of particles) {
        p.x += p.vx
        p.y += p.vy
        if (p.x < 0) p.x = w
        if (p.x > w) p.x = 0
        if (p.y < 0) p.y = h
        if (p.y > h) p.y = 0
        ctx.beginPath()
        ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2)
        ctx.fillStyle = `rgba(0, 229, 255, ${p.o})`
        ctx.fill()
      }
      animRef.current = requestAnimationFrame(draw)
    }

    draw()

    return () => {
      cancelAnimationFrame(animRef.current)
      window.removeEventListener('resize', resize)
    }
  }, [])

  useEffect(() => {
    const cleanup = initParticles()
    return cleanup
  }, [initParticles])

  return (
    <canvas
      ref={canvasRef}
      className="absolute inset-0 w-full h-full pointer-events-none"
      style={{ opacity: 0.4 }}
    />
  )
}

/* ═══════════════════════════════════════════════════
   MAIN SECTION EXPORT
   ═══════════════════════════════════════════════════ */
export default function ThreatLandscapeSection() {
  const { ref: sectionRef, isInView: sectionInView } = useInView({ threshold: 0.05 })
  const { ref: g1Ref, isInView: g1InView } = useInView({ threshold: 0.2 })
  const { ref: g2Ref, isInView: g2InView } = useInView({ threshold: 0.2 })
  const { ref: g3Ref, isInView: g3InView } = useInView({ threshold: 0.2 })
  const { ref: ctaRef, isInView: ctaInView } = useInView({ threshold: 0.3 })

  return (
    <section
      ref={sectionRef}
      className={`relative py-28 px-6 md:px-12 overflow-hidden section-reveal ${sectionInView ? 'in-view' : ''}`}
    >
      {/* Ambient particles */}
      <ParticleField />

      {/* Background radial */}
      <div
        className="absolute inset-0 pointer-events-none"
        style={{
          background:
            'radial-gradient(ellipse at 50% 30%, rgba(0,229,255,0.03) 0%, transparent 60%)',
        }}
      />

      <div className="relative z-10 max-w-[1200px] mx-auto">
        {/* Section header */}
        <div className="text-center mb-20">
          <div className="font-label text-[0.6rem] text-accent uppercase tracking-[0.3em] mb-3">
            [ THREAT LANDSCAPE ]
          </div>
          <h2 className="font-display text-[3rem] sm:text-[4rem] lg:text-[5rem] text-text-primary leading-[0.9] m-0">
            THE WEB IS <GlitchText text="UNDER SIEGE" className="text-accent" />
          </h2>
          <p className="font-mono text-[0.8rem] text-text-muted mt-4 max-w-[600px] mx-auto leading-relaxed">
            Three data points. One inescapable conclusion.
            <br />
            <span className="text-text-dim">Growth → Risk → Consequence → Your Solution</span>
          </p>
        </div>

        {/* Graph 1 — Explosion */}
        <div ref={g1Ref} className="mb-24">
          <DomainGrowthChart isInView={g1InView} />
        </div>

        {/* Divider */}
        <div className="graph-divider">
          <div className="graph-divider-line" />
          <span className="graph-divider-text">ESCALATING</span>
          <div className="graph-divider-line" />
        </div>

        {/* Graph 2 — Acceleration */}
        <div ref={g2Ref} className="mb-24">
          <BreakoutTimeChart isInView={g2InView} />
        </div>

        {/* Divider */}
        <div className="graph-divider">
          <div className="graph-divider-line graph-divider-line--red" />
          <span className="graph-divider-text graph-divider-text--red">COMPOUNDING</span>
          <div className="graph-divider-line graph-divider-line--red" />
        </div>

        {/* Graph 3 — Fragility */}
        <div ref={g3Ref} className="mb-24">
          <VulnerabilityChart isInView={g3InView} />
        </div>

        {/* Closing CTA */}
        <div
          ref={ctaRef}
          className="text-center pt-16 pb-8"
          style={{
            opacity: ctaInView ? 1 : 0,
            transform: ctaInView ? 'translateY(0)' : 'translateY(30px)',
            transition: 'all 1s cubic-bezier(0.16, 1, 0.3, 1)',
          }}
        >
          <div className="inline-block border border-accent/20 px-10 py-8 bg-bg-card/60 backdrop-blur-sm relative">
            {/* Corner decorations */}
            <div className="absolute top-0 left-0 w-4 h-4 border-t border-l border-accent/50" />
            <div className="absolute top-0 right-0 w-4 h-4 border-t border-r border-accent/50" />
            <div className="absolute bottom-0 left-0 w-4 h-4 border-b border-l border-accent/50" />
            <div className="absolute bottom-0 right-0 w-4 h-4 border-b border-r border-accent/50" />

            <p className="font-display text-[2rem] sm:text-[3rem] text-text-primary leading-none m-0">
              Validation must be{' '}
              <span className="text-accent relative">
                deterministic
                <span
                  className="absolute -bottom-1 left-0 h-px bg-accent"
                  style={{
                    width: ctaInView ? '100%' : '0%',
                    transition: 'width 1s ease 0.5s',
                  }}
                />
              </span>
              .
            </p>
            <p className="font-mono text-[0.7rem] text-text-dim mt-3 tracking-wider uppercase">
              Not optional. Not delayed. Not manual.
            </p>
          </div>
        </div>
      </div>
    </section>
  )
}
