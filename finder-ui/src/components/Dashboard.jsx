// src/components/Dashboard.jsx — Real-time live dashboard
import React, { useCallback, useState, useRef } from 'react'
import { api } from '../api'
import { useLive, useRelativeTime, useAction, isNewJob } from '../hooks'
import { Score, StatusBadge, ProgressBar, MiniChart, SectionCard } from './Shared'
import { SkeletonStat, SkeletonTable, SkeletonCard } from './Skeleton'
import CycleTimer    from './CycleTimer'
import ActivityFeed  from './ActivityFeed'

// ── Live Status Badge ─────────────────────────────────────────────────────────
function LiveStatus({ running, paused }) {
  const cfg = running
    ? { dot: 'var(--accent-light)', label: 'Processing', bg: 'var(--accent-dim)', border: 'var(--accent)' }
    : paused
    ? { dot: 'var(--yellow)',       label: 'Paused',      bg: 'var(--yellow-dim)', border: 'var(--yellow)' }
    : { dot: 'var(--green)',        label: 'Idle',         bg: 'var(--green-dim)',  border: 'var(--green)' }
  return (
    <div style={{
      display: 'inline-flex', alignItems: 'center', gap: 7,
      padding: '5px 12px', borderRadius: 20,
      background: cfg.bg, border: `1px solid ${cfg.border}`,
      fontSize: 12, fontWeight: 700,
    }}>
      <div style={{
        width: 8, height: 8, borderRadius: '50%',
        background: cfg.dot,
        animation: running ? 'pulse 0.8s infinite' : paused ? 'none' : 'pulse 2s infinite',
      }} />
      <span style={{ color: cfg.dot }}>{running ? '🟡' : paused ? '🔴' : '🟢'} {cfg.label}</span>
    </div>
  )
}

// ── Last Updated Label ────────────────────────────────────────────────────────
function LastUpdated({ ts }) {
  const label = useRelativeTime(ts)
  if (!ts) return null
  return (
    <span style={{ fontSize: 11, color: 'var(--text-muted)', fontFamily: 'monospace' }}>
      Last updated: {label}
    </span>
  )
}

// ── Apply Progress Bar (req #5) ───────────────────────────────────────────────
function ApplyProgress({ applied = 0, total = 5 }) {
  const pct = Math.min((applied / Math.max(total, 1)) * 100, 100)
  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12, marginBottom: 5 }}>
        <span style={{ color: 'var(--text-secondary)' }}>Applying progress</span>
        <span style={{ color: 'var(--accent-light)', fontWeight: 700 }}>{applied} / {total} jobs</span>
      </div>
      <div style={{ background: 'rgba(255,255,255,0.06)', borderRadius: 20, height: 8, overflow: 'hidden' }}>
        <div style={{
          height: '100%', borderRadius: 20,
          background: 'linear-gradient(90deg, var(--accent), var(--purple))',
          width: `${pct}%`,
          transition: 'width 0.6s ease',
          boxShadow: '0 0 8px var(--accent-glow)',
        }} />
      </div>
    </div>
  )
}

// ── Main Dashboard ────────────────────────────────────────────────────────────
export default function Dashboard({ toast }) {
  const [cycleRunning, setCycleRunning] = useState(false)
  const pollRef  = useRef(null)
  const { run }  = useAction(toast)

  // Real-time polling (req #1, #6, #12)
  const fetchStatus  = useCallback(() => api.status(),          [])
  const fetchSummary = useCallback(() => api.statsSummary(),    [])
  const fetchDaily   = useCallback(() => api.statsDaily(14),    [])
  const fetchQueue   = useCallback(() => api.queue({ limit: 8, sort: 'latest' }), [])
  const fetchCycle   = useCallback(() => api.cycleStatus(),     [])

  const { data: status,  lastUpdate: luStatus }  = useLive(fetchStatus,  4000)
  const { data: summary, lastUpdate: luSummary } = useLive(fetchSummary, 8000)
  const { data: daily }                          = useLive(fetchDaily,  30000)
  const { data: queue,   loading: qLoading }     = useLive(fetchQueue,   5000)
  const { data: cycle }                          = useLive(fetchCycle,   2000)

  // Sync cycleRunning with live API state
  const apiRunning = cycle?.running || false
  if (apiRunning !== cycleRunning && !cycleRunning) {/* detect externally started cycle */}

  const controls    = status?.controls  || {}
  const queueStat   = status?.queue     || {}
  const today       = status?.today     || {}
  const db          = status?.db_counts || {}
  const isPaused    = controls.paused === 'true'
  const dailyCap    = parseInt(controls.daily_cap || '10')
  const minMatch    = controls.min_match || '60'
  const totalApplied = (today.applied || 0) + (today.uncertain || 0)
  const isRunning   = cycleRunning || apiRunning

  // Chart data (req #2 — latest first from API, oldest first for chart)
  const chartData = (daily || []).slice(-14).map(d => ({
    label: d.day?.slice(5),
    value: (d.applied || 0) + (d.uncertain || 0),
  }))
  const scrapedChart = (daily || []).slice(-14).map(d => ({
    label: d.day?.slice(5),
    value: d.scraped || 0,
  }))

  // Optimistic cycle start (req #9)
  async function startCycle() {
    if (isRunning) return
    setCycleRunning(true)  // ← immediately show Running (optimistic)
    toast('🚀 Cycle started — 5 min budget', 'success')
    try {
      await api.cycle({ duration_minutes: 5, max_apply: 5 })
    } catch(e) {
      toast(`Cycle error: ${e.message}`, 'error')
    }
    // Poll until backend confirms done
    clearInterval(pollRef.current)
    pollRef.current = setInterval(async () => {
      try {
        const s = await api.cycleStatus()
        if (!s.running) {
          setCycleRunning(false)
          clearInterval(pollRef.current)
          toast('Cycle completed ✓', 'success')
        }
      } catch {
        setCycleRunning(false)
        clearInterval(pollRef.current)
      }
    }, 3000)
  }

  return (
    <div>
      {/* Header */}
      <div className="page-header">
        <div>
          <h2>🔍 Dashboard</h2>
          <p>Finder V6 — Intelligent Job Hunter</p>
        </div>
        <div className="header-actions" style={{ alignItems: 'center' }}>
          {/* Live status (req #3) */}
          <LiveStatus running={isRunning} paused={isPaused} />

          <button
            className={`btn ${isPaused ? 'btn-success' : 'btn-danger'}`}
            onClick={async () => {
              await (isPaused ? api.resume() : api.pause())
              toast(isPaused ? 'Agent resumed ▶' : 'Agent paused ⏸', 'info')
            }}
          >
            {isPaused ? '▶ Resume' : '⏸ Pause'}
          </button>

          <button className="btn btn-primary" onClick={startCycle} disabled={isRunning}>
            {isRunning ? '⏳ Running...' : '🚀 Run Cycle (5 min)'}
          </button>
        </div>
      </div>

      {/* Last updated (req #8) */}
      <div style={{ padding: '6px 32px 0', display: 'flex', justifyContent: 'flex-end' }}>
        <LastUpdated ts={luStatus} />
      </div>

      {/* Stopwatch (req #5 + CycleTimer) */}
      {isRunning && (
        <div style={{ padding: '12px 32px 0' }}>
          <CycleTimer isRunning={isRunning} />
          <div style={{ marginTop: 12 }}>
            <ApplyProgress applied={today.applied || 0} total={Math.min(dailyCap, 5)} />
          </div>
        </div>
      )}

      {/* Stats Grid (req #10 — skeleton on first load) */}
      <div className="stats-grid">
        {!status ? (
          Array.from({ length: 6 }, (_, i) => <SkeletonStat key={i} />)
        ) : [
          { label: 'Applied Today',  value: totalApplied,       sub: `cap: ${dailyCap}/day`,   color: 'green'  },
          { label: 'Pending',        value: queueStat.pending || 0, sub: 'ready to apply',     color: 'blue'   },
          { label: 'Total Scraped',  value: db.jobs || 0,       sub: 'jobs in DB',             color: 'cyan'   },
          { label: 'Failed Today',   value: today.failed || 0,  sub: 'errors',                 color: 'red'    },
          { label: 'Skipped',        value: queueStat.skip || 0, sub: 'below threshold',       color: 'yellow' },
          { label: 'Min Match',      value: `${minMatch}%`,     sub: 'score threshold',        color: 'purple' },
        ].map(s => (
          <div key={s.label} className={`stat-card ${s.color}`}>
            <div className="stat-label">{s.label}</div>
            <div className="stat-value">{s.value}</div>
            <div className="stat-sub">{s.sub}</div>
          </div>
        ))}
      </div>

      {/* Main grid */}
      <div className="content-grid grid-2" style={{ marginTop: 20 }}>

        {/* Today's progress */}
        <SectionCard title="Today's Progress" icon="📈">
          <div style={{ marginBottom: 12 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 6, fontSize: 13 }}>
              <span style={{ color: 'var(--text-secondary)' }}>Applications submitted</span>
              <span style={{ color: 'var(--accent-light)', fontWeight: 700 }}>{totalApplied} / {dailyCap}</span>
            </div>
            <ProgressBar value={totalApplied} max={dailyCap} color={totalApplied >= dailyCap ? 'yellow' : ''} />
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 10, marginTop: 16 }}>
            {[
              { label: '✅ Applied',   value: today.applied   || 0, color: 'var(--green)'  },
              { label: '⚠️ Uncertain', value: today.uncertain || 0, color: 'var(--yellow)' },
              { label: '❌ Failed',    value: today.failed    || 0, color: 'var(--red)'    },
            ].map(s => (
              <div key={s.label} style={{ textAlign: 'center' }}>
                <div style={{ fontSize: 22, fontWeight: 800, color: s.color }}>{s.value}</div>
                <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 2 }}>{s.label}</div>
              </div>
            ))}
          </div>
        </SectionCard>

        {/* Queue breakdown */}
        <SectionCard title="Queue Breakdown" icon="📋">
          {!status ? <div style={{ height: 80 }} /> :
            Object.entries(queueStat).length === 0
              ? <div style={{ color: 'var(--text-muted)', fontSize: 13 }}>No queue data yet</div>
              : Object.entries(queueStat).map(([st, cnt]) => (
                <div key={st} style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 8 }}>
                  <StatusBadge status={st} />
                  <div style={{ flex: 1 }}>
                    <ProgressBar value={cnt} max={db.queue || 1} />
                  </div>
                  <span style={{ fontWeight: 700, color: 'var(--text-primary)', fontSize: 14, minWidth: 28, textAlign: 'right' }}>{cnt}</span>
                </div>
              ))
          }
        </SectionCard>

        {/* Applications chart */}
        <SectionCard title="Applications (Last 14 Days)" icon="📊">
          <MiniChart data={chartData} color="var(--accent)" />
          <div style={{ display: 'flex', gap: 8, marginTop: 10, flexWrap: 'wrap' }}>
            {chartData.slice(-7).map((d, i) => (
              <span key={i} style={{ fontSize: 11, color: 'var(--text-muted)' }}>{d.label}</span>
            ))}
          </div>
        </SectionCard>

        {/* Activity feed (req #4) — spans remaining width */}
        <div style={{ gridRow: 'span 2' }}>
          <ActivityFeed />
        </div>

        {/* Top priority jobs — auto-refreshing, highlight new (req #2, #7) */}
        <SectionCard title="Top Priority Jobs" icon="🎯"
          action={
            <span style={{ fontSize: 10, color: 'var(--text-muted)', fontFamily: 'monospace' }}>
              auto-refresh 5s
            </span>
          }>
          {qLoading && !queue ? <SkeletonTable rows={5} /> : (
            <div className="table-wrap">
              <table>
                <thead>
                  <tr><th>Score</th><th>Title</th><th>Company</th><th>Status</th></tr>
                </thead>
                <tbody>
                  {(queue?.jobs || []).map(j => {
                    const isNew = isNewJob(j.queued_at, 5)  // highlight if added in last 5 min
                    return (
                      <tr key={j.id} style={{
                        background: isNew ? 'rgba(34,197,94,0.08)' : 'transparent',
                        borderLeft: isNew ? '3px solid var(--green)' : '3px solid transparent',
                        transition: 'background 0.5s',
                      }}>
                        <td><Score value={j.match_score_at_apply} /></td>
                        <td className="td-primary" style={{ maxWidth: 160, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                          {isNew && <span style={{ marginRight: 4, fontSize: 10 }}>🆕</span>}
                          {j.title || '—'}
                        </td>
                        <td style={{ maxWidth: 120, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{j.company || '—'}</td>
                        <td><StatusBadge status={j.status} /></td>
                      </tr>
                    )
                  })}
                  {!queue?.jobs?.length && (
                    <tr><td colSpan={4} style={{ textAlign: 'center', color: 'var(--text-muted)', padding: 24 }}>Run scraper + matcher first</td></tr>
                  )}
                </tbody>
              </table>
            </div>
          )}
        </SectionCard>

        {/* Scraped chart */}
        <SectionCard title="Jobs Scraped (Last 14 Days)" icon="🕷️">
          <MiniChart data={scrapedChart} color="var(--cyan)" />
          <div style={{ marginTop: 10, fontSize: 12, color: 'var(--text-muted)' }}>
            Total in DB: <strong style={{ color: 'var(--cyan)' }}>{db.jobs || 0}</strong> jobs
          </div>
        </SectionCard>

        {/* Quick actions */}
        <SectionCard title="Quick Actions" icon="⚡">
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
            {[
              { key: 'scraper',  label: '🕷️ Scrape (Headless)', fn: api.scrape,        cls: 'btn-ghost' },
              { key: 'scraperV', label: '🖥️ Scrape (Visible)',  fn: api.scrapeVisible, cls: 'btn-ghost' },
              { key: 'matcher',  label: '🎯 Score Jobs',         fn: api.match,         cls: 'btn-ghost' },
              { key: 'rank',     label: '📊 Re-rank Queue',      fn: api.rank,          cls: 'btn-ghost' },
            ].map(a => (
              <button key={a.key + a.label}
                className={`btn ${a.cls} btn-lg`}
                style={{ width: '100%', justifyContent: 'center' }}
                onClick={() => run(a.key, a.fn, a.label)}
              >
                {a.label}
              </button>
            ))}
          </div>

          <div style={{ marginTop: 14, padding: '10px 14px', background: 'var(--bg-glass)', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border)' }}>
            <div style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 6, textTransform: 'uppercase', letterSpacing: '0.8px', fontWeight: 600 }}>Current Settings</div>
            <div style={{ display: 'flex', gap: 16, fontSize: 13, flexWrap: 'wrap' }}>
              <LiveStatus running={isRunning} paused={isPaused} />
              <span style={{ color: 'var(--text-muted)' }}>Min: {minMatch}%</span>
              <span style={{ color: 'var(--text-muted)' }}>Cap: {dailyCap}/day</span>
            </div>
          </div>
        </SectionCard>

      </div>
    </div>
  )
}
