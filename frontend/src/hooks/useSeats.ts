import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { seatApi } from '../services/api'
import type { SeatCreateForm, AllocateForm } from '../types'

export function useSeats(params?: Parameters<typeof seatApi.list>[0]) {
  return useQuery({
    queryKey: ['seats', params],
    queryFn: () => seatApi.list(params),
  })
}

export function useAvailableSeats(params?: { floor?: number; zone?: string }) {
  return useQuery({
    queryKey: ['seats', 'available', params],
    queryFn: () => seatApi.getAvailable(params),
  })
}

export function useSuggestedSeats(project_id?: number) {
  return useQuery({
    queryKey: ['seats', 'suggest', project_id],
    queryFn: () => seatApi.suggest(project_id!, 5),
    enabled: !!project_id,
  })
}

export function useCreateSeat() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: SeatCreateForm) => seatApi.create(data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['seats'] })
      qc.invalidateQueries({ queryKey: ['dashboard'] })
    },
  })
}

export function useAllocateSeat() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: AllocateForm) => seatApi.allocate(data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['seats'] })
      qc.invalidateQueries({ queryKey: ['employees'] })
      qc.invalidateQueries({ queryKey: ['dashboard'] })
    },
  })
}

export function useReleaseSeat() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (employee_id: number) => seatApi.release(employee_id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['seats'] })
      qc.invalidateQueries({ queryKey: ['employees'] })
      qc.invalidateQueries({ queryKey: ['dashboard'] })
    },
  })
}
