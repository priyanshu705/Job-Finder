import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Area, AreaChart } from 'recharts'

const CustomTooltip = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null
  return (
    <div className="bg-navy-800 border border-slate-600 rounded-xl px-3 py-2 text-xs shadow-card">
      <p className="text-slate-400 mb-1">{label}</p>
      {payload.map((p, i) => (
        <p key={i} style={{ color: p.color }} className="font-semibold">{p.name}: {p.value}</p>
      ))}
    </div>
  )
}

export function LineChartCard({ title, data = [], dataKey = 'value', xKey = 'date', color = '#3b82f6', loading, sub }) {
  if (loading) return <div className="card p-5 h-64 skeleton" />
  return (
    <div className="card p-5">
      <p className="text-sm font-semibold text-slate-200 mb-0.5">{title}</p>
      {sub && <p className="text-xs text-slate-500 mb-4">{sub}</p>}
      {!data.length
        ? <div className="h-48 flex items-center justify-center text-slate-500 text-sm">No data yet</div>
        : (
          <ResponsiveContainer width="100%" height={180}>
            <AreaChart data={data} margin={{ top: 4, right: 4, left: -20, bottom: 0 }}>
              <defs>
                <linearGradient id={`grad-${dataKey}`} x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%"  stopColor={color} stopOpacity={0.25} />
                  <stop offset="95%" stopColor={color} stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(148,163,184,0.08)" />
              <XAxis dataKey={xKey} tick={{ fill: '#64748b', fontSize: 11 }} axisLine={false} tickLine={false} />
              <YAxis tick={{ fill: '#64748b', fontSize: 11 }} axisLine={false} tickLine={false} />
              <Tooltip content={<CustomTooltip />} />
              <Area type="monotone" dataKey={dataKey} stroke={color} strokeWidth={2} fill={`url(#grad-${dataKey})`} dot={false} activeDot={{ r: 4, fill: color }} />
            </AreaChart>
          </ResponsiveContainer>
        )
      }
    </div>
  )
}

export function MultiLineChartCard({ title, data = [], lines = [], xKey = 'date', loading, sub }) {
  const colors = ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6']
  if (loading) return <div className="card p-5 h-64 skeleton" />
  return (
    <div className="card p-5">
      <p className="text-sm font-semibold text-slate-200 mb-0.5">{title}</p>
      {sub && <p className="text-xs text-slate-500 mb-4">{sub}</p>}
      {!data.length
        ? <div className="h-48 flex items-center justify-center text-slate-500 text-sm">No data yet</div>
        : (
          <ResponsiveContainer width="100%" height={180}>
            <LineChart data={data} margin={{ top: 4, right: 4, left: -20, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(148,163,184,0.08)" />
              <XAxis dataKey={xKey} tick={{ fill: '#64748b', fontSize: 11 }} axisLine={false} tickLine={false} />
              <YAxis tick={{ fill: '#64748b', fontSize: 11 }} axisLine={false} tickLine={false} />
              <Tooltip content={<CustomTooltip />} />
              {lines.map((key, i) => (
                <Line key={key} type="monotone" dataKey={key} stroke={colors[i % colors.length]} strokeWidth={2} dot={false} activeDot={{ r: 4 }} />
              ))}
            </LineChart>
          </ResponsiveContainer>
        )
      }
    </div>
  )
}
