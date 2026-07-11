import { useState } from 'react'
import { Plus, MapPin, Unlock } from 'lucide-react'
import { Card } from '../components/ui/Card'
import { Badge } from '../components/ui/Badge'
import { Button } from '../components/ui/Button'
import { Table, Pagination } from '../components/ui/Table'
import { Modal } from '../components/ui/Modal'
import { useToast } from '../components/ui/Toast'
import { useSeats, useCreateSeat, useAllocateSeat, useReleaseSeat } from '../hooks/useSeats'
import { useEmployees } from '../hooks/useEmployees'
import { useProjects } from '../hooks/useProjects'
import type { Seat, SeatCreateForm, AllocateForm } from '../types'

const PAGE_SIZE = 20

export function Seats() {
  const [floorFilter, setFloorFilter] = useState<number | undefined>()
  const [zoneFilter, setZoneFilter] = useState('')
  const [statusFilter, setStatusFilter] = useState('')
  const [page, setPage] = useState(1)
  const [showCreate, setShowCreate] = useState(false)
  const [allocateTarget, setAllocateTarget] = useState<Seat | null>(null)

  const toast = useToast()
  const { data, isLoading } = useSeats({
    floor: floorFilter,
    zone: zoneFilter || undefined,
    status: statusFilter || undefined,
    page,
    page_size: PAGE_SIZE,
  })
  const createMutation = useCreateSeat()
  const allocateMutation = useAllocateSeat()
  const releaseMutation = useReleaseSeat()

  const columns = [
    { key: 'seat_number', header: 'Seat', render: (s: Seat) =>
      <div className="flex items-center gap-2">
        <MapPin className="w-3.5 h-3.5 text-ethara-primary shrink-0" />
        <span className="font-mono text-sm font-medium">{s.seat_number}</span>
      </div> },
    { key: 'location', header: 'Location', render: (s: Seat) =>
      <span className="text-sm text-ethara-muted">
        Floor {s.floor} · Zone {s.zone} · {s.bay}
      </span> },
    { key: 'status', header: 'Status', render: (s: Seat) => <Badge status={s.status} /> },
    { key: 'occupant', header: 'Occupant', render: (s: Seat) =>
      s.current_allocation
        ? <div>
            <p className="text-sm font-medium">{s.current_allocation.employee_name}</p>
            <p className="text-xs text-ethara-muted">{s.current_allocation.project_name ?? '—'}</p>
          </div>
        : <span className="text-ethara-muted text-sm">—</span> },
    { key: 'alloc_date', header: 'Allocated', render: (s: Seat) =>
      s.current_allocation
        ? <span className="text-xs text-ethara-muted">{s.current_allocation.allocation_date}</span>
        : <span className="text-ethara-muted">—</span> },
    { key: 'actions', header: '', render: (s: Seat) =>
      <div className="flex gap-2" onClick={ev => ev.stopPropagation()}>
        {s.status === 'available' && (
          <button onClick={() => setAllocateTarget(s)}
            className="text-ethara-muted hover:text-ethara-success p-1 rounded transition-colors" title="Allocate">
            <Plus className="w-3.5 h-3.5" />
          </button>
        )}
        {s.status === 'occupied' && s.current_allocation && (
          <button onClick={() => {
            releaseMutation.mutate(s.current_allocation!.employee_id, {
              onSuccess: () => toast.success(`Seat ${s.seat_number} released.`),
              onError: () => toast.error('Release failed.'),
            })
          }} className="text-ethara-muted hover:text-ethara-error p-1 rounded transition-colors" title="Release">
            <Unlock className="w-3.5 h-3.5" />
          </button>
        )}
      </div>
    },
  ]

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-white">Seat Allocation</h2>
          <p className="text-ethara-muted text-sm mt-1">{data?.total?.toLocaleString() ?? '—'} total seats</p>
        </div>
        <Button onClick={() => setShowCreate(true)}>
          <Plus className="w-4 h-4" /> Add Seat
        </Button>
      </div>

      {/* Summary bar */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        {(['available','occupied','reserved','maintenance'] as const).map(s => {
          const count = data?.seats.filter(seat => seat.status === s).length ?? 0
          return (
            <button key={s}
              onClick={() => { setStatusFilter(statusFilter === s ? '' : s); setPage(1) }}
              className={`ethara-card text-left hover:border-ethara-primary/40 transition-all cursor-pointer ${statusFilter === s ? 'border-ethara-primary/60' : ''}`}>
              <p className="text-xs text-ethara-muted capitalize">{s}</p>
              <p className="text-xl font-bold text-white mt-1">{count}</p>
            </button>
          )
        })}
      </div>

      {/* Filters */}
      <Card>
        <div className="flex flex-wrap gap-3">
          <select value={floorFilter ?? ''} onChange={e => { setFloorFilter(e.target.value ? Number(e.target.value) : undefined); setPage(1) }}
            className="ethara-input w-auto">
            <option value="">All Floors</option>
            {[1,2,3,4,5].map(f => <option key={f} value={f}>Floor {f}</option>)}
          </select>
          <select value={zoneFilter} onChange={e => { setZoneFilter(e.target.value); setPage(1) }}
            className="ethara-input w-auto">
            <option value="">All Zones</option>
            {'ABCDEFGHIJ'.split('').map(z => <option key={z} value={z}>Zone {z}</option>)}
          </select>
          <select value={statusFilter} onChange={e => { setStatusFilter(e.target.value); setPage(1) }}
            className="ethara-input w-auto">
            <option value="">All Statuses</option>
            <option value="available">Available</option>
            <option value="occupied">Occupied</option>
            <option value="reserved">Reserved</option>
            <option value="maintenance">Maintenance</option>
          </select>
          {(floorFilter || zoneFilter || statusFilter) && (
            <Button variant="ghost" onClick={() => { setFloorFilter(undefined); setZoneFilter(''); setStatusFilter(''); setPage(1) }}>
              Clear filters
            </Button>
          )}
        </div>
      </Card>

      <Card>
        <Table columns={columns} data={data?.seats ?? []} loading={isLoading}
          emptyMessage="No seats found. Try adjusting filters or adding seats." />
        <Pagination page={page} total={data?.total ?? 0} pageSize={PAGE_SIZE} onChange={setPage} />
      </Card>

      {/* Create seat modal */}
      <CreateSeatModal
        open={showCreate}
        onClose={() => setShowCreate(false)}
        onSubmit={async (d) => {
          await createMutation.mutateAsync(d)
          toast.success('Seat created.')
          setShowCreate(false)
        }}
        loading={createMutation.isPending}
      />

      {/* Allocate modal */}
      {allocateTarget && (
        <AllocateToSeatModal
          seat={allocateTarget}
          onClose={() => setAllocateTarget(null)}
          onAllocate={async (form) => {
            await allocateMutation.mutateAsync(form)
            toast.success(`Seat ${allocateTarget.seat_number} allocated.`)
            setAllocateTarget(null)
          }}
          loading={allocateMutation.isPending}
        />
      )}
    </div>
  )
}

function CreateSeatModal({ open, onClose, onSubmit, loading }: {
  open: boolean; onClose: () => void
  onSubmit: (d: SeatCreateForm) => Promise<void>; loading: boolean
}) {
  const [form, setForm] = useState<SeatCreateForm>({ floor: 1, zone: 'A', bay: 'Bay-1', seat_number: '' })
  const [error, setError] = useState('')
  const set = (k: keyof SeatCreateForm, v: unknown) => setForm(f => ({ ...f, [k]: v }))

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault(); setError('')
    try { await onSubmit(form) }
    catch (err: any) { setError(err?.response?.data?.detail ?? 'Failed.') }
  }

  return (
    <Modal open={open} onClose={onClose} title="Add Seat" size="sm">
      <form onSubmit={handleSubmit} className="space-y-4">
        {error && <p className="text-ethara-error text-sm bg-ethara-error/10 px-3 py-2 rounded-lg">{error}</p>}
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="text-xs text-ethara-muted mb-1.5 block">Floor</label>
            <select className="ethara-input" value={form.floor} onChange={e => set('floor', Number(e.target.value))}>
              {[1,2,3,4,5].map(f => <option key={f} value={f}>Floor {f}</option>)}
            </select>
          </div>
          <div>
            <label className="text-xs text-ethara-muted mb-1.5 block">Zone</label>
            <select className="ethara-input" value={form.zone} onChange={e => set('zone', e.target.value)}>
              {'ABCDEFGHIJ'.split('').map(z => <option key={z}>{z}</option>)}
            </select>
          </div>
          <div>
            <label className="text-xs text-ethara-muted mb-1.5 block">Bay</label>
            <input className="ethara-input" value={form.bay} onChange={e => set('bay', e.target.value)} required />
          </div>
          <div>
            <label className="text-xs text-ethara-muted mb-1.5 block">Seat Number *</label>
            <input className="ethara-input" value={form.seat_number} onChange={e => set('seat_number', e.target.value)} required placeholder="e.g. B4-23" />
          </div>
        </div>
        <div className="flex gap-3">
          <Button type="submit" loading={loading} className="flex-1 justify-center">Create</Button>
          <Button type="button" variant="secondary" onClick={onClose} className="flex-1 justify-center">Cancel</Button>
        </div>
      </form>
    </Modal>
  )
}

function AllocateToSeatModal({ seat, onClose, onAllocate, loading }: {
  seat: Seat; onClose: () => void
  onAllocate: (form: AllocateForm) => Promise<void>; loading: boolean
}) {
  const [empId, setEmpId] = useState('')
  const [error, setError] = useState('')
  const { data: empData } = useEmployees({ has_seat: false, page_size: 200 })

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault(); setError('')
    if (!empId) { setError('Please select an employee.'); return }
    try { await onAllocate({ employee_id: Number(empId), seat_id: seat.id }) }
    catch (err: any) { setError(err?.response?.data?.detail ?? 'Allocation failed.') }
  }

  return (
    <Modal open onClose={onClose} title={`Allocate Seat ${seat.seat_number}`} size="sm">
      <form onSubmit={handleSubmit} className="space-y-4">
        <p className="text-sm text-ethara-muted">Floor {seat.floor} · Zone {seat.zone} · {seat.bay}</p>
        {error && <p className="text-ethara-error text-sm bg-ethara-error/10 px-3 py-2 rounded-lg">{error}</p>}
        <div>
          <label className="text-xs text-ethara-muted mb-1.5 block">Select Employee (unallocated)</label>
          <select className="ethara-input" value={empId} onChange={e => setEmpId(e.target.value)} required>
            <option value="">Choose employee…</option>
            {empData?.employees.map(e => (
              <option key={e.id} value={e.id}>{e.name} — {e.project?.name ?? 'No Project'}</option>
            ))}
          </select>
        </div>
        <div className="flex gap-3">
          <Button type="submit" loading={loading} className="flex-1 justify-center">Allocate</Button>
          <Button type="button" variant="secondary" onClick={onClose} className="flex-1 justify-center">Cancel</Button>
        </div>
      </form>
    </Modal>
  )
}
