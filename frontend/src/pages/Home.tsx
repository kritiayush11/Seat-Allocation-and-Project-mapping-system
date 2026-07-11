import { Link, useNavigate } from 'react-router-dom'
import { ArrowRight, Sparkles, Briefcase, UserPlus, MapPin } from 'lucide-react'
import { useAuth } from '../App'

export function Home() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()

  // Mock seat grid matching the image layout (8x5 grid, 40 seats)
  // 'available' (green), 'occupied' (purple), 'reserved' (yellow), 'maintenance' (slate)
  const seatGrid = [
    'available', 'occupied', 'occupied', 'occupied', 'occupied', 'occupied', 'occupied', 'available',
    'occupied', 'occupied', 'occupied', 'reserved', 'occupied', 'occupied', 'available', 'occupied',
    'occupied', 'occupied', 'occupied', 'occupied', 'occupied', 'available', 'reserved', 'occupied',
    'occupied', 'occupied', 'occupied', 'occupied', 'available', 'occupied', 'occupied', 'occupied',
    'occupied', 'reserved', 'occupied', 'available', 'occupied', 'occupied', 'occupied', 'occupied'
  ]

  const getSeatColor = (status: string) => {
    switch (status) {
      case 'available':
        return 'bg-emerald-500/20 border border-emerald-500/30'
      case 'reserved':
        return 'bg-amber-500/20 border border-amber-500/30'
      case 'occupied':
        return 'bg-fuchsia-950/40 border border-fuchsia-500/20'
      default:
        return 'bg-slate-800/40 border border-slate-700/20'
    }
  }

  return (
    <div className="min-h-screen bg-ethara-bg text-white relative overflow-x-hidden font-sans">
      {/* Background hexagon pattern & radial gradient spots */}
      <div className="fixed inset-0 bg-hex-pattern opacity-25 pointer-events-none z-0" />
      <div className="absolute top-[-10%] right-[-10%] w-[50vw] h-[50vw] bg-ethara-secondary/10 rounded-full blur-[120px] pointer-events-none" />
      <div className="absolute bottom-[-10%] left-[-10%] w-[50vw] h-[50vw] bg-ethara-primary/10 rounded-full blur-[120px] pointer-events-none" />

      {/* ── Navbar ───────────────────────────────────────────────────────────── */}
      <header className="relative z-10 max-w-7xl mx-auto px-6 py-6 flex items-center justify-between">
        {/* Logo */}
        <Link to="/" className="flex items-center select-none">
          <img src="/logo.png" alt="Ethara.Ai" className="h-8 object-contain" />
        </Link>

        {/* Center Pill Navigation */}
        <nav className="hidden md:flex items-center bg-[#12121f]/60 border border-white/5 px-2 py-1.5 rounded-full backdrop-blur-md">
          <Link to="/dashboard" className="px-5 py-2 text-sm font-medium text-ethara-muted hover:text-white transition-colors">
            Dashboard
          </Link>
          <Link to="/employees" className="px-5 py-2 text-sm font-medium text-ethara-muted hover:text-white transition-colors">
            Employees
          </Link>
          <Link to="/seats" className="px-5 py-2 text-sm font-medium text-ethara-muted hover:text-white transition-colors">
            Seats
          </Link>
          <Link to="/ai" className="px-5 py-2 text-sm font-medium text-ethara-muted hover:text-white transition-colors">
            Assistant
          </Link>
        </nav>

        {/* Actions Button */}
        <div className="flex items-center gap-4">
          {user ? (
            <div className="flex items-center gap-4">
              <span className="text-sm text-ethara-muted hidden lg:inline">
                Hi, {user.username}
              </span>
              <button
                onClick={logout}
                className="px-5 py-2.5 rounded-full border border-ethara-error/20 hover:border-ethara-error/40 bg-ethara-error/5 hover:bg-ethara-error/10 text-xs font-semibold text-white transition-all cursor-pointer"
              >
                Sign Out
              </button>
            </div>
          ) : (
            <Link
              to="/login"
              className="px-6 py-2.5 rounded-full border border-white/10 hover:border-white/20 bg-white/5 hover:bg-white/10 text-sm font-medium text-white transition-all"
            >
              Sign In
            </Link>
          )}
        </div>
      </header>

      {/* ── Hero Section ──────────────────────────────────────────────────────── */}
      <main className="relative z-10 max-w-7xl mx-auto px-6 pt-12 pb-24 grid grid-cols-1 lg:grid-cols-12 gap-16 items-center">
        {/* Hero Left Content */}
        <div className="lg:col-span-6 space-y-8">
          <div className="space-y-4">
            <h1 className="text-5xl md:text-6xl font-extrabold tracking-tight leading-[1.1] text-white">
              Every seat. <br />
              <span className="bg-gradient-to-r from-ethara-primary to-ethara-secondary bg-clip-text text-transparent italic font-serif font-normal">
                Every project.
              </span> <br />
              One glance.
            </h1>
            <p className="text-lg text-ethara-muted font-normal leading-relaxed max-w-xl pt-2">
              Ethara's seat-allocation & project-mapping system for 5,000+ employees. Find where anyone sits, which project they're on, and allocate new joiners with AI-powered assistance.
            </p>
          </div>

          <div className="flex flex-col sm:flex-row gap-4 pt-4">
            <button
              onClick={() => navigate('/dashboard')}
              className="px-8 py-4 rounded-xl bg-gradient-to-r from-ethara-secondary to-ethara-primary hover:opacity-95 text-white font-semibold flex items-center justify-center gap-2 shadow-lg shadow-ethara-primary/20 hover:shadow-ethara-primary/30 transition-all duration-300 group cursor-pointer"
            >
              Open Dashboard
              <ArrowRight className="w-4 h-4 transition-transform group-hover:translate-x-1" />
            </button>
            <button
              onClick={() => navigate('/ai')}
              className="px-8 py-4 rounded-xl border border-white/5 hover:border-white/10 bg-[#12121f]/50 hover:bg-[#1e1e3a]/50 text-white font-semibold flex items-center justify-center gap-2 transition-all cursor-pointer"
            >
              <Sparkles className="w-4 h-4 text-ethara-primary" />
              Ask the Assistant
            </button>
          </div>
        </div>

        {/* Hero Right Snapshot Visual */}
        <div className="lg:col-span-6 flex justify-center lg:justify-end">
          <div className="w-full max-w-lg bg-[#12121f]/60 border border-white/5 rounded-2xl p-8 backdrop-blur-md shadow-2xl relative">
            <div className="space-y-6">
              {/* Snapshot Title */}
              <div>
                <p className="text-[10px] font-bold tracking-widest text-ethara-primary uppercase">
                  Live Snapshot
                </p>
              </div>

              {/* Statistics Grid */}
              <div className="grid grid-cols-2 gap-4">
                <div className="p-4 rounded-xl bg-white/[0.02] border border-white/5">
                  <p className="text-xs text-ethara-muted mb-1">EMPLOYEES</p>
                  <p className="text-3xl font-extrabold text-white">5,000+</p>
                </div>
                <div className="p-4 rounded-xl bg-white/[0.02] border border-white/5">
                  <p className="text-xs text-ethara-muted mb-1">TOTAL SEATS</p>
                  <p className="text-3xl font-extrabold text-white">5,500+</p>
                </div>
                <div className="p-4 rounded-xl bg-white/[0.02] border border-white/5">
                  <p className="text-xs text-ethara-muted mb-1">OCCUPANCY</p>
                  <p className="text-3xl font-extrabold text-white">68.8%</p>
                </div>
                <div className="p-4 rounded-xl bg-white/[0.02] border border-white/5">
                  <p className="text-xs text-ethara-muted mb-1">PROJECTS</p>
                  <p className="text-3xl font-extrabold text-white">11</p>
                </div>
              </div>

              {/* Mini Seat Matrix Grid */}
              <div className="pt-2">
                <div className="grid grid-cols-8 gap-2.5 max-w-xs mx-auto">
                  {seatGrid.map((status, index) => (
                    <div
                      key={index}
                      className={`w-[26px] h-[26px] rounded-[6px] transition-colors duration-300 ${getSeatColor(
                        status
                      )}`}
                      title={`Seat status: ${status}`}
                    />
                  ))}
                </div>
              </div>
            </div>
          </div>
        </div>
      </main>

      {/* ── Bottom Feature Cards ─────────────────────────────────────────────── */}
      <section className="relative z-10 border-t border-white/5 bg-[#12121f]/30 py-20">
        <div className="max-w-7xl mx-auto px-6 grid grid-cols-1 md:grid-cols-3 gap-8">
          {/* Card 1: Project Mapping */}
          <div className="p-8 rounded-2xl bg-white/[0.02] border border-white/5 hover:border-ethara-primary/20 transition-all duration-300 space-y-4">
            <div className="w-10 h-10 rounded-lg bg-ethara-primary/10 border border-ethara-primary/20 flex items-center justify-center text-ethara-primary">
              <Briefcase className="w-5 h-5" />
            </div>
            <h3 className="text-lg font-bold text-white uppercase tracking-wider text-xs">
              Project Mapping
            </h3>
            <p className="text-sm text-ethara-muted leading-relaxed">
              Track which project every employee is on — Indigo, Indreed, Mydreed, and 8 more. Spot team co-locations in a single click.
            </p>
          </div>

          {/* Card 2: New Joiners */}
          <div className="p-8 rounded-2xl bg-white/[0.02] border border-white/5 hover:border-ethara-primary/20 transition-all duration-300 space-y-4">
            <div className="w-10 h-10 rounded-lg bg-ethara-primary/10 border border-ethara-primary/20 flex items-center justify-center text-ethara-primary">
              <UserPlus className="w-5 h-5" />
            </div>
            <h3 className="text-lg font-bold text-white uppercase tracking-wider text-xs">
              New Joiners
            </h3>
            <p className="text-sm text-ethara-muted leading-relaxed">
              Auto-suggest seats near the project team using proximity-based greedy algorithms. Prevent co-location friction.
            </p>
          </div>

          {/* Card 3: Floor Insights */}
          <div className="p-8 rounded-2xl bg-white/[0.02] border border-white/5 hover:border-ethara-primary/20 transition-all duration-300 space-y-4">
            <div className="w-10 h-10 rounded-lg bg-ethara-primary/10 border border-ethara-primary/20 flex items-center justify-center text-ethara-primary">
              <MapPin className="w-5 h-5" />
            </div>
            <h3 className="text-lg font-bold text-white uppercase tracking-wider text-xs">
              Floor Insights
            </h3>
            <p className="text-sm text-ethara-muted leading-relaxed">
              Live utilization by floor, zone and bay. Never lose track of office space capacity or seat maintenance needs.
            </p>
          </div>
        </div>
      </section>
    </div>
  )
}
