import { useMemo } from 'react'
import {
  AreaChart, Area, XAxis, YAxis, Tooltip,
  ResponsiveContainer, CartesianGrid
} from 'recharts'
import type { ThreatEvent } from '../../hooks/useWebSocket'
import { format } from 'date-fns'

interface Props { events: ThreatEvent[] }

export function ThreatTimeline({ events }: Props) {
  const data = useMemo(() => {
    const buckets: Record<string, { time: string; critical: number; high: number; medium: number; low: number }> = {}

    events.forEach((e) => {
      const d = new Date(e.timestamp * 1000)
      const key = format(d, 'HH:mm')
      if (!buckets[key]) buckets[key] = { time: key, critical: 0, high: 0, medium: 0, low: 0 }
      if (e.severity in buckets[key]) (buckets[key] as any)[e.severity]++
    })

    return Object.values(buckets).slice(-20)
  }, [events])

  const CustomTooltip = ({ active, payload, label }: any) => {
    if (!active || !payload?.length) return null
    return (
      <div className="bg-fabric-surface border border-fabric-border rounded p-3 text-xs font-mono">
        <p className="text-fabric-dim mb-1">{label}</p>
        {payload.map((p: any) => (
          <p key={p.dataKey} style={{ color: p.color }}>{p.dataKey}: {p.value}</p>
        ))}
      </div>
    )
  }

  return (
    <div className="bg-fabric-surface border border-fabric-border rounded-lg p-4">
      <p className="text-xs font-mono text-fabric-dim uppercase tracking-widest mb-4">Threat Timeline</p>
      {data.length === 0 ? (
        <div className="h-40 flex items-center justify-center text-fabric-dim text-xs font-mono">
          Waiting for events...
        </div>
      ) : (
        <ResponsiveContainer width="100%" height={160}>
          <AreaChart data={data} margin={{ top: 0, right: 0, left: -30, bottom: 0 }}>
            <defs>
              {[
                { id: 'critical', color: '#ff3b30' },
                { id: 'high',     color: '#ff9500' },
                { id: 'medium',   color: '#ffd60a' },
                { id: 'low',      color: '#30d158' },
              ].map(({ id, color }) => (
                <linearGradient key={id} id={`grad-${id}`} x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%"  stopColor={color} stopOpacity={0.3} />
                  <stop offset="95%" stopColor={color} stopOpacity={0} />
                </linearGradient>
              ))}
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="#1c2333" vertical={false} />
            <XAxis dataKey="time" tick={{ fill: '#586069', fontSize: 10, fontFamily: 'JetBrains Mono' }} axisLine={false} tickLine={false} />
            <YAxis tick={{ fill: '#586069', fontSize: 10, fontFamily: 'JetBrains Mono' }} axisLine={false} tickLine={false} />
            <Tooltip content={<CustomTooltip />} />
            <Area type="monotone" dataKey="critical" stroke="#ff3b30" fill="url(#grad-critical)" strokeWidth={1.5} />
            <Area type="monotone" dataKey="high"     stroke="#ff9500" fill="url(#grad-high)"     strokeWidth={1.5} />
            <Area type="monotone" dataKey="medium"   stroke="#ffd60a" fill="url(#grad-medium)"   strokeWidth={1.5} />
            <Area type="monotone" dataKey="low"      stroke="#30d158" fill="url(#grad-low)"      strokeWidth={1.5} />
          </AreaChart>
        </ResponsiveContainer>
      )}
    </div>
  )
}
