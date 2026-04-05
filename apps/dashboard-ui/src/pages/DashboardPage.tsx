import { useEffect, useState } from 'react'
import { AlertTriangle, Zap, Activity, Cpu, Wifi } from 'lucide-react'
import { StatCard } from '../components/Charts/StatCard'
import { ThreatTimeline } from '../components/Charts/ThreatTimeline'
import { SeverityChart } from '../components/Charts/SeverityChart'
import { MetricsBar } from '../components/Charts/MetricsBar'
import { AlertsTable } from '../components/Tables/AlertsTable'
import { useThreatStream, useMetricsStream } from '../hooks/useWebSocket'
import { alertsApi } from '../lib/api'
import { formatDistanceToNow } from 'date-fns'
import clsx from 'clsx'

const SEV_COLOR: Record<string, string> = {
  critical: 'text-fabric-critical bg-fabric-critical/10 border-fabric-critical/30',
  high:     'text-fabric-high     bg-fabric-high/10     border-fabric-high/30',
  medium:   'text-fabric-medium   bg-fabric-medium/10   border-fabric-medium/30',
  low:      'text-fabric-low      bg-fabric-low/10      border-fabric-low/30',
  info:     'text-fabric-dim      bg-fabric-dim/10      border-fabric-dim/30',
}

export function DashboardPage() {
  const { events, connected } = useThreatStream()
  const { metrics, connected: metricsConnected } = useMetricsStream()
  const [stats, setStats] = useState<any>(null)
  const [alerts, setAlerts] = useState<any[]>([])

  const loadData = () => {
    alertsApi.stats().then((r) => setStats(r.data)).catch(() => {})
    alertsApi.list({ limit: 8 }).then((r) => setAlerts(r.data)).catch(() => {})
  }

  useEffect(() => { loadData() }, [])

  const liveStats = stats ? {
    ...stats,
    total:    stats.total    + events.length,
    critical: stats.critical + events.filter((e) => e.severity === 'critical').length,
    high:     stats.high     + events.filter((e) => e.severity === 'high').length,
    medium:   stats.medium   + events.filter((e) => e.severity === 'medium').length,
    low:      stats.low      + events.filter((e) => e.severity === 'low').length,
    open:     stats.open     + events.length,
  } : null

  return (
    <div className="p-6 space-y-5 animate-fade-in">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="font-display text-2xl font-bold text-white">Threat Dashboard</h1>
          <p className="text-sm text-fabric-dim font-mono mt-0.5">
            {connected ? `↑ Live · ${events.length} events this session` : '○ Connecting...'}
          </p>
        </div>
        <div className={clsx(
          'flex items-center gap-1.5 text-xs font-mono px-3 py-1.5 rounded-full border',
          connected ? 'text-fabric-low border-fabric-low/30 bg-fabric-low/10' : 'text-fabric-dim border-fabric-border'
        )}>
          <Wifi className="w-3 h-3" />
          {connected ? 'STREAM ACTIVE' : 'OFFLINE'}
        </div>
      </div>

      <MetricsBar metrics={metrics} connected={metricsConnected} />

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        <StatCard label="Critical Threats" value={liveStats?.critical ?? '—'} sub="requires immediate action"
          icon={AlertTriangle} variant="critical" pulse={(liveStats?.critical ?? 0) > 0} />
        <StatCard label="High Severity" value={liveStats?.high ?? '—'} sub="elevated risk"
          icon={Zap} variant="high" />
        <StatCard label="Open Alerts" value={liveStats?.open ?? '—'} sub="awaiting review"
          icon={Activity} variant="accent" />
        <StatCard label="Inference Latency" value={`${metrics.inference_latency_ms}ms`}
          sub="ML pipeline p95" icon={Cpu} variant="default" />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <div className="lg:col-span-2"><ThreatTimeline events={events} /></div>
        <SeverityChart stats={liveStats} />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <div className="bg-fabric-surface border border-fabric-border rounded-lg p-4">
          <p className="text-xs font-mono text-fabric-dim uppercase tracking-widest mb-3">Live Threats</p>
          <div className="space-y-2 max-h-64 overflow-y-auto">
            {events.length === 0 ? (
              <p className="text-xs text-fabric-dim font-mono text-center py-8">
                {connected ? 'Monitoring — no threats yet' : 'Connecting...'}
              </p>
            ) : events.slice(0, 25).map((e) => (
              <div key={e.threat_id} className="flex items-start gap-2 animate-slide-up">
                <span className={clsx('text-[10px] font-mono px-1.5 py-0.5 rounded border flex-shrink-0 uppercase', SEV_COLOR[e.severity])}>
                  {e.severity.slice(0, 4)}
                </span>
                <div className="min-w-0">
                  <p className="text-xs text-fabric-text truncate">{e.classification}</p>
                  <p className="text-[10px] text-fabric-dim font-mono">{e.source_ip} → {e.destination_ip}</p>
                  <p className="text-[10px] text-fabric-dim/60 font-mono">
                    {formatDistanceToNow(new Date(e.timestamp * 1000), { addSuffix: true })}
                  </p>
                </div>
              </div>
            ))}
          </div>
        </div>
        <div className="lg:col-span-2">
          <p className="text-xs font-mono text-fabric-dim uppercase tracking-widest mb-3">Recent Alerts</p>
          <AlertsTable alerts={alerts} onUpdate={loadData} />
        </div>
      </div>
    </div>
  )
}
