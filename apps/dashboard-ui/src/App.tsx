import { Routes, Route, Navigate } from 'react-router-dom'
import { AuthProvider, useAuth } from './hooks/useAuth'
import { ToastProvider } from './components/Toast'
import { ErrorBoundary } from './components/ErrorBoundary'
import { Layout } from './components/Layout/Layout'
import { LoginPage } from './pages/LoginPage'
import { RegisterPage } from './pages/RegisterPage'
import { DashboardPage } from './pages/DashboardPage'
import { AlertsPage } from './pages/AlertsPage'
import { TelemetryPage } from './pages/TelemetryPage'
import { BillingPage } from './pages/BillingPage'
import { NotFoundPage } from './pages/NotFoundPage'

function PrivateRoute({ children }: { children: React.ReactNode }) {
  const { user, loading } = useAuth()
  if (loading) return (
    <div className="flex items-center justify-center h-screen bg-fabric-bg">
      <div className="text-fabric-accent font-mono text-sm animate-pulse">
        INITIALIZING...
      </div>
    </div>
  )
  return user ? <>{children}</> : <Navigate to="/login" replace />
}

function AppRoutes() {
  return (
    <Routes>
      <Route path="/login"    element={<LoginPage />} />
      <Route path="/register" element={<RegisterPage />} />
      <Route path="/" element={
        <PrivateRoute>
          <Layout />
        </PrivateRoute>
      }>
        <Route index element={<Navigate to="/dashboard" replace />} />
        <Route path="dashboard" element={
          <ErrorBoundary><DashboardPage /></ErrorBoundary>
        } />
        <Route path="alerts" element={
          <ErrorBoundary><AlertsPage /></ErrorBoundary>
        } />
        <Route path="telemetry" element={
          <ErrorBoundary><TelemetryPage /></ErrorBoundary>
        } />
        <Route path="billing" element={
          <ErrorBoundary><BillingPage /></ErrorBoundary>
        } />
      </Route>
      <Route path="*" element={<NotFoundPage />} />
    </Routes>
  )
}

export default function App() {
  return (
    <AuthProvider>
      <ToastProvider>
        <AppRoutes />
      </ToastProvider>
    </AuthProvider>
  )
}
