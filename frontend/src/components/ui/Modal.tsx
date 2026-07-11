import { X } from 'lucide-react'
import type { ReactNode } from 'react'
import clsx from 'clsx'

interface ModalProps {
  open: boolean
  onClose: () => void
  title: string
  children: ReactNode
  size?: 'sm' | 'md' | 'lg'
}

const sizes = { sm: 'max-w-md', md: 'max-w-xl', lg: 'max-w-2xl' }

export function Modal({ open, onClose, title, children, size = 'md' }: ModalProps) {
  if (!open) return null
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/70 backdrop-blur-sm"
        onClick={onClose}
      />
      {/* Panel */}
      <div className={clsx(
        'relative w-full bg-ethara-card border border-ethara-border rounded-2xl',
        'shadow-2xl shadow-black/50 animate-slide-up',
        sizes[size]
      )}>
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-ethara-border">
          <h2 className="text-lg font-semibold text-white">{title}</h2>
          <button
            onClick={onClose}
            className="text-ethara-muted hover:text-white transition-colors p-1 rounded-lg hover:bg-ethara-hover"
          >
            <X className="w-5 h-5" />
          </button>
        </div>
        {/* Body */}
        <div className="p-6">{children}</div>
      </div>
    </div>
  )
}
