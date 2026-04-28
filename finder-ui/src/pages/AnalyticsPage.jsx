import { useState, useEffect } from 'react'
import { LineChartCard, MultiLineChartCard } from '../components/LineChartCard.jsx'
import BarChartCard from '../components/BarChartCard.jsx'
import PieChartCard from '../components/PieChartCard.jsx'
import PageHeader from '../components/PageHeader.jsx'
import StatCard from '../components/StatCard.jsx'
import { api } from '../api.js'
import { Building2 } from 'lucide-react'

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

  const lineData  = daily.map(r => ({ date: (r.date || r.day)?.slice(5), applied: r.applied || 0, failed: r.failed || 0, uncertain: r.uncertain || 0 }))
  const rateData  = daily.map(r => {
    const total = (r.applied || 0) + (r.failed || 0)
    return { date: (r.date || r.day)?.slice(5), rate: total ? Math.round((r.applied / total) * 100) : 0 }
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
    <div className="space-y-6" style={{ animation: 'fadeIn 0.4s ease-out both' }}>
      <PageHeader title="Analytics" sub="30-day performance metrics" />

      {/* Summary stat cards */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <StatCard label="Total Applied"  value={totalApplied}        color="green" sub="all time" loading={loading} />
        <StatCard label="Success Rate"   value={`${successRate}%`}  color="blue"  sub="applied / attempts" loading={loading} />
        <StatCard label="Total Failed"   value={totalFailed}         color="red"   sub="all time" loading={loading} />
        <StatCard label="Total Jobs"     value={s.total_jobs || '—'} color="slate" sub="scraped" loading={loading} />
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
        <div
          className="p-5 rounded-2xl"
          style={{
            background: 'linear-gradient(135deg, rgba(13,21,38,0.92) 0%, rgba(8,15,31,0.96) 100%)',
            border: '1px solid rgba(255,255,255,0.07)',
            boxShadow: '0 4px 24px rgba(0,0,0,0.4), inset 0 1px 0 rgba(255,255,255,0.04)',
          }}
        >
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
