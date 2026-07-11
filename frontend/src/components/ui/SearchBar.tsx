import { Search } from 'lucide-react'
import clsx from 'clsx'

interface SearchBarProps {
  value: string
  onChange: (v: string) => void
  placeholder?: string
  className?: string
}

export function SearchBar({ value, onChange, placeholder = 'Search...', className }: SearchBarProps) {
  return (
    <div className={clsx('relative', className)}>
      <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-ethara-muted" />
      <input
        type="text"
        value={value}
        onChange={e => onChange(e.target.value)}
        placeholder={placeholder}
        className="ethara-input pl-9"
      />
    </div>
  )
}
