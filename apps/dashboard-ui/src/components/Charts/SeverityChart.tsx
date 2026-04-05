import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer, Legend } from 'recharts'

interface Props {
  stats: {
    critical: number
    high: number
    medium: number
    low: number
    info?: number
  } | null
}

const SEGMENTS = [
  { key: 'critical', label: 'Critical', color: '#ff3b30' },
  { key: 'high',     label: 'High',     color: '#ff9500' },
  { key: 'medium',   label: 'Medium',   color: '#ffd60a' },
  { key: 'low',      label: 'Low',      color: '#30d158' },
]

const CustomTooltip = ({ active, payload }: any) => {
  if (!active || !payload?.length) return null
  const { name, value } = payload[0]
  return (
    <div className="bg-fabric-surface border border-fabric-border rounded px-3 py-2 text-xs font-mono">
      <span style={{ color: payload[0].payload.color }}>{name}: </span>
      <span className="text-white">{value}</span>
    </div>
  )
}

const CustomLegend = ({ payload }: any) => (
  <div className="flex flex-wrap gap-x-4 gap-y-1 justify-center mt-2">
    {payload?.map((entry: any) => (
      <div key={entry.value} className="flex items-center gap-1.5 text-[10px] font-mono text-fabric-dim">
        <span className="w-2 h-2 rounded-full inline-block" style={{ background: entry.color }} />
        {entry.value}
      </div>
    ))}
  </div>
)

export function SeverityChart({ stats }: Props) {
  const data = SEGMENTS
    .map((s) => ({ name: s.label, value: stats?.[s.key as keyof typeof stats] ?? 0, color: s.color }))
    .filter((d) => d.value > 0)

  const total = data.reduce((s, d) => s + d.value, 0)

  return (
    <div className="bg-fabric-surface border border-fabric-border rounded-lg p-4">
      <p className="text-xs font-mono text-fabric-dim uppercase tracking-widest mb-3">Severity Distribution</p>
      {total === 0 ? (
        <div className="h-40 flex items-center justify-center text-fabric-dim text-xs font-mono">
          No data yet
        </div>
      ) : (
        <ResponsiveContainer width="100%" height={180}>
          <PieChart>
            <Pie
              data={data}
              cx="50%"
              cy="45%"
              innerRadius={45}
              outerRadius={70}
              paddingAngle={3}
              dataKey="value"
              strokeWidth={0}
            >
              {data.map((entry) => (
                <Cell key={entry.name} fill={entry.color} />
              ))}
            </Pie>
            <Tooltip content={<CustomTooltip />} />
            <Legend content={<CustomLegend />} />
          </PieChart>
        </ResponsiveContainer>
      )}
    </div>
  )
}
