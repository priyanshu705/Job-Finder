import { useState, useEffect } from 'react'
import { Plus, Trash2, Target, AlertTriangle } from 'lucide-react'
import toast from 'react-hot-toast'
import { api } from '../api.js'

const GOAL_TYPES = [
  { value: 'role',            label: 'Target Role' },
  { value: 'company',         label: 'Preferred Company' },
  { value: 'blacklist',       label: 'Blacklisted Company' },
  { value: 'skill',           label: 'Required Skill' },
  { value: 'location',        label: 'Location Preference' },
  { value: 'daily_cap',       label: 'Daily Cap' },
  { value: 'min_match',       label: 'Min Match Score' },
  { value: 'explore_rate',    label: 'Explore Rate' },
  { value: 'aggressiveness',  label: 'Aggressiveness Mode' },
]

const TYPE_COLORS = {
  role: 'text-blue-400', company: 'text-emerald-400',
  blacklist: 'text-red-400', skill: 'text-purple-400',
  location: 'text-amber-400', daily_cap: 'text-cyan-400',
  min_match: 'text-indigo-400', aggressiveness: 'text-orange-400',
}

export default function GoalsPage() {
  const [goals, setGoals]     = useState([])
  const [loading, setLoading] = useState(true)
  const [saving, setSaving]   = useState(false)
  const [form, setForm]       = useState({ goal_type: 'role', value: '', priority: 5 })
  const [deleting, setDeleting] = useState(null)

  const load = async () => {
    try {
      const data = await api.goals()
      setGoals(Array.isArray(data) ? data : (data.goals || []))
    } catch { setGoals([]) }
    finally { setLoading(false) }
  }

  useEffect(() => { load() }, [])

  const handleAdd = async () => {
    if (!form.value.trim()) return toast.error('Value is required')
    setSaving(true)
    try {
      await api.addGoal(form)
      toast.success('Goal added!')
      setForm({ goal_type: 'role', value: '', priority: 5 })
      load()
    } catch (e) { toast.error(e.message) }
    finally { setSaving(false) }
  }

  const handleDelete = async (id) => {
    if (!confirm('Delete this goal?')) return
    setDeleting(id)
    try {
      await api.deleteGoal(id)
      toast.success('Goal removed')
      load()
    } catch (e) { toast.error(e.message) }
    finally { setDeleting(null) }
  }

  const grouped = goals.reduce((acc, g) => {
    const t = g.goal_type || 'other'
    ;(acc[t] = acc[t] || []).push(g)
    return acc
  }, {})

  return (
    <div className="space-y-6 animate-fade-in max-w-3xl">
      <div>
        <h2 className="section-title">Goals</h2>
        <p className="section-sub">Define what the agent should target and avoid</p>
      </div>

      {/* Add form */}
      <div className="card p-5 space-y-4">
        <p className="text-sm font-semibold text-slate-200 flex items-center gap-2">
          <Plus size={16} className="text-blue-400" /> Add New Goal
        </p>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
          <select className="select-field" value={form.goal_type} onChange={e => setForm(f => ({ ...f, goal_type: e.target.value }))}>
            {GOAL_TYPES.map(t => <option key={t.value} value={t.value}>{t.label}</option>)}
          </select>
          <input
            className="input-field"
            placeholder="Value (e.g. Python Developer, Google, 85)"
            value={form.value}
            onChange={e => setForm(f => ({ ...f, value: e.target.value }))}
            onKeyDown={e => e.key === 'Enter' && handleAdd()}
          />
          <div className="flex gap-2">
            <div className="flex items-center gap-2 flex-1">
              <label className="text-xs text-slate-500 whitespace-nowrap">Priority</label>
              <input
                type="number" min="1" max="10"
                className="input-field w-16"
                value={form.priority}
                onChange={e => setForm(f => ({ ...f, priority: +e.target.value }))}
              />
            </div>
            <button onClick={handleAdd} disabled={saving} className="btn-primary px-4">
              {saving ? 'Adding…' : 'Add'}
            </button>
          </div>
        </div>
      </div>

      {/* Goals list */}
      {loading ? (
        <div className="space-y-3">
          {[...Array(4)].map((_, i) => <div key={i} className="skeleton h-12 rounded-xl" />)}
        </div>
      ) : !goals.length ? (
        <div className="card flex flex-col items-center py-12 text-slate-500 gap-3">
          <Target size={36} className="opacity-30" />
          <p className="text-sm">No goals defined yet — add your first one above</p>
        </div>
      ) : (
        <div className="space-y-4">
          {Object.entries(grouped).map(([type, items]) => {
            const meta = GOAL_TYPES.find(t => t.value === type)
            const color = TYPE_COLORS[type] || 'text-slate-400'
            return (
              <div key={type} className="card p-4">
                <p className={`text-xs font-bold uppercase tracking-wider mb-3 ${color}`}>
                  {meta?.label || type}
                </p>
                <div className="space-y-2">
                  {items.map(g => (
                    <div key={g.id} className="flex items-center justify-between py-2 px-3 rounded-xl bg-white/[0.02] hover:bg-white/[0.04] transition-colors border border-slate-700/30">
                      <div className="flex items-center gap-3">
                        {type === 'blacklist' && <AlertTriangle size={14} className="text-red-400 flex-shrink-0" />}
                        <span className="text-sm text-slate-200">{g.value}</span>
                        <span className="text-xs text-slate-600">p{g.priority}</span>
                      </div>
                      <button
                        onClick={() => handleDelete(g.id)}
                        disabled={deleting === g.id}
                        className="p-1.5 rounded-lg text-slate-600 hover:text-red-400 hover:bg-red-500/10 transition-colors"
                      >
                        <Trash2 size={13} />
                      </button>
                    </div>
                  ))}
                </div>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
