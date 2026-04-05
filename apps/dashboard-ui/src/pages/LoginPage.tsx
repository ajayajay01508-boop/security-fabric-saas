import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth'
import { Shield, Eye, EyeOff, AlertCircle } from 'lucide-react'

export function LoginPage() {
  const { login } = useAuth()
  const navigate = useNavigate()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [showPw, setShowPw] = useState(false)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      await login(email, password)
      navigate('/dashboard')
    } catch {
      setError('Invalid credentials. Check your email and password.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-fabric-bg grid-bg flex items-center justify-center px-4">
      <div className="w-full max-w-sm animate-fade-in">
        {/* Logo */}
        <div className="flex items-center gap-2.5 mb-10 justify-center">
          <Shield className="w-6 h-6 text-fabric-accent" />
          <span className="font-display font-bold text-white text-lg tracking-wider">SECURITY FABRIC</span>
        </div>

        <div className="bg-fabric-surface border border-fabric-border rounded-xl p-8">
          <h1 className="font-display text-xl font-bold text-white mb-1">Sign in</h1>
          <p className="text-sm text-fabric-dim mb-7 font-body">Access your threat intelligence dashboard</p>

          {error && (
            <div className="flex items-center gap-2 bg-fabric-critical/10 border border-fabric-critical/30 rounded-lg px-3 py-2.5 mb-5">
              <AlertCircle className="w-4 h-4 text-fabric-critical flex-shrink-0" />
              <p className="text-xs text-fabric-critical">{error}</p>
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-xs font-mono text-fabric-dim uppercase tracking-widest mb-1.5">Email</label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                placeholder="operator@org.io"
                className="w-full bg-fabric-bg border border-fabric-border rounded-lg px-3 py-2.5 text-sm font-body text-fabric-text placeholder-fabric-dim/50 focus:outline-none focus:border-fabric-accent/60 transition-colors"
              />
            </div>
            <div>
              <label className="block text-xs font-mono text-fabric-dim uppercase tracking-widest mb-1.5">Password</label>
              <div className="relative">
                <input
                  type={showPw ? 'text' : 'password'}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                  placeholder="••••••••"
                  className="w-full bg-fabric-bg border border-fabric-border rounded-lg px-3 py-2.5 pr-10 text-sm font-body text-fabric-text placeholder-fabric-dim/50 focus:outline-none focus:border-fabric-accent/60 transition-colors"
                />
                <button
                  type="button"
                  onClick={() => setShowPw(!showPw)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-fabric-dim hover:text-fabric-text transition-colors"
                >
                  {showPw ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
            </div>
            <button
              type="submit"
              disabled={loading}
              className="w-full bg-fabric-accent/10 hover:bg-fabric-accent/20 border border-fabric-accent/40 text-fabric-accent font-mono text-sm py-2.5 rounded-lg transition-all duration-150 disabled:opacity-50 disabled:cursor-not-allowed mt-2"
            >
              {loading ? 'AUTHENTICATING...' : 'SIGN IN →'}
            </button>
          </form>
        </div>

        <p className="text-center text-xs text-fabric-dim mt-5 font-body">
          No account?{' '}
          <Link to="/register" className="text-fabric-accent hover:underline">Create one</Link>
        </p>
      </div>
    </div>
  )
}
