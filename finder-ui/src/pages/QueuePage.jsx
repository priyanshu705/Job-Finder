import { useState, useEffect, useCallback } from 'react'
import { TrendingUp, CheckCircle, Target, Clock, Phone, X } from 'lucide-react'
import PageHeader from '../components/PageHeader.jsx'
import FiltersBar from '../components/FiltersBar.jsx'
import QueueTable from '../components/QueueTable.jsx'
import StatCard from '../components/StatCard.jsx'
import { api } from '../api.js'

const DEFAULT_FILTERS = { q: '', status: '', sort: 'priority', min_score: '', company: '' }

export default function QueuePage({ agentStatus, summary, fetchStatus }) {
  const [rows, setRows]       = useState([])
  const [loading, setLoading] = useState(true)
  const [filters, setFilters] = useState(DEFAULT_FILTERS)
  const [stats, setStats]     = useState(null)
  const [total, setTotal]     = useState(0)

  const agent = agentStatus || { running: false, last_run: null, last_result: null, logs: [], phase: 'idle', progress: '' }

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const qData = await api.queue({ ...filters, limit: 100 })
      setRows(qData.jobs || [])
      setTotal(qData.total || 0)
      if (fetchStatus) fetchStatus()
    } catch {
      setRows([])
    } finally {
      setLoading(false)
    }
  }, [filters, fetchStatus])

  useEffect(() => { load() }, [load])

  const seedDemo = async () => {
    await api.seedDemo()
    load()
  }

  return (
    <div className="space-y-6" style={{ animation: 'fadeIn 0.4s ease-out both' }}>
      {/* Fix 4: removed duplicate Run Cycle button — navbar is the canonical action */}
      {/* Fix 5: using shared PageHeader for consistent gradient header */}
      <PageHeader title="Job Assistant" sub="AI-powered personalized applications">
        <button onClick={seedDemo} className="btn-secondary" style={{ fontSize: 11, padding: '6px 14px' }}>
          Demo Mode
        </button>
      </PageHeader>

      {/* Agent Result Summary Banner */}
      {agent.last_result && !agent.running && (
        <div
          className="p-3 rounded-xl flex items-center justify-between"
          style={{ background: 'rgba(52,211,153,0.08)', border: '1px solid rgba(52,211,153,0.2)', boxShadow: '0 0 20px rgba(52,211,153,0.06)', animation: 'fadeIn 0.35s ease-out both' }}
        >
           <div className="flex items-center gap-3">
              <div className="p-2 bg-emerald-500/20 rounded-lg text-emerald-500">
                 <CheckCircle size={16} />
              </div>
              <div>
                 <p className="text-xs font-bold text-emerald-500 uppercase tracking-wide">Last Run Complete</p>
                 <p className="text-[10px] text-slate-400">Successfully processed the queue</p>
              </div>
           </div>
           <div className="flex gap-4">
              <div className="text-center">
                 <p className="text-xs font-bold text-white">{agent.last_result.scraped || 0}</p>
                 <p className="text-[9px] uppercase text-slate-500">Scraped</p>
              </div>
              <div className="text-center">
                 <p className="text-xs font-bold text-white">{agent.last_result.matched || 0}</p>
                 <p className="text-[9px] uppercase text-slate-500">Matched</p>
              </div>
              <div className="text-center">
                 <p className="text-xs font-bold text-white">{agent.last_result.applied || 0}</p>
                 <p className="text-[9px] uppercase text-slate-500">Applied</p>
              </div>
           </div>
        </div>
      )}

      {agent.error && (
        <div className="p-3 rounded-xl flex items-center gap-3" style={{ background: 'rgba(248,113,113,0.08)', border: '1px solid rgba(248,113,113,0.2)', color: '#f87171', animation: 'fadeIn 0.35s ease-out both' }}>
           <X size={16} />
           <p className="text-xs font-medium">Agent Error: {agent.error}</p>
        </div>
      )}

      {/* Stats Cards — from API or sensible fallbacks */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {[
          { label: 'Total Applied', value: summary?.applied ?? 0,    icon: CheckCircle, color: 'green'  },
          { label: 'Success Rate',  value: `${summary?.applied && summary?.failed ? Math.round(summary.applied / (summary.applied + summary.failed) * 100) : 0}%`, icon: Target, color: 'blue' },
          { label: 'Interviews',    value: summary?.interviews ?? 0,  icon: Phone,       color: 'purple' },
          { label: 'Pending',       value: summary?.pending ?? 0,     icon: Clock,       color: 'yellow' },
        ].map((c, i) => (
          <StatCard key={i} {...c} />
        ))}
      </div>

      <div className="space-y-4">
        {/* Fix 1: removed duplicate standalone search — FiltersBar already has a search input */}
        <FiltersBar filters={filters} onChange={setFilters} />

        {rows.length > 0 && filters.sort === 'priority' && !filters.q && (
           <div className="rounded-2xl p-1" style={{ background: 'rgba(99,102,241,0.04)', border: '1px solid rgba(99,102,241,0.15)', boxShadow: '0 0 20px rgba(99,102,241,0.06)' }}>
              <div className="px-4 py-2 flex items-center gap-2">
                 <TrendingUp size={13} style={{ color: '#818cf8' }} />
                 <span style={{ fontSize: 10, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.1em', color: '#818cf8' }}>Top Matches</span>
              </div>
              <QueueTable rows={rows.slice(0, 3)} loading={loading} onUpdate={load} hidePagination />
           </div>
        )}

        <div className="space-y-2">
           <div className="px-1 flex items-center justify-between">
              <span className="text-xs font-medium text-slate-400">{total} Results Found</span>
           </div>
           <QueueTable rows={rows} loading={loading} onUpdate={load} />
        </div>
      </div>
    </div>
  )
}
