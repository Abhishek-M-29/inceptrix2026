import { useState } from 'react'
import './App.css'
import HeroSection from './components/HeroSection'
import ScanInputPanel from './components/ScanInputPanel'
import PipelineSection from './components/PipelineSection'
import ArsenalSection from './components/ArsenalSection'
import ReportPreviewSection from './components/ReportPreviewSection'
import StatusTimeline from './components/StatusTimeline'
import FooterCTA from './components/FooterCTA'
import ScanVisualizer from './components/ScanVisualizer'

function App() {
  const [scanUrl, setScanUrl] = useState<string | null>(null)

  const handleScan = (url: string) => {
    setScanUrl(url)
  }

  const handleBack = () => {
    setScanUrl(null)
  }

  // If scanning, show full-page visualizer
  if (scanUrl) {
    return (
      <>
        <div className="hex-grid-bg" />
        <div className="noise-overlay" />
        <div className="scanline-overlay" />
        <ScanVisualizer targetUrl={scanUrl} onBack={handleBack} />
      </>
    )
  }

  return (
    <div className="relative min-h-screen bg-bg-deep">
      {/* Background layers */}
      <div className="hex-grid-bg" />
      <div className="noise-overlay" />
      <div className="scanline-overlay" />

      {/* Page content */}
      <main className="relative z-10">
        <HeroSection />
        <ScanInputPanel onScan={handleScan} />
        <PipelineSection />
        <ArsenalSection />
        <ReportPreviewSection />
        <StatusTimeline />
        <FooterCTA onScan={handleScan} />
      </main>
    </div>
  )
}

export default App
