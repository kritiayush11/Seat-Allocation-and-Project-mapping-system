import type { ReactNode } from 'react'
import clsx from 'clsx'

interface Column<T> {
  key: string
  header: string
  render?: (row: T) => ReactNode
  className?: string
}

interface TableProps<T extends { id: number }> {
  columns: Column<T>[]
  data: T[]
  loading?: boolean
  emptyMessage?: string
  onRowClick?: (row: T) => void
}

export function Table<T extends { id: number }>({
  columns, data, loading, emptyMessage = 'No records found', onRowClick,
}: TableProps<T>) {
  if (loading) {
    return (
      <div className="w-full">
        {[...Array(5)].map((_, i) => (
          <div key={i} className="h-12 bg-ethara-hover/50 rounded-lg mb-2 animate-pulse" />
        ))}
      </div>
    )
  }

  if (!data.length) {
    return (
      <div className="text-center py-16 text-ethara-muted">
        <div className="text-4xl mb-3">🪑</div>
        <p>{emptyMessage}</p>
      </div>
    )
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-ethara-border">
            {columns.map(col => (
              <th key={col.key} className={clsx(
                'text-left py-3 px-4 text-ethara-muted font-medium text-xs uppercase tracking-wider',
                col.className
              )}>
                {col.header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {data.map(row => (
            <tr
              key={row.id}
              onClick={() => onRowClick?.(row)}
              className={clsx(
                'border-b border-ethara-border/50 transition-colors duration-150',
                onRowClick ? 'hover:bg-ethara-hover cursor-pointer' : 'hover:bg-ethara-hover/30'
              )}
            >
              {columns.map(col => (
                <td key={col.key} className={clsx('py-3.5 px-4 text-white', col.className)}>
                  {col.render
                    ? col.render(row)
                    : String((row as Record<string, unknown>)[col.key] ?? '—')}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

// Pagination component
interface PaginationProps {
  page: number
  total: number
  pageSize: number
  onChange: (page: number) => void
}

export function Pagination({ page, total, pageSize, onChange }: PaginationProps) {
  const totalPages = Math.ceil(total / pageSize)
  if (totalPages <= 1) return null

  return (
    <div className="flex items-center justify-between mt-4 pt-4 border-t border-ethara-border">
      <p className="text-sm text-ethara-muted">
        Showing {(page - 1) * pageSize + 1}–{Math.min(page * pageSize, total)} of {total}
      </p>
      <div className="flex gap-2">
        <button
          onClick={() => onChange(page - 1)}
          disabled={page <= 1}
          className="ethara-btn-secondary disabled:opacity-40 disabled:cursor-not-allowed px-3 py-1.5 text-xs"
        >
          Previous
        </button>
        <span className="flex items-center px-3 text-sm text-white">
          {page} / {totalPages}
        </span>
        <button
          onClick={() => onChange(page + 1)}
          disabled={page >= totalPages}
          className="ethara-btn-secondary disabled:opacity-40 disabled:cursor-not-allowed px-3 py-1.5 text-xs"
        >
          Next
        </button>
      </div>
    </div>
  )
}
