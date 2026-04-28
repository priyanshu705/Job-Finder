import { useState, useEffect, useRef, useCallback, memo } from 'react'
import { Zap, Search, CheckCircle, XCircle, AlertCircle, RefreshCw, FileText, Database, Activity } from 'lucide-react'
import { api } from '../api.js'

const ICONS = {
  scrape:  { icon: Search,      color: 'text-blue-400',    bg: 'bg-blue-500/10' },
  match:   { icon: Zap,         color: 'text-purple-400',  bg: 'bg-purple-500/10' },
  apply:   { icon: CheckCircle, color: 'text-emerald-400', bg: 'bg-emerald-500/10' },
  failed:  { icon: XCircle,     color: 'text-red-400',     bg: 'bg-red-500/10' },
  cycle:   { icon: RefreshCw,   color: 'text-cyan-400',    bg: 'bg-cyan-500/10' },
  sheets:  { icon: FileText,    color: 'text-amber-400',   bg: 'bg-amber-500/10' },
  queue:   { icon: Database,    color: 'text-slate-400',   bg: 'bg-slate-500/10' },
  default: { icon: Activity,    color: 'text-slate-400',   bg: 'bg-slate-500/10' },
}

function getConfig(type = '') {
  const t = type.toLowerCase()
  if (t.includes('scrap'))  return ICONS.scrape
  if (t.includes('match'))  return ICONS.match
  if (t.includes('apply') || t.includes('applied')) return ICONS.apply
  if (t.includes('fail') || t.includes('error'))    return ICONS.failed
  if (t.includes('cycle'))  return ICONS.cycle
  if (t.includes('sheet'))  return ICONS.sheets
  if (t.includes('queue') || t.includes('rank'))    return ICONS.queue
  return ICONS.default
}

function timeAgo(ts) {
  if (!ts) return ''
  const diff = Date.now() - new Date(ts).getTime()
  const s = Math.floor(diff / 1000)
  if (s < 60)  return `${s}s ago`
  if (s < 3600) return `${Math.floor(s / 60)}m ago`
  return `${Math.floor(s / 3600)}h ago`
}

const ActivityFeed = memo(function ActivityFeed({ compact = false, limit = 30 }) {
  const [items, setItems] = useState([])
  const [loading, setLoading] = useState(true)
  const timerRef = useRef(null)

  const load = useCallback(async () => {
    try {
      const data = await api.activity(limit)
      setItems(Array.isArray(data) ? data : (data.items || data.activity || []))
    } catch { /* silent */ }
    finally { setLoading(false) }
  }, [limit])

  useEffect(() => {
    load()
    timerRef.current = setInterval(load, 4000)
    return () => clearInterval(timerRef.current)
  }, [load])

  if (loading) return (
    <div className="space-y-3">
      {[...Array(5)].map((_, i) => (
        <div key={i} className="flex gap-3 items-start">
          <div className="skeleton w-8 h-8 rounded-xl flex-shrink-0" />
          <div className="flex-1 space-y-1.5">
            <div className="skeleton h-3.5 w-3/4" />
            <div className="skeleton h-3 w-1/3" />
          </div>
        </div>
      ))}
    </div>
  )

  if (!items.length) return (
    <div className="flex flex-col items-center justify-center py-12 text-slate-500">
      <Activity size={32} className="mb-3 opacity-40" />
      <p className="text-sm">No activity yet — run a cycle!</p>
    </div>
  )

  const displayed = compact ? items.slice(0, 8) : items

  return (
    <div className="space-y-1">
      {displayed.map((item, i) => {
        const cfg = getConfig(item.type || item.event || item.action || '')
        const Icon = cfg.icon
        // Backend sends `msg`; fall back to other shapes defensively
        const msg = item.msg || item.message || item.detail || item.event || item.action || '—'
        // Extract a raw color name for the left border
        const borderColor = cfg.color.replace('text-', '').replace('-400', '')
        return (
          <div
            key={item.id || i}
            className="flex gap-3 items-start py-2 px-3 rounded-xl transition-all duration-150"
            style={{
              animation: `fadeIn 0.3s ease-out ${i * 0.04}s both`,
              borderLeft: '2px solid transparent',
            }}
            onMouseEnter={e => {
              e.currentTarget.style.background = 'rgba(99,102,241,0.05)'
              e.currentTarget.style.borderLeftColor = 'rgba(99,102,241,0.4)'
            }}
            onMouseLeave={e => {
              e.currentTarget.style.background = 'transparent'
              e.currentTarget.style.borderLeftColor = 'transparent'
            }}
          >
            <div
              className={`w-7 h-7 rounded-lg flex items-center justify-center flex-shrink-0 mt-0.5 ${cfg.bg}`}
              style={{ border: `1px solid ${cfg.color.includes('blue') ? 'rgba(99,102,241,0.2)' : cfg.color.includes('emerald') ? 'rgba(52,211,153,0.2)' : cfg.color.includes('purple') ? 'rgba(168,85,247,0.2)' : cfg.color.includes('red') ? 'rgba(248,113,113,0.2)' : cfg.color.includes('cyan') ? 'rgba(34,211,238,0.2)' : cfg.color.includes('amber') ? 'rgba(251,191,36,0.2)' : 'rgba(255,255,255,0.08)'}` }}
            >
              <Icon size={13} className={cfg.color} />
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm leading-snug truncate" style={{ color: '#cbd5e1' }}>{msg}</p>
              <p className="text-xs mt-0.5" style={{ color: 'rgba(100,116,139,0.7)', fontFamily: 'monospace', fontSize: 10 }}>
                {timeAgo(item.created_at || item.timestamp || item.ts)}
              </p>
            </div>
          </div>
        )
      })}
    </div>
  )
})

export default ActivityFeed
