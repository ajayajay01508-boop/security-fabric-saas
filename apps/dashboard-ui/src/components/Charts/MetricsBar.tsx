import { Cpu, Zap, Database, Wifi } from 'lucide-react'
import clsx from 'clsx'

interface Metrics {
  threats_per_minute: number
  events_processed: number
  kafka_lag: number
  inference_latency_ms: number
  active_connections: number
  timestamp: number
}

interface Props { metrics: Metrics; connected: boolean }

function Bar({ value, max, color }: { value: number; max: number; color: string }) {
  const pct = Math.min(100, (value / max) * 100)
  return (
    <div className="h-1 bg-fabric-muted rounded-full overflow-hidden">
      <div
        className="h-full rounded-full transition-all duration-500"
        style={{ width: `${pct}%`, background: color }}
      />
    </div>
  )
}

export function MetricsBar({ metrics, connected }: Props) {
  const lagStatus = metrics.kafka_lag > 5000 ? 'critical' : metrics.kafka_lag > 1000 ? 'warn' : 'ok'
  const latStatus = metrics.inference_latency_ms > 300 ? 'critical' : metrics.inference_latency_ms > 100 ? 'warn' : 'ok'

  const statusColor = (s: string) =>
    s === 'critical' ? '#ff3b30' : s === 'warn' ? '#ff9500' : '#30d158'

  return (
    <div className="bg-fabric-surface border border-fabric-border rounded-lg px-4 py-3">
      <div className="flex items-center justify-between mb-3">
        <p className="text-xs font-mono text-fabric-dim uppercase tracking-widest">Pipeline Health</p>
        <div className={clsx(
          'text-[10px] font-mono flex items-center gap-1',
          connected ? 'text-fabric-low' : 'text-fabric-dim'
        )}>
          <span className={clsx('w-1.5 h-1.5 rounded-full', connected ? 'bg-fabric-low animate-pulse' : 'bg-fabric-dim')} />
          {connected ? 'LIVE' : 'OFFLINE'}
        </div>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div>
          <div className="flex items-center gap-1.5 mb-1">
            <Zap className="w-3 h-3 text-fabric-accent" />
            <span className="text-[10px] font-mono text-fabric-dim uppercase tracking-widest">Threats/min</span>
          </div>
          <p className="text-lg font-display font-bold text-white mb-1">{metrics.threats_per_minute}</p>
          <Bar value={metrics.threats_per_minute} max={100} color="#00e5ff" />
        </div>

        <div>
          <div className="flex items-center gap-1.5 mb-1">
            <Cpu className="w-3 h-3 text-fabric-accent" />
            <span className="text-[10px] font-mono text-fabric-dim uppercase tracking-widest">Inference</span>
          </div>
          <p className="text-lg font-display font-bold text-white mb-1">
            {metrics.inference_latency_ms}
            <span className="text-xs text-fabric-dim font-mono ml-0.5">ms</span>
          </p>
          <Bar value={metrics.inference_latency_ms} max={500} color={statusColor(latStatus)} />
        </div>

        <div>
          <div className="flex items-center gap-1.5 mb-1">
            <Database className="w-3 h-3 text-fabric-accent" />
            <span className="text-[10px] font-mono text-fabric-dim uppercase tracking-widest">Kafka Lag</span>
          </div>
          <p className="text-lg font-display font-bold text-white mb-1">{metrics.kafka_lag}</p>
          <Bar value={metrics.kafka_lag} max={10000} color={statusColor(lagStatus)} />
        </div>

        <div>
          <div className="flex items-center gap-1.5 mb-1">
            <Wifi className="w-3 h-3 text-fabric-accent" />
            <span className="text-[10px] font-mono text-fabric-dim uppercase tracking-widest">Connections</span>
          </div>
          <p className="text-lg font-display font-bold text-white mb-1">{metrics.active_connections}</p>
          <Bar value={metrics.active_connections} max={200} color="#30d158" />
        </div>
      </div>
    </div>
  )
}
