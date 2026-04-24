// src/components/Goals.jsx
import React, { useState, useCallback } from 'react'
import { api } from '../api'
import { useLive } from '../hooks'
import { Loading, Empty, SectionCard } from './Shared'

const GOAL_TYPES = ['skill','title','keyword','company','location','salary']
const PRIORITY_LABELS = { 9:'Critical',8:'High',7:'High',6:'Medium',5:'Medium',4:'Low',3:'Low',2:'Minimal',1:'Minimal' }

export default function Goals({ toast }) {
  const [form, setForm] = useState({ goal_type: 'skill', value: '', priority: 7 })
  const fetchGoals = useCallback(() => api.goals(), [])
  const { data: goals, loading, reload } = useLive(fetchGoals, 10000)

  async function addGoal(e) {
    e.preventDefault()
    if (!form.value.trim()) { toast('Enter a goal value', 'error'); return }
    try {
      await api.addGoal({ ...form, priority: parseInt(form.priority) })
      toast(`Goal added: [${form.goal_type}] '${form.value}'`, 'success')
      setForm(f => ({ ...f, value: '' }))
      reload()
    } catch(e) { toast('Failed to add goal', 'error') }
  }

  async function deleteGoal(id, val) {
    try {
      await api.deleteGoal(id)
      toast(`Goal '${val}' removed`, 'info')
      reload()
    } catch(e) { toast('Failed to delete', 'error') }
  }

  const typeColors = { skill:'badge-green', title:'badge-blue', keyword:'badge-purple', company:'badge-yellow', location:'badge-cyan', salary:'badge-muted' }

  return (
    <div>
      <div className="page-header">
        <div>
          <h2>🎯 Goals</h2>
          <p>Define what you're looking for. Goals boost matching priority scores.</p>
        </div>
      </div>

      <div className="content-grid grid-2">

        {/* Add goal form */}
        <SectionCard title="Add New Goal" icon="➕">
          <form onSubmit={addGoal}>
            <div className="form-group">
              <label>Goal Type</label>
              <select value={form.goal_type} onChange={e => setForm(f => ({...f, goal_type: e.target.value}))}>
                {GOAL_TYPES.map(t => <option key={t} value={t}>{t}</option>)}
              </select>
            </div>
            <div className="form-group">
              <label>Value</label>
              <input
                placeholder={
                  form.goal_type === 'skill' ? 'e.g. selenium, playwright' :
                  form.goal_type === 'title' ? 'e.g. automation, qa engineer' :
                  form.goal_type === 'location' ? 'e.g. remote, bangalore' :
                  form.goal_type === 'company' ? 'e.g. infosys, wipro' :
                  'keyword to match in any field'
                }
                value={form.value}
                onChange={e => setForm(f => ({...f, value: e.target.value}))}
              />
            </div>
            <div className="form-group">
              <label>Priority: <strong style={{ color: 'var(--accent-light)' }}>{form.priority} — {PRIORITY_LABELS[form.priority] || ''}</strong></label>
              <input type="range" min={1} max={9} value={form.priority}
                onChange={e => setForm(f => ({...f, priority: e.target.value}))}
                style={{ width: '100%', accentColor: 'var(--accent)' }}
              />
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11, color: 'var(--text-muted)', marginTop: 2 }}>
                <span>Minimal (1)</span><span>Critical (9)</span>
              </div>
            </div>
            <button type="submit" className="btn btn-primary" style={{ width: '100%' }}>
              ➕ Add Goal
            </button>
          </form>

          {/* Type reference */}
          <div style={{ marginTop: 20, padding: '12px 14px', background: 'var(--bg-glass)', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border)' }}>
            <div style={{ fontSize: 11, color: 'var(--text-muted)', fontWeight: 600, marginBottom: 8, textTransform: 'uppercase', letterSpacing: '0.5px' }}>Goal Type Reference</div>
            {[
              ['skill',    'Job requires this skill (skills field)'],
              ['title',    'Job title contains this word'],
              ['keyword',  'Appears anywhere in description'],
              ['company',  'Specific company name'],
              ['location', 'Job location matches'],
              ['salary',   'Min salary number (e.g. 5)'],
            ].map(([t, desc]) => (
              <div key={t} style={{ display: 'flex', gap: 8, marginBottom: 5, alignItems: 'flex-start', fontSize: 12 }}>
                <span className={`badge ${typeColors[t]}`} style={{ minWidth: 60, justifyContent: 'center' }}>{t}</span>
                <span style={{ color: 'var(--text-secondary)' }}>{desc}</span>
              </div>
            ))}
          </div>
        </SectionCard>

        {/* Active goals list */}
        <SectionCard title={`Active Goals (${(goals || []).length})`} icon="📋">
          {loading ? <Loading /> : !goals?.length
            ? (
              <Empty icon="🎯" msg="No goals set. Add goals to boost relevant job scores." />
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                {goals.map(g => (
                  <div key={g.id} style={{
                    display: 'flex', alignItems: 'center', gap: 10,
                    padding: '10px 12px',
                    background: 'var(--bg-glass)',
                    border: '1px solid var(--border)',
                    borderRadius: 'var(--radius-sm)',
                    transition: 'all 0.2s',
                  }}>
                    <span className={`badge ${typeColors[g.goal_type] || 'badge-muted'}`}>{g.goal_type}</span>
                    <span style={{ flex: 1, color: 'var(--text-primary)', fontWeight: 500, fontSize: 14 }}>'{g.value}'</span>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                      {/* Priority bar */}
                      <div style={{ display: 'flex', gap: 2 }}>
                        {Array.from({length: 9}, (_, i) => (
                          <div key={i} style={{
                            width: 6, height: 14, borderRadius: 2,
                            background: i < g.priority ? 'var(--accent)' : 'var(--border)',
                          }} />
                        ))}
                      </div>
                      <span style={{ fontSize: 11, color: 'var(--text-muted)', minWidth: 14 }}>{g.priority}</span>
                    </div>
                    <button className="btn btn-sm btn-danger" onClick={() => deleteGoal(g.id, g.value)}>✕</button>
                  </div>
                ))}
              </div>
            )
          }

          {/* Tip */}
          {(goals || []).length > 0 && (
            <div style={{ marginTop: 14, padding: '10px 12px', background: 'var(--accent-dim)', border: '1px solid var(--accent)', borderRadius: 'var(--radius-sm)', fontSize: 12, color: 'var(--accent-light)' }}>
              💡 Run <strong>Queue → Re-rank</strong> to apply your goals to the current job queue.
            </div>
          )}
        </SectionCard>

      </div>
    </div>
  )
}
