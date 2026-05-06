// src/components/AgentConsole.jsx
// Live agent console — shows when running AND a success/error banner when done
import { CheckCircle2, XCircle, RotateCcw } from 'lucide-react'

const PHASES = ['scraper', 'matcher', 'queue', 'apply', 'sheets']

const PHASE_LABELS = {
  scraper: 'Scraping',
  matcher: 'Matching',
  queue:   'Ranking',
  apply:   'Applying',
  sheets:  'Sheets',
  init:    'Starting',
  done:    'Complete',
  error:   'Error',
}

// Strip noisy Python module prefixes from log messages
function cleanMsg(msg = '') {
  return msg
    .replace(/^\[[\w./\\:]+\]\s*/,  '')   // remove [module/path] prefix
    .replace(/^finder\.\w+\.\w+:\s*/i, '') // remove finder.x.y: prefix
    .replace(/^(INFO|DEBUG|WARNING|ERROR):\s*/i, '')
    .trim() || msg
}

function PhaseStep({ label, isActive, isDone }) {
  return (
    <div className="flex flex-col items-center gap-1.5">
      <div
        className="rounded-full transition-all duration-400"
        style={{
          width:  isActive ? 10 : 8,
          height: isActive ? 10 : 8,
          background: isActive
            ? 'linear-gradient(135deg, #818cf8, #6366f1)'
            : isDone ? 'rgba(52,211,153,0.7)' : 'rgba(255,255,255,0.08)',
          boxShadow: isActive
            ? '0 0 10px rgba(99,102,241,0.8), 0 0 20px rgba(99,102,241,0.4)'
            : isDone ? '0 0 6px rgba(52,211,153,0.4)' : 'none',
          border: `1px solid ${isActive ? 'rgba(99,102,241,0.6)' : isDone ? 'rgba(52,211,153,0.4)' : 'rgba(255,255,255,0.1)'}`,
          animation: isActive ? 'pulse 1s ease-in-out infinite' : 'none',
        }}
      />
      <div style={{ width: 28, height: 2, background: isDone ? 'rgba(52,211,153,0.4)' : isActive ? 'rgba(99,102,241,0.4)' : 'rgba(255,255,255,0.06)', borderRadius: 2, transition: 'background 0.4s' }} />
      <span style={{ fontSize: 9, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.08em', color: isActive ? '#818cf8' : isDone ? 'rgba(52,211,153,0.7)' : 'rgba(100,116,139,0.5)' }}>
        {PHASE_LABELS[label] || label}
      </span>
    </div>
  )
}

// ── Success / Error result banner (shown when done/error, not running) ─────────
function ResultBanner({ agent }) {
  if (!agent || agent.running) return null
  if (agent.phase !== 'done' && agent.phase !== 'error') return null

  const isSuccess = agent.phase === 'done'
  return (
    <div
      className="mb-6 rounded-2xl px-5 py-4 flex items-center gap-4"
      style={{
        background: isSuccess
          ? 'linear-gradient(135deg, rgba(52,211,153,0.08) 0%, rgba(13,21,38,0.95) 100%)'
          : 'linear-gradient(135deg, rgba(248,113,113,0.08) 0%, rgba(13,21,38,0.95) 100%)',
        border: `1px solid ${isSuccess ? 'rgba(52,211,153,0.25)' : 'rgba(248,113,113,0.25)'}`,
        boxShadow: isSuccess ? '0 0 24px rgba(52,211,153,0.08)' : '0 0 24px rgba(248,113,113,0.08)',
        animation: 'fadeIn 0.4s ease-out both',
      }}
    >
      <div
        className="p-2.5 rounded-xl flex-shrink-0"
        style={{ background: isSuccess ? 'rgba(52,211,153,0.15)' : 'rgba(248,113,113,0.15)' }}
      >
        {isSuccess
          ? <CheckCircle2 size={22} style={{ color: '#34d399' }} />
          : <XCircle      size={22} style={{ color: '#f87171' }} />
        }
      </div>
      <div className="flex-1">
        <p className="text-sm font-bold uppercase tracking-wider" style={{ color: isSuccess ? '#34d399' : '#f87171' }}>
          {isSuccess ? 'Cycle Completed Successfully ✅' : 'Cycle Error ⚠'}
        </p>
        <p className="text-slate-400 mt-0.5" style={{ fontSize: 12 }}>
          {isSuccess
            ? (agent.last_result
                ? `Scraped ${agent.last_result.scraped ?? '—'} · Matched ${agent.last_result.matched ?? '—'} · Applied ${agent.last_result.applied ?? '—'}`
                : 'All phases completed — dashboard updated')
            : (agent.error || 'An error occurred during the cycle')
          }
        </p>
      </div>
      {agent.last_run && (
        <span style={{ fontSize: 10, color: 'rgba(100,116,139,0.6)', fontFamily: 'monospace', flexShrink: 0 }}>
          {new Date(agent.last_run).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
        </span>
      )}
    </div>
  )
}

// ── Live running console ───────────────────────────────────────────────────────
export default function AgentConsole({ agent, isPaused, onResume, manualVerificationRequired }) {
  // Show result banner when not running but just finished
  if (!agent) return null
  if (!agent.running) return <ResultBanner agent={agent} />

  const currentIdx = PHASES.indexOf(agent.phase)

  return (
    <div
      className="mb-6 rounded-2xl overflow-hidden relative"
      style={{
        background: 'linear-gradient(135deg, rgba(13,21,38,0.95) 0%, rgba(8,15,31,0.98) 100%)',
        border: '1px solid rgba(99,102,241,0.3)',
        boxShadow: '0 0 30px rgba(99,102,241,0.12), 0 8px 32px rgba(0,0,0,0.5), inset 0 1px 0 rgba(255,255,255,0.06)',
        animation: 'fadeIn 0.35s ease-out',
        backdropFilter: 'blur(16px)',
      }}
    >
      {/* Top glow line */}
      <div style={{ position: 'absolute', inset: 0, top: 0, height: 1, background: 'linear-gradient(90deg, transparent, rgba(99,102,241,0.6), rgba(168,85,247,0.4), transparent)', pointerEvents: 'none' }} />

      {/* Header */}
      <div className="px-5 py-3 flex items-center justify-between" style={{ borderBottom: '1px solid rgba(255,255,255,0.06)' }}>
        <div className="flex items-center gap-3">
          <div className="flex gap-1.5">
            <span className="w-3 h-3 rounded-full" style={{ background: '#f87171' }} />
            <span className="w-3 h-3 rounded-full" style={{ background: '#fbbf24' }} />
            <span className="w-3 h-3 rounded-full" style={{ background: '#34d399' }} />
          </div>
          <div className="flex items-center gap-2">
            <span className="rounded-full" style={{ width: 7, height: 7, background: '#818cf8', boxShadow: '0 0 8px rgba(99,102,241,0.9)', animation: 'pulse 0.9s infinite' }} />
            <span style={{ fontSize: 11, fontWeight: 700, letterSpacing: '0.12em', textTransform: 'uppercase', color: '#818cf8' }}>
              Agent Active
            </span>
          </div>
        </div>
        <div className="flex items-center gap-3">
          {(isPaused || manualVerificationRequired) && (
            <button
              onClick={onResume}
              className="flex items-center gap-1.5 px-3 py-1 rounded-lg text-[10px] font-bold uppercase tracking-wider transition-all duration-200"
              style={{
                background: 'linear-gradient(135deg, #34d399, #10b981)',
                color: 'white',
                boxShadow: '0 0 15px rgba(52,211,153,0.3)',
                border: '1px solid rgba(52,211,153,0.4)',
              }}
              onMouseEnter={e => { e.currentTarget.style.transform = 'translateY(-1px)'; e.currentTarget.style.boxShadow = '0 0 20px rgba(52,211,153,0.5)' }}
              onMouseLeave={e => { e.currentTarget.style.transform = 'none'; e.currentTarget.style.boxShadow = '0 0 15px rgba(52,211,153,0.3)' }}
            >
              <Play size={11} fill="currentColor" />
              Resume Agent
            </button>
          )}
          <span style={{ fontSize: 10, color: 'rgba(100,116,139,0.8)', fontFamily: 'monospace', background: 'rgba(99,102,241,0.08)', padding: '2px 8px', borderRadius: 4, border: '1px solid rgba(99,102,241,0.15)' }}>
            {PHASE_LABELS[agent.phase] || agent.phase || 'initializing'}
          </span>
        </div>
      </div>

      <div className="p-5 grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Left: progress + phase pipeline */}
        <div className="space-y-5">
          <div>
            <p style={{ fontSize: 10, color: 'rgba(100,116,139,0.7)', textTransform: 'uppercase', letterSpacing: '0.1em', fontWeight: 700, marginBottom: 6 }}>
              Current Task
            </p>
            <div className="flex items-center justify-between">
              <p style={{ fontSize: 18, fontWeight: 800, color: '#e2e8f0', lineHeight: 1.3, letterSpacing: '-0.01em' }}>
                {manualVerificationRequired ? 'Waiting for Manual Verification' : (agent.progress || 'Starting…')}
              </p>
              {manualVerificationRequired && (
                <div 
                  className="px-2 py-1 rounded text-[10px] font-bold"
                  style={{ background: 'rgba(251,191,36,0.15)', color: '#fbbf24', border: '1px solid rgba(251,191,36,0.3)' }}
                >
                  ACTION NEEDED
                </div>
              )}
            </div>
            {manualVerificationRequired && (
              <p className="mt-1 text-slate-400" style={{ fontSize: 12 }}>
                Challenge: <span style={{ color: '#fbbf24', fontFamily: 'monospace' }}>{manualVerificationRequired}</span>
              </p>
            )}
          </div>

          <div className="flex gap-3 items-center">
            {PHASES.map((p, i) => (
              <PhaseStep
                key={p}
                label={p}
                isActive={agent.phase === p}
                isDone={currentIdx > i}
              />
            ))}
          </div>
        </div>

        {/* Right: live log terminal */}
        <div
          className="rounded-xl flex flex-col"
          style={{
            background: 'rgba(2,8,23,0.8)',
            border: '1px solid rgba(255,255,255,0.07)',
            height: 140,
            fontFamily: "'JetBrains Mono', 'Fira Code', monospace",
          }}
        >
          <div className="flex items-center justify-between px-3 py-1.5" style={{ borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
            <div className="flex items-center gap-1.5">
              <RotateCcw size={10} className="animate-spin" style={{ color: '#818cf8' }} />
              <span style={{ fontSize: 9, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.12em', color: 'rgba(100,116,139,0.8)' }}>
                Live Logs
              </span>
            </div>
            <span style={{ fontSize: 8, color: 'rgba(100,116,139,0.4)', fontWeight: 600 }}>STDOUT</span>
          </div>
          <div className="flex-1 overflow-y-auto px-3 py-2 space-y-1">
            {(agent.logs || []).map((l, i) => (
              <div key={i} className="flex gap-2" style={{ animation: 'fadeIn 0.25s ease-out both', fontSize: 9 }}>
                <span style={{ color: 'rgba(99,102,241,0.7)', flexShrink: 0 }}>[{l.time}]</span>
                <span style={{ color: '#94a3b8' }}>{cleanMsg(l.msg)}</span>
              </div>
            ))}
            {(!agent.logs || agent.logs.length === 0) && (
              <p style={{ fontSize: 9, color: 'rgba(100,116,139,0.5)', fontStyle: 'italic' }}>
                Initializing stream…
              </p>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
