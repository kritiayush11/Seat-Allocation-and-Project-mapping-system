import { useState } from 'react'
import { Outlet, useLocation } from 'react-router-dom'
import { Sidebar } from './Sidebar'
import { Navbar } from './Navbar'

const titles: Record<string, string> = {
  '/dashboard': 'Dashboard',
  '/employees': 'Employee Management',
  '/seats':     'Seat Allocation',
  '/projects':  'Project Mapping',
  '/ai':        'AI Assistant',
}

export function Layout() {
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const { pathname } = useLocation()
  const title = titles[pathname] ?? 'Ethara'

  return (
    <div className="flex h-screen overflow-hidden bg-ethara-bg">
      {/* Hexagonal background pattern */}
      <div className="fixed inset-0 bg-hex-pattern opacity-30 pointer-events-none" />

      <Sidebar open={sidebarOpen} onClose={() => setSidebarOpen(false)} />

      <div className="flex flex-col flex-1 min-w-0 overflow-hidden">
        <Navbar onMenuClick={() => setSidebarOpen(true)} title={title} />
        <main className="flex-1 overflow-y-auto p-6">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
