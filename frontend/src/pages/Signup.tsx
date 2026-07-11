import { useState, FormEvent } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { authApi } from '../services/api'
import { Card, CardHeader, CardTitle } from '../components/ui/Card'
import { Button } from '../components/ui/Button'
import { useToast } from '../components/ui/Toast'

export function Signup() {
  const [username, setUsername] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const navigate = useNavigate()
  const toast = useToast()

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    setError('')

    if (password !== confirmPassword) {
      setError('Passwords do not match')
      return
    }

    setLoading(true)

    try {
      await authApi.signup({
        username,
        email,
        password,
      })

      toast.success('Admin account created! Please log in.')
      navigate('/login')
    } catch (err: any) {
      console.error(err)
      setError(
        err.response?.data?.detail || 
        'Registration failed. Please make sure the username/email are unique.'
      )
      toast.error('Registration failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-ethara-bg p-4 relative overflow-hidden">
      {/* Background hexagon overlay */}
      <div className="fixed inset-0 bg-hex-pattern opacity-30 pointer-events-none" />
      
      <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-ethara-primary/10 rounded-full blur-3xl pointer-events-none" />
      <div className="absolute bottom-1/4 right-1/4 w-96 h-96 bg-ethara-secondary/10 rounded-full blur-3xl pointer-events-none" />

      <Card className="w-full max-w-md relative z-10 p-8 border border-ethara-border bg-ethara-card/85 backdrop-blur-md shadow-2xl">
        <CardHeader className="text-center">
          <div className="flex justify-center mb-4 select-none">
            <img src="/logo.png" alt="Ethara.Ai" className="h-10 object-contain" />
          </div>
          <CardTitle className="text-2xl font-bold tracking-tight text-white mb-1">
            Register Admin Account
          </CardTitle>
          <p className="text-sm text-ethara-text-secondary">
            Set up administrator credentials to manage seat assignments.
          </p>
        </CardHeader>

        {error && (
          <div className="mb-6 p-4 rounded-lg bg-ethara-error/10 border border-ethara-error/20 text-ethara-error text-sm">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-5">
          <div>
            <label className="block text-sm font-medium text-white mb-1.5" htmlFor="username">
              Username
            </label>
            <input
              id="username"
              type="text"
              required
              minLength={3}
              className="w-full bg-ethara-bg/50 border border-ethara-border hover:border-ethara-primary/30 focus:border-ethara-primary text-white rounded-lg px-4 py-2outline-none transition-all duration-200"
              placeholder="admin"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-white mb-1.5" htmlFor="email">
              Email Address
            </label>
            <input
              id="email"
              type="email"
              required
              className="w-full bg-ethara-bg/50 border border-ethara-border hover:border-ethara-primary/30 focus:border-ethara-primary text-white rounded-lg px-4 py-2 outline-none transition-all duration-200"
              placeholder="admin@ethara.ai"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-white mb-1.5" htmlFor="password">
              Password
            </label>
            <input
              id="password"
              type="password"
              required
              minLength={6}
              className="w-full bg-ethara-bg/50 border border-ethara-border hover:border-ethara-primary/30 focus:border-ethara-primary text-white rounded-lg px-4 py-2 outline-none transition-all duration-200"
              placeholder="••••••••"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-white mb-1.5" htmlFor="confirmPassword">
              Confirm Password
            </label>
            <input
              id="confirmPassword"
              type="password"
              required
              className="w-full bg-ethara-bg/50 border border-ethara-border hover:border-ethara-primary/30 focus:border-ethara-primary text-white rounded-lg px-4 py-2 outline-none transition-all duration-200"
              placeholder="••••••••"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
            />
          </div>

          <Button
            type="submit"
            className="w-full text-center py-3 bg-gradient-to-r from-ethara-secondary to-ethara-primary hover:from-ethara-secondary/95 hover:to-ethara-primary/95 text-white font-semibold rounded-lg shadow-lg hover:shadow-ethara-primary/20 transition-all duration-300"
            loading={loading}
          >
            Create Account
          </Button>
        </form>

        <div className="mt-6 text-center text-sm">
          <span className="text-ethara-text-secondary">Already have an account? </span>
          <Link to="/login" className="text-ethara-primary hover:text-ethara-secondary transition-colors font-medium">
            Log In
          </Link>
        </div>
      </Card>
    </div>
  )
}
