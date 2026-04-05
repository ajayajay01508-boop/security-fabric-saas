import { useState, useEffect, useCallback } from 'react'
import { alertsApi } from '../lib/api'

export interface Alert {
  id: number
  threat_id: string
  severity: 'critical' | 'high' | 'medium' | 'low' | 'info'
  status: 'open' | 'acknowledged' | 'resolved' | 'false_positive'
  classification: string
  source_ip?: string
  destination_ip?: string
  source_port?: number
  destination_port?: number
  protocol?: string
  confidence_score?: number
  description?: string
  created_at: string
  acknowledged_at?: string
  resolved_at?: string
}

export interface AlertStats {
  total: number
  critical: number
  high: number
  medium: number
  low: number
  open: number
  acknowledged: number
  resolved: number
}

interface UseAlertsOptions {
  severity?: string
  status?: string
  limit?: number
  autoRefresh?: boolean
  refreshInterval?: number
}

export function useAlerts(options: UseAlertsOptions = {}) {
  const {
    severity,
    status,
    limit = 50,
    autoRefresh = false,
    refreshInterval = 30_000,
  } = options

  const [alerts, setAlerts]   = useState<Alert[]>([])
  const [stats, setStats]     = useState<AlertStats | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError]     = useState<string | null>(null)
  const [offset, setOffset]   = useState(0)

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const [alertRes, statsRes] = await Promise.all([
        alertsApi.list({ severity: severity || undefined, status: status || undefined, limit, offset }),
        alertsApi.stats(),
      ])
      setAlerts(alertRes.data)
      setStats(statsRes.data)
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Failed to load alerts')
    } finally {
      setLoading(false)
    }
  }, [severity, status, limit, offset])

  useEffect(() => {
    load()
  }, [load])

  useEffect(() => {
    if (!autoRefresh) return
    const interval = setInterval(load, refreshInterval)
    return () => clearInterval(interval)
  }, [autoRefresh, refreshInterval, load])

  const acknowledge = async (id: number, note?: string) => {
    await alertsApi.acknowledge(id, note)
    await load()
  }

  const resolve = async (id: number) => {
    await alertsApi.resolve(id)
    await load()
  }

  const nextPage = () => setOffset((o) => o + limit)
  const prevPage = () => setOffset((o) => Math.max(0, o - limit))
  const hasNext  = alerts.length >= limit
  const hasPrev  = offset > 0

  return {
    alerts, stats, loading, error,
    offset, limit, hasNext, hasPrev,
    reload: load, acknowledge, resolve,
    nextPage, prevPage,
  }
}
