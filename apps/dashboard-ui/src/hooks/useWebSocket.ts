import { useEffect, useRef, useState, useCallback } from 'react'

export interface ThreatEvent {
  threat_id: string
  timestamp: number
  severity: 'critical' | 'high' | 'medium' | 'low' | 'info'
  classification: string
  confidence_score: number
  source_ip: string
  destination_ip: string
  source_port: number
  destination_port: number
  protocol: string
  description: string
}

const WS_URL = import.meta.env.VITE_WS_URL || 'ws://localhost:8000'
const MAX_EVENTS = 200

export function useThreatStream() {
  const [events, setEvents] = useState<ThreatEvent[]>([])
  const [connected, setConnected] = useState(false)
  const [reconnecting, setReconnecting] = useState(false)
  const wsRef = useRef<WebSocket | null>(null)
  const retryRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const retryCount = useRef(0)

  const connect = useCallback(() => {
    const token = localStorage.getItem('access_token')
    if (!token) return

    const ws = new WebSocket(`${WS_URL}/ws/threats?token=${token}`)
    wsRef.current = ws

    ws.onopen = () => {
      setConnected(true)
      setReconnecting(false)
      retryCount.current = 0
    }

    ws.onmessage = (evt) => {
      try {
        if (evt.data === 'ping') { ws.send('pong'); return }
        const threat: ThreatEvent = JSON.parse(evt.data)
        setEvents((prev) => [threat, ...prev].slice(0, MAX_EVENTS))
      } catch {}
    }

    ws.onclose = () => {
      setConnected(false)
      if (retryCount.current < 10) {
        const delay = Math.min(1000 * 2 ** retryCount.current, 30000)
        setReconnecting(true)
        retryCount.current++
        retryRef.current = setTimeout(connect, delay)
      }
    }

    ws.onerror = () => ws.close()
  }, [])

  useEffect(() => {
    connect()
    return () => {
      if (retryRef.current) clearTimeout(retryRef.current)
      wsRef.current?.close()
    }
  }, [connect])

  const clear = () => setEvents([])

  return { events, connected, reconnecting, clear }
}

export function useMetricsStream() {
  const [metrics, setMetrics] = useState({
    threats_per_minute: 0,
    events_processed: 0,
    active_connections: 0,
    kafka_lag: 0,
    inference_latency_ms: 0,
    timestamp: Date.now() / 1000,
  })
  const [connected, setConnected] = useState(false)
  const wsRef = useRef<WebSocket | null>(null)

  useEffect(() => {
    const token = localStorage.getItem('access_token')
    if (!token) return

    const ws = new WebSocket(`${WS_URL}/ws/metrics?token=${token}`)
    wsRef.current = ws

    ws.onopen = () => setConnected(true)
    ws.onmessage = (evt) => {
      try { setMetrics(JSON.parse(evt.data)) } catch {}
    }
    ws.onclose = () => setConnected(false)

    return () => ws.close()
  }, [])

  return { metrics, connected }
}
