import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer, Legend } from 'recharts'

const COLORS = ['#10b981', '#f59e0b', '#ef4444', '#f97316', '#3b82f6', '#8b5cf6', '#64748b']

const CustomTooltip = ({ active, payload }) => {
  if (!active || !payload?.length) return null
  return (
    <div className="bg-navy-800 border border-slate-600 rounded-xl px-3 py-2 text-xs shadow-card">
      <p style={{ color: payload[0].payload.fill }} className="font-semibold">
        {payload[0].name}: {payload[0].value} ({payload[0].payload.pct}%)
      </p>
    </div>
  )
}

export default function PieChartCard({ title, data = [], loading, sub }) {
  const total = data.reduce((s, d) => s + (d.value || 0), 0)
  const enriched = data.map((d, i) => ({
    ...d,
    fill: COLORS[i % COLORS.length],
    pct: total ? Math.round((d.value / total) * 100) : 0,
  }))

  if (loading) return <div className="card p-5 h-64 skeleton" />
  return (
    <div className="card p-5">
      <p className="text-sm font-semibold text-slate-200 mb-0.5">{title}</p>
      {sub && <p className="text-xs text-slate-500 mb-2">{sub}</p>}
      {!data.length || total === 0
        ? <div className="h-48 flex items-center justify-center text-slate-500 text-sm">No data yet</div>
        : (
          <div className="flex items-center gap-4">
            <ResponsiveContainer width="55%" height={160}>
              <PieChart>
                <Pie data={enriched} cx="50%" cy="50%" innerRadius={45} outerRadius={70} dataKey="value" paddingAngle={3}>
                  {enriched.map((entry, i) => (
                    <Cell key={i} fill={entry.fill} stroke="transparent" />
                  ))}
                </Pie>
                <Tooltip content={<CustomTooltip />} />
              </PieChart>
            </ResponsiveContainer>
            <div className="flex flex-col gap-2">
              {enriched.map((entry, i) => (
                <div key={i} className="flex items-center gap-2 text-xs">
                  <div className="w-2.5 h-2.5 rounded-full flex-shrink-0" style={{ background: entry.fill }} />
                  <span className="text-slate-400">{entry.name}</span>
                  <span className="font-semibold text-slate-200 ml-auto">{entry.value}</span>
                </div>
              ))}
            </div>
          </div>
        )
      }
    </div>
  )
}
