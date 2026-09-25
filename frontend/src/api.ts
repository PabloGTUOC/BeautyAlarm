import type {
  AuthConfig,
  CalendarDay,
  DailyLog,
  LogStatus,
  Product,
  Routine,
  RoutineInput,
  RoutineAdherence,
  Streak,
  TodayResponse,
  User
} from './types'

/** Same-origin in production behind nginx (D9); the Vite dev server proxies it. */
const BASE = '/api'

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message)
    this.name = 'ApiError'
  }
}

function errorMessage(status: number, body: string): string {
  try {
    const parsed = JSON.parse(body)
    if (typeof parsed.detail === 'string') return parsed.detail
    if (Array.isArray(parsed.detail) && parsed.detail[0]?.msg) return parsed.detail[0].msg
  } catch {
    /* not JSON */
  }
  return body || `Request failed with status ${status}`
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers)
  if (init.body) headers.set('Content-Type', 'application/json')

  // The session lives in an httpOnly cookie (D5a), which scripts cannot read;
  // it only has to be sent. Same-origin behind nginx (D9).
  const response = await fetch(`${BASE}${path}`, {
    ...init,
    headers,
    credentials: 'same-origin'
  })
  const body = response.status === 204 ? '' : await response.text()
  if (!response.ok) throw new ApiError(response.status, errorMessage(response.status, body))
  return (body ? JSON.parse(body) : undefined) as T
}

export const api = {
  // Auth (D5a)
  register: (data: { email: string; password: string; display_name: string }) =>
    request<User>('/auth/register', { method: 'POST', body: JSON.stringify(data) }),
  login: (data: { email: string; password: string }) =>
    request<User>('/auth/login', { method: 'POST', body: JSON.stringify(data) }),
  logout: () => request<void>('/auth/logout', { method: 'POST' }),
  me: () => request<User>('/auth/me'),
  authConfig: () => request<AuthConfig>('/auth/config'),

  // Products
  listProducts: () => request<Product[]>('/products/'),
  createProduct: (data: { name: string; brand?: string | null; notes?: string | null }) =>
    request<Product>('/products/', { method: 'POST', body: JSON.stringify(data) }),
  archiveProduct: (id: number) => request<void>(`/products/${id}`, { method: 'DELETE' }),

  // Routines
  listRoutines: () => request<Routine[]>('/routines/'),
  getRoutine: (id: number) => request<Routine>(`/routines/${id}`),
  createRoutine: (data: RoutineInput) =>
    request<Routine>('/routines/', { method: 'POST', body: JSON.stringify(data) }),
  updateRoutine: (id: number, data: Partial<RoutineInput>) =>
    request<Routine>(`/routines/${id}`, { method: 'PATCH', body: JSON.stringify(data) }),
  deleteRoutine: (id: number) => request<void>(`/routines/${id}`, { method: 'DELETE' }),
  today: () => request<TodayResponse>('/routines/today'),

  // Logs
  logRoutine: (routineId: number, status: LogStatus, logDate?: string) =>
    request<DailyLog>('/logs/', {
      method: 'POST',
      body: JSON.stringify({ routine_id: routineId, status, log_date: logDate ?? null })
    }),
  deleteLog: (id: number) => request<void>(`/logs/${id}`, { method: 'DELETE' }),
  calendar: (from: string, to: string) =>
    request<CalendarDay[]>(`/logs/calendar?from=${from}&to=${to}`),
  streak: () => request<Streak>('/stats/streak'),
  adherence: (days = 30) => request<RoutineAdherence[]>(`/stats/adherence?days=${days}`),

  // Push
  pushPublicKey: () => request<{ public_key: string }>('/push/public-key'),
  pushSubscribe: (subscription: PushSubscriptionJSON) =>
    request<{ id: number }>('/push/subscribe', {
      method: 'POST',
      body: JSON.stringify(subscription)
    }),
  pushUnsubscribe: (endpoint: string) =>
    request<void>('/push/unsubscribe', { method: 'POST', body: JSON.stringify({ endpoint }) }),
  pushTest: () => request<{ delivered: number }>('/push/test', { method: 'POST' })
}
