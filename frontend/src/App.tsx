import { useState } from 'react'
import './App.css'
import HeroSection from './components/HeroSection'
import ScanInputPanel from './components/ScanInputPanel'
import ThreatLandscapeSection from './components/ThreatLandscapeSection'
import PipelineSection from './components/PipelineSection'
import ArsenalSection from './components/ArsenalSection'
import ReportPreviewSection from './components/ReportPreviewSection'
import StatusTimeline from './components/StatusTimeline'
import FooterCTA from './components/FooterCTA'
import ScanVisualizer from './components/ScanVisualizer'
import { useScan } from './hooks/useScan'

function App() {
  const [targetUrl, setTargetUrl] = useState<string | null>(null)
  const scan = useScan()

  const handleScan = async (url: string) => {
    setTargetUrl(url)
    await scan.startScan(url)
  }

  const handleBack = () => {
    scan.reset()
    setTargetUrl(null)
  }

  // If scanning (or scan just completed), show full-page visualizer
  if (targetUrl && (scan.engagementId || scan.isLoading)) {
    return (
      <>
        <div className="hex-grid-bg" />
        <div className="noise-overlay" />
        <div className="scanline-overlay" />
        <ScanVisualizer
          targetUrl={targetUrl}
          engagementId={scan.engagementId}
          status={scan.status}
          history={scan.history}
          report={scan.report}
          error={scan.error}
          isLoading={scan.isLoading}
          onBack={handleBack}
        />
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
        <ScanInputPanel onScan={handleScan} isLoading={scan.isLoading} />
        <ThreatLandscapeSection />
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
