import { useState, useEffect, useRef } from 'react'
import { Save, RotateCcw, Upload, FileText, Wand2, Wrench, CheckCircle, AlertCircle } from 'lucide-react'
import toast from 'react-hot-toast'
import PageHeader from '../components/PageHeader.jsx'
import { api } from '../api.js'

const CONTROL_DEFS = [
  { key: 'min_match',       label: 'Min Match Score',    type: 'number', min: 0, max: 100, hint: '0–100 — jobs below this score are skipped' },
  { key: 'daily_cap',       label: 'Daily Cap',          type: 'number', min: 1, max: 100, hint: 'Max applications per day' },
  { key: 'weekly_cap',      label: 'Weekly Cap',         type: 'number', min: 1, max: 500, hint: 'Max applications per week' },
  { key: 'aggressiveness',  label: 'Aggressiveness',     type: 'select', options: ['normal', 'aggressive', 'conservative'] },
  { key: 'explore_rate',    label: 'Explore Rate',       type: 'number', min: 0, max: 1, step: 0.05, hint: '0.0–1.0 — how often to try lower-score jobs' },
  { key: 'max_risk',        label: 'Max Risk Score',     type: 'number', min: 0, max: 1, step: 0.05, hint: '0.0–1.0 — skip riskier applications above this' },
  { key: 'platforms',       label: 'Platforms (JSON)',   type: 'text',   hint: '["internshala","indeed"]' },
  { key: 'require_approval',label: 'Require Approval',   type: 'select', options: ['false', 'true'] },
]

// ── Resume Section ─────────────────────────────────────────────────────────────
function ResumeSection() {
  const [resumeInfo, setResumeInfo]   = useState(null)
  const [uploading, setUploading]     = useState(false)
  const [genRunning, setGenRunning]   = useState(false)
  const [fixRunning, setFixRunning]   = useState(false)
  const fileRef = useRef(null)

  useEffect(() => {
    api.getResume()
      .then(d => setResumeInfo(d))
      .catch(() => setResumeInfo(null))
  }, [])

  const handleUpload = async (e) => {
    const file = e.target.files?.[0]
    if (!file) return
    setUploading(true)
    toast.loading('Parsing resume…', { id: 'resume' })
    try {
      const fd = new FormData()
      fd.append('file', file)
      const res = await api.uploadResume(fd)
      setResumeInfo(res)
      toast.success(
        `✅ Resume uploaded! Detected ${res.skill_count} skills. Queue will re-match on next cycle.`,
        { id: 'resume', duration: 5000 }
      )
    } catch (e) {
      toast.error(e.message || 'Upload failed', { id: 'resume' })
    } finally {
      setUploading(false)
      if (fileRef.current) fileRef.current.value = ''
    }
  }

  const handleGenerateAssistant = async () => {
    setGenRunning(true)
    toast.loading('Generating AI assistant data…', { id: 'gen' })
    try {
      await api.generateAssistant()
      toast.success('✅ Assistant data generation started! Refresh the Queue panel.', { id: 'gen', duration: 4000 })
    } catch (e) {
      toast.error(e.message || 'Failed', { id: 'gen' })
    } finally {
      setGenRunning(false)
    }
  }

  const handleFixPending = async () => {
    setFixRunning(true)
    toast.loading('Repairing stuck jobs…', { id: 'fix' })
    try {
      await api.resetPending()
      toast.success('✅ Stuck jobs promoted to ready_to_apply!', { id: 'fix', duration: 4000 })
    } catch (e) {
      toast.error(e.message || 'Failed', { id: 'fix' })
    } finally {
      setFixRunning(false)
    }
  }

  const skills = resumeInfo?.skills || []

  return (
    <div className="space-y-4">
      {/* Upload card */}
      <div
        className="rounded-2xl p-5"
        style={{
          background: 'linear-gradient(135deg, rgba(99,102,241,0.06) 0%, rgba(13,21,38,0.95) 100%)',
          border: '1px solid rgba(99,102,241,0.2)',
          boxShadow: '0 0 20px rgba(99,102,241,0.06)',
        }}
      >
        <div className="flex items-start justify-between gap-4">
          <div className="flex items-center gap-3 min-w-0">
            <div className="p-2.5 rounded-xl flex-shrink-0" style={{ background: 'rgba(99,102,241,0.12)', color: '#818cf8' }}>
              <FileText size={20} />
            </div>
            <div className="min-w-0">
              <p className="text-sm font-semibold text-slate-200">
                {resumeInfo?.filename ? resumeInfo.filename : 'No resume uploaded'}
              </p>
              <p className="text-xs mt-0.5" style={{ color: 'rgba(100,116,139,0.8)' }}>
                {resumeInfo?.source === 'db'
                  ? `Uploaded · ${skills.length} skills detected`
                  : resumeInfo?.source === 'filesystem'
                  ? `From filesystem · ${skills.length} skills`
                  : resumeInfo?.source === 'env'
                  ? `From .env USER_SKILLS · ${skills.length} skills`
                  : 'Upload your resume to enable resume-driven job matching'}
              </p>
            </div>
          </div>
          <div>
            <input
              ref={fileRef}
              type="file"
              accept=".pdf,.docx,.doc,.txt"
              className="hidden"
              id="resume-upload-input"
              onChange={handleUpload}
            />
            <label
              htmlFor="resume-upload-input"
              className="btn-primary cursor-pointer"
              style={{ padding: '7px 16px', fontSize: 12, display: 'inline-flex', alignItems: 'center', gap: 6, opacity: uploading ? 0.7 : 1 }}
            >
              <Upload size={13} />
              {uploading ? 'Uploading…' : 'Upload Resume'}
            </label>
          </div>
        </div>

        {/* Skills chips */}
        {skills.length > 0 && (
          <div className="mt-4">
            <p className="text-[10px] font-bold uppercase tracking-wider text-slate-500 mb-2">Detected Skills</p>
            <div className="flex flex-wrap gap-1.5">
              {skills.map(s => (
                <span
                  key={s}
                  className="px-2 py-0.5 rounded-full text-[10px] font-medium"
                  style={{ background: 'rgba(99,102,241,0.15)', color: '#a5b4fc', border: '1px solid rgba(99,102,241,0.25)' }}
                >
                  {s}
                </span>
              ))}
            </div>
          </div>
        )}

        {skills.length === 0 && !uploading && (
          <div className="mt-3 p-3 rounded-xl flex items-center gap-2" style={{ background: 'rgba(251,191,36,0.06)', border: '1px solid rgba(251,191,36,0.15)' }}>
            <AlertCircle size={13} style={{ color: '#fbbf24', flexShrink: 0 }} />
            <p className="text-xs" style={{ color: '#fde68a' }}>
              No resume detected. Matching will use USER_SKILLS from .env as fallback.
            </p>
          </div>
        )}
      </div>

      {/* Quick-action tools */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        <div
          className="rounded-2xl p-4 flex items-start gap-3"
          style={{
            background: 'linear-gradient(135deg, rgba(52,211,153,0.05) 0%, rgba(13,21,38,0.95) 100%)',
            border: '1px solid rgba(52,211,153,0.15)',
          }}
        >
          <div className="p-2 rounded-xl flex-shrink-0" style={{ background: 'rgba(52,211,153,0.1)', color: '#34d399' }}>
            <Wand2 size={16} />
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-sm font-semibold text-slate-200">Generate AI Answers</p>
            <p className="text-xs text-slate-500 mt-0.5 mb-3">
              Pre-fill assistant panel for all queue jobs missing AI answers.
            </p>
            <button
              onClick={handleGenerateAssistant}
              disabled={genRunning}
              className="btn-primary text-xs"
              style={{ padding: '6px 14px', background: 'rgba(52,211,153,0.15)', border: '1px solid rgba(52,211,153,0.3)', color: '#34d399' }}
            >
              {genRunning ? 'Running…' : '⚡ Generate Now'}
            </button>
          </div>
        </div>

        <div
          className="rounded-2xl p-4 flex items-start gap-3"
          style={{
            background: 'linear-gradient(135deg, rgba(251,191,36,0.05) 0%, rgba(13,21,38,0.95) 100%)',
            border: '1px solid rgba(251,191,36,0.15)',
          }}
        >
          <div className="p-2 rounded-xl flex-shrink-0" style={{ background: 'rgba(251,191,36,0.1)', color: '#fbbf24' }}>
            <Wrench size={16} />
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-sm font-semibold text-slate-200">Fix Stuck Jobs</p>
            <p className="text-xs text-slate-500 mt-0.5 mb-3">
              Promote scored pending jobs to <span className="text-indigo-400 font-mono text-[10px]">ready_to_apply</span> so they appear in the queue.
            </p>
            <button
              onClick={handleFixPending}
              disabled={fixRunning}
              className="btn-primary text-xs"
              style={{ padding: '6px 14px', background: 'rgba(251,191,36,0.12)', border: '1px solid rgba(251,191,36,0.25)', color: '#fbbf24' }}
            >
              {fixRunning ? 'Fixing…' : '🔧 Fix Pending'}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}

// ── Main Settings Page ─────────────────────────────────────────────────────────
export default function SettingsPage() {
  const [controls, setControls] = useState({})
  const [form, setForm]         = useState({})
  const [loading, setLoading]   = useState(true)
  const [saving, setSaving]     = useState({})

  useEffect(() => {
    api.controls()
      .then(data => {
        const map = {}
        const items = Array.isArray(data)
          ? data
          : (data.controls || Object.entries(data).map(([key, value]) => ({ key, value })))
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

  const handleReset = (key) => setForm(f => ({ ...f, [key]: controls[key] }))

  if (loading) return (
    <div className="space-y-3 max-w-2xl">
      {[...Array(6)].map((_, i) => <div key={i} className="skeleton h-16 rounded-2xl" />)}
    </div>
  )

  return (
    <div className="space-y-8 max-w-2xl" style={{ animation: 'fadeIn 0.4s ease-out both' }}>
      <PageHeader title="Settings" sub="Agent controls &amp; resume management" />

      {/* ── Resume &amp; Intelligence Section ───────────────────────────── */}
      <div className="space-y-3">
        <div className="flex items-center gap-2 px-1">
          <div className="h-px flex-1" style={{ background: 'rgba(99,102,241,0.2)' }} />
          <span className="text-[10px] font-bold uppercase tracking-widest" style={{ color: '#818cf8' }}>
            Resume &amp; Intelligence
          </span>
          <div className="h-px flex-1" style={{ background: 'rgba(99,102,241,0.2)' }} />
        </div>
        <ResumeSection />
      </div>

      {/* ── Agent Controls ──────────────────────────────────────────────── */}
      <div className="space-y-3">
        <div className="flex items-center gap-2 px-1">
          <div className="h-px flex-1" style={{ background: 'rgba(255,255,255,0.06)' }} />
          <span className="text-[10px] font-bold uppercase tracking-widest text-slate-500">
            Agent Controls
          </span>
          <div className="h-px flex-1" style={{ background: 'rgba(255,255,255,0.06)' }} />
        </div>

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

      {/* ── Danger Zone ─────────────────────────────────────────────────── */}
      <div
        className="rounded-2xl p-5"
        style={{
          background: 'linear-gradient(135deg, rgba(248,113,113,0.06) 0%, rgba(13,21,38,0.95) 100%)',
          border: '1px solid rgba(248,113,113,0.2)',
          boxShadow: '0 0 20px rgba(248,113,113,0.05)',
        }}
      >
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
