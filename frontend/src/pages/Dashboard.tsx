import {
  Users, Armchair, CheckCircle, Clock, AlertCircle, Wrench, TrendingUp, UserX
} from 'lucide-react'
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell, Legend
} from 'recharts'
import { Card, CardHeader, CardTitle } from '../components/ui/Card'
import { useDashboardSummary, useProjectUtilization, useFloorUtilization } from '../hooks/useDashboard'

const COLORS = ['#c026d3', '#7c3aed', '#a855f7', '#ec4899', '#8b5cf6', '#06b6d4', '#10b981', '#f59e0b', '#ef4444', '#3b82f6', '#84cc16']

interface StatCardProps {
  icon: React.ElementType
  label: string
  value: number | string
  sub?: string
  color?: string
}

function StatCard({ icon: Icon, label, value, sub, color = 'text-ethara-primary' }: StatCardProps) {
  return (
    <Card className="flex items-start gap-4">
      <div className={`p-3 rounded-xl bg-ethara-hover ${color} shrink-0`}>
        <Icon className="w-5 h-5" />
      </div>
      <div className="min-w-0">
        <p className="text-ethara-muted text-sm">{label}</p>
        <p className="text-2xl font-bold text-white mt-0.5">{value.toLocaleString()}</p>
        {sub && <p className="text-xs text-ethara-muted mt-0.5">{sub}</p>}
      </div>
    </Card>
  )
}

const CustomTooltip = ({ active, payload, label }: any) => {
  if (!active || !payload?.length) return null
  return (
    <div className="bg-ethara-card border border-ethara-border rounded-lg px-3 py-2 text-sm shadow-xl">
      <p className="text-white font-medium mb-1">{label}</p>
      {payload.map((p: any) => (
        <p key={p.dataKey} style={{ color: p.fill || p.color }}>
          {p.name}: <span className="text-white font-medium">{p.value}</span>
        </p>
      ))}
    </div>
  )
}

export function Dashboard() {
  const { data: summary, isLoading: sl } = useDashboardSummary()
  const { data: projUtil, isLoading: pl } = useProjectUtilization()
  const { data: floorUtil, isLoading: fl } = useFloorUtilization()

  const pieData = summary ? [
    { name: 'Occupied',    value: summary.occupied_seats,    color: '#ef4444' },
    { name: 'Available',   value: summary.available_seats,   color: '#10b981' },
    { name: 'Reserved',    value: summary.reserved_seats,    color: '#f59e0b' },
    { name: 'Maintenance', value: summary.maintenance_seats, color: '#64748b' },
  ] : []

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <div>
        <h2 className="text-2xl font-bold text-white">Overview</h2>
        <p className="text-ethara-muted text-sm mt-1">Real-time seat allocation metrics for Ethara</p>
      </div>

      {/* Stats grid */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard icon={Users}      label="Total Employees"   value={summary?.total_employees ?? '—'}  color="text-ethara-primary" />
        <StatCard icon={Armchair}   label="Total Seats"       value={summary?.total_seats ?? '—'}      color="text-ethara-accent"  />
        <StatCard icon={CheckCircle}label="Occupied Seats"    value={summary?.occupied_seats ?? '—'}   color="text-ethara-error"   sub={`${summary?.utilization_rate ?? 0}% utilization`} />
        <StatCard icon={Clock}      label="Available Seats"   value={summary?.available_seats ?? '—'}  color="text-ethara-success" />
      </div>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard icon={AlertCircle} label="Reserved"          value={summary?.reserved_seats ?? '—'}   color="text-ethara-warning" />
        <StatCard icon={Wrench}      label="Maintenance"       value={summary?.maintenance_seats ?? '—'}color="text-ethara-muted"   />
        <StatCard icon={TrendingUp}  label="Active Employees"  value={summary?.active_employees ?? '—'} color="text-ethara-accent"  />
        <StatCard icon={UserX}       label="Pending Allocation"value={summary?.pending_allocation ?? '—'}color="text-ethara-error"  sub="No seat assigned" />
      </div>

      {/* Charts row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Seat status pie */}
        <Card>
          <CardHeader><CardTitle>Seat Status Distribution</CardTitle></CardHeader>
          {sl ? (
            <div className="h-64 bg-ethara-hover/30 rounded-xl animate-pulse" />
          ) : (
            <ResponsiveContainer width="100%" height={260}>
              <PieChart>
                <Pie data={pieData} cx="50%" cy="50%" innerRadius={60} outerRadius={95}
                  paddingAngle={3} dataKey="value">
                  {pieData.map((entry, i) => (
                    <Cell key={i} fill={entry.color} stroke="transparent" />
                  ))}
                </Pie>
                <Tooltip content={<CustomTooltip />} />
                <Legend
                  formatter={(value) => <span className="text-sm text-ethara-muted">{value}</span>}
                />
              </PieChart>
            </ResponsiveContainer>
          )}
        </Card>

        {/* Floor utilization bar */}
        <Card>
          <CardHeader><CardTitle>Floor Occupancy</CardTitle></CardHeader>
          {fl ? (
            <div className="h-64 bg-ethara-hover/30 rounded-xl animate-pulse" />
          ) : (
            <ResponsiveContainer width="100%" height={260}>
              <BarChart data={floorUtil} margin={{ top: 5, right: 10, left: -20, bottom: 5 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1e1e3a" />
                <XAxis dataKey="floor" tick={{ fill: '#94a3b8', fontSize: 12 }}
                  tickFormatter={v => `F${v}`} />
                <YAxis tick={{ fill: '#94a3b8', fontSize: 12 }} />
                <Tooltip content={<CustomTooltip />} cursor={{ fill: '#ffffff08' }} />
                <Bar dataKey="occupied"  name="Occupied"  fill="#ef4444" radius={[3,3,0,0]} />
                <Bar dataKey="available" name="Available" fill="#10b981" radius={[3,3,0,0]} />
                <Bar dataKey="reserved"  name="Reserved"  fill="#f59e0b" radius={[3,3,0,0]} />
              </BarChart>
            </ResponsiveContainer>
          )}
        </Card>
      </div>

      {/* Project utilization table */}
      <Card>
        <CardHeader>
          <CardTitle>Project Utilization</CardTitle>
        </CardHeader>
        {pl ? (
          <div className="space-y-3">
            {[...Array(5)].map((_, i) => (
              <div key={i} className="h-10 bg-ethara-hover/30 rounded animate-pulse" />
            ))}
          </div>
        ) : (
          <div className="space-y-3">
            {projUtil?.map(p => {
              const pct = p.total_employees > 0
                ? Math.round(p.allocated_seats / p.total_employees * 100)
                : 0
              return (
                <div key={p.project_id} className="flex items-center gap-4">
                  <span className="text-sm text-white w-28 shrink-0 truncate font-medium">{p.project_name}</span>
                  <div className="flex-1 h-2 bg-ethara-hover rounded-full overflow-hidden">
                    <div
                      className="h-full bg-gradient-to-r from-ethara-primary to-ethara-secondary rounded-full transition-all duration-500"
                      style={{ width: `${pct}%` }}
                    />
                  </div>
                  <span className="text-xs text-ethara-muted w-32 text-right shrink-0">
                    {p.allocated_seats}/{p.total_employees} seats ({pct}%)
                  </span>
                </div>
              )
            })}
          </div>
        )}
      </Card>
    </div>
  )
}
