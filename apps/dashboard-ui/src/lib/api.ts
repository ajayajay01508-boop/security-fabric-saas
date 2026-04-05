import axios from 'axios'

const BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

export const api = axios.create({ baseURL: BASE_URL })

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

api.interceptors.response.use(
  (r) => r,
  (err) => {
    if (err.response?.status === 401) {
      localStorage.removeItem('access_token')
      window.location.href = '/login'
    }
    return Promise.reject(err)
  }
)

// ─── Auth ────────────────────────────────────────────────────────
export const authApi = {
  login: (email: string, password: string) =>
    api.post('/auth/token', new URLSearchParams({ username: email, password }), {
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    }),
  register: (data: { email: string; password: string; full_name: string; organization: string }) =>
    api.post('/auth/register', data),
  me: () => api.get('/auth/me'),
  logout: () => api.delete('/auth/token'),
}

// ─── Alerts ──────────────────────────────────────────────────────
export const alertsApi = {
  list: (params?: { severity?: string; status?: string; q?: string; limit?: number; offset?: number }) =>
    api.get('/alerts', { params }),
  export: (params?: { severity?: string; status?: string }) =>
    api.get('/alerts/export', { params, responseType: 'blob' }),
  search: (q: string, limit = 50) =>
    api.get('/alerts', { params: { q, limit } }),
  stats: () => api.get('/alerts/stats'),
  get: (id: number) => api.get(`/alerts/${id}`),
  acknowledge: (id: number, note?: string) =>
    api.patch(`/alerts/${id}/acknowledge`, { note }),
  resolve: (id: number) => api.patch(`/alerts/${id}/resolve`),
}

// ─── Payments ────────────────────────────────────────────────────
export const paymentsApi = {
  status: () => api.get('/payments/status'),
  subscribe: (plan: string) => api.post('/payments/subscribe', { plan }),
  portal: () => api.post('/payments/portal'),
}

// ─── Telemetry ───────────────────────────────────────────────────
export const telemetryApi = {
  ingest: (event: object) => api.post('/telemetry/ingest', event),
  ingestBatch: (events: object[]) => api.post('/telemetry/ingest/batch', { events }),
}
