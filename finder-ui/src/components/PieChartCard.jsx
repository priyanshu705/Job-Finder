import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer } from 'recharts'

const COLORS = ['#34d399', '#fbbf24', '#f87171', '#fb923c', '#818cf8', '#c084fc', '#22d3ee']

const CustomTooltip = ({ active, payload }) => {
  if (!active || !payload?.length) return null
  return (
    <div style={{ background: 'rgba(8,15,31,0.95)', border: '1px solid rgba(99,102,241,0.3)', borderRadius: 12, padding: '8px 12px', fontSize: 12, boxShadow: '0 8px 32px rgba(0,0,0,0.5)', backdropFilter: 'blur(16px)' }}>
      <p style={{ color: payload[0].payload.fill, fontWeight: 700 }}>
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

  if (loading) return <div className="rounded-2xl p-5 h-64 skeleton" style={{ border: '1px solid rgba(255,255,255,0.06)' }} />
  return (
    <div className="rounded-2xl p-5" style={{ background: 'linear-gradient(135deg, rgba(13,21,38,0.92) 0%, rgba(8,15,31,0.96) 100%)', border: '1px solid rgba(255,255,255,0.07)', boxShadow: '0 4px 24px rgba(0,0,0,0.4), inset 0 1px 0 rgba(255,255,255,0.04)' }}>
      <p className="text-sm font-semibold mb-0.5" style={{ color: '#e2e8f0' }}>{title}</p>
      {sub && <p className="text-xs mb-2" style={{ color: 'rgba(100,116,139,0.8)' }}>{sub}</p>}
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
                <div key={i} className="flex items-center gap-2" style={{ fontSize: 11 }}>
                  <div className="w-2 h-2 rounded-full flex-shrink-0" style={{ background: entry.fill, boxShadow: `0 0 6px ${entry.fill}80` }} />
                  <span style={{ color: 'rgba(148,163,184,0.8)' }}>{entry.name}</span>
                  <span className="font-semibold ml-auto" style={{ color: '#e2e8f0' }}>{entry.value}</span>
                </div>
              ))}
            </div>
          </div>
        )
      }
    </div>
  )
}
