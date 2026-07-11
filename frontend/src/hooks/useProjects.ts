import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { projectApi } from '../services/api'
import type { ProjectCreateForm } from '../types'

export function useProjects(activeOnly = true) {
  return useQuery({
    queryKey: ['projects', { activeOnly }],
    queryFn: () => projectApi.list(activeOnly),
  })
}

export function useProject(id: number) {
  return useQuery({
    queryKey: ['projects', id],
    queryFn: () => projectApi.get(id),
    enabled: !!id,
  })
}

export function useProjectEmployees(id: number) {
  return useQuery({
    queryKey: ['projects', id, 'employees'],
    queryFn: () => projectApi.getEmployees(id),
    enabled: !!id,
  })
}

export function useCreateProject() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: ProjectCreateForm) => projectApi.create(data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['projects'] }),
  })
}

export function useUpdateProject() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, data }: { id: number; data: Partial<ProjectCreateForm> }) =>
      projectApi.update(id, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['projects'] }),
  })
}
