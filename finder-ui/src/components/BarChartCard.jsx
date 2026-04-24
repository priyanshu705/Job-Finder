import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell } from 'recharts'

const CustomTooltip = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null
  return (
    <div className="bg-navy-800 border border-slate-600 rounded-xl px-3 py-2 text-xs shadow-card">
      <p className="text-slate-400 mb-1">{label}</p>
      {payload.map((p, i) => (
        <p key={i} style={{ color: p.fill || '#3b82f6' }} className="font-semibold">{p.name}: {p.value}</p>
      ))}
    </div>
  )
}

const STATUS_COLORS = {
  applied:  '#10b981',
  pending:  '#f59e0b',
  failed:   '#ef4444',
  uncertain:'#f97316',
  skip:     '#64748b',
  external_skip: '#8b5cf6',
}

export default function BarChartCard({ title, data = [], dataKey = 'value', xKey = 'name', loading, sub, colorByName }) {
  if (loading) return <div className="card p-5 h-64 skeleton" />
  return (
    <div className="card p-5">
      <p className="text-sm font-semibold text-slate-200 mb-0.5">{title}</p>
      {sub && <p className="text-xs text-slate-500 mb-4">{sub}</p>}
      {!data.length
        ? <div className="h-48 flex items-center justify-center text-slate-500 text-sm">No data yet</div>
        : (
          <ResponsiveContainer width="100%" height={180}>
            <BarChart data={data} margin={{ top: 4, right: 4, left: -20, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(148,163,184,0.08)" />
              <XAxis dataKey={xKey} tick={{ fill: '#64748b', fontSize: 11 }} axisLine={false} tickLine={false} />
              <YAxis tick={{ fill: '#64748b', fontSize: 11 }} axisLine={false} tickLine={false} allowDecimals={false} />
              <Tooltip content={<CustomTooltip />} cursor={{ fill: 'rgba(148,163,184,0.06)' }} />
              <Bar dataKey={dataKey} radius={[6, 6, 0, 0]} maxBarSize={40}>
                {data.map((entry, i) => (
                  <Cell
                    key={i}
                    fill={colorByName ? (STATUS_COLORS[entry[xKey]] || '#3b82f6') : '#3b82f6'}
                  />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        )
      }
    </div>
  )
}
