import { useState, useRef } from 'react'
import { Play, Square, Zap, Activity, Send } from 'lucide-react'
import { telemetryApi } from '../lib/api'
import { useThreatStream } from '../hooks/useWebSocket'
import { formatDistanceToNow } from 'date-fns'
import clsx from 'clsx'

function randomIp() {
  return Array.from({ length: 4 }, () => Math.floor(Math.random() * 256)).join('.')
}
function randomPort() { return Math.floor(Math.random() * 65535) }
function randomProtocol() { return ['TCP','UDP','ICMP','HTTP','HTTPS','FTP','SSH'][Math.floor(Math.random()*7)] }

function generateEvent() {
  return {
    source_ip:        randomIp(),
    destination_ip:   randomIp(),
    source_port:      randomPort(),
    destination_port: [80,443,22,3389,445,1433,6379,4444][Math.floor(Math.random()*8)],
    protocol:         randomProtocol(),
    bytes_sent:       Math.floor(Math.random() * 10_000_000),
    bytes_received:   Math.floor(Math.random() * 1_000_000),
    packets:          Math.floor(Math.random() * 50000),
    duration_ms:      Math.floor(Math.random() * 5000),
  }
}

const SEV_COLOR: Record<string, string> = {
  critical: 'text-fabric-critical border-l-fabric-critical',
  high:     'text-fabric-high     border-l-fabric-high',
  medium:   'text-fabric-medium   border-l-fabric-medium',
  low:      'text-fabric-low      border-l-fabric-low',
  info:     'text-fabric-dim      border-l-fabric-dim',
}

export function TelemetryPage() {
  const { events, connected, clear } = useThreatStream()
  const [simRunning, setSimRunning] = useState(false)
  const [interval, setIntervalMs] = useState(500)
  const [sent, setSent] = useState(0)
  const [errors, setErrors] = useState(0)
  const [manual, setManual] = useState(JSON.stringify(generateEvent(), null, 2))
  const [manualStatus, setManualStatus] = useState('')
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null)

  const startSim = () => {
    setSimRunning(true)
    timerRef.current = setInterval(async () => {
      try {
        await telemetryApi.ingest(generateEvent())
        setSent((n) => n + 1)
      } catch { setErrors((n) => n + 1) }
    }, interval)
  }

  const stopSim = () => {
    setSimRunning(false)
    if (timerRef.current) clearInterval(timerRef.current)
  }

  const sendManual = async () => {
    setManualStatus('sending...')
    try {
      const parsed = JSON.parse(manual)
      await telemetryApi.ingest(parsed)
      setManualStatus('✓ sent')
      setTimeout(() => setManualStatus(''), 2000)
    } catch (e: any) {
      setManualStatus(`✗ ${e?.response?.data?.detail || e.message || 'error'}`)
    }
  }

  return (
    <div className="p-6 space-y-5 animate-fade-in">
      <div>
        <h1 className="font-display text-2xl font-bold text-white">Telemetry</h1>
        <p className="text-sm text-fabric-dim font-mono mt-0.5">Ingest network events and observe real-time detection</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Simulator */}
        <div className="bg-fabric-surface border border-fabric-border rounded-lg p-5">
          <p className="text-xs font-mono text-fabric-dim uppercase tracking-widest mb-4">Traffic Simulator</p>
          <div className="space-y-4">
            <div>
              <label className="text-xs font-mono text-fabric-dim uppercase tracking-widest block mb-1.5">
                Interval (ms)
              </label>
              <input
                type="range" min={100} max={2000} step={100}
                value={interval}
                onChange={(e) => setIntervalMs(Number(e.target.value))}
                disabled={simRunning}
                className="w-full accent-cyan-400"
              />
              <div className="flex justify-between text-[10px] font-mono text-fabric-dim mt-1">
                <span>100ms</span>
                <span className="text-fabric-accent">{interval}ms</span>
                <span>2000ms</span>
              </div>
            </div>

            <div className="flex gap-2">
              <button
                onClick={simRunning ? stopSim : startSim}
                className={clsx(
                  'flex items-center gap-2 px-4 py-2 rounded-lg text-xs font-mono border transition-all',
                  simRunning
                    ? 'border-fabric-critical/40 text-fabric-critical bg-fabric-critical/10 hover:bg-fabric-critical/20'
                    : 'border-fabric-accent/40 text-fabric-accent bg-fabric-accent/10 hover:bg-fabric-accent/20'
                )}
              >
                {simRunning ? <><Square className="w-3.5 h-3.5" /> STOP</> : <><Play className="w-3.5 h-3.5" /> START</>}
              </button>
              <button onClick={() => { setSent(0); setErrors(0) }}
                className="px-4 py-2 rounded-lg text-xs font-mono border border-fabric-border text-fabric-dim hover:text-fabric-text hover:border-fabric-text/30 transition-all">
                Reset
              </button>
            </div>

            <div className="grid grid-cols-3 gap-3 pt-1">
              {[
                { label: 'Sent', value: sent, color: 'text-fabric-low' },
                { label: 'Errors', value: errors, color: 'text-fabric-critical' },
                { label: 'Detections', value: events.length, color: 'text-fabric-accent' },
              ].map(({ label, value, color }) => (
                <div key={label} className="bg-fabric-bg rounded-lg p-3 text-center">
                  <p className="text-xs font-mono text-fabric-dim uppercase tracking-widest">{label}</p>
                  <p className={clsx('text-2xl font-display font-bold mt-1', color)}>{value}</p>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Manual inject */}
        <div className="bg-fabric-surface border border-fabric-border rounded-lg p-5">
          <p className="text-xs font-mono text-fabric-dim uppercase tracking-widest mb-4">Manual Inject</p>
          <textarea
            value={manual}
            onChange={(e) => setManual(e.target.value)}
            rows={10}
            className="w-full bg-fabric-bg border border-fabric-border rounded-lg px-3 py-2.5 text-xs font-mono text-fabric-text focus:outline-none focus:border-fabric-accent/60 resize-none transition-colors"
          />
          <div className="flex items-center justify-between mt-3">
            <button
              onClick={() => setManual(JSON.stringify(generateEvent(), null, 2))}
              className="text-xs font-mono text-fabric-dim hover:text-fabric-text transition-colors"
            >
              ↻ randomize
            </button>
            <div className="flex items-center gap-3">
              {manualStatus && (
                <span className={clsx('text-xs font-mono', manualStatus.startsWith('✓') ? 'text-fabric-low' : 'text-fabric-critical')}>
                  {manualStatus}
                </span>
              )}
              <button onClick={sendManual}
                className="flex items-center gap-2 px-4 py-2 rounded-lg text-xs font-mono border border-fabric-accent/40 text-fabric-accent bg-fabric-accent/10 hover:bg-fabric-accent/20 transition-all">
                <Send className="w-3.5 h-3.5" /> Send
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Live detections */}
      <div className="bg-fabric-surface border border-fabric-border rounded-lg">
        <div className="flex items-center justify-between px-4 py-3 border-b border-fabric-border">
          <div className="flex items-center gap-2">
            <Activity className="w-4 h-4 text-fabric-accent" />
            <p className="text-xs font-mono text-fabric-dim uppercase tracking-widest">Live Detections</p>
            <span className={clsx(
              'text-[10px] font-mono px-1.5 py-0.5 rounded-full border',
              connected ? 'text-fabric-low border-fabric-low/30' : 'text-fabric-dim border-fabric-border'
            )}>
              {connected ? '● LIVE' : '○ OFFLINE'}
            </span>
          </div>
          <button onClick={clear} className="text-xs font-mono text-fabric-dim hover:text-fabric-text transition-colors">
            Clear
          </button>
        </div>
        <div className="divide-y divide-fabric-border/30 max-h-96 overflow-y-auto">
          {events.length === 0 ? (
            <p className="text-xs text-fabric-dim font-mono text-center py-10">
              {connected ? 'No detections yet. Start the simulator.' : 'Connecting...'}
            </p>
          ) : (
            events.map((e) => (
              <div key={e.threat_id}
                className={clsx('px-4 py-3 flex items-start gap-4 border-l-2 animate-slide-up', SEV_COLOR[e.severity])}>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-0.5">
                    <span className="text-xs font-mono font-medium">{e.classification}</span>
                    <span className="text-[10px] font-mono text-fabric-dim">
                      conf: {(e.confidence_score * 100).toFixed(0)}%
                    </span>
                  </div>
                  <p className="text-[10px] font-mono text-fabric-dim">
                    {e.source_ip}:{e.source_port} → {e.destination_ip}:{e.destination_port} · {e.protocol}
                  </p>
                </div>
                <p className="text-[10px] font-mono text-fabric-dim/60 whitespace-nowrap flex-shrink-0">
                  {formatDistanceToNow(new Date(e.timestamp * 1000), { addSuffix: true })}
                </p>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  )
}
