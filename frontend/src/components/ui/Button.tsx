import clsx from 'clsx'
import type { ReactNode, ButtonHTMLAttributes } from 'react'

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'ghost' | 'danger'
  size?: 'sm' | 'md' | 'lg'
  loading?: boolean
  children: ReactNode
}

const variants = {
  primary:   'ethara-btn-primary',
  secondary: 'ethara-btn-secondary',
  ghost:     'ethara-btn-ghost',
  danger:    'bg-ethara-error/10 hover:bg-ethara-error/20 text-ethara-error border border-ethara-error/30 px-4 py-2.5 rounded-lg transition-all duration-200 text-sm flex items-center gap-2 cursor-pointer',
}

const sizes = {
  sm: 'px-3 py-1.5 text-xs',
  md: '',
  lg: 'px-6 py-3 text-base',
}

export function Button({
  variant = 'primary',
  size = 'md',
  loading,
  children,
  className,
  disabled,
  ...props
}: ButtonProps) {
  return (
    <button
      className={clsx(variants[variant], size !== 'md' && sizes[size], className)}
      disabled={disabled || loading}
      {...props}
    >
      {loading && (
        <svg className="animate-spin h-4 w-4" fill="none" viewBox="0 0 24 24">
          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8z" />
        </svg>
      )}
      {children}
    </button>
  )
}
