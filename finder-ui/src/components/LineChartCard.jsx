import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Area, AreaChart } from 'recharts'

const CustomTooltip = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null
  return (
    <div style={{ background: 'rgba(8,15,31,0.95)', border: '1px solid rgba(99,102,241,0.3)', borderRadius: 12, padding: '8px 12px', fontSize: 12, boxShadow: '0 8px 32px rgba(0,0,0,0.5), 0 0 16px rgba(99,102,241,0.1)', backdropFilter: 'blur(16px)' }}>
      <p style={{ color: 'rgba(148,163,184,0.8)', marginBottom: 4 }}>{label}</p>
      {payload.map((p, i) => (
        <p key={i} style={{ color: p.color, fontWeight: 700 }}>{p.name}: {p.value}</p>
      ))}
    </div>
  )
}

export function LineChartCard({ title, data = [], dataKey = 'value', xKey = 'date', color = '#3b82f6', loading, sub }) {
  if (loading) return <div className="rounded-2xl p-5 h-64 skeleton" style={{ border: '1px solid rgba(255,255,255,0.06)' }} />
  return (
    <div className="rounded-2xl p-5" style={{ background: 'linear-gradient(135deg, rgba(13,21,38,0.92) 0%, rgba(8,15,31,0.96) 100%)', border: '1px solid rgba(255,255,255,0.07)', boxShadow: '0 4px 24px rgba(0,0,0,0.4), inset 0 1px 0 rgba(255,255,255,0.04)' }}>
      <p className="text-sm font-semibold mb-0.5" style={{ color: '#e2e8f0' }}>{title}</p>
      {sub && <p className="text-xs mb-4" style={{ color: 'rgba(100,116,139,0.8)' }}>{sub}</p>}
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
  const colors = ['#6366f1', '#34d399', '#fbbf24', '#f87171', '#c084fc']
  if (loading) return <div className="rounded-2xl p-5 h-64 skeleton" style={{ border: '1px solid rgba(255,255,255,0.06)' }} />
  return (
    <div className="rounded-2xl p-5" style={{ background: 'linear-gradient(135deg, rgba(13,21,38,0.92) 0%, rgba(8,15,31,0.96) 100%)', border: '1px solid rgba(255,255,255,0.07)', boxShadow: '0 4px 24px rgba(0,0,0,0.4), inset 0 1px 0 rgba(255,255,255,0.04)' }}>
      <p className="text-sm font-semibold mb-0.5" style={{ color: '#e2e8f0' }}>{title}</p>
      {sub && <p className="text-xs mb-4" style={{ color: 'rgba(100,116,139,0.8)' }}>{sub}</p>}
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
