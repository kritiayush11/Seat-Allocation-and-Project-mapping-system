import { Link } from 'react-router-dom'

export function NotFound() {
  return (
    <div className="flex flex-col items-center justify-center h-full text-center py-24">
      <div className="text-8xl mb-6">🪑</div>
      <h1 className="text-4xl font-bold text-white mb-3">404</h1>
      <p className="text-ethara-muted mb-8">This page doesn't have a seat.</p>
      <Link to="/" className="ethara-btn-primary">
        Back to Dashboard
      </Link>
    </div>
  )
}
