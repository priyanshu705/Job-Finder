import { useState } from 'react'
import { ExternalLink, ChevronLeft, ChevronRight, Wand2, Check, X, Copy, Info, Target, CheckCircle } from 'lucide-react'
import { api } from '../api.js'

const PAGE_SIZE = 20

function Badge({ status }) {
  const map = {
    applied:               'badge-applied',
    applied_manual:        'badge-applied',
    pending:               'badge-pending',
    ready_to_apply:        'badge-pending',
    opened:                'badge-uncertain',
    failed:                'badge-failed',
    uncertain:             'badge-uncertain',
    verification_required: 'badge-failed',
    skip:                  'badge-skip',
    skipped:               'badge-skip',
    external_skip:         'badge-external',
  }
  return <span className={map[status] || 'badge-skip'}>{status?.replace(/_/g, ' ') ?? '—'}</span>
}

function ScoreBar({ score }) {
  if (score == null) return <span className="text-slate-500 text-xs">—</span>
  const pct = Math.min(Math.max(score, 0), 100)
  const color = pct >= 75 ? 'bg-emerald-500' : pct >= 50 ? 'bg-amber-500' : 'bg-red-500'
  return (
    <div className="flex items-center gap-2">
      <div className="h-1.5 w-16 bg-slate-700 rounded-full overflow-hidden">
        <div className={`h-full ${color} rounded-full`} style={{ width: `${pct}%` }} />
      </div>
      <span className="text-xs text-slate-300">{Math.round(pct)}</span>
    </div>
  )
}

function fmtDate(s) {
  if (!s) return '—'
  return new Date(s).toLocaleDateString([], { month: 'short', day: 'numeric' })
}

function JobAssistantPanel({ job, onClose, onUpdate, nextJob }) {
  let data = null
  try {
    data = job.assistant_data
      ? (typeof job.assistant_data === 'string' ? JSON.parse(job.assistant_data) : job.assistant_data)
      : null
  } catch { data = null }
  const [copied, setCopied] = useState(null)
  const [showFeedback, setShowFeedback] = useState(false)
  const [showConfirmation, setShowConfirmation] = useState(false)

  const copy = (text, key) => {
    navigator.clipboard.writeText(text)
    setCopied(key)
    setTimeout(() => setCopied(null), 2000)
  }

  const handleAction = async (status) => {
    if (status === 'applied_manual' && !showConfirmation) {
      setShowConfirmation(true)
      return
    }
    await api.updateJobStatus(job.id, status)
    if (status === 'applied_manual') {
      setShowConfirmation(false)
      setShowFeedback(true)
    } else {
      onUpdate()
      if (nextJob) nextJob()
      else onClose()
    }
  }

  const handleFeedback = async (fb) => {
    await api.updateFeedback(job.id, fb)
    setShowFeedback(false)
    onUpdate()
    if (nextJob) nextJob()
    else onClose()
  }

  return (
    <div className="fixed inset-y-0 right-0 w-[460px] z-50 flex flex-col animate-slide-in-right" style={{ background: 'linear-gradient(180deg, rgba(8,15,31,0.99) 0%, rgba(13,21,38,0.99) 100%)', borderLeft: '1px solid rgba(99,102,241,0.25)', boxShadow: '-8px 0 60px rgba(0,0,0,0.7), -2px 0 20px rgba(99,102,241,0.08)', backdropFilter: 'blur(24px)' }}>
      <div className="p-4 flex items-center justify-between" style={{ borderBottom: '1px solid rgba(99,102,241,0.12)', background: 'rgba(99,102,241,0.04)' }}>
        <div style={{ flex: 1, minWidth: 0, paddingRight: 12 }}>
          <h3 className="font-bold line-clamp-1" style={{ color: '#e2e8f0', fontSize: 15 }}>{job.title}</h3>
          <p className="text-xs mt-0.5" style={{ color: '#818cf8' }}>{job.company}</p>
        </div>
        <button onClick={onClose} className="p-2 rounded-xl transition-all" style={{ background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.08)', color: 'rgba(148,163,184,0.7)' }} onMouseEnter={e=>{e.currentTarget.style.background='rgba(248,113,113,0.1)';e.currentTarget.style.color='#f87171'}} onMouseLeave={e=>{e.currentTarget.style.background='rgba(255,255,255,0.04)';e.currentTarget.style.color='rgba(148,163,184,0.7)'}}><X size={18} /></button>
      </div>

      <div className="flex-1 overflow-y-auto p-5 space-y-6">
        {showConfirmation ? (
           <div className="h-full flex flex-col items-center justify-center text-center space-y-4 animate-fade-in">
              <div className="w-16 h-16 bg-blue-500/10 text-blue-500 rounded-full flex items-center justify-center">
                 <Target size={32} />
              </div>
              <div>
                 <h4 className="text-lg font-bold text-white">Confirmation Required</h4>
                 <p className="text-sm text-slate-400 px-8">Did you actually submit the application in the browser?</p>
              </div>
              <div className="flex flex-col gap-2 w-full max-w-[240px]">
                 <button onClick={() => handleAction('applied_manual')} className="w-full btn-primary py-2.5">Yes, I Submitted</button>
                 <button onClick={() => setShowConfirmation(false)} className="w-full btn-secondary py-2">Go Back</button>
              </div>
           </div>
        ) : showFeedback ? (
           <div className="h-full flex flex-col items-center justify-center text-center space-y-4 animate-fade-in">
              <div className="w-16 h-16 bg-emerald-500/10 text-emerald-500 rounded-full flex items-center justify-center">
                 <CheckCircle size={32} />
              </div>
              <div>
                 <h4 className="text-lg font-bold text-white">Application Logged!</h4>
                 <p className="text-sm text-slate-400">Was this job match relevant to you?</p>
              </div>
              <div className="flex gap-2 w-full max-w-[240px]">
                 <button onClick={() => handleFeedback('relevant')} className="flex-1 btn-primary bg-emerald-600 hover:bg-emerald-500 py-2">Yes</button>
                 <button onClick={() => handleFeedback('irrelevant')} className="flex-1 btn-secondary py-2">No</button>
              </div>
           </div>
        ) : !data ? (
          <div className="flex flex-col items-center justify-center py-10 text-slate-500 text-center">
            <Info size={40} className="mb-3 opacity-20" />
            <p className="text-sm">No assistant data available yet.</p>
            <p className="text-xs mt-1">Run the apply assistant to generate AI answers.</p>
          </div>
        ) : (
          <>
            {/* Match Reason */}
            {data.explanation && (
              <div className="p-3 bg-blue-500/10 border border-blue-500/20 rounded-xl">
                 <div className="flex items-center gap-2 mb-1.5">
                    <Target size={14} className="text-blue-400" />
                    <span className="text-[10px] font-bold uppercase tracking-wider text-blue-400">Why You Match</span>
                 </div>
                 <p className="text-xs text-slate-300 leading-relaxed">{data.explanation}</p>
              </div>
            )}

            {/* Pitch */}
            <div className="space-y-2">
              <label className="text-[10px] font-bold uppercase tracking-wider text-slate-500">Elevator Pitch</label>
              <div className="p-3 bg-slate-950 border border-slate-800 rounded-xl relative group hover:border-slate-700">
                <p className="text-sm text-slate-300 pr-8 italic">"{data.highlights?.pitch ?? '—'}"</p>
                <button onClick={() => copy(data.highlights?.pitch ?? '', 'pitch')} className="absolute top-2 right-2 p-1.5 opacity-0 group-hover:opacity-100 transition-opacity text-slate-500 hover:text-blue-400">
                  {copied === 'pitch' ? <Check size={14} className="text-emerald-500" /> : <Copy size={14} />}
                </button>
              </div>
            </div>

            {/* Cover Letter */}
            <div className="space-y-2">
              <label className="text-[10px] font-bold uppercase tracking-wider text-slate-500">Tailored Cover Letter</label>
              <div className="p-4 bg-slate-950 border border-slate-800 rounded-xl relative group hover:border-slate-700">
                <pre className="text-xs text-slate-400 whitespace-pre-wrap font-sans leading-relaxed">{data.cover_letter ?? ''}</pre>
                <button onClick={() => copy(data.cover_letter ?? '', 'letter')} className="absolute top-3 right-3 p-1.5 bg-slate-900 border border-slate-700 rounded-lg opacity-0 group-hover:opacity-100 transition-opacity text-slate-500 hover:text-blue-400 shadow-xl">
                  {copied === 'letter' ? <Check size={14} className="text-emerald-500" /> : <Copy size={14} />}
                </button>
              </div>
            </div>

            {/* Specific Answers */}
            {data.specific_answers && Object.keys(data.specific_answers).length > 0 && (
              <div className="space-y-4">
                <label className="text-[10px] font-bold uppercase tracking-wider text-slate-500">Smart Answers</label>
                {Object.entries(data.specific_answers).map(([q, a], idx) => (
                  <div key={idx} className="space-y-1.5 group">
                    <p className="text-[11px] text-slate-400 font-medium">Q: {q}</p>
                    <div className="p-3 bg-slate-950 border border-slate-800 rounded-xl relative group-hover:border-slate-700">
                      <p className="text-xs text-slate-300 pr-8">{a}</p>
                      <button onClick={() => copy(a, `q-${idx}`)} className="absolute top-2 right-2 p-1.5 opacity-0 group-hover:opacity-100 transition-opacity text-slate-500 hover:text-blue-400">
                        {copied === `q-${idx}` ? <Check size={14} className="text-emerald-500" /> : <Copy size={14} />}
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </>
        )}
      </div>

      {!showFeedback && !showConfirmation && (
        <div className="p-4 flex flex-col gap-3" style={{ borderTop: '1px solid rgba(99,102,241,0.12)', background: 'rgba(2,8,23,0.6)' }}>
          <div className="flex gap-3">
            <button onClick={() => handleAction('applied_manual')} className="flex-1 btn-primary py-2.5 flex items-center justify-center gap-2">
              <Check size={16} /> Mark Applied
            </button>
            <button onClick={() => handleAction('skipped')} className="flex-1 py-2.5 rounded-xl text-sm font-medium flex items-center justify-center gap-2 transition-all" style={{ background: 'rgba(248,113,113,0.08)', border: '1px solid rgba(248,113,113,0.2)', color: '#f87171' }}>
              <X size={16} /> Skip
            </button>
          </div>
          <div className="flex gap-2">
             <button onClick={() => handleAction('interview')} className="flex-1 py-1.5 rounded-xl text-xs font-bold uppercase tracking-wider transition-all" style={{ background: 'rgba(168,85,247,0.08)', border: '1px solid rgba(168,85,247,0.2)', color: '#c084fc' }}>Interview</button>
             <button onClick={() => handleAction('rejected')} className="flex-1 py-1.5 rounded-xl text-xs font-bold uppercase tracking-wider transition-all" style={{ background: 'rgba(248,113,113,0.08)', border: '1px solid rgba(248,113,113,0.2)', color: '#f87171' }}>Rejected</button>
          </div>
        </div>
      )}
    </div>
  )
}

export default function QueueTable({ rows = [], loading, onUpdate, hidePagination }) {
  const [page, setPage] = useState(0)
  const [selectedIndex, setSelectedIndex] = useState(-1)
  
  const total = rows.length
  const pages = Math.ceil(total / PAGE_SIZE)
  const slice = rows.slice(page * PAGE_SIZE, (page + 1) * PAGE_SIZE)

  const openJob = async (job) => {
    window.open(job.job_url, '_blank')
    if (job.status === 'pending' || job.status === 'ready_to_apply') {
        await api.updateJobStatus(job.id, 'opened')
        if (onUpdate) onUpdate()
    }
  }

  const nextJob = () => {
    if (selectedIndex < slice.length - 1) {
      setSelectedIndex(selectedIndex + 1)
    } else {
      setSelectedIndex(-1)
    }
  }

  const selectedJob = selectedIndex >= 0 ? slice[selectedIndex] : null;

  if (loading) return (
    <div className="card overflow-hidden">
      <table className="w-full">
        <thead><tr className="border-b border-slate-700/50">
          {['Company','Role','Score','Status',''].map(h => (
            <th key={h} className="table-head">{h}</th>
          ))}
        </tr></thead>
        <tbody>
          {[...Array(6)].map((_, i) => (
            <tr key={i} className="border-b border-slate-700/30">
              {[...Array(5)].map((_, j) => (
                <td key={j} className="table-cell"><div className="skeleton h-4 w-full" /></td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )

  if (!rows.length) return (
    <div className="card flex flex-col items-center justify-center py-16 text-slate-500">
      <p className="text-3xl mb-3">📭</p>
      <p className="text-sm font-medium">Queue is empty</p>
      <p className="text-xs mt-1">Run a scrape + match cycle to populate it</p>
    </div>
  )

  return (
    <>
      <div className="rounded-2xl overflow-hidden" style={{ background: 'linear-gradient(135deg, rgba(13,21,38,0.92) 0%, rgba(8,15,31,0.96) 100%)', border: '1px solid rgba(255,255,255,0.07)', boxShadow: '0 4px 24px rgba(0,0,0,0.45), inset 0 1px 0 rgba(255,255,255,0.04)' }}>
        <div className="overflow-x-auto">
          <table className="w-full min-w-[600px]">
            <thead>
              <tr style={{ borderBottom: '1px solid rgba(99,102,241,0.1)' }}>
                <th className="table-head">Company</th>
                <th className="table-head">Role</th>
                <th className="table-head">Score</th>
                <th className="table-head">Status</th>
                <th className="table-head"></th>
              </tr>
            </thead>
            <tbody>
              {slice.map((row, i) => {
                const isNew = row.queued_at && (Date.now() - new Date(row.queued_at).getTime()) < 3_600_000
                const isOpened = row.status === 'opened'
                const isSelected = selectedIndex === i
                return (
                  <tr key={row.id || i} className="transition-all duration-150" style={{ borderBottom: '1px solid rgba(255,255,255,0.04)', background: isSelected ? 'rgba(99,102,241,0.08)' : isNew ? 'rgba(99,102,241,0.04)' : isOpened ? 'rgba(251,191,36,0.03)' : 'transparent', outline: isSelected ? '1px solid rgba(99,102,241,0.3)' : 'none', outlineOffset: -1 }} onMouseEnter={e=>{if(!isSelected)e.currentTarget.style.background='rgba(99,102,241,0.05)'}} onMouseLeave={e=>{if(!isSelected)e.currentTarget.style.background=isNew?'rgba(99,102,241,0.04)':isOpened?'rgba(251,191,36,0.03)':'transparent'}}>
                    <td className="table-cell font-medium text-slate-200">
                      <div className="flex items-center gap-2">
                        {isNew && <span className="w-1.5 h-1.5 rounded-full bg-blue-400 flex-shrink-0" />}
                        {row.company || '—'}
                      </div>
                    </td>
                    <td className="table-cell">
                      <span className="text-slate-200 line-clamp-1">{row.title || row.role || '—'}</span>
                    </td>
                    <td className="table-cell">
                      <ScoreBar score={row.match_score_at_apply ?? row.match_score} />
                    </td>
                    <td className="table-cell"><Badge status={row.status} /></td>
                    <td className="table-cell">
                      <div className="flex items-center justify-end gap-1">
                        <button onClick={() => setSelectedIndex(i)} className="btn-primary py-1 px-3 text-[10px] uppercase font-bold tracking-wider flex items-center gap-1">
                          <Wand2 size={11} /> Assistant
                        </button>
                        {row.job_url && (
                          <button onClick={() => openJob(row)} className="p-1.5 rounded-lg hover:bg-blue-500/10 text-slate-500 hover:text-blue-400 transition-colors" title="Open job page">
                            <ExternalLink size={13} />
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>

        {/* Pagination */}
        {!hidePagination && pages > 1 && (
          <div className="flex items-center justify-between px-4 py-3 border-t border-slate-700/50">
            <span className="text-xs text-slate-500">{total} jobs · page {page + 1} of {pages}</span>
            <div className="flex gap-2">
              <button className="btn-secondary px-2 py-1.5" disabled={page === 0} onClick={() => setPage(p => p - 1)}>
                <ChevronLeft size={14} />
              </button>
              <button className="btn-secondary px-2 py-1.5" disabled={page >= pages - 1} onClick={() => setPage(p => p + 1)}>
                <ChevronRight size={14} />
              </button>
            </div>
          </div>
        )}
      </div>

      {selectedJob && (
        <>
          <div className="fixed inset-0 z-40 animate-fade-in" style={{ background: 'rgba(2,8,23,0.6)', backdropFilter: 'blur(8px)' }} onClick={() => setSelectedIndex(-1)} />
          <JobAssistantPanel 
            job={selectedJob} 
            onClose={() => setSelectedIndex(-1)} 
            onUpdate={onUpdate} 
            nextJob={nextJob}
          />
        </>
      )}
    </>
  )
}
