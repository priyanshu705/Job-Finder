import { useState, useEffect, useCallback } from 'react'
import { Briefcase, Clock, CheckCircle, XCircle, AlertCircle, HelpCircle, Play, RotateCcw, TrendingUp } from 'lucide-react'
import StatCard from '../components/StatCard.jsx'
import ActivityFeed from '../components/ActivityFeed.jsx'
import { LineChartCard } from '../components/LineChartCard.jsx'
import BarChartCard from '../components/BarChartCard.jsx'
import PieChartCard from '../components/PieChartCard.jsx'
import { api } from '../api.js'

export default function DashboardPage({ status, summary, loading, onCycle, running, agentStatus }) {
  const [daily, setDaily] = useState([])
  const agent = agentStatus || { running: false, phase: 'idle', progress: '', logs: [] }

  useEffect(() => {
    api.statsDaily(14).then(d => setDaily(Array.isArray(d) ? d : (d.rows || []))).catch(() => {})
  }, [])

  const s = summary || {}
  const applied   = s.applied   ?? status?.total_applied   ?? 0
  const pending   = s.pending   ?? status?.pending_jobs    ?? 0
  const failed    = s.failed    ?? status?.total_failed    ?? 0
  const uncertain = s.uncertain ?? 0
  const total     = s.total_jobs ?? status?.total_jobs     ?? 0
  const rate      = applied + failed > 0 ? Math.round((applied / (applied + failed)) * 100) : 0

  // Build chart data from daily stats
  const lineData  = daily.map(r => ({ date: r.date?.slice(5), applied: r.applied || 0, failed: r.failed || 0 }))
  const pieData   = [
    { name: 'Applied',   value: applied },
    { name: 'Pending',   value: pending },
    { name: 'Failed',    value: failed },
    { name: 'Uncertain', value: uncertain },
  ].filter(d => d.value > 0)
  const barData   = [
    { name: 'applied',   value: applied },
    { name: 'pending',   value: pending },
    { name: 'failed',    value: failed },
    { name: 'uncertain', value: uncertain },
  ]

  const isPaused = status?.paused === true || status?.paused === 'true'

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="section-title">Overview</h2>
          <p className="section-sub">Real-time snapshot of your job hunt agent</p>
        </div>
        <div className="flex gap-2">
          {isPaused && (
            <div className="flex items-center gap-2 px-3 py-1.5 rounded-xl bg-amber-500/10 border border-amber-500/20 text-amber-400 text-sm">
              <span className="w-2 h-2 rounded-full bg-amber-400" /> Agent Paused
            </div>
          )}
          <button 
            onClick={onCycle} 
            disabled={running} 
            className={`btn-primary text-[11px] px-4 py-2 uppercase font-bold tracking-widest ${running ? 'opacity-50 cursor-not-allowed' : ''}`}
          >
            {running ? <><RotateCcw size={14} className="animate-spin mr-2" /> Running…</> : <><Play size={14} className="mr-2" /> Run Cycle</>}
          </button>
        </div>
      </div>

      {/* Manual Verification Alert */}
      {status?.manual_verification_required && (
        <div className="p-4 rounded-2xl bg-amber-500/10 border border-amber-500/20 flex items-start gap-4 animate-in fade-in slide-in-from-top duration-500">
          <div className="p-2 rounded-xl bg-amber-500/20 text-amber-500">
            <AlertCircle size={24} />
          </div>
          <div className="flex-1">
            <p className="text-sm font-bold text-amber-400 uppercase tracking-wider">Manual Action Required</p>
            <p className="text-slate-200 mt-0.5">
              The agent has detected a verification challenge: <span className="font-mono text-amber-200">"{status.manual_verification_required}"</span>.
            </p>
            <p className="text-sm text-slate-500 mt-2">
              Please open a visible browser, log in manually to solve the challenge, then click <span className="text-emerald-400 font-semibold">Resume</span> to continue.
            </p>
          </div>
        </div>
      )}

      {/* Stat cards */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
        <StatCard label="Total Jobs"   value={total}     icon={Briefcase}     color="blue"   loading={loading} />
        <StatCard label="Pending"      value={pending}   icon={Clock}         color="yellow" loading={loading} />
        <StatCard label="Applied"      value={applied}   icon={CheckCircle}   color="green"  loading={loading} />
        <StatCard label="Success Rate" value={`${rate}%`} icon={TrendingUp}   color="green"  loading={loading} sub={`${applied} of ${applied+failed} attempts`} />
        <StatCard label="Failed"       value={failed}    icon={XCircle}       color="red"    loading={loading} />
        <StatCard label="Uncertain"    value={uncertain} icon={HelpCircle}    color="orange" loading={loading} />
      </div>

      {/* CTA when queue is empty */}
      {!loading && total === 0 && !agent.running && (
        <div className="card p-8 flex flex-col items-center text-center gap-4">
          <div className="text-5xl">🤖</div>
          <div>
            <p className="text-lg font-semibold text-slate-200">No jobs yet</p>
            <p className="text-sm text-slate-500 mt-1">Run a full cycle to scrape, match, and queue jobs automatically</p>
          </div>
          <button onClick={onCycle} disabled={running} className="btn-primary px-6 py-2.5">
             <Play size={15} /> Run First Cycle
          </button>
        </div>
      )}

      {/* Charts row */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <div className="lg:col-span-2">
          <LineChartCard
            title="Applications Over Time"
            sub="Daily applied vs failed — last 14 days"
            data={lineData} dataKey="applied" xKey="date" color="#10b981" loading={loading && !lineData.length}
          />
        </div>
        <PieChartCard
          title="Status Distribution"
          sub="Current queue breakdown"
          data={pieData} loading={loading}
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <BarChartCard
          title="Jobs by Status"
          sub="Total count per status"
          data={barData} dataKey="value" xKey="name"
          colorByName loading={loading}
        />
        {/* Activity panel */}
        <div className="card p-5">
          <div className="flex items-center justify-between mb-4">
            <p className="text-sm font-semibold text-slate-200">Recent Activity</p>
            <div className="flex items-center gap-1.5 text-xs text-emerald-400">
              <span className="live-dot" /> Live
            </div>
          </div>
          <ActivityFeed compact limit={8} />
        </div>
      </div>
    </div>
  )
}
