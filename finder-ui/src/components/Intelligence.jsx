// src/components/Intelligence.jsx
import React, { useCallback } from 'react'
import { api } from '../api'
import { useLive, useRelativeTime, useAction } from '../hooks'
import { Empty, SectionCard } from './Shared'
import { SkeletonTable } from './Skeleton'

export default function Intelligence({ toast }) {
  const fetchInsights  = useCallback(() => api.insights(), [])
  const fetchCompanies = useCallback(() => api.companies(), [])

  const { data: insights,  loading: li, lastUpdate } = useLive(fetchInsights,  15000)
  const { data: companies, loading: lc }              = useLive(fetchCompanies, 15000)
  const updLabel = useRelativeTime(lastUpdate)
  const { running, run } = useAction(toast)

  const skills     = insights?.best_skills      || []
  const threshHist = insights?.threshold_history || []
  const failPat    = insights?.failure_patterns  || []
  const outcomes   = insights?.outcomes          || []

  const tierEmoji  = { tier1:'🌟', tier2:'⭐', startup:'🚀', blacklist:'🚫', unknown:'❓' }
  const tierColor  = { tier1:'var(--green)', tier2:'var(--accent-light)', startup:'var(--cyan)', blacklist:'var(--red)', unknown:'var(--text-muted)' }

  const totalOutcomes  = outcomes.reduce((a, o) => a + (o.cnt || 0), 0)

  return (
    <div>
      <div className="page-header">
        <div>
          <h2>🧠 Intelligence</h2>
          <p>Company learning, skill outcome map, and threshold optimisation</p>
        </div>
        <div className="header-actions">
          <span style={{ fontSize: 11, color: 'var(--text-muted)', fontFamily: 'monospace', alignSelf: 'center' }}>
            auto-refresh · {updLabel}
          </span>
          <button className="btn btn-primary" onClick={() => run('intelligence', api.cycle, 'Intelligence')} disabled={running.intelligence}>
            {running.intelligence ? '⏳' : '🔄 Run Analysis'}
          </button>
        </div>
      </div>

      <div className="content-grid grid-2">

        {/* Outcome breakdown */}
        <SectionCard title="Application Outcomes (All-Time)" icon="📊">
          {outcomes.length === 0
            ? <Empty icon="📭" msg="No outcomes recorded yet. Apply to jobs first." />
            : outcomes.map(o => {
              const pct = Math.round((o.cnt / totalOutcomes) * 100)
              const color = o.outcome === 'applied' || o.outcome === 'interview' || o.outcome === 'offer'
                ? 'var(--green)' : o.outcome === 'failed' ? 'var(--red)' : 'var(--text-muted)'
              return (
                <div key={o.outcome} style={{ marginBottom: 12 }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 13, marginBottom: 4 }}>
                    <span style={{ color: 'var(--text-primary)', fontWeight: 500 }}>{o.outcome}</span>
                    <span style={{ color, fontWeight: 700 }}>{o.cnt} ({pct}%)</span>
                  </div>
                  <div style={{ background: 'rgba(255,255,255,0.06)', borderRadius: 20, height: 6, overflow: 'hidden' }}>
                    <div style={{ height: '100%', borderRadius: 20, background: color, width: `${pct}%`, transition: 'width 0.8s' }} />
                  </div>
                </div>
              )
            })
          }
        </SectionCard>

        {/* Threshold history */}
        <SectionCard title="Threshold History" icon="📈">
          {threshHist.length === 0
            ? <Empty icon="📭" msg="No threshold changes yet. Need 3+ outcomes." />
            : (
              <table style={{ width: '100%', fontSize: 12, borderCollapse: 'collapse' }}>
                <thead>
                  <tr>
                    {['Date','Threshold','Success Rate','Applied','Failed'].map(h => (
                      <th key={h} style={{ textAlign:'left', padding:'6px 8px', color:'var(--text-muted)', fontSize:10, textTransform:'uppercase', letterSpacing:'0.6px', borderBottom:'1px solid var(--border)' }}>{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {threshHist.map((r, i) => (
                    <tr key={i}>
                      <td style={{ padding:'7px 8px', color:'var(--text-muted)', fontFamily:'monospace' }}>{r.date}</td>
                      <td style={{ padding:'7px 8px', color:'var(--accent-light)', fontWeight:700 }}>{r.threshold}%</td>
                      <td style={{ padding:'7px 8px', color:'var(--green)' }}>{((r.success_rate||0)*100).toFixed(1)}%</td>
                      <td style={{ padding:'7px 8px', color:'var(--text-secondary)' }}>{r.applied}</td>
                      <td style={{ padding:'7px 8px', color:'var(--red)' }}>{r.failed}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )
          }
        </SectionCard>

        {/* Top skills */}
        <SectionCard title="Top Skills by Positive Outcome" icon="✅">
          {skills.length === 0
            ? <Empty icon="🔬" msg="Gathering skill data... apply to more jobs." />
            : skills.map((s, i) => {
              const pct = Math.round((s.positive / Math.max(s.total, 1)) * 100)
              return (
                <div key={s.skill} style={{ display:'flex', alignItems:'center', gap:10, marginBottom:10 }}>
                  <span style={{ fontSize:11, color:'var(--text-muted)', fontFamily:'monospace', minWidth:18, textAlign:'right' }}>#{i+1}</span>
                  <span style={{ fontWeight:600, color:'var(--text-primary)', minWidth:120, fontSize:13 }}>{s.skill}</span>
                  <div style={{ flex:1, background:'rgba(255,255,255,0.06)', borderRadius:20, height:6, overflow:'hidden' }}>
                    <div style={{ height:'100%', borderRadius:20, background:'var(--green)', width:`${pct}%`, transition:'width 0.8s' }} />
                  </div>
                  <span style={{ fontSize:12, color:'var(--green)', fontWeight:600, minWidth:36, textAlign:'right' }}>{s.positive}</span>
                </div>
              )
            })
          }
        </SectionCard>

        {/* Failure patterns */}
        <SectionCard title="Failure Patterns" icon="🔴">
          {failPat.length === 0
            ? <Empty icon="✨" msg="No failure patterns detected yet." />
            : (
              <table style={{ width:'100%', fontSize:12, borderCollapse:'collapse' }}>
                <thead>
                  <tr>
                    {['Error Type','Platform','Hour','Count'].map(h => (
                      <th key={h} style={{ textAlign:'left', padding:'6px 8px', color:'var(--text-muted)', fontSize:10, textTransform:'uppercase', letterSpacing:'0.6px', borderBottom:'1px solid var(--border)' }}>{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {failPat.map((r, i) => (
                    <tr key={i}>
                      <td style={{ padding:'7px 8px', color:'var(--red)' }}>{r.error_type}</td>
                      <td style={{ padding:'7px 8px', color:'var(--text-secondary)' }}>{r.platform}</td>
                      <td style={{ padding:'7px 8px', color:'var(--yellow)', fontFamily:'monospace' }}>{r.hour_of_day}:00</td>
                      <td style={{ padding:'7px 8px', color:'var(--text-primary)', fontWeight:700 }}>{r.count}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )
          }
        </SectionCard>

        {/* Company intelligence */}
        <div style={{ gridColumn: '1 / -1' }}>
          <SectionCard title="Company Intelligence" icon="🏢">
            {lc && !companies ? <SkeletonTable rows={4} /> : !companies?.length
              ? <Empty icon="🏢" msg="No company data yet. Apply to jobs to build intelligence." />
              : (
                <div className="table-wrap">
                  <table>
                    <thead>
                      <tr>
                        <th>Company</th><th>Tier</th><th>Applied</th><th>Interviews</th>
                        <th>Interview Rate</th><th>Response Rate</th><th>Avg Days</th>
                      </tr>
                    </thead>
                    <tbody>
                      {companies.map(c => (
                        <tr key={c.company}>
                          <td className="td-primary">{c.company}</td>
                          <td>
                            <span style={{ color: tierColor[c.tier] || 'var(--text-muted)', fontWeight:600, fontSize:13 }}>
                              {tierEmoji[c.tier] || '❓'} {c.tier}
                            </span>
                          </td>
                          <td style={{ fontFamily:'monospace' }}>{c.total_applies}</td>
                          <td style={{ fontFamily:'monospace', color:'var(--green)' }}>{c.total_interviews}</td>
                          <td>
                            <span style={{ color: (c.interview_rate||0) >= 0.2 ? 'var(--green)' : (c.interview_rate||0) >= 0.1 ? 'var(--yellow)' : 'var(--red)', fontWeight:600 }}>
                              {((c.interview_rate||0)*100).toFixed(0)}%
                            </span>
                          </td>
                          <td><span style={{ color:'var(--accent-light)' }}>{((c.response_rate||0)*100).toFixed(0)}%</span></td>
                          <td style={{ fontFamily:'monospace', color:'var(--text-muted)' }}>{(c.avg_response_days||0).toFixed(1)}d</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )
            }
          </SectionCard>
        </div>

      </div>
    </div>
  )
}
