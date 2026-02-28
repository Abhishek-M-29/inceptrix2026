/* ─── useQueue Hook ─── */
/* Polls the webhook event queue for live tool execution logs */

import { useState, useEffect } from 'react'
import { getQueue } from '../api/client'
import type { QueueItem } from '../api/types'

const QUEUE_POLL_INTERVAL = 3000 // 3 seconds

export interface UseQueueReturn {
  items: QueueItem[]
  total: number
  isPolling: boolean
}

export function useQueue(active: boolean): UseQueueReturn {
  const [items, setItems] = useState<QueueItem[]>([])
  const [total, setTotal] = useState(0)
  const [isPolling, setIsPolling] = useState(false)

  useEffect(() => {
    if (!active) {
      setIsPolling(false)
      return
    }

    let cancelled = false
    setIsPolling(true)

    const poll = async () => {
      try {
        const res = await getQueue(1, 100)
        if (cancelled) return
        setItems(res.items)
        setTotal(res.total)
      } catch (e) {
        console.error('Queue poll error:', e)
      }
    }

    poll()
    const id = setInterval(poll, QUEUE_POLL_INTERVAL)

    return () => {
      cancelled = true
      clearInterval(id)
      setIsPolling(false)
    }
  }, [active])

  return { items, total, isPolling }
}
