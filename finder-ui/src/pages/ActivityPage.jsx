// src/pages/ActivityPage.jsx — Fix 5: PageHeader + two-column layout fills dead right space
import ActivityFeed from '../components/ActivityFeed.jsx'
import PageHeader from '../components/PageHeader.jsx'
import StatCard from '../components/StatCard.jsx'
import { Activity, Zap, CheckCircle, AlertCircle } from 'lucide-react'
import { useState, useEffect } from 'react'
import { api } from '../api.js'

export default function ActivityPage() {
  const [summary, setSummary] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    api.statsSummary().then(s => setSummary(s)).catch(() => {}).finally(() => setLoading(false))
  }, [])

  const s = summary || {}

  return (
    <div className="space-y-6" style={{ animation: 'fadeIn 0.4s ease-out both' }}>
      {/* Fix 5: gradient PageHeader — removed duplicate inline "Live" badge */}
      <PageHeader title="Activity Feed" sub="Live log of every agent action — auto-refreshing" />

      {/* Two-column layout: feed + summary sidebar */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* Main feed — takes 2/3 width */}
        <div
          className="lg:col-span-2 rounded-2xl p-5"
          style={{
            background: 'linear-gradient(135deg, rgba(13,21,38,0.92) 0%, rgba(8,15,31,0.96) 100%)',
            border: '1px solid rgba(255,255,255,0.07)',
            boxShadow: '0 4px 24px rgba(0,0,0,0.4), inset 0 1px 0 rgba(255,255,255,0.04)',
          }}
        >
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              <Activity size={14} style={{ color: '#818cf8' }} />
              <span style={{ fontSize: 13, fontWeight: 600, color: '#e2e8f0' }}>Event Stream</span>
            </div>
            <div className="flex items-center gap-1.5" style={{ fontSize: 11, color: '#34d399' }}>
              <span
                className="rounded-full"
                style={{ width: 6, height: 6, background: '#34d399', boxShadow: '0 0 8px #34d399', animation: 'pulse 2s infinite', display: 'inline-block' }}
              />
              Live
            </div>
          </div>
          <ActivityFeed limit={100} />
        </div>

        {/* Summary sidebar — takes 1/3 */}
        <div className="flex flex-col gap-3">
          <p style={{ fontSize: 11, fontWeight: 600, color: 'rgba(148,163,184,0.5)', textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: 4 }}>
            All-time summary
          </p>
          <StatCard label="Applied" value={s.applied ?? '—'} icon={CheckCircle} color="green" loading={loading} />
          <StatCard label="Pending" value={s.pending ?? '—'} icon={Zap} color="yellow" loading={loading} />
          <StatCard label="Failed" value={s.failed ?? '—'} icon={AlertCircle} color="red" loading={loading} />
          <StatCard label="Total Jobs" value={s.total_jobs ?? '—'} icon={Activity} color="blue" loading={loading} />
        </div>
      </div>
    </div>
  )
}
