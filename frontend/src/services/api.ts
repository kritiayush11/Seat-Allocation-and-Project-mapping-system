import axios from 'axios'
import type {
  Employee, PaginatedEmployees, EmployeeCreateForm,
  Project, ProjectCreateForm,
  Seat, PaginatedSeats, SeatCreateForm, SeatAllocation, AllocateForm,
  DashboardSummary, ProjectUtilization, FloorUtilization,
  AIQuery, AIResponse,
  User, TokenResponse,
} from '../types'

const BASE_URL = process.env.REACT_APP_API_URL || "http://localhost:8000";

export const api = axios.create({
  baseURL: BASE_URL,
  headers: { 'Content-Type': 'application/json' },
})

// Request interceptor to inject bearer token
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => Promise.reject(error)
)

// ── Employees ──────────────────────────────────────────────────────────────────

export const employeeApi = {
  list: (params?: {
    q?: string; project_id?: number; status?: string
    department?: string; has_seat?: boolean; page?: number; page_size?: number
  }) => api.get<PaginatedEmployees>('/employees', { params }).then(r => r.data),

  get: (id: number) => api.get<Employee>(`/employees/${id}`).then(r => r.data),

  create: (data: EmployeeCreateForm) =>
    api.post<Employee>('/employees', data).then(r => r.data),

  update: (id: number, data: Partial<EmployeeCreateForm>) =>
    api.put<Employee>(`/employees/${id}`, data).then(r => r.data),

  deactivate: (id: number) =>
    api.delete<{ message: string }>(`/employees/${id}`).then(r => r.data),
}

// ── Projects ───────────────────────────────────────────────────────────────────

export const projectApi = {
  list: (activeOnly = true) =>
    api.get<Project[]>('/projects', { params: { active_only: activeOnly } }).then(r => r.data),

  get: (id: number) => api.get<Project>(`/projects/${id}`).then(r => r.data),

  create: (data: ProjectCreateForm) =>
    api.post<Project>('/projects', data).then(r => r.data),

  update: (id: number, data: Partial<ProjectCreateForm>) =>
    api.put<Project>(`/projects/${id}`, data).then(r => r.data),

  getEmployees: (id: number) =>
    api.get<Employee[]>(`/projects/${id}/employees`).then(r => r.data),
}

// ── Seats ──────────────────────────────────────────────────────────────────────

export const seatApi = {
  list: (params?: {
    floor?: number; zone?: string; status?: string; page?: number; page_size?: number
  }) => api.get<PaginatedSeats>('/seats', { params }).then(r => r.data),

  get: (id: number) => api.get<Seat>(`/seats/${id}`).then(r => r.data),

  getAvailable: (params?: { floor?: number; zone?: string }) =>
    api.get<Seat[]>('/seats/available', { params }).then(r => r.data),

  suggest: (project_id: number, count = 5) =>
    api.get<Seat[]>('/seats/suggest', { params: { project_id, count } }).then(r => r.data),

  create: (data: SeatCreateForm) =>
    api.post<Seat>('/seats', data).then(r => r.data),

  update: (id: number, data: Partial<SeatCreateForm & { status: string }>) =>
    api.put<Seat>(`/seats/${id}`, data).then(r => r.data),

  allocate: (data: AllocateForm) =>
    api.post<SeatAllocation>('/seats/allocate', data).then(r => r.data),

  release: (employee_id: number) =>
    api.post<{ message: string; seat_id: number; employee_id: number }>(
      '/seats/release', { employee_id }
    ).then(r => r.data),
}

// ── Dashboard ──────────────────────────────────────────────────────────────────

export const dashboardApi = {
  summary: () =>
    api.get<DashboardSummary>('/dashboard/summary').then(r => r.data),

  projectUtilization: () =>
    api.get<ProjectUtilization[]>('/dashboard/project-utilization').then(r => r.data),

  floorUtilization: () =>
    api.get<FloorUtilization[]>('/dashboard/floor-utilization').then(r => r.data),
}

// ── AI Assistant ───────────────────────────────────────────────────────────────

export const aiApi = {
  query: (data: AIQuery) =>
    api.post<AIResponse>('/ai/query', data).then(r => r.data),
}

// ── Seed ───────────────────────────────────────────────────────────────────────

export const seedApi = {
  seed: () => api.post('/seed').then(r => r.data),
}

// ── Authentication ─────────────────────────────────────────────────────────────

export const authApi = {
  signup: (data: any) =>
    api.post<User>('/auth/signup', data).then(r => r.data),

  login: (data: any) =>
    api.post<TokenResponse>('/auth/login', data).then(r => r.data),

  me: () =>
    api.get<User>('/auth/me').then(r => r.data),
}
