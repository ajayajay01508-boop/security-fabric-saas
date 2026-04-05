import { Link } from 'react-router-dom'
import { Shield, ArrowLeft } from 'lucide-react'

export function NotFoundPage() {
  return (
    <div className="min-h-screen bg-fabric-bg grid-bg flex items-center justify-center px-4">
      <div className="text-center animate-fade-in">
        <div className="flex items-center justify-center gap-2.5 mb-10">
          <Shield className="w-5 h-5 text-fabric-accent" />
          <span className="font-display font-bold text-white text-sm tracking-wider">
            SECURITY FABRIC
          </span>
        </div>

        <div className="font-display text-8xl font-bold text-fabric-border mb-4 select-none">
          404
        </div>
        <h1 className="font-display text-2xl font-bold text-white mb-2">
          Page not found
        </h1>
        <p className="text-sm text-fabric-dim font-body mb-8 max-w-xs mx-auto">
          The route you're looking for doesn't exist or has been moved.
        </p>

        <Link
          to="/dashboard"
          className="inline-flex items-center gap-2 text-xs font-mono text-fabric-accent
                     border border-fabric-accent/40 bg-fabric-accent/10 hover:bg-fabric-accent/20
                     px-5 py-2.5 rounded-lg transition-all"
        >
          <ArrowLeft className="w-3.5 h-3.5" />
          Return to Dashboard
        </Link>
      </div>
    </div>
  )
}
