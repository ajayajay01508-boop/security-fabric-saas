import clsx from 'clsx'
import type { LucideIcon } from 'lucide-react'

interface StatCardProps {
  label: string
  value: string | number
  sub?: string
  icon: LucideIcon
  variant?: 'default' | 'critical' | 'high' | 'accent' | 'low'
  pulse?: boolean
}

const VARIANT_STYLES = {
  default:  { border: 'border-fabric-border', icon: 'text-fabric-dim',     value: 'text-white' },
  critical: { border: 'border-fabric-critical/40', icon: 'text-fabric-critical', value: 'text-fabric-critical' },
  high:     { border: 'border-fabric-high/40',     icon: 'text-fabric-high',     value: 'text-fabric-high' },
  accent:   { border: 'border-fabric-accent/30',   icon: 'text-fabric-accent',   value: 'text-fabric-accent' },
  low:      { border: 'border-fabric-low/40',       icon: 'text-fabric-low',      value: 'text-white' },
}

export function StatCard({ label, value, sub, icon: Icon, variant = 'default', pulse }: StatCardProps) {
  const s = VARIANT_STYLES[variant]
  return (
    <div className={clsx(
      'bg-fabric-surface border rounded-lg p-4 relative overflow-hidden animate-fade-in',
      s.border,
      variant === 'critical' && 'glow-critical',
      variant === 'accent' && 'glow-accent',
    )}>
      <div className="flex items-start justify-between">
        <div>
          <p className="text-xs font-mono text-fabric-dim uppercase tracking-widest mb-2">{label}</p>
          <p className={clsx('text-3xl font-display font-bold', s.value, pulse && 'animate-pulse-slow')}>
            {value}
          </p>
          {sub && <p className="text-xs text-fabric-dim mt-1 font-mono">{sub}</p>}
        </div>
        <Icon className={clsx('w-5 h-5 mt-0.5', s.icon)} />
      </div>
    </div>
  )
}
