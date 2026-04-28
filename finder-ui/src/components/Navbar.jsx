import { memo } from 'react'
import { RefreshCw, Play, Pause, RotateCcw, Menu } from 'lucide-react'

const PAGE_TITLES = {
  dashboard: 'Dashboard',
  queue:     'Apply Queue',
  goals:     'Goals',
  activity:  'Activity Feed',
  analytics: 'Analytics',
  settings:  'Settings',
}
const PAGE_SUBS = {
  dashboard: 'Real-time overview',
  queue:     'Manage job applications',
  goals:     'Track your targets',
  activity:  'Agent event log',
  analytics: 'Performance insights',
  settings:  'Configure the agent',
}

function fmt(d) {
  if (!d) return '—'
  return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })
}

const Navbar = memo(function Navbar({ page, running, isPaused, lastUpdated, onCycle, onPause, onResume, onRefresh, onMenuToggle }) {
  return (
    <header
      className="h-16 flex items-center px-4 gap-3 flex-shrink-0 relative"
      style={{
        background: 'linear-gradient(180deg, rgba(8,15,31,0.98) 0%, rgba(13,21,38,0.95) 100%)',
        borderBottom: '1px solid rgba(99,102,241,0.12)',
        backdropFilter: 'blur(24px)',
        WebkitBackdropFilter: 'blur(24px)',
        boxShadow: '0 4px 24px rgba(0,0,0,0.3), inset 0 -1px 0 rgba(255,255,255,0.04)',
      }}
    >
      {/* Menu toggle */}
      <button
        onClick={onMenuToggle}
        aria-label="Toggle sidebar"
        className="p-2 rounded-xl transition-all duration-200 flex-shrink-0"
        style={{ background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.07)', color: 'rgba(148,163,184,0.7)' }}
        onMouseEnter={e => { e.currentTarget.style.background = 'rgba(99,102,241,0.1)'; e.currentTarget.style.color = '#818cf8' }}
        onMouseLeave={e => { e.currentTarget.style.background = 'rgba(255,255,255,0.04)'; e.currentTarget.style.color = 'rgba(148,163,184,0.7)' }}
      >
        <Menu size={17} />
      </button>

      {/* Page title block */}
      <div className="flex flex-col leading-none mr-2">
        <div
          className="font-bold"
          style={{
            fontSize: 15,
            background: 'linear-gradient(135deg, #e2e8f0, #94a3b8)',
            WebkitBackgroundClip: 'text',
            WebkitTextFillColor: 'transparent',
            backgroundClip: 'text',
            letterSpacing: '-0.01em',
          }}
        >
          {PAGE_TITLES[page]}
        </div>
        <span style={{ fontSize: 10, color: 'rgba(100,116,139,0.8)', marginTop: 1 }}>
          {PAGE_SUBS[page]}
        </span>
      </div>

      {/* Live status pill */}
      <div
        className="hidden sm:flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-semibold"
        style={{
          background: isPaused
            ? 'rgba(251,191,36,0.1)'
            : running
            ? 'rgba(99,102,241,0.12)'
            : 'rgba(52,211,153,0.1)',
          border: `1px solid ${isPaused ? 'rgba(251,191,36,0.25)' : running ? 'rgba(99,102,241,0.3)' : 'rgba(52,211,153,0.25)'}`,
          color: isPaused ? '#fbbf24' : running ? '#818cf8' : '#34d399',
          boxShadow: isPaused ? '0 0 12px rgba(251,191,36,0.15)' : running ? '0 0 12px rgba(99,102,241,0.2)' : '0 0 12px rgba(52,211,153,0.15)',
        }}
      >
        <span
          className="rounded-full"
          style={{
            width: 6, height: 6,
            background: isPaused ? '#fbbf24' : running ? '#818cf8' : '#34d399',
            boxShadow: isPaused ? '0 0 6px #fbbf24' : running ? '0 0 6px #818cf8' : '0 0 6px #34d399',
            animation: running ? 'pulse 0.9s infinite' : 'pulse 2.5s infinite',
          }}
        />
        {isPaused ? 'Paused' : running ? 'Running' : 'Live'}
      </div>

      <div className="flex-1" />

      {/* Last updated */}
      {lastUpdated && (
        <span
          className="text-xs hidden md:block"
          style={{ color: 'rgba(100,116,139,0.7)', fontFamily: 'monospace' }}
        >
          ↻ {fmt(lastUpdated)}
        </span>
      )}

      {/* Refresh */}
      <button
        onClick={onRefresh}
        title="Refresh"
        className="p-2 rounded-xl transition-all duration-200"
        style={{ color: 'rgba(148,163,184,0.6)', background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.06)' }}
        onMouseEnter={e => { e.currentTarget.style.color = '#818cf8'; e.currentTarget.style.background = 'rgba(99,102,241,0.1)' }}
        onMouseLeave={e => { e.currentTarget.style.color = 'rgba(148,163,184,0.6)'; e.currentTarget.style.background = 'rgba(255,255,255,0.03)' }}
      >
        <RefreshCw size={15} />
      </button>

      {/* Pause / Resume */}
      {isPaused ? (
        <button onClick={onResume} className="btn-success" style={{ fontSize: 12, paddingTop: 7, paddingBottom: 7 }}>
          <Play size={13} /> Resume
        </button>
      ) : (
        <button onClick={onPause} className="btn-secondary" style={{ fontSize: 12, paddingTop: 7, paddingBottom: 7 }}>
          <Pause size={13} /> Pause
        </button>
      )}

      {/* Run Cycle — primary gradient CTA */}
      <button
        onClick={onCycle}
        disabled={running}
        className="btn-primary"
        style={{ fontSize: 12, paddingTop: 7, paddingBottom: 7 }}
      >
        {running
          ? <><RotateCcw size={13} className="animate-spin" /> Running…</>
          : <><Play size={13} /> Run Cycle</>
        }
      </button>
    </header>
  )
})

export default Navbar
