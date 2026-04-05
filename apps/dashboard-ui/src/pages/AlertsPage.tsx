import { useEffect, useState, useCallback } from 'react'
import { AlertsTable } from '../components/Tables/AlertsTable'
import { alertsApi } from '../lib/api'
import { Search, RefreshCw, Filter } from 'lucide-react'
import clsx from 'clsx'

const SEVERITIES = ['', 'critical', 'high', 'medium', 'low', 'info']
const STATUSES   = ['', 'open', 'acknowledged', 'resolved', 'false_positive']

export function AlertsPage() {
  const [alerts, setAlerts] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [stats, setStats] = useState<any>(null)
  const [severity, setSeverity] = useState('')
  const [status, setStatus] = useState('')
  const [offset, setOffset] = useState(0)
  const LIMIT = 25

  const fetch = useCallback(async () => {
    setLoading(true)
    try {
      const [alertRes, statsRes] = await Promise.all([
        alertsApi.list({ severity: severity || undefined, status: status || undefined, limit: LIMIT, offset }),
        alertsApi.stats(),
      ])
      setAlerts(alertRes.data)
      setStats(statsRes.data)
    } catch {}
    finally { setLoading(false) }
  }, [severity, status, offset])

  useEffect(() => { fetch() }, [fetch])

  const SEV_PILL = (s: string, label: string, count?: number) => (
    <button
      key={s}
      onClick={() => { setSeverity(s); setOffset(0) }}
      className={clsx(
        'px-3 py-1.5 rounded-full text-xs font-mono border transition-all duration-150 whitespace-nowrap',
        severity === s
          ? 'bg-fabric-accent/20 border-fabric-accent/50 text-fabric-accent'
          : 'bg-transparent border-fabric-border text-fabric-dim hover:border-fabric-text/30 hover:text-fabric-text'
      )}
    >
      {label}{count != null ? ` (${count})` : ''}
    </button>
  )

  return (
    <div className="p-6 space-y-5 animate-fade-in">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="font-display text-2xl font-bold text-white">Alerts</h1>
          <p className="text-sm text-fabric-dim font-mono mt-0.5">
            {stats ? `${stats.total} total · ${stats.open} open` : 'Loading...'}
          </p>
        </div>
        <button onClick={fetch} disabled={loading}
          className="flex items-center gap-2 text-xs font-mono text-fabric-dim hover:text-fabric-text border border-fabric-border hover:border-fabric-text/30 px-3 py-2 rounded-lg transition-all disabled:opacity-50">
          <RefreshCw className={clsx('w-3.5 h-3.5', loading && 'animate-spin')} />
          Refresh
        </button>
      </div>

      {/* Severity filters */}
      <div className="flex items-center gap-2 flex-wrap">
        <Filter className="w-3.5 h-3.5 text-fabric-dim flex-shrink-0" />
        {SEV_PILL('', 'All', stats?.total)}
        {SEV_PILL('critical', 'Critical', stats?.critical)}
        {SEV_PILL('high', 'High', stats?.high)}
        {SEV_PILL('medium', 'Medium', stats?.medium)}
        {SEV_PILL('low', 'Low', stats?.low)}
        <div className="w-px h-4 bg-fabric-border mx-1" />
        {STATUSES.filter(Boolean).map((s) => (
          <button
            key={s}
            onClick={() => { setStatus(status === s ? '' : s); setOffset(0) }}
            className={clsx(
              'px-3 py-1.5 rounded-full text-xs font-mono border transition-all duration-150',
              status === s
                ? 'bg-fabric-muted border-fabric-text/40 text-fabric-text'
                : 'bg-transparent border-fabric-border text-fabric-dim hover:border-fabric-text/30'
            )}
          >
            {s.replace('_', ' ')}
          </button>
        ))}
      </div>

      {/* Table */}
      <AlertsTable alerts={alerts} onUpdate={fetch} />

      {/* Pagination */}
      <div className="flex items-center justify-between text-xs font-mono text-fabric-dim">
        <span>
          Showing {offset + 1}–{offset + alerts.length}
          {stats?.total != null ? ` of ${stats.total}` : ''}
        </span>
        <div className="flex gap-2">
          <button
            onClick={() => setOffset((o) => Math.max(0, o - LIMIT))}
            disabled={offset === 0 || loading}
            className="px-3 py-1.5 border border-fabric-border rounded hover:border-fabric-text/30 disabled:opacity-30 transition-all"
          >
            ← Prev
          </button>
          <button
            onClick={() => setOffset((o) => o + LIMIT)}
            disabled={alerts.length < LIMIT || loading}
            className="px-3 py-1.5 border border-fabric-border rounded hover:border-fabric-text/30 disabled:opacity-30 transition-all"
          >
            Next →
          </button>
        </div>
      </div>
    </div>
  )
}
