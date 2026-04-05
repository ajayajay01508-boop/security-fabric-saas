import React, { createContext, useContext, useState, useCallback, useEffect } from 'react'
import { CheckCircle, XCircle, AlertTriangle, Info, X } from 'lucide-react'
import clsx from 'clsx'

export type ToastType = 'success' | 'error' | 'warning' | 'info'

export interface Toast {
  id: string
  type: ToastType
  title: string
  message?: string
  duration?: number
}

interface ToastCtx {
  toasts: Toast[]
  toast: (t: Omit<Toast, 'id'>) => void
  success: (title: string, message?: string) => void
  error: (title: string, message?: string) => void
  warning: (title: string, message?: string) => void
  info: (title: string, message?: string) => void
  dismiss: (id: string) => void
}

const ToastContext = createContext<ToastCtx | null>(null)

const ICONS: Record<ToastType, React.ReactNode> = {
  success: <CheckCircle className="w-4 h-4 text-fabric-low flex-shrink-0" />,
  error:   <XCircle    className="w-4 h-4 text-fabric-critical flex-shrink-0" />,
  warning: <AlertTriangle className="w-4 h-4 text-fabric-high flex-shrink-0" />,
  info:    <Info       className="w-4 h-4 text-fabric-accent flex-shrink-0" />,
}

const BORDERS: Record<ToastType, string> = {
  success: 'border-fabric-low/40',
  error:   'border-fabric-critical/40',
  warning: 'border-fabric-high/40',
  info:    'border-fabric-accent/40',
}

function ToastItem({ toast, onDismiss }: { toast: Toast; onDismiss: (id: string) => void }) {
  useEffect(() => {
    const t = setTimeout(() => onDismiss(toast.id), toast.duration ?? 4000)
    return () => clearTimeout(t)
  }, [toast.id, toast.duration, onDismiss])

  return (
    <div className={clsx(
      'flex items-start gap-3 bg-fabric-surface border rounded-lg px-4 py-3',
      'shadow-lg animate-slide-up max-w-sm w-full',
      BORDERS[toast.type]
    )}>
      {ICONS[toast.type]}
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium text-white font-body">{toast.title}</p>
        {toast.message && (
          <p className="text-xs text-fabric-dim font-body mt-0.5">{toast.message}</p>
        )}
      </div>
      <button
        onClick={() => onDismiss(toast.id)}
        className="text-fabric-dim hover:text-fabric-text transition-colors flex-shrink-0"
      >
        <X className="w-3.5 h-3.5" />
      </button>
    </div>
  )
}

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([])

  const dismiss = useCallback((id: string) => {
    setToasts((t) => t.filter((x) => x.id !== id))
  }, [])

  const toast = useCallback((t: Omit<Toast, 'id'>) => {
    const id = `${Date.now()}-${Math.random().toString(36).slice(2)}`
    setToasts((prev) => [...prev.slice(-4), { ...t, id }])
  }, [])

  const success = useCallback((title: string, message?: string) =>
    toast({ type: 'success', title, message }), [toast])
  const error   = useCallback((title: string, message?: string) =>
    toast({ type: 'error',   title, message, duration: 6000 }), [toast])
  const warning = useCallback((title: string, message?: string) =>
    toast({ type: 'warning', title, message }), [toast])
  const info    = useCallback((title: string, message?: string) =>
    toast({ type: 'info',    title, message }), [toast])

  return (
    <ToastContext.Provider value={{ toasts, toast, success, error, warning, info, dismiss }}>
      {children}
      {/* Toast container */}
      <div className="fixed bottom-4 right-4 z-50 flex flex-col gap-2">
        {toasts.map((t) => (
          <ToastItem key={t.id} toast={t} onDismiss={dismiss} />
        ))}
      </div>
    </ToastContext.Provider>
  )
}

export function useToast(): ToastCtx {
  const ctx = useContext(ToastContext)
  if (!ctx) throw new Error('useToast must be used within ToastProvider')
  return ctx
}
