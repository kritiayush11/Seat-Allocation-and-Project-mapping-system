import { createContext, useContext, useState, useEffect, ReactNode } from 'react'
import { BrowserRouter, Routes, Route, Navigate, Outlet } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { Layout } from './components/layout/Layout'
import { ToastProvider } from './components/ui/Toast'
import { Dashboard } from './pages/Dashboard'
import { Employees } from './pages/Employees'
import { Seats } from './pages/Seats'
import { Projects } from './pages/Projects'
import { AIAssistant } from './pages/AIAssistant'
import { NotFound } from './pages/NotFound'
import { Login } from './pages/Login'
import { Signup } from './pages/Signup'
import { Home } from './pages/Home'
import { authApi } from './services/api'
import type { User } from './types'

// ── Auth Context ──────────────────────────────────────────────────────────────

interface AuthContextType {
  user: User | null
  loading: boolean
  logout: () => void
}

const AuthContext = createContext<AuthContextType>({
  user: null,
  loading: true,
  logout: () => {},
})

export const useAuth = () => useContext(AuthContext)

function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    async function loadUser() {
      const token = localStorage.getItem('token')
      if (!token) {
        setLoading(false)
        return
      }

      try {
        const userData = await authApi.me()
        setUser(userData)
      } catch (err) {
        console.error('Failed to load user session', err)
        localStorage.removeItem('token')
      } finally {
        setLoading(false)
      }
    }
    loadUser()
  }, [])

  const logout = () => {
    localStorage.removeItem('token')
    setUser(null)
    window.location.href = '/login'
  }

  return (
    <AuthContext.Provider value={{ user, loading, logout }}>
      {children}
    </AuthContext.Provider>
  )
}

// ── Protected Route Wrapper ───────────────────────────────────────────────────

function ProtectedRoute() {
  const { user, loading } = useAuth()

  if (loading) {
    return (
      <div className="min-h-screen bg-ethara-bg flex items-center justify-center">
        {/* Spinner */}
        <div className="animate-spin rounded-full h-10 w-10 border-t-2 border-b-2 border-ethara-primary"></div>
      </div>
    )
  }

  if (!user) {
    return <Navigate to="/login" replace />
  }

  return <Outlet />
}

// ── Main App Component ────────────────────────────────────────────────────────

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      staleTime: 10_000,
    },
  },
})

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <ToastProvider>
        <AuthProvider>
          <BrowserRouter>
            <Routes>
              {/* Public Routes */}
              <Route path="/" element={<Home />} />
              <Route path="/login" element={<Login />} />
              <Route path="/signup" element={<Signup />} />

              {/* Protected Routes */}
              <Route element={<ProtectedRoute />}>
                <Route element={<Layout />}>
                  <Route path="/dashboard" element={<Dashboard />} />
                  <Route path="/employees" element={<Employees />} />
                  <Route path="/seats"     element={<Seats />} />
                  <Route path="/projects"  element={<Projects />} />
                  <Route path="/ai"        element={<AIAssistant />} />
                  <Route path="*"          element={<NotFound />} />
                </Route>
              </Route>
            </Routes>
          </BrowserRouter>
        </AuthProvider>
      </ToastProvider>
    </QueryClientProvider>
  )
}
