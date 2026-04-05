import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { Shield, AlertCircle } from 'lucide-react'
import { authApi } from '../lib/api'
import { useAuth } from '../hooks/useAuth'

export function RegisterPage() {
  const { login } = useAuth()
  const navigate = useNavigate()
  const [form, setForm] = useState({ email: '', password: '', full_name: '', organization: '' })
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const set = (k: keyof typeof form) => (e: React.ChangeEvent<HTMLInputElement>) =>
    setForm((f) => ({ ...f, [k]: e.target.value }))

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      await authApi.register(form)
      await login(form.email, form.password)
      navigate('/dashboard')
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Registration failed.')
    } finally {
      setLoading(false)
    }
  }

  const fields = [
    { key: 'full_name' as const,     label: 'Full Name',     type: 'text',     placeholder: 'Ada Lovelace' },
    { key: 'organization' as const,  label: 'Organization',  type: 'text',     placeholder: 'Acme Security' },
    { key: 'email' as const,         label: 'Email',         type: 'email',    placeholder: 'ada@acme.io' },
    { key: 'password' as const,      label: 'Password',      type: 'password', placeholder: '••••••••' },
  ]

  return (
    <div className="min-h-screen bg-fabric-bg grid-bg flex items-center justify-center px-4">
      <div className="w-full max-w-sm animate-fade-in">
        <div className="flex items-center gap-2.5 mb-10 justify-center">
          <Shield className="w-6 h-6 text-fabric-accent" />
          <span className="font-display font-bold text-white text-lg tracking-wider">SECURITY FABRIC</span>
        </div>

        <div className="bg-fabric-surface border border-fabric-border rounded-xl p-8">
          <h1 className="font-display text-xl font-bold text-white mb-1">Create account</h1>
          <p className="text-sm text-fabric-dim mb-7 font-body">Start your threat intelligence deployment</p>

          {error && (
            <div className="flex items-center gap-2 bg-fabric-critical/10 border border-fabric-critical/30 rounded-lg px-3 py-2.5 mb-5">
              <AlertCircle className="w-4 h-4 text-fabric-critical flex-shrink-0" />
              <p className="text-xs text-fabric-critical">{error}</p>
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            {fields.map(({ key, label, type, placeholder }) => (
              <div key={key}>
                <label className="block text-xs font-mono text-fabric-dim uppercase tracking-widest mb-1.5">{label}</label>
                <input
                  type={type}
                  value={form[key]}
                  onChange={set(key)}
                  required={key !== 'organization'}
                  placeholder={placeholder}
                  className="w-full bg-fabric-bg border border-fabric-border rounded-lg px-3 py-2.5 text-sm font-body text-fabric-text placeholder-fabric-dim/50 focus:outline-none focus:border-fabric-accent/60 transition-colors"
                />
              </div>
            ))}
            <button
              type="submit"
              disabled={loading}
              className="w-full bg-fabric-accent/10 hover:bg-fabric-accent/20 border border-fabric-accent/40 text-fabric-accent font-mono text-sm py-2.5 rounded-lg transition-all duration-150 disabled:opacity-50 mt-2"
            >
              {loading ? 'CREATING...' : 'CREATE ACCOUNT →'}
            </button>
          </form>
        </div>

        <p className="text-center text-xs text-fabric-dim mt-5 font-body">
          Already have an account?{' '}
          <Link to="/login" className="text-fabric-accent hover:underline">Sign in</Link>
        </p>
      </div>
    </div>
  )
}
