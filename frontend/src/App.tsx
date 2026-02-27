import './App.css'
import HeroSection from './components/HeroSection'
import ScanInputPanel from './components/ScanInputPanel'
import PipelineSection from './components/PipelineSection'
import FooterCTA from './components/FooterCTA'

function App() {
  return (
    <div className="relative min-h-screen bg-bg-deep">
      {/* Background layers */}
      <div className="hex-grid-bg" />
      <div className="noise-overlay" />
      <div className="scanline-overlay" />

      {/* Page content */}
      <main className="relative z-10">
        <HeroSection />
        <ScanInputPanel />
        <PipelineSection />
        <FooterCTA />
      </main>
    </div>
  )
}

export default App
