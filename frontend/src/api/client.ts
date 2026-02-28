/* ─── API Client ─── */
/* Plain fetch()-based client. All routes go through /api → Vite proxy → backend */

import type {
  ScanResponse,
  StatusResponse,
  QueueResponse,
  Report,
} from './types'

const BASE = '/api'

class ApiError extends Error {
  status: number
  statusText: string
  body?: string
  constructor(status: number, statusText: string, body?: string) {
    super(`API ${status}: ${statusText}`)
    this.name = 'ApiError'
    this.status = status
    this.statusText = statusText
    this.body = body
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { 'Content-Type': 'application/json', ...init?.headers },
    ...init,
  })
  if (!res.ok) {
    const body = await res.text().catch(() => '')
    throw new ApiError(res.status, res.statusText, body)
  }
  return res.json() as Promise<T>
}

/** POST /scan — kick off a new engagement */
export function startScan(targetUrl: string): Promise<ScanResponse> {
  return request<ScanResponse>('/scan', {
    method: 'POST',
    body: JSON.stringify({ target_url: targetUrl }),
  })
}

/** GET /status/{engagement_id} — poll current state + optional history */
export function getStatus(
  engagementId: string,
  includeHistory = true,
): Promise<StatusResponse> {
  const qs = includeHistory ? '?include_history=true' : ''
  return request<StatusResponse>(`/status/${engagementId}${qs}`)
}

/** GET /queue — paginated webhook event log */
export function getQueue(page = 1, pageSize = 50): Promise<QueueResponse> {
  return request<QueueResponse>(`/queue?page=${page}&page_size=${pageSize}`)
}

/** GET /report/{engagement_id} — final report */
export function getReport(engagementId: string): Promise<Report> {
  return request<Report>(`/report/${engagementId}`)
}

export { ApiError }
