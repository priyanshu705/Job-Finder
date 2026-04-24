import { useState, useEffect } from 'react'
import { LineChartCard, MultiLineChartCard } from '../components/LineChartCard.jsx'
import BarChartCard from '../components/BarChartCard.jsx'
import PieChartCard from '../components/PieChartCard.jsx'
import { api } from '../api.js'
import { TrendingUp, Award, Building2, Zap } from 'lucide-react'

function WeekCard({ label, value, sub, color = 'text-blue-400' }) {
  return (
    <div className="card p-4 flex flex-col gap-1">
      <p className="text-xs text-slate-500">{label}</p>
      <p className={`text-2xl font-bold ${color}`}>{value ?? '—'}</p>
      {sub && <p className="text-xs text-slate-600">{sub}</p>}
    </div>
  )
}

export default function AnalyticsPage() {
  const [daily,     setDaily]     = useState([])
  const [summary,   setSummary]   = useState({})
  const [companies, setCompanies] = useState([])
  const [loading,   setLoading]   = useState(true)

  useEffect(() => {
    Promise.all([
      api.statsDaily(30).catch(() => []),
      api.statsSummary().catch(() => ({})),
      api.companies().catch(() => []),
    ]).then(([d, s, c]) => {
      setDaily(Array.isArray(d) ? d : (d.rows || []))
      setSummary(s || {})
      setCompanies(Array.isArray(c) ? c : (c.companies || []))
    }).finally(() => setLoading(false))
  }, [])

  const lineData  = daily.map(r => ({ date: r.date?.slice(5), applied: r.applied || 0, failed: r.failed || 0, uncertain: r.uncertain || 0 }))
  const rateData  = daily.map(r => {
    const total = (r.applied || 0) + (r.failed || 0)
    return { date: r.date?.slice(5), rate: total ? Math.round((r.applied / total) * 100) : 0 }
  })

  // Top companies by applies
  const topCompanies = [...companies]
    .sort((a, b) => (b.total_applies || 0) - (a.total_applies || 0))
    .slice(0, 8)
    .map(c => ({ name: c.company?.slice(0, 16), value: c.total_applies || 0 }))

  const s = summary
  const totalApplied  = s.applied   || 0
  const totalFailed   = s.failed    || 0
  const successRate   = totalApplied + totalFailed > 0
    ? Math.round((totalApplied / (totalApplied + totalFailed)) * 100) : 0

  return (
    <div className="space-y-6 animate-fade-in">
      <div>
        <h2 className="section-title">Analytics</h2>
        <p className="section-sub">30-day performance metrics</p>
      </div>

      {/* Weekly summary cards */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <WeekCard label="Total Applied"  value={totalApplied}  color="text-emerald-400" sub="all time" />
        <WeekCard label="Success Rate"   value={`${successRate}%`} color="text-blue-400" sub="applied / attempts" />
        <WeekCard label="Total Failed"   value={totalFailed}   color="text-red-400"     sub="all time" />
        <WeekCard label="Total Jobs"     value={s.total_jobs || '—'} color="text-slate-300" sub="scraped" />
      </div>

      {/* Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <MultiLineChartCard
          title="Application Trend (30 days)"
          sub="Applied · Failed · Uncertain"
          data={lineData} lines={['applied', 'failed', 'uncertain']} xKey="date" loading={loading}
        />
        <LineChartCard
          title="Success Rate Trend"
          sub="% of attempts that succeeded"
          data={rateData} dataKey="rate" xKey="date" color="#3b82f6" loading={loading}
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <BarChartCard
          title="Top Companies"
          sub="By number of applications"
          data={topCompanies} dataKey="value" xKey="name" loading={loading}
        />
        <PieChartCard
          title="Outcome Distribution"
          sub="All-time results"
          data={[
            { name: 'Applied',   value: totalApplied },
            { name: 'Failed',    value: totalFailed },
            { name: 'Uncertain', value: s.uncertain || 0 },
          ].filter(d => d.value > 0)}
          loading={loading}
        />
      </div>

      {/* Companies table */}
      {topCompanies.length > 0 && (
        <div className="card p-5">
          <p className="text-sm font-semibold text-slate-200 mb-4 flex items-center gap-2">
            <Building2 size={15} className="text-blue-400" /> Company Intelligence
          </p>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-slate-700/50">
                  <th className="table-head">Company</th>
                  <th className="table-head">Tier</th>
                  <th className="table-head">Applies</th>
                  <th className="table-head">Interviews</th>
                  <th className="table-head">Response Rate</th>
                </tr>
              </thead>
              <tbody>
                {companies.slice(0, 10).map((c, i) => (
                  <tr key={i} className="table-row">
                    <td className="table-cell font-medium text-slate-200">{c.company}</td>
                    <td className="table-cell">
                      <span className={`text-xs font-semibold ${c.tier === 'A' ? 'text-emerald-400' : c.tier === 'B' ? 'text-blue-400' : 'text-slate-500'}`}>
                        {c.tier || '—'}
                      </span>
                    </td>
                    <td className="table-cell">{c.total_applies || 0}</td>
                    <td className="table-cell">{c.total_interviews || 0}</td>
                    <td className="table-cell">{c.response_rate ? `${Math.round(c.response_rate * 100)}%` : '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  )
}
