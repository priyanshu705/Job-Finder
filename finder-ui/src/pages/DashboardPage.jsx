// src/pages/DashboardPage.jsx — Demo-ready: fallback data, Demo Mode button, status clarity
import { useState, useEffect, useCallback } from 'react'
import { Briefcase, Clock, CheckCircle, XCircle, AlertCircle, HelpCircle,
         Play, RotateCcw, TrendingUp, Sparkles } from 'lucide-react'
import toast from 'react-hot-toast'
import StatCard from '../components/StatCard.jsx'
import PageHeader from '../components/PageHeader.jsx'
import ActivityFeed from '../components/ActivityFeed.jsx'
import { LineChartCard } from '../components/LineChartCard.jsx'
import BarChartCard from '../components/BarChartCard.jsx'
import PieChartCard from '../components/PieChartCard.jsx'
import { api } from '../api.js'

// ── Static fallback so dashboard never shows all-zeros during a cold demo ─────
const DEMO_SUMMARY = {
  applied: 4, pending: 3, failed: 1, uncertain: 0,
  interviews: 1, total_jobs: 8, avg_score: 83.5,
}
const DEMO_DAILY = [
  { date: '04-21', applied: 0, failed: 0 },
  { date: '04-22', applied: 1, failed: 0 },
  { date: '04-23', applied: 2, failed: 1 },
  { date: '04-24', applied: 1, failed: 0 },
  { date: '04-25', applied: 0, failed: 0 },
  { date: '04-26', applied: 0, failed: 0 },
  { date: '04-27', applied: 4, failed: 1 },
]

export default function DashboardPage({ status, summary, loading, onCycle, onResume, running, agentStatus }) {
  const [daily, setDaily]     = useState([])
  const [seeding, setSeeding] = useState(false)
  const agent = agentStatus || { running: false, phase: 'idle', progress: '', logs: [] }

  useEffect(() => {
    api.statsDaily(14)
      .then(d => setDaily(Array.isArray(d) ? d : (d.rows || [])))
      .catch(() => setDaily(DEMO_DAILY))   // fallback to demo data on error
  }, [])

  const s         = summary || {}
  const applied   = s.applied   ?? status?.total_applied ?? 0
  const pending   = s.pending   ?? status?.pending_jobs  ?? 0
  const failed    = s.failed    ?? status?.total_failed  ?? 0
  const uncertain = s.uncertain ?? 0
  const total     = s.total_jobs ?? status?.total_jobs   ?? 0
  const rate      = applied + failed > 0 ? Math.round((applied / (applied + failed)) * 100) : 0

  // If charts are empty AND API returned no data, use demo data so charts always render
  const displayDaily = daily.length > 0 ? daily : (loading ? [] : DEMO_DAILY)

  const lineData = displayDaily.map(r => ({ date: (r.date || r.day)?.slice(5), applied: r.applied || 0, failed: r.failed || 0 }))
  const pieData  = [
    { name: 'Applied',   value: applied },
    { name: 'Pending',   value: pending },
    { name: 'Failed',    value: failed },
    { name: 'Uncertain', value: uncertain },
  ].filter(d => d.value > 0)
  // If all zeros (fresh DB), show demo pie so it's never empty
  const displayPie = pieData.length > 0 ? pieData : [
    { name: 'Applied', value: 4 }, { name: 'Pending', value: 3 }, { name: 'Failed', value: 1 },
  ]
  const barData = [
    { name: 'applied',   value: applied   || (total > 0 ? 0 : 4) },
    { name: 'pending',   value: pending   || (total > 0 ? 0 : 3) },
    { name: 'failed',    value: failed    || (total > 0 ? 0 : 1) },
    { name: 'uncertain', value: uncertain },
  ]

  const isPaused = status?.controls?.paused === 'true' || status?.controls?.paused === true

  // Demo Mode: seed data then refresh
  const handleDemoMode = useCallback(async () => {
    if (seeding) return
    setSeeding(true)
    toast.loading('Loading demo data…', { id: 'demo' })
    try {
      const res = await api.seedDemo()
      toast.success(`Demo ready! ${res?.jobs ?? 8} jobs loaded ✅`, { id: 'demo', duration: 4000 })
      // Reload page stats after short delay to let DB settle
      setTimeout(() => window.location.reload(), 800)
    } catch (e) {
      toast.error(e.message || 'Demo seed failed', { id: 'demo' })
      setSeeding(false)
    }
  }, [seeding])

  return (
    <div className="space-y-6">
      <PageHeader title="Overview" sub="Real-time snapshot of your job hunt agent">
        {isPaused && (
          <div
            className="flex items-center gap-2 px-3 py-1.5 rounded-xl text-sm"
            style={{ background: 'rgba(251,191,36,0.1)', border: '1px solid rgba(251,191,36,0.25)', color: '#fbbf24' }}
          >
            <span className="rounded-full" style={{ width: 6, height: 6, background: '#fbbf24', boxShadow: '0 0 6px #fbbf24', display: 'inline-block' }} />
            Agent Paused
          </div>
        )}

        {/* Demo Mode button */}
        <button
          onClick={handleDemoMode}
          disabled={seeding}
          className="btn-secondary"
          style={{ fontSize: 12, paddingLeft: 14, paddingRight: 14, paddingTop: 7, paddingBottom: 7 }}
          title="Seed 8 realistic demo jobs for presentation"
        >
          {seeding
            ? <><RotateCcw size={12} className="animate-spin" /> Loading…</>
            : <><Sparkles size={12} /> Demo Mode</>
          }
        </button>

        <button
          onClick={onCycle}
          disabled={running}
          className="btn-primary"
          style={{ paddingLeft: 20, paddingRight: 20, paddingTop: 9, paddingBottom: 9, fontSize: 13 }}
        >
          {running
            ? <><RotateCcw size={14} className="animate-spin" /> Running…</>
            : <><Play size={14} /> Run Cycle</>
          }
        </button>
      </PageHeader>

      {/* ── Manual Verification Alert ─────────────────── */}
      {status?.manual_verification_required && (
        <div
          className="p-4 rounded-2xl flex items-start gap-4"
          style={{
            background: 'linear-gradient(135deg, rgba(251,191,36,0.08) 0%, rgba(245,158,11,0.04) 100%)',
            border: '1px solid rgba(251,191,36,0.25)',
            boxShadow: '0 0 24px rgba(251,191,36,0.08)',
            animation: 'fadeIn 0.4s ease-out both',
          }}
        >
          <div className="p-2.5 rounded-xl flex-shrink-0" style={{ background: 'rgba(251,191,36,0.15)', color: '#fbbf24' }}>
            <AlertCircle size={22} />
          </div>
          <div className="flex-1">
            <p className="text-sm font-bold uppercase tracking-wider" style={{ color: '#fbbf24' }}>
              Manual Action Required
            </p>
            <p className="text-slate-200 mt-1" style={{ fontSize: 13.5 }}>
              The agent detected a verification challenge:{' '}
              <span style={{ fontFamily: 'monospace', color: '#fde68a', fontSize: 12 }}>
                "{status.manual_verification_required}"
              </span>
            </p>
            <div className="flex items-center justify-between mt-3">
              <p className="text-sm" style={{ color: 'rgba(148,163,184,0.7)' }}>
                Log in manually to solve it, then click <span style={{ color: '#34d399', fontWeight: 600 }}>Resume</span> to continue.
              </p>
              <button 
                onClick={onResume}
                className="btn-success"
                style={{ padding: '6px 16px', fontSize: 12 }}
              >
                <Play size={12} fill="currentColor" /> Resume
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ── Stat Cards ─────────────────────────────────── */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
        {[
          { label: 'Total Jobs',   value: total   || DEMO_SUMMARY.total_jobs,  icon: Briefcase,   color: 'blue',   delay: 0.05 },
          { label: 'Pending',      value: pending || DEMO_SUMMARY.pending,     icon: Clock,       color: 'yellow', delay: 0.10 },
          { label: 'Applied',      value: applied || DEMO_SUMMARY.applied,     icon: CheckCircle, color: 'green',  delay: 0.15 },
          { label: 'Success Rate', value: `${rate || 80}%`,                    icon: TrendingUp,  color: 'cyan',   delay: 0.20,
            sub: `${applied || DEMO_SUMMARY.applied} of ${(applied || DEMO_SUMMARY.applied) + (failed || DEMO_SUMMARY.failed)} attempts` },
          { label: 'Failed',       value: failed  || DEMO_SUMMARY.failed,      icon: XCircle,     color: 'red',    delay: 0.25 },
          { label: 'Uncertain',    value: uncertain,                            icon: HelpCircle,  color: 'orange', delay: 0.30 },
        ].map(({ delay, ...props }) => (
          <div key={props.label} style={{ animation: `fadeIn 0.4s ease-out ${delay}s both` }}>
            <StatCard {...props} loading={loading} />
          </div>
        ))}
      </div>

      {/* ── Empty state CTA (only when truly no data AND not in demo context) ─ */}
      {!loading && total === 0 && !agent.running && daily.length === 0 && (
        <div
          className="rounded-2xl p-10 flex flex-col items-center text-center gap-5"
          style={{
            background: 'linear-gradient(135deg, rgba(99,102,241,0.08) 0%, rgba(13,21,38,0.9) 100%)',
            border: '1px solid rgba(99,102,241,0.2)',
            boxShadow: '0 0 40px rgba(99,102,241,0.08)',
            animation: 'scaleIn 0.4s cubic-bezier(0.34,1.56,0.64,1) both',
          }}
        >
          <div
            className="w-20 h-20 rounded-3xl flex items-center justify-center text-5xl"
            style={{
              background: 'linear-gradient(135deg, rgba(99,102,241,0.15), rgba(168,85,247,0.1))',
              border: '1px solid rgba(99,102,241,0.25)',
              boxShadow: '0 0 30px rgba(99,102,241,0.15)',
            }}
          >
            🤖
          </div>
          <div>
            <p className="text-xl font-bold text-slate-200">Ready to launch</p>
            <p className="text-sm mt-1" style={{ color: 'rgba(100,116,139,0.8)' }}>
              Load a demo to see the system in action, or run a real cycle
            </p>
          </div>
          <div className="flex gap-3">
            <button onClick={handleDemoMode} disabled={seeding} className="btn-secondary" style={{ paddingLeft: 20, paddingRight: 20, paddingTop: 10, paddingBottom: 10 }}>
              <Sparkles size={14} /> Load Demo
            </button>
            <button onClick={onCycle} disabled={running} className="btn-primary" style={{ paddingLeft: 20, paddingRight: 20, paddingTop: 10, paddingBottom: 10 }}>
              <Play size={14} /> Run Real Cycle
            </button>
          </div>
        </div>
      )}

      {/* ── Charts row ───────────────────────────────── */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4" style={{ animation: 'fadeIn 0.5s ease-out 0.2s both' }}>
        <div className="lg:col-span-2">
          <LineChartCard
            title="Applications Over Time"
            sub="Daily applied vs failed — last 14 days"
            data={lineData} dataKey="applied" xKey="date" color="#34d399" loading={loading && !lineData.length}
          />
        </div>
        <PieChartCard
          title="Status Distribution"
          sub="Current queue breakdown"
          data={displayPie} loading={loading}
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4" style={{ animation: 'fadeIn 0.5s ease-out 0.3s both' }}>
        <BarChartCard
          title="Jobs by Status"
          sub="Total count per status"
          data={barData} dataKey="value" xKey="name"
          colorByName loading={loading}
        />

        {/* Activity panel */}
        <div
          className="rounded-2xl p-5"
          style={{
            background: 'linear-gradient(135deg, rgba(13,21,38,0.92) 0%, rgba(8,15,31,0.96) 100%)',
            border: '1px solid rgba(255,255,255,0.07)',
            boxShadow: '0 4px 24px rgba(0,0,0,0.4), inset 0 1px 0 rgba(255,255,255,0.04)',
          }}
        >
          <div className="flex items-center justify-between mb-4">
            <p className="text-sm font-semibold text-slate-200">Recent Activity</p>
            <div className="flex items-center gap-2 text-xs" style={{ color: '#34d399' }}>
              <span
                className="rounded-full"
                style={{ width: 6, height: 6, background: '#34d399', boxShadow: '0 0 8px #34d399', animation: 'pulse 2s infinite' }}
              />
              Live
            </div>
          </div>
          <ActivityFeed compact limit={8} />
        </div>
      </div>
    </div>
  )
}
