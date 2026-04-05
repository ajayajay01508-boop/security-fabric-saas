import { useState } from 'react'
import { CheckCircle, Eye, XCircle } from 'lucide-react'
import { alertsApi } from '../../lib/api'
import { useToast } from '../Toast'
import { formatDistanceToNow } from 'date-fns'
import clsx from 'clsx'

const SEV_BADGE: Record<string, string> = {
  critical: 'text-fabric-critical bg-fabric-critical/10 border-fabric-critical/30',
  high:     'text-fabric-high     bg-fabric-high/10     border-fabric-high/30',
  medium:   'text-fabric-medium   bg-fabric-medium/10   border-fabric-medium/30',
  low:      'text-fabric-low      bg-fabric-low/10      border-fabric-low/30',
  info:     'text-fabric-dim      bg-fabric-muted       border-fabric-border',
}

const STATUS_BADGE: Record<string, string> = {
  open:           'text-fabric-accent  bg-fabric-accent/10  border-fabric-accent/30',
  acknowledged:   'text-fabric-medium  bg-fabric-medium/10  border-fabric-medium/30',
  resolved:       'text-fabric-low     bg-fabric-low/10     border-fabric-low/30',
  false_positive: 'text-fabric-dim     bg-fabric-muted      border-fabric-border',
}

interface Alert {
  id: number
  threat_id: string
  severity: string
  status: string
  classification: string
  source_ip?: string
  destination_ip?: string
  confidence_score?: number
  description?: string
  created_at: string
}

interface Props {
  alerts: Alert[]
  onUpdate: () => void
}

export function AlertsTable({ alerts, onUpdate }: Props) {
  const [loading, setLoading] = useState<number | null>(null)
  const [expanded, setExpanded] = useState<number | null>(null)
  const { success, error } = useToast()

  const ack = async (id: number) => {
    setLoading(id)
    try {
      await alertsApi.acknowledge(id)
      success('Alert acknowledged', 'The alert has been marked as acknowledged.')
      onUpdate()
    } catch {
      error('Failed to acknowledge', 'Please try again.')
    } finally {
      setLoading(null)
    }
  }

  const resolve = async (id: number) => {
    setLoading(id)
    try {
      await alertsApi.resolve(id)
      success('Alert resolved', 'The alert has been marked as resolved.')
      onUpdate()
    } catch {
      error('Failed to resolve', 'Please try again.')
    } finally {
      setLoading(null)
    }
  }

  const exportCsv = async () => {
    try {
      const res = await alertsApi.export()
      const url  = URL.createObjectURL(new Blob([res.data], { type: 'text/csv' }))
      const link = document.createElement('a')
      link.href = url
      link.download = `alerts-${new Date().toISOString().slice(0,10)}.csv`
      link.click()
      URL.revokeObjectURL(url)
      success('Export ready', 'CSV downloaded successfully.')
    } catch {
      error('Export failed', 'Please try again.')
    }
  }

  return (
    <div className="bg-fabric-surface border border-fabric-border rounded-lg overflow-hidden">
      {/* Export button */}
      {alerts.length > 0 && (
        <div className="flex justify-end px-3 py-2 border-b border-fabric-border/50">
          <button onClick={exportCsv}
            className="text-xs font-mono text-fabric-dim hover:text-fabric-accent transition-colors">
            ↓ Export CSV
          </button>
        </div>
      )}

      <table className="w-full text-xs">
        <thead>
          <tr className="border-b border-fabric-border">
            {['Severity','Classification','Source → Dest','Confidence','Status','Time',''].map((h) => (
              <th key={h} className="px-3 py-2.5 text-left font-mono text-fabric-dim uppercase tracking-widest text-[10px]">
                {h}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {alerts.map((a) => (
            <>
              <tr key={a.id}
                className={clsx(
                  'border-b border-fabric-border/50 hover:bg-fabric-muted/30 transition-colors cursor-pointer',
                  expanded === a.id && 'bg-fabric-muted/20'
                )}
                onClick={() => setExpanded(expanded === a.id ? null : a.id)}
              >
                <td className="px-3 py-2.5">
                  <span className={clsx('px-1.5 py-0.5 rounded border font-mono uppercase text-[10px]', SEV_BADGE[a.severity])}>
                    {a.severity}
                  </span>
                </td>
                <td className="px-3 py-2.5 font-body text-fabric-text max-w-[160px] truncate">{a.classification}</td>
                <td className="px-3 py-2.5 font-mono text-fabric-dim">
                  {a.source_ip ?? '—'} → {a.destination_ip ?? '—'}
                </td>
                <td className="px-3 py-2.5 font-mono text-fabric-text">
                  {a.confidence_score != null ? `${(a.confidence_score * 100).toFixed(0)}%` : '—'}
                </td>
                <td className="px-3 py-2.5">
                  <span className={clsx('px-1.5 py-0.5 rounded border font-mono uppercase text-[10px]', STATUS_BADGE[a.status])}>
                    {a.status.replace('_',' ')}
                  </span>
                </td>
                <td className="px-3 py-2.5 font-mono text-fabric-dim whitespace-nowrap">
                  {formatDistanceToNow(new Date(a.created_at), { addSuffix: true })}
                </td>
                <td className="px-3 py-2.5">
                  <div className="flex items-center gap-1">
                    <button title="Toggle detail"
                      onClick={(e) => { e.stopPropagation(); setExpanded(expanded === a.id ? null : a.id) }}
                      className="p-1 text-fabric-dim hover:text-fabric-accent rounded transition-colors">
                      <Eye className="w-3.5 h-3.5" />
                    </button>
                    {a.status === 'open' && (
                      <>
                        <button title="Acknowledge" disabled={loading === a.id}
                          onClick={(e) => { e.stopPropagation(); ack(a.id) }}
                          className="p-1 text-fabric-dim hover:text-fabric-medium rounded transition-colors disabled:opacity-50">
                          <CheckCircle className="w-3.5 h-3.5" />
                        </button>
                        <button title="Resolve" disabled={loading === a.id}
                          onClick={(e) => { e.stopPropagation(); resolve(a.id) }}
                          className="p-1 text-fabric-dim hover:text-fabric-low rounded transition-colors disabled:opacity-50">
                          <XCircle className="w-3.5 h-3.5" />
                        </button>
                      </>
                    )}
                  </div>
                </td>
              </tr>
              {expanded === a.id && (
                <tr key={`${a.id}-detail`} className="bg-fabric-muted/10">
                  <td colSpan={7} className="px-4 py-3">
                    <p className="text-xs font-mono text-fabric-dim mb-1 uppercase tracking-widest">Description</p>
                    <p className="text-xs text-fabric-text font-body">{a.description || 'No description available.'}</p>
                    <p className="text-[10px] font-mono text-fabric-dim/60 mt-2">ID: {a.threat_id}</p>
                  </td>
                </tr>
              )}
            </>
          ))}
          {alerts.length === 0 && (
            <tr>
              <td colSpan={7} className="px-3 py-8 text-center text-xs text-fabric-dim font-mono">
                No alerts found
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  )
}
