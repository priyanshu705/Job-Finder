import { useState, useEffect } from 'react'
import { Save, RotateCcw } from 'lucide-react'
import toast from 'react-hot-toast'
import PageHeader from '../components/PageHeader.jsx'
import { api } from '../api.js'

const CONTROL_DEFS = [
  { key: 'min_match',       label: 'Min Match Score',    type: 'number', min: 0, max: 100, hint: '0–100' },
  { key: 'daily_cap',       label: 'Daily Cap',          type: 'number', min: 1, max: 100, hint: 'Max applies/day' },
  { key: 'weekly_cap',      label: 'Weekly Cap',         type: 'number', min: 1, max: 500, hint: 'Max applies/week' },
  { key: 'aggressiveness',  label: 'Aggressiveness',     type: 'select', options: ['normal', 'aggressive', 'conservative'] },
  { key: 'explore_rate',    label: 'Explore Rate',       type: 'number', min: 0, max: 1, step: 0.05, hint: '0.0–1.0' },
  { key: 'max_risk',        label: 'Max Risk Score',     type: 'number', min: 0, max: 1, step: 0.05, hint: '0.0–1.0' },
  { key: 'platforms',       label: 'Platforms (JSON)',   type: 'text',   hint: '["internshala","indeed"]' },
  { key: 'require_approval',label: 'Require Approval',   type: 'select', options: ['false', 'true'] },
]

export default function SettingsPage() {
  const [controls, setControls] = useState({})
  const [form, setForm]         = useState({})
  const [loading, setLoading]   = useState(true)
  const [saving, setSaving]     = useState({})

  useEffect(() => {
    api.controls()
      .then(data => {
        const map = {}
        const items = Array.isArray(data) ? data : (data.controls || Object.entries(data).map(([key, value]) => ({ key, value })))
        items.forEach(c => { map[c.key] = c.value })
        setControls(map)
        setForm(map)
      })
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [])

  const handleSave = async (key) => {
    setSaving(s => ({ ...s, [key]: true }))
    try {
      await api.setControl(key, form[key])
      setControls(c => ({ ...c, [key]: form[key] }))
      toast.success(`${key} updated`)
    } catch (e) { toast.error(e.message) }
    finally { setSaving(s => ({ ...s, [key]: false })) }
  }

  const handleReset = (key) => {
    setForm(f => ({ ...f, [key]: controls[key] }))
  }

  if (loading) return (
    <div className="space-y-3 max-w-2xl">
      {[...Array(6)].map((_, i) => <div key={i} className="skeleton h-16 rounded-2xl" />)}
    </div>
  )

  return (
    <div className="space-y-6 max-w-2xl" style={{ animation: 'fadeIn 0.4s ease-out both' }}>
      <PageHeader title="Settings" sub="Agent controls — changes apply to the next cycle" />

      <div className="space-y-3">
        {CONTROL_DEFS.map(def => {
          const changed = form[def.key] !== controls[def.key]
          return (
            <div
              key={def.key}
              className="rounded-2xl p-4 flex items-center gap-4 transition-all duration-200"
              style={{
                background: changed
                  ? 'linear-gradient(135deg, rgba(99,102,241,0.08) 0%, rgba(13,21,38,0.95) 100%)'
                  : 'linear-gradient(135deg, rgba(13,21,38,0.9) 0%, rgba(8,15,31,0.95) 100%)',
                border: `1px solid ${changed ? 'rgba(99,102,241,0.3)' : 'rgba(255,255,255,0.07)'}`,
                boxShadow: changed ? '0 0 16px rgba(99,102,241,0.08)' : 'none',
              }}
            >
              <div className="flex-1 min-w-0">
                <label className="text-sm font-medium text-slate-200 block mb-0.5">{def.label}</label>
                {def.hint && <p className="text-xs text-slate-500">{def.hint}</p>}
              </div>
              <div className="flex items-center gap-2">
                {def.type === 'select' ? (
                  <select
                    className="select-field w-36"
                    value={form[def.key] || ''}
                    onChange={e => setForm(f => ({ ...f, [def.key]: e.target.value }))}
                  >
                    {def.options.map(o => <option key={o} value={o}>{o}</option>)}
                  </select>
                ) : (
                  <input
                    type={def.type}
                    className="input-field w-36"
                    min={def.min} max={def.max} step={def.step || 1}
                    value={form[def.key] || ''}
                    onChange={e => setForm(f => ({ ...f, [def.key]: e.target.value }))}
                  />
                )}
                {changed && (
                  <button onClick={() => handleReset(def.key)} className="p-2 rounded-xl text-slate-500 hover:text-slate-300 hover:bg-white/5">
                    <RotateCcw size={13} />
                  </button>
                )}
                <button
                  onClick={() => handleSave(def.key)}
                  disabled={!changed || saving[def.key]}
                  className="btn-primary px-3 py-1.5 text-xs"
                >
                  {saving[def.key] ? 'Saving…' : <><Save size={12} /> Save</>}
                </button>
              </div>
            </div>
          )
        })}
      </div>

      {/* Danger zone */}
      <div className="rounded-2xl p-5" style={{ background: 'linear-gradient(135deg, rgba(248,113,113,0.06) 0%, rgba(13,21,38,0.95) 100%)', border: '1px solid rgba(248,113,113,0.2)', boxShadow: '0 0 20px rgba(248,113,113,0.05)' }}>
        <p className="text-sm font-semibold mb-4" style={{ color: '#f87171' }}>⚠ Danger Zone</p>
        <div className="flex gap-3">
          <button
            className="btn-danger"
            onClick={async () => {
              if (!confirm('Reset entire apply queue? This cannot be undone.')) return
              try { await api.reset(); toast.success('Queue reset') }
              catch (e) { toast.error(e.message) }
            }}
          >
            Reset Queue
          </button>
        </div>
      </div>
    </div>
  )
}
