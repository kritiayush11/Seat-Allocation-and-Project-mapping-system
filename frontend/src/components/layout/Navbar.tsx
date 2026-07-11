import { Menu, Database } from 'lucide-react'
import { useState } from 'react'
import { seedApi } from '../../services/api'
import { useToast } from '../ui/Toast'
import { useAuth } from '../../App'

interface NavbarProps {
  onMenuClick: () => void
  title: string
}

export function Navbar({ onMenuClick, title }: NavbarProps) {
  const [seeding, setSeeding] = useState(false)
  const toast = useToast()
  const { user, logout } = useAuth()

  async function handleSeed() {
    setSeeding(true)
    try {
      const result = await seedApi.seed()
      if (result.status === 'already_seeded') {
        toast.success('Database already has data — no action needed.')
      } else {
        toast.success(`Seeded! ${result.employees} employees, ${result.seats} seats.`)
      }
    } catch {
      toast.error('Seeding failed. Is the backend running?')
    } finally {
      setSeeding(false)
    }
  }

  return (
    <header className="flex items-center justify-between px-6 py-4 border-b border-ethara-border bg-ethara-card/50 backdrop-blur-sm sticky top-0 z-20">
      <div className="flex items-center gap-4">
        <button
          onClick={onMenuClick}
          className="lg:hidden text-ethara-muted hover:text-white transition-colors"
        >
          <Menu className="w-5 h-5" />
        </button>
        <h1 className="text-base font-semibold text-white">{title}</h1>
      </div>

      <div className="flex items-center gap-3">
        <button
          onClick={handleSeed}
          disabled={seeding}
          className="ethara-btn-secondary text-xs gap-1.5 py-2"
          title="Seed database with demo data"
        >
          <Database className={`w-3.5 h-3.5 ${seeding ? 'animate-pulse' : ''}`} />
          {seeding ? 'Seeding…' : 'Seed Data'}
        </button>

        {user && (
          <div className="flex items-center gap-3 ml-2 border-l border-ethara-border pl-3">
            <span className="text-sm text-ethara-text-secondary hidden sm:inline" title={user.email}>
              {user.username}
            </span>
            <div className="w-8 h-8 rounded-full bg-gradient-to-br from-ethara-primary to-ethara-secondary flex items-center justify-center text-xs font-bold text-white select-none">
              {user.username[0].toUpperCase()}
            </div>
            <button
              onClick={logout}
              className="text-xs text-ethara-error/80 hover:text-ethara-error transition-colors px-2.5 py-1.5 border border-ethara-error/20 hover:border-ethara-error/40 rounded bg-ethara-error/5 cursor-pointer"
            >
              Logout
            </button>
          </div>
        )}
      </div>
    </header>
  )
}
