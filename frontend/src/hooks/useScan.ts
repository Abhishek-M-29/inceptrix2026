/* ─── useScan Hook ─── */
/* Manages the full scan lifecycle: start → poll status → fetch report */
/* Falls back to mock data when backend is unreachable */

import { useState, useEffect, useRef, useCallback } from 'react'
import { startScan as apiStartScan, getStatus, getReport } from '../api/client'
import type { JobState, StateHistoryEntry, Report } from '../api/types'
import { MOCK_REPORT } from '../data/mockData'

const POLL_INTERVAL = 2000 // 2 seconds

/** Terminal states that stop polling */
const TERMINAL_STATES: JobState[] = ['Completed', 'Failed']

/** Mock scan state sequence (simulates the full pipeline) */
const MOCK_STATE_SEQUENCE: { state: JobState; durationMs: number }[] = [
  { state: 'Queued',            durationMs: 1500 },
  { state: 'Provisioning',      durationMs: 3000 },
  { state: 'Provisioned',       durationMs: 1500 },
  { state: 'Attacking',         durationMs: 5000 },
  { state: 'Normalizing',       durationMs: 2000 },
  { state: 'Generating_Report', durationMs: 2000 },
  { state: 'Completed',         durationMs: 0    },
]

export interface UseScanReturn {
  engagementId: string | null
  status: JobState | null
  history: StateHistoryEntry[]
  report: Report | null
  error: string | null
  isLoading: boolean   // true while POST /scan is in-flight
  isPolling: boolean   // true while polling status
  isMocked: boolean    // true when running on mock data (backend unreachable)
  startScan: (url: string) => Promise<void>
  reset: () => void
}

export function useScan(): UseScanReturn {
  const [engagementId, setEngagementId] = useState<string | null>(null)
  const [status, setStatus] = useState<JobState | null>(null)
  const [history, setHistory] = useState<StateHistoryEntry[]>([])
  const [report, setReport] = useState<Report | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [isPolling, setIsPolling] = useState(false)
  const [isMocked, setIsMocked] = useState(false)

  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null)
  const mockTimeouts = useRef<ReturnType<typeof setTimeout>[]>([])
  const mountedRef = useRef(true)

  // Cleanup on unmount
  useEffect(() => {
    mountedRef.current = true
    return () => {
      mountedRef.current = false
      if (pollRef.current) clearInterval(pollRef.current)
      mockTimeouts.current.forEach(t => clearTimeout(t))
    }
  }, [])

  /** Stop polling */
  const stopPolling = useCallback(() => {
    if (pollRef.current) {
      clearInterval(pollRef.current)
      pollRef.current = null
    }
    setIsPolling(false)
  }, [])

  /** Cancel any mock simulation timers */
  const cancelMockSimulation = useCallback(() => {
    mockTimeouts.current.forEach(t => clearTimeout(t))
    mockTimeouts.current = []
  }, [])

  /** Begin polling status for a given engagement */
  const startPolling = useCallback((eid: string) => {
    stopPolling()
    setIsPolling(true)

    const poll = async () => {
      try {
        const res = await getStatus(eid, true)
        if (!mountedRef.current) return
        setStatus(res.status)
        if (res.history) setHistory(res.history)

        if (TERMINAL_STATES.includes(res.status)) {
          stopPolling()
          if (res.status === 'Completed') {
            try {
              const rpt = await getReport(eid)
              if (mountedRef.current) setReport(rpt)
            } catch (e) {
              console.error('Failed to fetch report:', e)
              // Fallback to mock report if report fetch fails
              if (mountedRef.current) {
                setReport(MOCK_REPORT)
                setIsMocked(true)
              }
            }
          }
          if (res.status === 'Failed') {
            setError('Scan failed on the server.')
          }
        }
      } catch (e) {
        if (!mountedRef.current) return
        console.error('Status poll error:', e)
        // Don't stop polling on transient errors — just log
      }
    }

    // First poll immediately
    poll()
    pollRef.current = setInterval(poll, POLL_INTERVAL)
  }, [stopPolling])

  /** Simulate a full mock scan by stepping through states on timers */
  const startMockSimulation = useCallback((targetUrl: string) => {
    cancelMockSimulation()
    setIsMocked(true)
    setIsPolling(true)

    const mockId = `mock-${Date.now().toString(36)}`
    setEngagementId(mockId)

    const baseTime = new Date()
    let cumulativeMs = 0
    const historyAccumulator: StateHistoryEntry[] = []

    MOCK_STATE_SEQUENCE.forEach(({ state, durationMs }, _idx) => {
      const delay = cumulativeMs
      const entryTimestamp = new Date(baseTime.getTime() + delay).toISOString()

      const tid = setTimeout(() => {
        if (!mountedRef.current) return

        const entry: StateHistoryEntry = { state, timestamp: entryTimestamp }
        historyAccumulator.push(entry)

        setStatus(state)
        setHistory([...historyAccumulator])

        if (state === 'Completed') {
          setIsPolling(false)
          // Deliver mock report with target replaced
          const mockReport: Report = {
            ...MOCK_REPORT,
            target: targetUrl,
            sandbox: {
              ...MOCK_REPORT.sandbox,
              github_url: targetUrl,
            },
          }
          setReport(mockReport)
        }
      }, delay)

      mockTimeouts.current.push(tid)
      cumulativeMs += durationMs
    })
  }, [cancelMockSimulation])

  /** Public: kick off a scan */
  const startScan = useCallback(async (url: string) => {
    // Reset state
    setError(null)
    setReport(null)
    setHistory([])
    setStatus(null)
    setEngagementId(null)
    setIsMocked(false)
    setIsLoading(true)

    try {
      const res = await apiStartScan(url)
      if (!mountedRef.current) return
      setEngagementId(res.engagement_id)
      setStatus(res.status)
      setIsLoading(false)
      startPolling(res.engagement_id)
    } catch (e) {
      if (!mountedRef.current) return
      console.warn('Backend unreachable, falling back to mock simulation:', e)
      setIsLoading(false)
      // Instead of showing an error, start mock simulation
      startMockSimulation(url)
    }
  }, [startPolling, startMockSimulation])

  /** Public: reset everything */
  const reset = useCallback(() => {
    stopPolling()
    cancelMockSimulation()
    setEngagementId(null)
    setStatus(null)
    setHistory([])
    setReport(null)
    setError(null)
    setIsLoading(false)
    setIsMocked(false)
  }, [stopPolling, cancelMockSimulation])

  return {
    engagementId,
    status,
    history,
    report,
    error,
    isLoading,
    isPolling,
    isMocked,
    startScan,
    reset,
  }
}
