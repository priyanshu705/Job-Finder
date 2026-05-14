// src/pages/FollowupPage.jsx — AI-Powered Follow-up Inbox
import { useState, useEffect, useCallback } from 'react'
import { api } from '../api.js'
import PageHeader from '../components/PageHeader.jsx'
import toast from 'react-hot-toast'
import {
  Mail, CheckCircle2, XCircle, Trash2, Sparkles, RefreshCw,
  Briefcase, Building2, Copy, Clock, Filter, Loader2
} from 'lucide-react'

const STATUS_COLORS = {
  pending:   { bg: 'rgba(245,158,11,0.15)', text: '#f59e0b', border: 'rgba(245,158,11,0.3)' },
  approved:  { bg: 'rgba(16,185,129,0.15)', text: '#10b981', border: 'rgba(16,185,129,0.3)' },
  dismissed: { bg: 'rgba(239,68,68,0.12)',  text: '#f87171', border: 'rgba(239,68,68,0.25)' },
}

const card = {
  background: 'linear-gradient(135deg, rgba(13,21,38,0.95) 0%, rgba(8,15,31,0.98) 100%)',
  border: '1px solid rgba(255,255,255,0.07)',
  borderRadius: 16,
  boxShadow: '0 4px 24px rgba(0,0,0,0.4)',
}

const inputStyle = {
  background: 'rgba(255,255,255,0.04)',
  border: '1px solid rgba(255,255,255,0.1)',
  borderRadius: 10,
  color: 'rgba(226,232,240,0.9)',
  fontSize: 13,
  padding: '9px 14px',
  outline: 'none',
  fontFamily: 'inherit',
  transition: 'border-color 0.2s',
}

function StatusBadge({ status }) {
  const s = STATUS_COLORS[status] || STATUS_COLORS.pending
  return (
    <span style={{
      padding: '3px 10px', borderRadius: 20, fontSize: 11, fontWeight: 600,
      background: s.bg, color: s.text, border: `1px solid ${s.border}`,
    }}>
      {status}
    </span>
  )
}

function FollowupCard({ item, onApprove, onDismiss, onDelete }) {
  const [copied, setCopied] = useState(false)
  const [expanded, setExpanded] = useState(false)

  const copy = () => {
    navigator.clipboard.writeText(item.draft_text || '')
    setCopied(true)
    toast.success('Draft copied!')
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <div
      style={{
        ...card, padding: '1.25rem',
        animation: 'fadeIn 0.3s ease-out',
        transition: 'box-shadow 0.2s',
      }}
      onMouseEnter={e => e.currentTarget.style.boxShadow = '0 8px 32px rgba(0,0,0,0.5), 0 0 0 1px rgba(99,102,241,0.15)'}
      onMouseLeave={e => e.currentTarget.style.boxShadow = '0 4px 24px rgba(0,0,0,0.4)'}
    >
      {/* Header row */}
      <div style={{ display: 'flex', alignItems: 'flex-start', gap: 12, marginBottom: 12 }}>
        <div style={{
          width: 40, height: 40, borderRadius: 10, flexShrink: 0,
          background: 'linear-gradient(135deg, rgba(59,130,246,0.3), rgba(99,102,241,0.2))',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
        }}>
          <Mail size={18} style={{ color: '#60a5fa' }} />
        </div>

        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
            <p style={{ fontSize: 14, fontWeight: 700, color: 'rgba(226,232,240,0.95)' }}>
              {item.job_title || 'Unknown Role'}
            </p>
            <StatusBadge status={item.status || 'pending'} />
          </div>
          <div style={{ display: 'flex', gap: 12, marginTop: 4, flexWrap: 'wrap' }}>
            <span style={{ fontSize: 12, color: 'rgba(148,163,184,0.6)', display: 'flex', alignItems: 'center', gap: 4 }}>
              <Building2 size={11} /> {item.company || '—'}
            </span>
            <span style={{ fontSize: 12, color: 'rgba(148,163,184,0.6)', display: 'flex', alignItems: 'center', gap: 4 }}>
              <Clock size={11} /> {item.created_at ? new Date(item.created_at).toLocaleDateString() : '—'}
            </span>
          </div>
        </div>
      </div>

      {/* Draft preview */}
      <div
        onClick={() => setExpanded(e => !e)}
        style={{
          background: 'rgba(255,255,255,0.03)',
          border: '1px solid rgba(255,255,255,0.07)',
          borderRadius: 10, padding: '12px',
          cursor: 'pointer', marginBottom: 12,
          maxHeight: expanded ? 'none' : 120,
          overflow: 'hidden',
          position: 'relative',
        }}
      >
        <pre style={{
          fontSize: 12.5, color: 'rgba(203,213,225,0.8)',
          lineHeight: 1.7, whiteSpace: 'pre-wrap', fontFamily: 'inherit',
          margin: 0,
        }}>
          {item.draft_text || 'No draft text available.'}
        </pre>
        {!expanded && (
          <div style={{
            position: 'absolute', bottom: 0, left: 0, right: 0,
            height: 48,
            background: 'linear-gradient(transparent, rgba(8,15,31,0.95))',
            display: 'flex', alignItems: 'flex-end', justifyContent: 'center',
            paddingBottom: 6,
          }}>
            <span style={{ fontSize: 11, color: 'rgba(99,102,241,0.8)' }}>Click to expand ▾</span>
          </div>
        )}
      </div>

      {/* Action buttons */}
      {item.status === 'pending' && (
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
          <button
            id={`followup-approve-${item.id}`}
            onClick={() => onApprove(item.id)}
            style={{
              display: 'flex', alignItems: 'center', gap: 6,
              padding: '7px 14px', borderRadius: 9, cursor: 'pointer',
              background: 'rgba(16,185,129,0.15)',
              border: '1px solid rgba(16,185,129,0.35)',
              color: '#10b981', fontSize: 12.5, fontWeight: 600,
              transition: 'all 0.2s',
            }}
            onMouseEnter={e => e.currentTarget.style.background = 'rgba(16,185,129,0.25)'}
            onMouseLeave={e => e.currentTarget.style.background = 'rgba(16,185,129,0.15)'}
          >
            <CheckCircle2 size={13} /> Approve
          </button>
          <button
            id={`followup-copy-${item.id}`}
            onClick={copy}
            style={{
              display: 'flex', alignItems: 'center', gap: 6,
              padding: '7px 14px', borderRadius: 9, cursor: 'pointer',
              background: copied ? 'rgba(16,185,129,0.12)' : 'rgba(255,255,255,0.06)',
              border: `1px solid ${copied ? 'rgba(16,185,129,0.3)' : 'rgba(255,255,255,0.1)'}`,
              color: copied ? '#10b981' : 'rgba(148,163,184,0.8)',
              fontSize: 12.5, fontWeight: 600, transition: 'all 0.2s',
            }}
          >
            <Copy size={13} /> {copied ? 'Copied!' : 'Copy Draft'}
          </button>
          <button
            id={`followup-dismiss-${item.id}`}
            onClick={() => onDismiss(item.id)}
            style={{
              display: 'flex', alignItems: 'center', gap: 6,
              padding: '7px 14px', borderRadius: 9, cursor: 'pointer',
              background: 'rgba(239,68,68,0.08)',
              border: '1px solid rgba(239,68,68,0.2)',
              color: '#f87171', fontSize: 12.5, fontWeight: 600,
              transition: 'all 0.2s',
            }}
            onMouseEnter={e => e.currentTarget.style.background = 'rgba(239,68,68,0.18)'}
            onMouseLeave={e => e.currentTarget.style.background = 'rgba(239,68,68,0.08)'}
          >
            <XCircle size={13} /> Dismiss
          </button>
        </div>
      )}
      {item.status !== 'pending' && (
        <div style={{ display: 'flex', gap: 8 }}>
          <button
            onClick={copy}
            style={{
              display: 'flex', alignItems: 'center', gap: 6,
              padding: '7px 14px', borderRadius: 9, cursor: 'pointer',
              background: 'rgba(255,255,255,0.05)',
              border: '1px solid rgba(255,255,255,0.08)',
              color: 'rgba(148,163,184,0.7)', fontSize: 12.5,
            }}
          >
            <Copy size={13} /> Copy
          </button>
          <button
            onClick={() => onDelete(item.id)}
            style={{
              display: 'flex', alignItems: 'center', gap: 6,
              padding: '7px 14px', borderRadius: 9, cursor: 'pointer',
              background: 'rgba(239,68,68,0.07)',
              border: '1px solid rgba(239,68,68,0.18)',
              color: '#f87171', fontSize: 12.5,
            }}
          >
            <Trash2 size={13} /> Delete
          </button>
        </div>
      )}
    </div>
  )
}

export default function FollowupPage() {
  const [followups, setFollowups]   = useState([])
  const [loading, setLoading]       = useState(true)
  const [filter, setFilter]         = useState('')
  const [genForm, setGenForm]       = useState({ job_url: '', job_title: '', company: '', days_since_apply: 7 })
  const [generating, setGenerating] = useState(false)

  const load = useCallback(async (statusFilter) => {
    setLoading(true)
    try {
      const data = await api.followups(statusFilter || '')
      setFollowups(Array.isArray(data) ? data : [])
    } catch {
      setFollowups([])
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { load(filter) }, [filter, load])

  const handleApprove = async (id) => {
    try {
      await api.approveFollowup(id)
      toast.success('Follow-up approved!')
      load(filter)
    } catch (e) { toast.error(e.message) }
  }

  const handleDismiss = async (id) => {
    try {
      await api.dismissFollowup(id)
      toast('Follow-up dismissed', { icon: '🚫' })
      load(filter)
    } catch (e) { toast.error(e.message) }
  }

  const handleDelete = async (id) => {
    try {
      await api.deleteFollowup(id)
      toast.success('Deleted')
      load(filter)
    } catch (e) { toast.error(e.message) }
  }

  const handleGenerate = async () => {
    if (!genForm.job_url) { toast.error('Job URL required'); return }
    setGenerating(true)
    try {
      await api.generateFollowup(genForm)
      toast.success('Follow-up draft queued! It will appear shortly.')
      setTimeout(() => load(filter), 3000)
    } catch (e) {
      toast.error(e.message || 'Generation failed')
    } finally {
      setGenerating(false)
    }
  }

  const counts = {
    pending:   followups.filter(f => f.status === 'pending').length,
    approved:  followups.filter(f => f.status === 'approved').length,
    dismissed: followups.filter(f => f.status === 'dismissed').length,
  }

  return (
    <div className="space-y-6" style={{ animation: 'fadeIn 0.4s ease-out both' }}>
      <PageHeader
        title="Follow-up Inbox"
        sub="AI-drafted follow-up emails — review, approve & copy to send manually"
      />

      {/* Stats bar */}
      <div style={{ display: 'flex', gap: 12 }}>
        {Object.entries(counts).map(([status, count]) => {
          const s = STATUS_COLORS[status]
          return (
            <button
              key={status}
              onClick={() => setFilter(filter === status ? '' : status)}
              style={{
                padding: '10px 20px', borderRadius: 12, cursor: 'pointer',
                background: filter === status ? s.bg : 'rgba(255,255,255,0.03)',
                border: `1px solid ${filter === status ? s.border : 'rgba(255,255,255,0.08)'}`,
                color: filter === status ? s.text : 'rgba(148,163,184,0.7)',
                fontWeight: 600, fontSize: 13, transition: 'all 0.2s',
                display: 'flex', alignItems: 'center', gap: 8,
              }}
            >
              <span style={{ textTransform: 'capitalize' }}>{status}</span>
              <span style={{
                padding: '1px 8px', borderRadius: 12, fontSize: 11,
                background: filter === status ? s.border : 'rgba(255,255,255,0.08)',
              }}>
                {count}
              </span>
            </button>
          )
        })}
        <button
          id="followup-refresh-btn"
          onClick={() => load(filter)}
          style={{
            marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: 6,
            padding: '10px 16px', borderRadius: 12, cursor: 'pointer',
            background: 'rgba(255,255,255,0.03)',
            border: '1px solid rgba(255,255,255,0.08)',
            color: 'rgba(148,163,184,0.7)', fontSize: 12.5,
          }}
        >
          <RefreshCw size={14} /> Refresh
        </button>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 340px', gap: 20, alignItems: 'start' }}>

        {/* ── Left: Follow-up list ── */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          {loading && (
            <div style={{ textAlign: 'center', padding: '3rem', color: 'rgba(148,163,184,0.4)' }}>
              <Loader2 size={24} style={{ animation: 'spin 1s linear infinite', margin: '0 auto 12px' }} />
              <p style={{ fontSize: 13 }}>Loading follow-ups…</p>
            </div>
          )}
          {!loading && followups.length === 0 && (
            <div style={{
              ...card, padding: '3rem', textAlign: 'center',
              color: 'rgba(148,163,184,0.4)',
            }}>
              <Mail size={40} style={{ margin: '0 auto 16px', opacity: 0.3 }} />
              <p style={{ fontSize: 14, fontWeight: 600 }}>No follow-ups yet</p>
              <p style={{ fontSize: 12, marginTop: 6 }}>Generate a follow-up using the form on the right →</p>
            </div>
          )}
          {followups.map((f, i) => (
            <FollowupCard
              key={f.id || i}
              item={f}
              onApprove={handleApprove}
              onDismiss={handleDismiss}
              onDelete={handleDelete}
            />
          ))}
        </div>

        {/* ── Right: Generator form ── */}
        <div style={{ ...card, padding: '1.5rem', position: 'sticky', top: 20 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 16 }}>
            <div style={{
              width: 32, height: 32, borderRadius: 9,
              background: 'linear-gradient(135deg, #3b82f6, #6366f1)',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              boxShadow: '0 0 12px rgba(59,130,246,0.4)',
            }}>
              <Sparkles size={15} className="text-white" />
            </div>
            <p style={{ fontSize: 13, fontWeight: 700, color: 'rgba(226,232,240,0.95)' }}>Generate Follow-up</p>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            {[
              { key: 'job_url',   label: 'JOB URL *',         placeholder: 'https://...' },
              { key: 'job_title', label: 'JOB TITLE',         placeholder: 'e.g. QA Engineer' },
              { key: 'company',   label: 'COMPANY',           placeholder: 'e.g. Razorpay' },
            ].map(({ key, label, placeholder }) => (
              <div key={key}>
                <label style={{ fontSize: 10.5, color: 'rgba(148,163,184,0.55)', fontWeight: 600, display: 'block', marginBottom: 4, letterSpacing: '0.05em' }}>
                  {label}
                </label>
                <input
                  id={`followup-gen-${key}`}
                  value={genForm[key]}
                  onChange={e => setGenForm(f => ({ ...f, [key]: e.target.value }))}
                  placeholder={placeholder}
                  style={{ ...inputStyle, width: '100%' }}
                  onFocus={e => e.target.style.borderColor = 'rgba(59,130,246,0.5)'}
                  onBlur={e => e.target.style.borderColor = 'rgba(255,255,255,0.1)'}
                />
              </div>
            ))}
            <div>
              <label style={{ fontSize: 10.5, color: 'rgba(148,163,184,0.55)', fontWeight: 600, display: 'block', marginBottom: 4, letterSpacing: '0.05em' }}>
                DAYS SINCE APPLYING
              </label>
              <input
                id="followup-gen-days"
                type="number"
                min={1} max={30}
                value={genForm.days_since_apply}
                onChange={e => setGenForm(f => ({ ...f, days_since_apply: Number(e.target.value) }))}
                style={{ ...inputStyle, width: '100%' }}
                onFocus={e => e.target.style.borderColor = 'rgba(59,130,246,0.5)'}
                onBlur={e => e.target.style.borderColor = 'rgba(255,255,255,0.1)'}
              />
            </div>
          </div>

          <button
            id="followup-generate-btn"
            onClick={handleGenerate}
            disabled={generating}
            style={{
              marginTop: 16, width: '100%', display: 'flex',
              alignItems: 'center', justifyContent: 'center', gap: 8,
              padding: '11px 16px', borderRadius: 12, cursor: generating ? 'not-allowed' : 'pointer',
              background: generating
                ? 'rgba(59,130,246,0.2)'
                : 'linear-gradient(135deg, #3b82f6 0%, #6366f1 100%)',
              border: 'none', color: '#fff', fontWeight: 700, fontSize: 13,
              boxShadow: generating ? 'none' : '0 0 16px rgba(59,130,246,0.35)',
              transition: 'all 0.2s', opacity: generating ? 0.7 : 1,
            }}
          >
            {generating
              ? <><Loader2 size={15} style={{ animation: 'spin 1s linear infinite' }} /> Queuing…</>
              : <><Sparkles size={15} /> Draft Follow-up</>}
          </button>

          <p style={{ fontSize: 11, color: 'rgba(148,163,184,0.45)', marginTop: 10, lineHeight: 1.5 }}>
            Drafts are <strong style={{ color: 'rgba(148,163,184,0.7)' }}>never sent automatically</strong>.
            Review, copy & send manually from your email client.
          </p>
        </div>

      </div>
    </div>
  )
}
