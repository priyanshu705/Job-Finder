// src/components/Queue.jsx
import React, { useState, useCallback } from 'react'
import { api } from '../api'
import { useLive, useRelativeTime, useAction, isNewJob } from '../hooks'
import { Empty, Score, StatusBadge, SectionCard } from './Shared'
import { SkeletonTable } from './Skeleton'

const STATUS_TABS = ['all','pending','applied','skip','failed','uncertain','external_skip']

export default function Queue({ toast }) {
  const [statusFilter, setStatusFilter] = useState('all')
  const [sortMode,     setSortMode]     = useState('priority')
  const [offset, setOffset] = useState(0)
  const [selectedJob, setSelectedJob] = useState(null)
  const LIMIT = 30

  const fetchQueue = useCallback(
    () => api.queue({ status: statusFilter === 'all' ? '' : statusFilter, limit: LIMIT, offset, sort: sortMode }),
    [statusFilter, offset, sortMode]
  )
  // Auto-refresh every 5s — no manual button (req #6)
  const { data, loading, lastUpdate } = useLive(fetchQueue, 5000)
  const { running, run } = useAction(toast)
  const updLabel = useRelativeTime(lastUpdate)

  const jobs  = data?.jobs  || []
  const total = data?.total || 0

  function handleTabChange(t) { setStatusFilter(t); setOffset(0) }

  return (
    <div>
      <div className="page-header">
        <div>
          <h2>📋 Application Queue</h2>
          <p>
            {total} total · {jobs.length} shown ·{' '}
            <span style={{ fontFamily: 'monospace', fontSize: 11, color: 'var(--text-muted)' }}>
              auto-refresh · {updLabel}
            </span>
          </p>
        </div>
        <div className="header-actions">
          {/* Sort toggle (req #2) */}
          <button className={`btn btn-sm ${sortMode === 'priority' ? 'btn-primary' : 'btn-ghost'}`}
            onClick={() => setSortMode('priority')}>🎯 Priority</button>
          <button className={`btn btn-sm ${sortMode === 'latest' ? 'btn-primary' : 'btn-ghost'}`}
            onClick={() => setSortMode('latest')}>🕒 Latest</button>
          <button className="btn btn-ghost btn-sm" onClick={() => run('match', api.match, 'Matcher')} disabled={running.match}>
            {running.match ? '⏳' : '🎯 Score All'}
          </button>
          <button className="btn btn-ghost btn-sm" onClick={() => run('rank', api.rank, 'Queue rank')} disabled={running.rank}>
            {running.rank ? '⏳' : '📊 Re-rank'}
          </button>
          <button className="btn btn-danger btn-sm"
            onClick={async () => { await api.reset(); toast('Queue reset', 'info') }}>
            🔄 Reset
          </button>
        </div>
      </div>

      {/* Status tabs */}
      <div style={{ padding: '12px 32px 0', display: 'flex', gap: 6, flexWrap: 'wrap' }}>
        {STATUS_TABS.map(t => (
          <button key={t}
            className={`btn btn-sm ${statusFilter === t ? 'btn-primary' : 'btn-ghost'}`}
            onClick={() => handleTabChange(t)}
          >
            {t === 'all' ? '🔍 All' : t}
          </button>
        ))}
      </div>

      <div className="content-grid" style={{ gridTemplateColumns: selectedJob ? '1fr 380px' : '1fr', marginTop: 16 }}>

        <SectionCard title={`${statusFilter === 'all' ? 'All Jobs' : statusFilter.toUpperCase()} (${total})`} icon="">
          {/* Skeleton on first load (req #10) */}
          {loading && !data
            ? <SkeletonTable rows={8} />
            : jobs.length === 0
            ? <Empty icon="📭" msg="No jobs in this status. Run scraper + matcher." />
            : (
              <div className="table-wrap">
                <table>
                  <thead>
                    <tr>
                      <th></th>
                      <th>Score</th><th>Boost</th><th>Title</th><th>Company</th>
                      <th>Form</th><th>Status</th><th>Added</th>
                    </tr>
                  </thead>
                  <tbody>
                    {jobs.map(j => {
                      // req #7 — highlight jobs added in last 5 minutes
                      const _isNew = isNewJob(j.queued_at, 5)
                      return (
                        <tr key={j.id}
                          style={{
                            cursor: 'pointer',
                            background: selectedJob?.id === j.id
                              ? 'var(--accent-dim)'
                              : _isNew ? 'rgba(34,197,94,0.07)' : 'transparent',
                            borderLeft: _isNew ? '3px solid var(--green)' : '3px solid transparent',
                            transition: 'background 0.4s',
                          }}
                          onClick={() => setSelectedJob(j)}
                        >
                          <td style={{ padding: '8px 6px 8px 8px', fontSize: 12 }}>
                            {_isNew ? '🆕' : ''}
                          </td>
                          <td><Score value={j.match_score_at_apply} /></td>
                          <td className="td-mono" style={{ color: 'var(--purple)', fontSize: 12 }}>
                            {j.goal_boost != null ? `G:${Math.round(j.goal_boost)}` : '—'}
                          </td>
                          <td className="td-primary" style={{ maxWidth: 200, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                            {j.title || '—'}
                          </td>
                          <td style={{ maxWidth: 140, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{j.company || '—'}</td>
                          <td>
                            <span className={`badge ${j.form_type === 'easy_apply' ? 'badge-green' : j.form_type === 'external' ? 'badge-purple' : 'badge-muted'}`}>
                              {j.form_type || '—'}
                            </span>
                          </td>
                          <td><StatusBadge status={j.status} /></td>
                          <td style={{ fontSize: 11, color: 'var(--text-muted)', fontFamily: 'monospace' }}>
                            {(j.queued_at || '').slice(5, 16)}
                          </td>
                        </tr>
                      )
                    })}
                  </tbody>
                </table>
              </div>
            )
          }
          {/* Pagination */}
          {total > LIMIT && (
            <div style={{ display: 'flex', gap: 8, marginTop: 14, alignItems: 'center', justifyContent: 'flex-end' }}>
              <button className="btn btn-ghost btn-sm" disabled={offset === 0} onClick={() => setOffset(Math.max(0, offset - LIMIT))}>← Prev</button>
              <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>{offset + 1}–{Math.min(offset + LIMIT, total)} of {total}</span>
              <button className="btn btn-ghost btn-sm" disabled={offset + LIMIT >= total} onClick={() => setOffset(offset + LIMIT)}>Next →</button>
            </div>
          )}
        </SectionCard>

        {/* Job detail panel */}
        {selectedJob && (
          <div className="card" style={{ alignSelf: 'start', position: 'sticky', top: 16 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 16 }}>
              <div className="card-title" style={{ margin: 0 }}>Job Detail</div>
              <button className="btn btn-ghost btn-sm" onClick={() => setSelectedJob(null)}>✕</button>
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
              <div>
                <div style={{ fontSize: 15, fontWeight: 700, color: 'var(--text-primary)', lineHeight: 1.3 }}>{selectedJob.title}</div>
                <div style={{ fontSize: 13, color: 'var(--accent-light)', marginTop: 3 }}>{selectedJob.company}</div>
              </div>

              {[
                ['Platform',  selectedJob.platform],
                ['Location',  selectedJob.location],
                ['Salary',    selectedJob.salary],
                ['Form Type', selectedJob.form_type],
                ['Posted',    selectedJob.posted_at],
              ].filter(([,v]) => v).map(([k, v]) => (
                <div key={k} style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12 }}>
                  <span style={{ color: 'var(--text-muted)' }}>{k}</span>
                  <span style={{ color: 'var(--text-primary)', maxWidth: 180, textAlign: 'right' }}>{v}</span>
                </div>
              ))}

              <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                <div style={{ textAlign: 'center', flex: 1, background: 'var(--bg-glass)', borderRadius: 6, padding: '8px 4px' }}>
                  <Score value={selectedJob.match_score_at_apply} />
                  <div style={{ fontSize: 10, color: 'var(--text-muted)', marginTop: 2 }}>Match</div>
                </div>
                <div style={{ textAlign: 'center', flex: 1, background: 'var(--bg-glass)', borderRadius: 6, padding: '8px 4px' }}>
                  <span style={{ color: 'var(--purple)', fontWeight: 700 }}>G:{Math.round(selectedJob.goal_boost || 0)}</span>
                  <div style={{ fontSize: 10, color: 'var(--text-muted)', marginTop: 2 }}>Goal</div>
                </div>
                <div style={{ textAlign: 'center', flex: 1, background: 'var(--bg-glass)', borderRadius: 6, padding: '8px 4px' }}>
                  <span style={{ color: 'var(--red)', fontWeight: 700 }}>{(selectedJob.risk_score || 0).toFixed(2)}</span>
                  <div style={{ fontSize: 10, color: 'var(--text-muted)', marginTop: 2 }}>Risk</div>
                </div>
              </div>

              <StatusBadge status={selectedJob.status} />

              {selectedJob.skills && (
                <div>
                  <div style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 6, textTransform: 'uppercase', letterSpacing: '0.5px' }}>Skills</div>
                  <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap' }}>
                    {selectedJob.skills.split(',').slice(0,10).map((s, i) => (
                      <span key={i} className="badge badge-blue" style={{ fontSize: 10 }}>{s.trim()}</span>
                    ))}
                  </div>
                </div>
              )}

              {selectedJob.last_error && (
                <div style={{ background: 'var(--red-dim)', border: '1px solid rgba(239,68,68,0.3)', borderRadius: 6, padding: '8px 10px', fontSize: 11, color: 'var(--red)' }}>
                  ❌ {selectedJob.last_error}
                </div>
              )}

              <a href={selectedJob.job_url} target="_blank" rel="noreferrer"
                className="btn btn-ghost"
                style={{ textDecoration: 'none', justifyContent: 'center' }}>
                🔗 Open Job Page
              </a>

              {/* Record outcome */}
              <div style={{ borderTop: '1px solid var(--border)', paddingTop: 12 }}>
                <div style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 8, textTransform: 'uppercase', letterSpacing: '0.5px' }}>Record Outcome</div>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 6 }}>
                  {['interview','offer','rejected','no_response'].map(o => (
                    <button key={o}
                      className={`btn btn-sm ${o === 'interview' || o === 'offer' ? 'btn-success' : 'btn-ghost'}`}
                      onClick={async () => {
                        await api.recordOutcome({ job_url: selectedJob.job_url, outcome: o })
                        toast(`Outcome recorded: ${o}`, 'success')
                      }}
                    >
                      {o === 'interview' ? '📞' : o === 'offer' ? '🎉' : o === 'rejected' ? '❌' : '📭'} {o}
                    </button>
                  ))}
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
