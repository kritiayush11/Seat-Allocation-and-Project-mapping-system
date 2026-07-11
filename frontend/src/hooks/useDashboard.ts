import { useQuery } from '@tanstack/react-query'
import { dashboardApi } from '../services/api'

export function useDashboardSummary() {
  return useQuery({
    queryKey: ['dashboard', 'summary'],
    queryFn: dashboardApi.summary,
    refetchInterval: 30_000,
  })
}

export function useProjectUtilization() {
  return useQuery({
    queryKey: ['dashboard', 'project-utilization'],
    queryFn: dashboardApi.projectUtilization,
    refetchInterval: 30_000,
  })
}

export function useFloorUtilization() {
  return useQuery({
    queryKey: ['dashboard', 'floor-utilization'],
    queryFn: dashboardApi.floorUtilization,
    refetchInterval: 30_000,
  })
}
