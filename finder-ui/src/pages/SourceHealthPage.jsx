import { useState, useEffect } from 'react'
import { Server, Activity, AlertTriangle, ShieldCheck, Clock, RefreshCcw } from 'lucide-react'
import { api } from '../api.js'
import { socket } from '../services/socket.js'
import PageHeader from '../components/PageHeader.jsx'
import toast from 'react-hot-toast'

export default function SourceHealthPage() {
  const [sources, setSources] = useState([])
  const [loading, setLoading] = useState(true)

  const fetchHealth = async () => {
    try {
      const controls = await api.controls()
      // Parse controls to extract health metrics
      const healthData = {}
      
      Object.entries(controls).forEach(([key, value]) => {
        if (key.startsWith("health_")) {
          const parts = key.split("_")
          const platform = parts[1]
          const metric = parts.slice(2).join("_")
          
          if (!healthData[platform]) healthData[platform] = { platform, jobs: 0, failures: 0, last_success: null, cooldown: null }
          
          if (metric === "jobs") healthData[platform].jobs = parseInt(value, 10) || 0
          if (metric === "failures") healthData[platform].failures = parseInt(value, 10) || 0
          if (metric === "last_success") healthData[platform].last_success = value
        } else if (key.startsWith("cooldown_")) {
          const platform = key.split("_")[1]
          if (!healthData[platform]) healthData[platform] = { platform, jobs: 0, failures: 0, last_success: null }
          
          const valParts = value.split("|")
          const expiresAt = new Date(valParts[0])
          
          if (expiresAt > new Date()) {
            healthData[platform].cooldown = { expiresAt, reason: valParts[1] || 'Rate limit' }
          }
        }
      })
      
      setSources(Object.values(healthData))
    } catch (e) {
      toast.error("Failed to load source health")
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchHealth()

    socket.on('scraper:health', () => fetchHealth())
    socket.on('scraper:cooldown', () => fetchHealth())

    return () => {
      socket.off('scraper:health')
      socket.off('scraper:cooldown')
    }
  }, [])

  const calculateHealthScore = (source) => {
    const total = source.jobs + source.failures
    if (total === 0) return 100
    
    const successRate = (source.jobs / total) * 100
    const banPenalty = source.failures > (source.jobs * 2) ? 50 : 0
    
    return Math.max(0, Math.min(100, Math.round(successRate - banPenalty)))
  }

  return (
    <div className="space-y-6 max-w-5xl" style={{ animation: 'fadeIn 0.4s ease-out both' }}>
      <PageHeader title="Source Health" sub="Real-time observability of discovery scrapers and rate limits." />
      
      {loading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {[...Array(2)].map((_, i) => <div key={i} className="skeleton h-48 rounded-2xl" />)}
        </div>
      ) : sources.length === 0 ? (
        <div className="p-8 rounded-2xl flex flex-col items-center justify-center text-slate-500 bg-white/[0.02] border border-white/[0.05]">
          <Server size={32} className="mb-3 opacity-50" />
          <p>No scraping sources initialized yet.</p>
          <p className="text-xs mt-1">Run a discovery cycle to populate health metrics.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {sources.map(source => {
            const score = calculateHealthScore(source)
            const isDegraded = score < 50
            
            return (
              <div 
                key={source.platform}
                className="p-5 rounded-2xl flex flex-col justify-between"
                style={{
                  background: 'linear-gradient(135deg, rgba(13,21,38,0.92) 0%, rgba(8,15,31,0.96) 100%)',
                  border: `1px solid ${source.cooldown ? 'rgba(248,113,113,0.3)' : isDegraded ? 'rgba(251,191,36,0.3)' : 'rgba(52,211,153,0.2)'}`,
                  boxShadow: '0 4px 24px rgba(0,0,0,0.4), inset 0 1px 0 rgba(255,255,255,0.04)',
                }}
              >
                <div>
                  <div className="flex items-center justify-between mb-4">
                    <h3 className="text-lg font-bold text-white capitalize flex items-center gap-2">
                      <Server size={18} className="text-slate-400" />
                      {source.platform}
                    </h3>
                    <div className="flex items-center gap-2">
                      {source.cooldown ? (
                        <span className="px-2 py-1 rounded-md bg-red-500/20 text-red-400 text-xs font-bold border border-red-500/30 flex items-center gap-1">
                          <AlertTriangle size={12} /> Cooldown
                        </span>
                      ) : isDegraded ? (
                        <span className="px-2 py-1 rounded-md bg-amber-500/20 text-amber-400 text-xs font-bold border border-amber-500/30 flex items-center gap-1">
                          <Activity size={12} /> Degraded
                        </span>
                      ) : (
                        <span className="px-2 py-1 rounded-md bg-emerald-500/20 text-emerald-400 text-xs font-bold border border-emerald-500/30 flex items-center gap-1">
                          <ShieldCheck size={12} /> Healthy
                        </span>
                      )}
                    </div>
                  </div>

                  <div className="grid grid-cols-3 gap-3 mb-4">
                    <div className="p-3 rounded-xl bg-white/[0.03] border border-white/[0.05]">
                      <p className="text-[10px] text-slate-500 uppercase font-bold tracking-wider mb-1">Health Score</p>
                      <p className={`text-xl font-black ${score >= 80 ? 'text-emerald-400' : score >= 50 ? 'text-amber-400' : 'text-red-400'}`}>
                        {score}%
                      </p>
                    </div>
                    <div className="p-3 rounded-xl bg-white/[0.03] border border-white/[0.05]">
                      <p className="text-[10px] text-slate-500 uppercase font-bold tracking-wider mb-1">Jobs Found</p>
                      <p className="text-xl font-black text-indigo-400">{source.jobs}</p>
                    </div>
                    <div className="p-3 rounded-xl bg-white/[0.03] border border-white/[0.05]">
                      <p className="text-[10px] text-slate-500 uppercase font-bold tracking-wider mb-1">Failures</p>
                      <p className="text-xl font-black text-slate-300">{source.failures}</p>
                    </div>
                  </div>
                </div>

                <div className="space-y-2 mt-2">
                  {source.cooldown && (
                    <div className="flex items-center gap-2 text-xs text-red-400 bg-red-500/10 p-2 rounded-lg border border-red-500/20">
                      <AlertTriangle size={14} />
                      <span>{source.cooldown.reason} (Expires: {source.cooldown.expiresAt.toLocaleTimeString()})</span>
                    </div>
                  )}
                  {source.last_success && (
                    <div className="flex items-center gap-2 text-xs text-slate-400 bg-white/[0.02] p-2 rounded-lg border border-white/[0.03]">
                      <Clock size={14} />
                      <span>Last Success: {new Date(source.last_success).toLocaleString()}</span>
                    </div>
                  )}
                </div>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
