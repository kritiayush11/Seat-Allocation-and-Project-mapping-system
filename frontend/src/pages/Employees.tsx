import { useState } from 'react'
import { Plus, UserMinus, Edit2, MapPin } from 'lucide-react'
import { Card } from '../components/ui/Card'
import { Badge } from '../components/ui/Badge'
import { Button } from '../components/ui/Button'
import { SearchBar } from '../components/ui/SearchBar'
import { Table, Pagination } from '../components/ui/Table'
import { Modal } from '../components/ui/Modal'
import { useToast } from '../components/ui/Toast'
import { useEmployees, useCreateEmployee, useUpdateEmployee, useDeactivateEmployee } from '../hooks/useEmployees'
import { useProjects } from '../hooks/useProjects'
import { useReleaseSeat, useAllocateSeat } from '../hooks/useSeats'
import type { Employee, EmployeeCreateForm } from '../types'

const PAGE_SIZE = 20

export function Employees() {
  const [search, setSearch] = useState('')
  const [projectFilter, setProjectFilter] = useState<number | undefined>()
  const [statusFilter, setStatusFilter] = useState('')
  const [page, setPage] = useState(1)
  const [showCreate, setShowCreate] = useState(false)
  const [editTarget, setEditTarget] = useState<Employee | null>(null)
  const [allocateTarget, setAllocateTarget] = useState<Employee | null>(null)

  const toast = useToast()
  const { data: projects } = useProjects()

  const { data, isLoading } = useEmployees({
    q: search || undefined,
    project_id: projectFilter,
    status: statusFilter || undefined,
    page,
    page_size: PAGE_SIZE,
  })

  const createMutation = useCreateEmployee()
  const updateMutation = useUpdateEmployee()
  const deactivateMutation = useDeactivateEmployee()
  const releaseMutation = useReleaseSeat()
  const allocateMutation = useAllocateSeat()

  const columns = [
    { key: 'employee_code', header: 'Code', render: (e: Employee) =>
      <span className="font-mono text-xs text-ethara-muted">{e.employee_code}</span> },
    { key: 'name', header: 'Name', render: (e: Employee) =>
      <div>
        <p className="font-medium text-white">{e.name}</p>
        <p className="text-xs text-ethara-muted">{e.email}</p>
      </div> },
    { key: 'project', header: 'Project', render: (e: Employee) =>
      <span className="text-sm">{e.project?.name ?? <span className="text-ethara-muted">—</span>}</span> },
    { key: 'department', header: 'Dept', render: (e: Employee) =>
      <span className="text-sm text-ethara-muted">{e.department ?? '—'}</span> },
    { key: 'seat', header: 'Seat', render: (e: Employee) =>
      e.seat
        ? <div className="flex items-center gap-1.5 text-xs">
            <MapPin className="w-3 h-3 text-ethara-primary" />
            <span>F{e.seat.floor} {e.seat.zone} {e.seat.seat_number}</span>
          </div>
        : <span className="text-xs text-ethara-warning px-2 py-0.5 bg-ethara-warning/10 rounded-full">Pending</span> },
    { key: 'status', header: 'Status', render: (e: Employee) => <Badge status={e.status} /> },
    { key: 'actions', header: 'Actions', render: (e: Employee) =>
      <div className="flex gap-2" onClick={ev => ev.stopPropagation()}>
        <button onClick={() => setEditTarget(e)}
          className="text-ethara-muted hover:text-white p-1 rounded transition-colors" title="Edit">
          <Edit2 className="w-3.5 h-3.5" />
        </button>
        {e.seat
          ? <button onClick={() => releaseMutation.mutate(e.id, {
              onSuccess: () => toast.success(`Seat released for ${e.name}`),
              onError: () => toast.error('Failed to release seat'),
            })} className="text-ethara-muted hover:text-ethara-error p-1 rounded transition-colors" title="Release seat">
              <UserMinus className="w-3.5 h-3.5" />
            </button>
          : <button onClick={() => setAllocateTarget(e)}
              className="text-ethara-muted hover:text-ethara-success p-1 rounded transition-colors" title="Allocate seat">
              <MapPin className="w-3.5 h-3.5" />
            </button>
        }
      </div>
    },
  ]

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-white">Employees</h2>
          <p className="text-ethara-muted text-sm mt-1">{data?.total?.toLocaleString() ?? '—'} total records</p>
        </div>
        <Button onClick={() => setShowCreate(true)}>
          <Plus className="w-4 h-4" /> Add Employee
        </Button>
      </div>

      {/* Filters */}
      <Card>
        <div className="flex flex-col sm:flex-row gap-3">
          <SearchBar value={search} onChange={v => { setSearch(v); setPage(1) }}
            placeholder="Search by name, email, code…" className="flex-1" />
          <select value={projectFilter ?? ''} onChange={e => { setProjectFilter(e.target.value ? Number(e.target.value) : undefined); setPage(1) }}
            className="ethara-input w-auto">
            <option value="">All Projects</option>
            {projects?.map(p => <option key={p.id} value={p.id}>{p.name}</option>)}
          </select>
          <select value={statusFilter} onChange={e => { setStatusFilter(e.target.value); setPage(1) }}
            className="ethara-input w-auto">
            <option value="">All Statuses</option>
            <option value="active">Active</option>
            <option value="inactive">Inactive</option>
            <option value="on_leave">On Leave</option>
          </select>
        </div>
      </Card>

      <Card>
        <Table columns={columns} data={data?.employees ?? []} loading={isLoading}
          emptyMessage="No employees found. Try adjusting your filters." />
        <Pagination page={page} total={data?.total ?? 0} pageSize={PAGE_SIZE} onChange={setPage} />
      </Card>

      {/* Create modal */}
      <EmployeeFormModal
        open={showCreate}
        onClose={() => setShowCreate(false)}
        title="Add Employee"
        projects={projects ?? []}
        onSubmit={async (d) => {
          await createMutation.mutateAsync(d)
          toast.success('Employee created successfully.')
          setShowCreate(false)
        }}
        loading={createMutation.isPending}
      />

      {/* Edit modal */}
      {editTarget && (
        <EmployeeFormModal
          open
          onClose={() => setEditTarget(null)}
          title="Edit Employee"
          projects={projects ?? []}
          initial={editTarget}
          onSubmit={async (d) => {
            await updateMutation.mutateAsync({ id: editTarget.id, data: d })
            toast.success('Employee updated.')
            setEditTarget(null)
          }}
          loading={updateMutation.isPending}
        />
      )}

      {/* Allocate seat modal */}
      {allocateTarget && (
        <AllocateSeatModal
          employee={allocateTarget}
          onClose={() => setAllocateTarget(null)}
          onAllocate={async (seatId) => {
            await allocateMutation.mutateAsync({ employee_id: allocateTarget.id, seat_id: seatId || undefined })
            toast.success(`Seat allocated to ${allocateTarget.name}.`)
            setAllocateTarget(null)
          }}
          loading={allocateMutation.isPending}
        />
      )}
    </div>
  )
}

// ── Sub-components ────────────────────────────────────────────────────────────

interface EmployeeFormModalProps {
  open: boolean
  onClose: () => void
  title: string
  projects: Array<{ id: number; name: string }>
  initial?: Employee
  onSubmit: (data: EmployeeCreateForm) => Promise<void>
  loading: boolean
}

function EmployeeFormModal({ open, onClose, title, projects, initial, onSubmit, loading }: EmployeeFormModalProps) {
  const [form, setForm] = useState<EmployeeCreateForm>({
    name: initial?.name ?? '',
    email: initial?.email ?? '',
    department: initial?.department ?? '',
    role: initial?.role ?? '',
    project_id: initial?.project_id,
    joining_date: initial?.joining_date ?? new Date().toISOString().split('T')[0],
    status: initial?.status ?? 'active',
  })
  const [error, setError] = useState('')

  const set = (k: keyof EmployeeCreateForm, v: unknown) => setForm(f => ({ ...f, [k]: v }))

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError('')
    try {
      await onSubmit(form)
    } catch (err: any) {
      setError(err?.response?.data?.detail ?? 'An error occurred.')
    }
  }

  return (
    <Modal open={open} onClose={onClose} title={title} size="md">
      <form onSubmit={handleSubmit} className="space-y-4">
        {error && <p className="text-ethara-error text-sm bg-ethara-error/10 px-3 py-2 rounded-lg border border-ethara-error/20">{error}</p>}
        <div className="grid grid-cols-2 gap-4">
          <div className="col-span-2">
            <label className="text-xs text-ethara-muted mb-1.5 block">Full Name *</label>
            <input className="ethara-input" value={form.name} onChange={e => set('name', e.target.value)} required />
          </div>
          <div className="col-span-2">
            <label className="text-xs text-ethara-muted mb-1.5 block">Email *</label>
            <input type="email" className="ethara-input" value={form.email} onChange={e => set('email', e.target.value)} required />
          </div>
          <div>
            <label className="text-xs text-ethara-muted mb-1.5 block">Department</label>
            <input className="ethara-input" value={form.department ?? ''} onChange={e => set('department', e.target.value)} />
          </div>
          <div>
            <label className="text-xs text-ethara-muted mb-1.5 block">Role</label>
            <input className="ethara-input" value={form.role ?? ''} onChange={e => set('role', e.target.value)} />
          </div>
          <div>
            <label className="text-xs text-ethara-muted mb-1.5 block">Project</label>
            <select className="ethara-input" value={form.project_id ?? ''} onChange={e => set('project_id', e.target.value ? Number(e.target.value) : undefined)}>
              <option value="">No Project</option>
              {projects.map(p => <option key={p.id} value={p.id}>{p.name}</option>)}
            </select>
          </div>
          <div>
            <label className="text-xs text-ethara-muted mb-1.5 block">Joining Date</label>
            <input type="date" className="ethara-input" value={form.joining_date ?? ''} onChange={e => set('joining_date', e.target.value)} />
          </div>
          <div>
            <label className="text-xs text-ethara-muted mb-1.5 block">Status</label>
            <select className="ethara-input" value={form.status} onChange={e => set('status', e.target.value as any)}>
              <option value="active">Active</option>
              <option value="inactive">Inactive</option>
              <option value="on_leave">On Leave</option>
            </select>
          </div>
        </div>
        <div className="flex gap-3 pt-2">
          <Button type="submit" loading={loading} className="flex-1 justify-center">Save</Button>
          <Button type="button" variant="secondary" onClick={onClose} className="flex-1 justify-center">Cancel</Button>
        </div>
      </form>
    </Modal>
  )
}

function AllocateSeatModal({ employee, onClose, onAllocate, loading }: {
  employee: Employee
  onClose: () => void
  onAllocate: (seatId: number | null) => Promise<void>
  loading: boolean
}) {
  const [seatId, setSeatId] = useState('')
  const [error, setError] = useState('')

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError('')
    try {
      await onAllocate(seatId ? Number(seatId) : null)
    } catch (err: any) {
      setError(err?.response?.data?.detail ?? 'Allocation failed.')
    }
  }

  return (
    <Modal open onClose={onClose} title="Allocate Seat" size="sm">
      <form onSubmit={handleSubmit} className="space-y-4">
        <p className="text-sm text-ethara-muted">
          Allocating seat for <span className="text-white font-medium">{employee.name}</span>
          {employee.project && <> — Project <span className="text-ethara-primary">{employee.project.name}</span></>}
        </p>
        {error && <p className="text-ethara-error text-sm bg-ethara-error/10 px-3 py-2 rounded-lg">{error}</p>}
        <div>
          <label className="text-xs text-ethara-muted mb-1.5 block">
            Seat ID (leave blank for auto-assign by proximity)
          </label>
          <input type="number" className="ethara-input" value={seatId}
            onChange={e => setSeatId(e.target.value)} placeholder="Auto-assign" />
        </div>
        <p className="text-xs text-ethara-muted">
          Auto-assign picks the best available seat near the employee's project team.
        </p>
        <div className="flex gap-3">
          <Button type="submit" loading={loading} className="flex-1 justify-center">Allocate</Button>
          <Button type="button" variant="secondary" onClick={onClose} className="flex-1 justify-center">Cancel</Button>
        </div>
      </form>
    </Modal>
  )
}
