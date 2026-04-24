import { useState, useEffect, useCallback } from 'react'
import { Search, Filter, TrendingUp, CheckCircle, Target, Clock, Phone, Play, X } from 'lucide-react'
import FiltersBar from '../components/FiltersBar.jsx'
import QueueTable from '../components/QueueTable.jsx'
import { api } from '../api.js'

const DEFAULT_FILTERS = { q: '', status: '', sort: 'priority', min_score: '', company: '' }

function StatCard({ label, value, icon: Icon, color }) {
  const colors = {
    emerald: 'bg-emerald-500/10 text-emerald-500 border-emerald-500/20',
    blue:    'bg-blue-500/10 text-blue-500 border-blue-500/20',
    purple:  'bg-purple-500/10 text-purple-500 border-purple-500/20',
    amber:   'bg-amber-500/10 text-amber-500 border-amber-500/20',
  }
  return (
    <div className={`card p-4 border flex items-center gap-4 ${colors[color]}`}>
      <div className="p-2.5 rounded-xl bg-white/10">
        <Icon size={20} />
      </div>
      <div>
        <p className="text-[10px] uppercase font-bold tracking-wider opacity-70">{label}</p>
        <p className="text-xl font-bold">{value}</p>
      </div>
    </div>
  )
}

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

  const runCycle = async () => {
    try {
       await api.runCycle()
       if (fetchStatus) fetchStatus()
    } catch (err) {
       alert(err.message)
    }
  }

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="section-title">Job Assistant Dashboard</h2>
          <p className="section-sub">Personalized job applications powered by AI</p>
        </div>
        <div className="flex gap-2">
          <button 
            onClick={runCycle}
            disabled={agent.running}
            className={`btn-primary text-[10px] py-1.5 px-3 uppercase tracking-wider font-bold ${agent.running ? 'opacity-50 cursor-not-allowed' : ''}`}
          >
            {agent.running ? (
              <span className="flex items-center">
                 <div className="w-3 h-3 border-2 border-white/30 border-t-white rounded-full animate-spin mr-2" />
                 Running...
              </span>
            ) : (
              <><Play size={12} className="mr-1 inline" /> Run Cycle</>
            )}
          </button>
          <button onClick={seedDemo} className="btn-secondary text-[10px] py-1.5 px-3 uppercase tracking-wider font-bold">
             Demo Mode
          </button>
        </div>
      </div>

      {/* Agent Result Summary Banner */}
      {agent.last_result && !agent.running && (
        <div className="p-3 bg-emerald-500/10 border border-emerald-500/20 rounded-xl flex items-center justify-between animate-fade-in">
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
        <div className="p-3 bg-red-500/10 border border-red-500/20 rounded-xl flex items-center gap-3 text-red-400 animate-fade-in">
           <X size={16} />
           <p className="text-xs font-medium">Agent Error: {agent.error}</p>
        </div>
      )}

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {(summary?.cards || [
          { label: 'Total Applied', value: '0', icon: CheckCircle, color: 'emerald' },
          { label: 'Success Rate', value: '0%', icon: Target, color: 'blue' },
          { label: 'Interviews', value: '0', icon: Phone, color: 'purple' },
          { label: 'Pending', value: '0', icon: Clock, color: 'amber' },
        ]).map((c, i) => (
          <StatCard key={i} {...c} icon={c.icon === 'CheckCircle' ? CheckCircle : c.icon === 'Target' ? Target : c.icon === 'Phone' ? Phone : Clock} />
        ))}
      </div>

      <div className="space-y-4">
        <div className="flex flex-col md:flex-row gap-4">
          <div className="relative flex-1">
            <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
            <input 
              type="text" 
              placeholder="Search by role or company..." 
              className="w-full pl-10 pr-4 py-2 bg-slate-900 border border-slate-700 rounded-xl text-sm focus:border-blue-500 transition-colors"
              value={filters.q}
              onChange={e => setFilters({...filters, q: e.target.value})}
            />
          </div>
          <FiltersBar filters={filters} onChange={setFilters} />
        </div>

        {rows.length > 0 && filters.sort === 'priority' && !filters.q && (
           <div className="bg-blue-500/5 border border-blue-500/10 rounded-2xl p-1">
              <div className="px-4 py-2 flex items-center gap-2">
                 <TrendingUp size={14} className="text-blue-400" />
                 <span className="text-[11px] font-bold uppercase tracking-wider text-blue-400">Top Matches</span>
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
