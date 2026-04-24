// src/components/Controls.jsx
import React, { useState, useCallback } from 'react'
import { api } from '../api'
import { useLive } from '../hooks'
import { Loading, SectionCard } from './Shared'
import { SkeletonCard } from './Skeleton'

const CONTROL_META = {
  paused:          { label:'Agent Paused',       type:'toggle',  desc:'Stop all automation activity' },
  daily_cap:       { label:'Daily Application Cap', type:'number', min:1, max:50,  desc:'Max applications per day' },
  min_match:       { label:'Min Match Score (%)', type:'number', min:20, max:95, desc:'Threshold below which jobs are skipped' },
  aggressiveness:  { label:'Aggressiveness',     type:'select', options:['conservative','normal','aggressive'], desc:'Controls apply speed and risk tolerance' },
  platforms:       { label:'Platforms',          type:'text',    desc:'JSON array of platforms to scrape' },
  explore_rate:    { label:'Exploration Rate',   type:'number', min:0, max:1, step:0.05, desc:'Fraction of slots used for exploration (0–1)' },
}

export default function Controls({ toast }) {
  const fetchControls = useCallback(() => api.controls(), [])
  const { data: controls, loading, reload } = useLive(fetchControls, 8000)
  const [saving, setSaving] = useState({})

  async function save(key, value) {
    setSaving(s => ({...s, [key]: true}))
    try {
      await api.setControl(key, value)
      toast(`${CONTROL_META[key]?.label || key} updated`, 'success')
      reload()
    } catch(e) {
      toast(`Failed: ${e.message}`, 'error')
    } finally {
      setSaving(s => ({...s, [key]: false}))
    }
  }

  if (loading && !controls) return <SkeletonCard />

  return (
    <div>
      <div className="page-header">
        <div>
          <h2>⚙️ Controls</h2>
          <p>Tune the agent behaviour and automation parameters</p>
        </div>
      </div>

      <div className="content-grid">
        <SectionCard title="Agent Controls" icon="🎛️">
          <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>

            {/* Pause toggle — prominent */}
            <div style={{
              display: 'flex', alignItems: 'center', justifyContent: 'space-between',
              padding: '14px 16px',
              background: controls?.paused === 'true' ? 'var(--yellow-dim)' : 'var(--green-dim)',
              border: `1px solid ${controls?.paused === 'true' ? 'var(--yellow)' : 'var(--green)'}`,
              borderRadius: 'var(--radius-md)',
            }}>
              <div>
                <div style={{ fontWeight:700, fontSize:14, color: controls?.paused === 'true' ? 'var(--yellow)' : 'var(--green)' }}>
                  {controls?.paused === 'true' ? '⏸ Agent is PAUSED' : '▶ Agent is RUNNING'}
                </div>
                <div style={{ fontSize:12, color:'var(--text-muted)', marginTop:2 }}>
                  {CONTROL_META.paused.desc}
                </div>
              </div>
              <label className="toggle">
                <input type="checkbox"
                  checked={controls?.paused !== 'true'}
                  onChange={e => save('paused', e.target.checked ? 'false' : 'true')}
                />
                <span className="toggle-slider" />
              </label>
            </div>

            {/* Numeric + Select controls */}
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
              {Object.entries(CONTROL_META).filter(([k]) => k !== 'paused' && k !== 'platforms').map(([key, meta]) => (
                <ControlItem key={key} keyName={key} meta={meta}
                  value={controls?.[key] || ''}
                  saving={saving[key]}
                  onSave={save}
                />
              ))}
            </div>

            {/* Platforms (JSON) */}
            <ControlItem keyName="platforms" meta={CONTROL_META.platforms}
              value={controls?.platforms || ''}
              saving={saving.platforms}
              onSave={save}
              fullWidth
            />

            {/* Danger zone */}
            <div style={{ borderTop:'1px solid var(--border)', paddingTop:16 }}>
              <div style={{ fontSize:11, color:'var(--text-muted)', fontWeight:600, textTransform:'uppercase', letterSpacing:'0.8px', marginBottom:12 }}>
                Danger Zone
              </div>
              <div style={{ display:'flex', gap:10, flexWrap:'wrap' }}>
                <button className="btn btn-danger"
                  onClick={async () => {
                    if (confirm('Reset all queued jobs to pending?')) {
                      await api.reset()
                      toast('Queue reset — all jobs back to pending', 'info')
                    }
                  }}>
                  🔄 Reset Queue
                </button>
                <button className="btn btn-ghost"
                  onClick={async () => {
                    await api.pause()
                    toast('Agent paused', 'info')
                    reload()
                  }}>
                  ⏸ Emergency Stop
                </button>
              </div>
            </div>

          </div>
        </SectionCard>

        {/* Controls reference */}
        <SectionCard title="Parameter Reference" icon="📖">
          <div style={{ display:'flex', flexDirection:'column', gap:12 }}>
            {[
              { name:'MIN_MATCH',      range:'40–95%', effect:'Higher = more selective, fewer but better-fit jobs' },
              { name:'DAILY_CAP',      range:'1–50',   effect:'Hard limit on applications per day' },
              { name:'AGGRESSIVENESS', range:'conservative/normal/aggressive', effect:'Controls timing delays between applications' },
              { name:'EXPLORE_RATE',   range:'0.0–1.0', effect:'Fraction of slots exploring below-threshold jobs to learn' },
              { name:'PLATFORMS',      range:'JSON array', effect:'Which platforms to scrape (internshala, indeed, etc.)' },
            ].map(r => (
              <div key={r.name} style={{ padding:'10px 12px', background:'var(--bg-glass)', border:'1px solid var(--border)', borderRadius:'var(--radius-sm)' }}>
                <div style={{ display:'flex', justifyContent:'space-between', marginBottom:4 }}>
                  <span style={{ fontFamily:'JetBrains Mono, monospace', fontSize:12, color:'var(--accent-light)', fontWeight:600 }}>{r.name}</span>
                  <span className="badge badge-muted">{r.range}</span>
                </div>
                <div style={{ fontSize:12, color:'var(--text-muted)' }}>{r.effect}</div>
              </div>
            ))}
          </div>
        </SectionCard>
      </div>
    </div>
  )
}

function ControlItem({ keyName, meta, value, saving, onSave, fullWidth }) {
  const [local, setLocal] = useState(value)
  const changed = local !== value

  // Sync when parent value changes
  React.useEffect(() => { setLocal(value) }, [value])

  return (
    <div className="form-group" style={{ margin:0, gridColumn: fullWidth ? '1/-1' : 'auto' }}>
      <label style={{ display:'flex', flexDirection:'column', gap:2 }}>
        {meta.label}
        <span style={{ fontSize:11, color:'var(--text-muted)', fontWeight:400, textTransform:'none', letterSpacing:0 }}>{meta.desc}</span>
      </label>
      <div style={{ display:'flex', gap:8, alignItems:'center' }}>
        {meta.type === 'select'
          ? (
            <select value={local} onChange={e => setLocal(e.target.value)} style={{ flex:1 }}>
              {(meta.options||[]).map(o => <option key={o} value={o}>{o}</option>)}
            </select>
          ) : (
            <input
              type={meta.type === 'number' ? 'number' : 'text'}
              min={meta.min} max={meta.max} step={meta.step || 1}
              value={local}
              onChange={e => setLocal(e.target.value)}
              style={{ flex:1 }}
            />
          )
        }
        <button
          className={`btn btn-sm ${changed ? 'btn-primary' : 'btn-ghost'}`}
          disabled={!changed || saving}
          onClick={() => onSave(keyName, local)}
        >
          {saving ? '⏳' : 'Save'}
        </button>
      </div>
    </div>
  )
}
