/* ─── Backend API Types ─── */
/* Mirrors the OpenAPI schema from the Inceptrix Red Team Engine */

export type JobState =
  | 'Queued'
  | 'Provisioning'
  | 'Provisioned'
  | 'Attacking'
  | 'Normalizing'
  | 'Generating_Report'
  | 'Completed'
  | 'Failed'

export interface ScanRequest {
  target_url: string
}

export interface ScanResponse {
  engagement_id: string
  status: JobState
}

export interface StateHistoryEntry {
  state: JobState
  timestamp: string // ISO 8601
}

export interface StatusResponse {
  engagement_id: string
  status: JobState
  history?: StateHistoryEntry[] | null
}

export interface QueueItem {
  tool: string
  target: string
  command_used: string
  status: string // "started" | "ended"
  received_at: string // ISO 8601
}

export interface QueueResponse {
  page: number
  page_size: number
  total: number
  total_pages: number
  items: QueueItem[]
}

/* ─── Report Types (from actual backend response) ─── */

export interface ReportSandbox {
  sandbox_id: string
  sandbox_url: string
  github_url: string
}

export interface ScanSummary {
  open_ports: string[]
  services_detected: string[]
  total_findings: number
}

export interface Finding {
  id: string
  title: string
  severity: 'Critical' | 'High' | 'Medium' | 'Low' | 'Info'
  category: string
  tool: string
  evidence: string
  description: string
  impact: string
  remediation: string
}

export interface ReportMetadata {
  generated_at: string
  agent: string
  total_steps: number
  total_actions: number
  elapsed_seconds: number
}

export interface ReportLog {
  ts: string
  event: string
  tool?: string
  repo?: string
  timeout?: number
  elapsed?: number
  error?: string
  sandbox_id?: string
  url?: string
  target?: string
  session_id?: string
}

export interface Report {
  job_id: string
  status: string
  target: string
  sandbox: ReportSandbox
  scan_summary: ScanSummary
  findings: Finding[]
  metadata: ReportMetadata
  logs: ReportLog[]
}
