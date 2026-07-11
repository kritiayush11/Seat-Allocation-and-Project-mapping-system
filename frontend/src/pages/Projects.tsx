import { useState } from 'react'
import { Plus, Users, Armchair, Edit2 } from 'lucide-react'
import { Card } from '../components/ui/Card'
import { Badge } from '../components/ui/Badge'
import { Button } from '../components/ui/Button'
import { Modal } from '../components/ui/Modal'
import { useToast } from '../components/ui/Toast'
import { useProjects, useCreateProject, useUpdateProject, useProjectEmployees } from '../hooks/useProjects'
import type { Project, ProjectCreateForm } from '../types'

export function Projects() {
  const [showCreate, setShowCreate] = useState(false)
  const [editTarget, setEditTarget] = useState<Project | null>(null)
  const [detailTarget, setDetailTarget] = useState<Project | null>(null)

  const toast = useToast()
  const { data: projects, isLoading } = useProjects(false)
  const createMutation = useCreateProject()
  const updateMutation = useUpdateProject()

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-white">Projects</h2>
          <p className="text-ethara-muted text-sm mt-1">{projects?.length ?? 0} projects</p>
        </div>
        <Button onClick={() => setShowCreate(true)}>
          <Plus className="w-4 h-4" /> New Project
        </Button>
      </div>

      {isLoading ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {[...Array(6)].map((_, i) => (
            <div key={i} className="h-40 bg-ethara-card rounded-xl animate-pulse border border-ethara-border" />
          ))}
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {projects?.map(p => (
            <Card key={p.id} hover onClick={() => setDetailTarget(p)}
              className="cursor-pointer group relative">
              <div className="flex items-start justify-between mb-3">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-ethara-primary/20 to-ethara-secondary/20 border border-ethara-primary/20 flex items-center justify-center">
                    <span className="text-ethara-primary font-bold text-sm">{p.name[0]}</span>
                  </div>
                  <div>
                    <h3 className="font-semibold text-white">{p.name}</h3>
                    {p.manager_name && (
                      <p className="text-xs text-ethara-muted">Lead: {p.manager_name}</p>
                    )}
                  </div>
                </div>
                <button
                  onClick={e => { e.stopPropagation(); setEditTarget(p) }}
                  className="opacity-0 group-hover:opacity-100 text-ethara-muted hover:text-white transition-all p-1"
                >
                  <Edit2 className="w-3.5 h-3.5" />
                </button>
              </div>
              {p.description && (
                <p className="text-xs text-ethara-muted mb-3 line-clamp-2">{p.description}</p>
              )}
              <div className="flex items-center justify-between">
                <div className="flex gap-3">
                  <div className="flex items-center gap-1.5 text-xs text-ethara-muted">
                    <Users className="w-3.5 h-3.5" />
                    <span>{p.employee_count} employees</span>
                  </div>
                  <div className="flex items-center gap-1.5 text-xs text-ethara-muted">
                    <Armchair className="w-3.5 h-3.5" />
                    <span>{p.occupied_seats} seats</span>
                  </div>
                </div>
                <Badge status={p.status} />
              </div>
              {p.employee_count > 0 && (
                <div className="mt-3 h-1.5 bg-ethara-hover rounded-full overflow-hidden">
                  <div
                    className="h-full bg-gradient-to-r from-ethara-primary to-ethara-secondary rounded-full"
                    style={{ width: `${Math.min(100, Math.round(p.occupied_seats / p.employee_count * 100))}%` }}
                  />
                </div>
              )}
            </Card>
          ))}
        </div>
      )}

      {/* Create modal */}
      <ProjectFormModal
        open={showCreate}
        onClose={() => setShowCreate(false)}
        title="New Project"
        onSubmit={async d => {
          await createMutation.mutateAsync(d)
          toast.success('Project created.')
          setShowCreate(false)
        }}
        loading={createMutation.isPending}
      />

      {/* Edit modal */}
      {editTarget && (
        <ProjectFormModal
          open
          onClose={() => setEditTarget(null)}
          title={`Edit — ${editTarget.name}`}
          initial={editTarget}
          onSubmit={async d => {
            await updateMutation.mutateAsync({ id: editTarget.id, data: d })
            toast.success('Project updated.')
            setEditTarget(null)
          }}
          loading={updateMutation.isPending}
        />
      )}

      {/* Detail modal */}
      {detailTarget && (
        <ProjectDetailModal project={detailTarget} onClose={() => setDetailTarget(null)} />
      )}
    </div>
  )
}

function ProjectFormModal({ open, onClose, title, initial, onSubmit, loading }: {
  open: boolean; onClose: () => void; title: string
  initial?: Project; onSubmit: (d: ProjectCreateForm) => Promise<void>; loading: boolean
}) {
  const [form, setForm] = useState<ProjectCreateForm>({
    name: initial?.name ?? '',
    description: initial?.description ?? '',
    manager_name: initial?.manager_name ?? '',
    status: initial?.status ?? 'active',
  })
  const [error, setError] = useState('')
  const set = (k: keyof ProjectCreateForm, v: unknown) => setForm(f => ({ ...f, [k]: v }))

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault(); setError('')
    try { await onSubmit(form) }
    catch (err: any) { setError(err?.response?.data?.detail ?? 'Error occurred.') }
  }

  return (
    <Modal open={open} onClose={onClose} title={title} size="sm">
      <form onSubmit={handleSubmit} className="space-y-4">
        {error && <p className="text-ethara-error text-sm bg-ethara-error/10 px-3 py-2 rounded-lg">{error}</p>}
        <div>
          <label className="text-xs text-ethara-muted mb-1.5 block">Project Name *</label>
          <input className="ethara-input" value={form.name} onChange={e => set('name', e.target.value)} required />
        </div>
        <div>
          <label className="text-xs text-ethara-muted mb-1.5 block">Description</label>
          <textarea className="ethara-input h-20 resize-none" value={form.description ?? ''} onChange={e => set('description', e.target.value)} />
        </div>
        <div>
          <label className="text-xs text-ethara-muted mb-1.5 block">Manager</label>
          <input className="ethara-input" value={form.manager_name ?? ''} onChange={e => set('manager_name', e.target.value)} />
        </div>
        <div>
          <label className="text-xs text-ethara-muted mb-1.5 block">Status</label>
          <select className="ethara-input" value={form.status} onChange={e => set('status', e.target.value as any)}>
            <option value="active">Active</option>
            <option value="inactive">Inactive</option>
            <option value="archived">Archived</option>
          </select>
        </div>
        <div className="flex gap-3">
          <Button type="submit" loading={loading} className="flex-1 justify-center">Save</Button>
          <Button type="button" variant="secondary" onClick={onClose} className="flex-1 justify-center">Cancel</Button>
        </div>
      </form>
    </Modal>
  )
}

function ProjectDetailModal({ project, onClose }: { project: Project; onClose: () => void }) {
  const { data: employees, isLoading } = useProjectEmployees(project.id)
  return (
    <Modal open onClose={onClose} title={project.name} size="lg">
      <div className="space-y-4">
        <div className="grid grid-cols-3 gap-3 text-center">
          <div className="bg-ethara-hover rounded-xl p-3">
            <p className="text-xl font-bold text-white">{project.employee_count}</p>
            <p className="text-xs text-ethara-muted mt-0.5">Employees</p>
          </div>
          <div className="bg-ethara-hover rounded-xl p-3">
            <p className="text-xl font-bold text-white">{project.occupied_seats}</p>
            <p className="text-xs text-ethara-muted mt-0.5">Seats Allocated</p>
          </div>
          <div className="bg-ethara-hover rounded-xl p-3">
            <p className="text-xl font-bold text-white">
              {project.employee_count > 0 ? Math.round(project.occupied_seats / project.employee_count * 100) : 0}%
            </p>
            <p className="text-xs text-ethara-muted mt-0.5">Allocation Rate</p>
          </div>
        </div>
        <div className="max-h-64 overflow-y-auto space-y-2">
          {isLoading
            ? [...Array(4)].map((_, i) => <div key={i} className="h-10 bg-ethara-hover rounded animate-pulse" />)
            : employees?.map(e => (
              <div key={e.id} className="flex items-center justify-between px-3 py-2 bg-ethara-hover rounded-lg">
                <div>
                  <p className="text-sm font-medium text-white">{e.name}</p>
                  <p className="text-xs text-ethara-muted">{e.role ?? e.department ?? '—'}</p>
                </div>
                {e.seat
                  ? <span className="text-xs text-ethara-success">F{e.seat.floor} {e.seat.zone} {e.seat.seat_number}</span>
                  : <span className="text-xs text-ethara-warning">No Seat</span>
                }
              </div>
            ))
          }
        </div>
      </div>
    </Modal>
  )
}
