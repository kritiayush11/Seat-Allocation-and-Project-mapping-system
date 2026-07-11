// ── Enums ─────────────────────────────────────────────────────────────────────

export type EmployeeStatus = 'active' | 'inactive' | 'on_leave' | 'terminated'
export type ProjectStatus = 'active' | 'inactive' | 'archived'
export type SeatStatus = 'available' | 'occupied' | 'reserved' | 'maintenance'
export type AllocationStatus = 'active' | 'released' | 'transferred'

// ── Core entities ──────────────────────────────────────────────────────────────

export interface ProjectSummary {
  id: number
  name: string
  status: ProjectStatus
}

export interface Project extends ProjectSummary {
  description?: string
  manager_name?: string
  created_at: string
  employee_count: number
  occupied_seats: number
}

export interface SeatInfo {
  seat_id: number
  floor: number
  zone: string
  bay: string
  seat_number: string
  allocation_date: string
}

export interface Employee {
  id: number
  employee_code: string
  name: string
  email: string
  department?: string
  role?: string
  joining_date: string
  status: EmployeeStatus
  project_id?: number
  created_at: string
  project?: ProjectSummary
  seat?: SeatInfo
}

export interface AllocationSummary {
  id: number
  employee_id: number
  employee_name?: string
  employee_code?: string
  project_id?: number
  project_name?: string
  allocation_date: string
  allocation_status: AllocationStatus
}

export interface Seat {
  id: number
  floor: number
  zone: string
  bay: string
  seat_number: string
  status: SeatStatus
  created_at: string
  current_allocation?: AllocationSummary
}

export interface SeatAllocation {
  id: number
  employee_id: number
  seat_id: number
  project_id?: number
  allocation_status: AllocationStatus
  allocation_date: string
  released_date?: string
  seat?: Seat
}

// ── Paginated responses ────────────────────────────────────────────────────────

export interface PaginatedEmployees {
  total: number
  page: number
  page_size: number
  employees: Employee[]
}

export interface PaginatedSeats {
  total: number
  page: number
  page_size: number
  seats: Seat[]
}

// ── Dashboard ──────────────────────────────────────────────────────────────────

export interface DashboardSummary {
  total_employees: number
  active_employees: number
  total_seats: number
  occupied_seats: number
  available_seats: number
  reserved_seats: number
  maintenance_seats: number
  pending_allocation: number
  utilization_rate: number
}

export interface ProjectUtilization {
  project_id: number
  project_name: string
  total_employees: number
  allocated_seats: number
  unallocated_employees: number
}

export interface FloorUtilization {
  floor: number
  total_seats: number
  occupied: number
  available: number
  reserved: number
  maintenance: number
  occupancy_rate: number
}

// ── AI Assistant ───────────────────────────────────────────────────────────────

export interface AIQuery {
  query: string
  session_id?: string
}

export interface AIResponse {
  answer: string
  intent?: string
  data?: Record<string, unknown>
  confidence?: number
  source?: string
  session_id?: string
}

// ── Forms ──────────────────────────────────────────────────────────────────────

export interface EmployeeCreateForm {
  name: string
  email: string
  department?: string
  role?: string
  joining_date?: string
  status?: EmployeeStatus
  project_id?: number
  employee_code?: string
}

export interface ProjectCreateForm {
  name: string
  description?: string
  manager_name?: string
  status?: ProjectStatus
}

export interface SeatCreateForm {
  floor: number
  zone: string
  bay: string
  seat_number: string
  status?: SeatStatus
}

export interface AllocateForm {
  employee_id: number
  seat_id?: number
  project_id?: number
}

// ── Auth ────────────────────────────────────────────────────────────────────────

export interface User {
  id: number
  username: string
  email: string
  is_admin: boolean
}

export interface TokenResponse {
  access_token: string
  token_type: string
}

