import { useCountUp } from '../hooks/useCountUp'
import { MOCK_STATS } from '../data/mockData'
import SplineGlobe from './SplineGlobe'

const SCENE_URL = 'https://prod.spline.design/LNKg2528lXG3YehA/scene.splinecode'

function StatCounter({ label, target, delay }: { label: string; target: number; delay: number }) {
  const value = useCountUp(target, 2400, true)
  return (
    <div
      className="text-center"
      style={{ animation: `fade-slide-up 0.6s ${delay}s both` }}
    >
      <span className="font-display text-2xl text-accent tabular-nums tracking-wide">
        {value.toLocaleString()}
      </span>
      <span className="block font-label text-[0.65rem] text-text-muted uppercase tracking-[0.2em] mt-1">
        {label}
      </span>
    </div>
  )
}

export default function HeroSection() {
  return (
    <section className="relative min-h-screen flex items-center overflow-hidden">
      {/* Globe — lowest interactive layer */}
      <div className="absolute inset-0 z-10 hidden lg:block">
        <div className="absolute top-1/2 -translate-y-[52%] -right-[5%] w-[72vw] max-w-[1000px] aspect-square">
          <SplineGlobe sceneUrl={SCENE_URL} />
        </div>
      </div>

      {/* Gradient vignette — visual only */}
      <div
        className="absolute inset-0 pointer-events-none z-20"
        style={{
          background:
            'radial-gradient(ellipse at 65% 50%, transparent 25%, var(--color-bg-deep) 75%)',
        }}
      />

      {/* Text content — pointer-events-none wrapper so globe stays clickable */}
      <div className="relative z-30 w-full max-w-[1400px] mx-auto px-8 md:px-16 pointer-events-none">
        <div className="flex flex-col gap-8 py-24 lg:py-0 max-w-[650px] pointer-events-auto">
          {/* Classification stamp */}
          <div
            className="font-label text-[0.7rem] text-accent uppercase tracking-[0.35em]"
            style={{ animation: 'hero-text-reveal 0.8s 0.1s both' }}
          >
            [ REDSHELL // THREAT SIMULATION ENGINE ]
          </div>

          {/* Main headline */}
          <h1
            className="font-display text-[4.5rem] sm:text-[6rem] lg:text-[8rem] leading-[0.88] text-text-primary m-0"
            style={{ textShadow: '0 2px 40px rgba(0,0,0,0.6)' }}
          >
            <span className="block" style={{ animation: 'hero-text-reveal 0.7s 0.2s both' }}>
              Your App.
            </span>
            <span className="block" style={{ animation: 'hero-text-reveal 0.7s 0.4s both' }}>
              Attacked.
            </span>
            <span
              className="block text-accent"
              style={{
                animation: 'hero-text-reveal 0.7s 0.6s both, pulse-glow-text 3s 1.3s ease-in-out infinite',
                textShadow: '0 0 30px rgba(0,229,255,0.3)',
              }}
            >
              Reported.
            </span>
          </h1>

          {/* Sub-headline */}
          <p
            className="font-mono text-[0.9rem] text-text-muted max-w-[520px] leading-relaxed"
            style={{ animation: 'hero-text-reveal 0.8s 0.8s both' }}
          >
            Paste a GitHub URL. We clone it, build it, attack it, and hand you a
            penetration testing report — fully automated.
          </p>

          {/* CTA */}
          <div style={{ animation: 'hero-text-reveal 0.8s 1s both' }}>
            <a href="#scan-input">
              <button className="redshell-btn">
                INITIATE SCAN →
              </button>
            </a>
            <p className="font-label text-[0.6rem] text-text-dim mt-3 tracking-wider">
              No account required. Public GitHub repos only. Results in minutes.
            </p>
          </div>

          {/* Live counters */}
          <div
            className="flex gap-10 mt-6 pt-6 border-t border-border-subtle"
            style={{ animation: 'hero-text-reveal 0.8s 1.2s both' }}
          >
            <StatCounter label="Scans Run" target={MOCK_STATS.scansRun} delay={1.4} />
            <StatCounter label="Vulns Found" target={MOCK_STATS.vulnsFound} delay={1.6} />
            <StatCounter label="Repos Tested" target={MOCK_STATS.reposTested} delay={1.8} />
          </div>
        </div>
      </div>

      {/* Scroll indicator */}
      <div
        className="absolute bottom-8 left-1/2 -translate-x-1/2 z-20 flex flex-col items-center gap-2"
        style={{ animation: 'fade-slide-up 0.8s 2s both' }}
      >
        <span className="font-label text-[0.6rem] text-text-dim tracking-[0.2em] uppercase">Scroll</span>
        <div className="w-px h-8 bg-border-subtle relative overflow-hidden">
          <div
            className="w-full h-3 bg-accent absolute"
            style={{ animation: 'scanline 2s linear infinite' }}
          />
        </div>
      </div>
    </section>
  )
}
