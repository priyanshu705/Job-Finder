import { RefreshCw, Play, Pause, RotateCcw, Menu } from 'lucide-react'

const PAGE_TITLES = {
  dashboard: 'Dashboard',
  queue:     'Apply Queue',
  goals:     'Goals',
  activity:  'Activity Feed',
  analytics: 'Analytics',
  settings:  'Settings',
}

function fmt(d) {
  if (!d) return '—'
  return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })
}

export default function Navbar({ page, running, isPaused, lastUpdated, onCycle, onPause, onResume, onRefresh, onMenuToggle }) {
  return (
    <header className="h-16 bg-navy-900 border-b border-slate-700/50 flex items-center px-4 gap-4 flex-shrink-0">
      {/* Menu toggle */}
      <button onClick={onMenuToggle} className="p-2 rounded-xl text-slate-500 hover:text-slate-300 hover:bg-white/5 transition-all">
        <Menu size={18} />
      </button>

      {/* Page title */}
      <h1 className="font-semibold text-slate-100 text-base">{PAGE_TITLES[page]}</h1>

      {/* Live indicator */}
      <div className="flex items-center gap-1.5 text-xs text-slate-500 ml-1">
        <span className={`w-2 h-2 rounded-full ${isPaused ? 'bg-amber-400' : 'bg-emerald-400 animate-pulse'}`} />
        <span className={isPaused ? 'text-amber-400' : 'text-emerald-400'}>{isPaused ? 'Paused' : 'Live'}</span>
      </div>

      <div className="flex-1" />

      {/* Last updated */}
      {lastUpdated && (
        <span className="text-xs text-slate-500 hidden sm:block">
          Updated {fmt(lastUpdated)}
        </span>
      )}

      {/* Refresh */}
      <button
        onClick={onRefresh}
        className="p-2 rounded-xl text-slate-500 hover:text-slate-300 hover:bg-white/5 transition-all"
        title="Refresh"
      >
        <RefreshCw size={16} />
      </button>

      {/* Pause / Resume */}
      {isPaused ? (
        <button onClick={onResume} className="btn-success">
          <Play size={14} /> Resume
        </button>
      ) : (
        <button onClick={onPause} className="btn-secondary">
          <Pause size={14} /> Pause
        </button>
      )}

      {/* Run Cycle */}
      <button
        onClick={onCycle}
        disabled={running}
        className="btn-primary"
      >
        {running
          ? <><RotateCcw size={14} className="animate-spin" /> Running…</>
          : <><Play size={14} /> Run Cycle</>
        }
      </button>
    </header>
  )
}
