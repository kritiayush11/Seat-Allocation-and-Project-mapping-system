import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { employeeApi } from '../services/api'
import type { EmployeeCreateForm } from '../types'

export function useEmployees(params?: Parameters<typeof employeeApi.list>[0]) {
  return useQuery({
    queryKey: ['employees', params],
    queryFn: () => employeeApi.list(params),
  })
}

export function useEmployee(id: number) {
  return useQuery({
    queryKey: ['employees', id],
    queryFn: () => employeeApi.get(id),
    enabled: !!id,
  })
}

export function useCreateEmployee() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: EmployeeCreateForm) => employeeApi.create(data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['employees'] }),
  })
}

export function useUpdateEmployee() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, data }: { id: number; data: Partial<EmployeeCreateForm> }) =>
      employeeApi.update(id, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['employees'] }),
  })
}

export function useDeactivateEmployee() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: number) => employeeApi.deactivate(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['employees'] })
      qc.invalidateQueries({ queryKey: ['dashboard'] })
    },
  })
}
