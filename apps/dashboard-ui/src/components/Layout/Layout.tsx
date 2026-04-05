import { Outlet, NavLink, useLocation } from 'react-router-dom'
import { useAuth } from '../../hooks/useAuth'
import { useThreatStream } from '../../hooks/useWebSocket'
import {
  LayoutDashboard, Bell, Activity, CreditCard,
  LogOut, Shield, Wifi, WifiOff, Circle
} from 'lucide-react'
import clsx from 'clsx'

const NAV = [
  { to: '/dashboard', icon: LayoutDashboard, label: 'Dashboard' },
  { to: '/alerts',    icon: Bell,            label: 'Alerts' },
  { to: '/telemetry', icon: Activity,        label: 'Telemetry' },
  { to: '/billing',   icon: CreditCard,      label: 'Billing' },
]

const SEVERITY_DOT: Record<string, string> = {
  critical: 'bg-fabric-critical animate-pulse',
  high:     'bg-fabric-high animate-pulse',
  medium:   'bg-fabric-medium',
  low:      'bg-fabric-low',
  info:     'bg-fabric-dim',
}

export function Layout() {
  const { user, logout } = useAuth()
  const { events, connected } = useThreatStream()
  const latest = events.slice(0, 4)

  return (
    <div className="flex h-screen bg-fabric-bg overflow-hidden">
      {/* Sidebar */}
      <aside className="w-56 flex-shrink-0 bg-fabric-surface border-r border-fabric-border flex flex-col">
        {/* Logo */}
        <div className="px-4 py-5 border-b border-fabric-border">
          <div className="flex items-center gap-2.5">
            <Shield className="w-5 h-5 text-fabric-accent" />
            <span className="font-display font-bold text-white text-sm tracking-wider">SECURITY FABRIC</span>
          </div>
          <div className="mt-1 flex items-center gap-1.5">
            {connected
              ? <Wifi className="w-3 h-3 text-fabric-low" />
              : <WifiOff className="w-3 h-3 text-fabric-critical" />}
            <span className={clsx('text-xs font-mono', connected ? 'text-fabric-low' : 'text-fabric-critical')}>
              {connected ? 'LIVE' : 'OFFLINE'}
            </span>
          </div>
        </div>

        {/* Nav */}
        <nav className="flex-1 py-4 px-2 space-y-0.5">
          {NAV.map(({ to, icon: Icon, label }) => (
            <NavLink
              key={to}
              to={to}
              className={({ isActive }) => clsx(
                'flex items-center gap-3 px-3 py-2.5 rounded text-sm transition-all duration-150',
                isActive
                  ? 'bg-fabric-muted text-white font-medium'
                  : 'text-fabric-dim hover:text-fabric-text hover:bg-fabric-muted/50'
              )}
            >
              <Icon className="w-4 h-4 flex-shrink-0" />
              <span className="font-body">{label}</span>
            </NavLink>
          ))}
        </nav>

        {/* Live feed */}
        {latest.length > 0 && (
          <div className="border-t border-fabric-border px-3 py-3">
            <p className="text-xs font-mono text-fabric-dim mb-2 uppercase tracking-widest">Live Feed</p>
            <div className="space-y-1.5">
              {latest.map((e) => (
                <div key={e.threat_id} className="flex items-start gap-2 animate-slide-up">
                  <Circle className={clsx('w-1.5 h-1.5 mt-1.5 rounded-full flex-shrink-0', SEVERITY_DOT[e.severity])} />
                  <div className="min-w-0">
                    <p className="text-xs text-fabric-text truncate">{e.classification}</p>
                    <p className="text-xs text-fabric-dim font-mono truncate">{e.source_ip}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* User */}
        <div className="border-t border-fabric-border p-3">
          <div className="flex items-center justify-between">
            <div className="min-w-0">
              <p className="text-xs font-medium text-fabric-text truncate">{user?.full_name}</p>
              <p className="text-xs text-fabric-dim truncate">{user?.email}</p>
            </div>
            <button onClick={logout} className="p-1.5 text-fabric-dim hover:text-fabric-critical transition-colors rounded">
              <LogOut className="w-4 h-4" />
            </button>
          </div>
        </div>
      </aside>

      {/* Main content */}
      <main className="flex-1 overflow-y-auto grid-bg">
        <Outlet />
      </main>
    </div>
  )
}
