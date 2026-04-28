import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell } from 'recharts'

const CustomTooltip = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null
  return (
    <div style={{ background: 'rgba(8,15,31,0.95)', border: '1px solid rgba(99,102,241,0.3)', borderRadius: 12, padding: '8px 12px', fontSize: 12, boxShadow: '0 8px 32px rgba(0,0,0,0.5)', backdropFilter: 'blur(16px)' }}>
      <p style={{ color: 'rgba(148,163,184,0.8)', marginBottom: 4 }}>{label}</p>
      {payload.map((p, i) => (
        <p key={i} style={{ color: p.fill || '#6366f1', fontWeight: 700 }}>{p.name}: {p.value}</p>
      ))}
    </div>
  )
}

const STATUS_COLORS = {
  applied:       '#34d399',
  pending:       '#fbbf24',
  failed:        '#f87171',
  uncertain:     '#fb923c',
  skip:          '#64748b',
  external_skip: '#c084fc',
}

export default function BarChartCard({ title, data = [], dataKey = 'value', xKey = 'name', loading, sub, colorByName }) {
  if (loading) return <div className="rounded-2xl p-5 h-64 skeleton" style={{ border: '1px solid rgba(255,255,255,0.06)' }} />
  return (
    <div className="rounded-2xl p-5" style={{ background: 'linear-gradient(135deg, rgba(13,21,38,0.92) 0%, rgba(8,15,31,0.96) 100%)', border: '1px solid rgba(255,255,255,0.07)', boxShadow: '0 4px 24px rgba(0,0,0,0.4), inset 0 1px 0 rgba(255,255,255,0.04)' }}>
      <p className="text-sm font-semibold mb-0.5" style={{ color: '#e2e8f0' }}>{title}</p>
      {sub && <p className="text-xs mb-4" style={{ color: 'rgba(100,116,139,0.8)' }}>{sub}</p>}
      {/* Fix 3: also guard against all-zero values to avoid misleading empty Y-axis */}
      {!data.length || data.every(d => !d[dataKey])
        ? (
          <div style={{ height: 180, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: 8 }}>
            <div style={{ fontSize: 28, opacity: 0.12 }}>📊</div>
            <p style={{ fontSize: 12, color: 'rgba(100,116,139,0.6)' }}>No data yet</p>
          </div>
        )
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
