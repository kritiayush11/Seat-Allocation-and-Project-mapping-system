import clsx from 'clsx'

interface BadgeProps {
  status: string
  className?: string
}

const statusMap: Record<string, string> = {
  available:   'status-available',
  occupied:    'status-occupied',
  reserved:    'status-reserved',
  maintenance: 'status-maintenance',
  active:      'status-active',
  inactive:    'status-inactive',
  on_leave:    'text-ethara-warning bg-ethara-warning/10 border border-ethara-warning/20',
  terminated:  'status-inactive',
  archived:    'status-inactive',
}

export function Badge({ status, className }: BadgeProps) {
  return (
    <span className={clsx(
      'inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium capitalize',
      statusMap[status] ?? 'text-ethara-muted bg-ethara-muted/10 border border-ethara-muted/20',
      className
    )}>
      {status.replace('_', ' ')}
    </span>
  )
}
