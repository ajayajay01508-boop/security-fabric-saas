import { useEffect, useState } from 'react'
import { paymentsApi } from '../lib/api'
import { CheckCircle, ExternalLink, CreditCard, Zap } from 'lucide-react'
import clsx from 'clsx'

const PLANS = [
  {
    id: 'starter',
    name: 'Starter',
    price: '$49',
    period: '/mo',
    description: 'For small teams getting started with threat detection',
    features: ['Up to 100k events/day', '30-day alert history', 'Email notifications', 'API access', 'Community support'],
    accent: 'border-fabric-border',
    button: 'border-fabric-border text-fabric-text hover:border-fabric-text/60',
  },
  {
    id: 'professional',
    name: 'Professional',
    price: '$149',
    period: '/mo',
    description: 'For teams that need real-time response at scale',
    features: ['Up to 1M events/day', '90-day alert history', 'Email + SMS alerts', 'Voice call alerts', 'Priority support', 'Custom ML model tuning'],
    accent: 'border-fabric-accent/50',
    button: 'border-fabric-accent/50 text-fabric-accent hover:bg-fabric-accent/10',
    highlight: true,
  },
  {
    id: 'enterprise',
    name: 'Enterprise',
    price: '$499',
    period: '/mo',
    description: 'Unlimited scale with dedicated infrastructure',
    features: ['Unlimited events', '1-year alert history', 'All notification channels', 'Multi-cloud failover', 'SLA guarantee', 'Dedicated support', 'Custom integrations'],
    accent: 'border-fabric-border',
    button: 'border-fabric-border text-fabric-text hover:border-fabric-text/60',
  },
]

export function BillingPage() {
  const [subscription, setSubscription] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [subscribing, setSubscribing] = useState<string | null>(null)

  useEffect(() => {
    paymentsApi.status()
      .then((r) => setSubscription(r.data))
      .catch(() => setSubscription({ plan: 'free', status: 'active' }))
      .finally(() => setLoading(false))
  }, [])

  const subscribe = async (plan: string) => {
    setSubscribing(plan)
    try {
      await paymentsApi.subscribe(plan)
      const r = await paymentsApi.status()
      setSubscription(r.data)
    } catch {}
    finally { setSubscribing(null) }
  }

  const openPortal = async () => {
    const r = await paymentsApi.portal()
    window.open(r.data.url, '_blank')
  }

  const currentPlan = subscription?.plan ?? 'free'

  return (
    <div className="p-6 space-y-6 animate-fade-in">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="font-display text-2xl font-bold text-white">Billing</h1>
          <p className="text-sm text-fabric-dim font-mono mt-0.5">
            {loading ? 'Loading...' : `Current plan: ${currentPlan.toUpperCase()} · ${subscription?.status ?? ''}`}
          </p>
        </div>
        <button onClick={openPortal}
          className="flex items-center gap-2 text-xs font-mono text-fabric-dim hover:text-fabric-text border border-fabric-border hover:border-fabric-text/30 px-3 py-2 rounded-lg transition-all">
          <CreditCard className="w-3.5 h-3.5" />
          Manage Billing
          <ExternalLink className="w-3 h-3" />
        </button>
      </div>

      {/* Current plan banner */}
      {currentPlan !== 'free' && (
        <div className="bg-fabric-accent/5 border border-fabric-accent/30 rounded-lg px-4 py-3 flex items-center gap-3">
          <Zap className="w-4 h-4 text-fabric-accent flex-shrink-0" />
          <p className="text-sm text-fabric-text font-body">
            You're on the <span className="text-fabric-accent font-medium">{currentPlan}</span> plan.
            Next billing cycle renews automatically.
          </p>
        </div>
      )}

      {/* Plan cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {PLANS.map((plan) => {
          const isCurrent = currentPlan === plan.id
          return (
            <div key={plan.id} className={clsx(
              'bg-fabric-surface border rounded-xl p-5 flex flex-col relative',
              plan.accent,
              plan.highlight && 'glow-accent',
            )}>
              {plan.highlight && (
                <div className="absolute -top-px left-1/2 -translate-x-1/2">
                  <span className="bg-fabric-accent text-fabric-bg text-[10px] font-mono font-bold px-3 py-0.5 rounded-b-lg uppercase tracking-widest">
                    Popular
                  </span>
                </div>
              )}
              <div className="mb-4 mt-1">
                <h3 className="font-display text-lg font-bold text-white">{plan.name}</h3>
                <div className="flex items-baseline gap-0.5 mt-1">
                  <span className="font-display text-3xl font-bold text-white">{plan.price}</span>
                  <span className="text-sm text-fabric-dim font-mono">{plan.period}</span>
                </div>
                <p className="text-xs text-fabric-dim font-body mt-2">{plan.description}</p>
              </div>

              <ul className="space-y-2 flex-1 mb-5">
                {plan.features.map((f) => (
                  <li key={f} className="flex items-start gap-2 text-xs font-body text-fabric-text">
                    <CheckCircle className="w-3.5 h-3.5 text-fabric-low mt-0.5 flex-shrink-0" />
                    {f}
                  </li>
                ))}
              </ul>

              <button
                onClick={() => !isCurrent && subscribe(plan.id)}
                disabled={isCurrent || subscribing === plan.id}
                className={clsx(
                  'w-full py-2.5 rounded-lg text-xs font-mono border transition-all duration-150',
                  isCurrent
                    ? 'border-fabric-low/40 text-fabric-low bg-fabric-low/10 cursor-default'
                    : plan.button,
                  subscribing === plan.id && 'opacity-50 cursor-not-allowed'
                )}
              >
                {isCurrent ? '✓ CURRENT PLAN' : subscribing === plan.id ? 'SUBSCRIBING...' : `UPGRADE TO ${plan.name.toUpperCase()}`}
              </button>
            </div>
          )
        })}
      </div>

      {/* Free tier */}
      <div className="bg-fabric-surface border border-fabric-border rounded-lg px-5 py-4 flex items-center justify-between">
        <div>
          <p className="text-sm font-body font-medium text-fabric-text">Free Tier</p>
          <p className="text-xs text-fabric-dim font-body mt-0.5">Up to 1,000 events/day · 7-day history · Community support</p>
        </div>
        <span className={clsx(
          'text-xs font-mono px-2.5 py-1 rounded-full border',
          currentPlan === 'free'
            ? 'text-fabric-accent border-fabric-accent/30 bg-fabric-accent/10'
            : 'text-fabric-dim border-fabric-border'
        )}>
          {currentPlan === 'free' ? 'ACTIVE' : 'FREE'}
        </span>
      </div>
    </div>
  )
}
