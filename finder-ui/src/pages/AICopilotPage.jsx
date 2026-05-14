// src/pages/AICopilotPage.jsx — Gemini AI Career Copilot
import { useState, useEffect, useRef } from 'react'
import { api } from '../api.js'
import PageHeader from '../components/PageHeader.jsx'
import toast from 'react-hot-toast'
import {
  Sparkles, FileText, MessageSquare, Mail, Lightbulb,
  Copy, RefreshCw, ChevronDown, Briefcase, Clock, CheckCircle2, Loader2
} from 'lucide-react'

const GEN_TYPES = [
  { id: 'cover_letter',      label: 'Cover Letter',      icon: FileText,      color: '#6366f1', desc: 'Personalised cover letter tailored to the role' },
  { id: 'hire_me_pitch',     label: 'Hire Me Pitch',     icon: Lightbulb,     color: '#f59e0b', desc: 'Concise elevator pitch to impress recruiters' },
  { id: 'interview_answer',  label: 'Interview Answer',  icon: MessageSquare, color: '#10b981', desc: 'Structured answers to common interview questions' },
  { id: 'followup_email',    label: 'Follow-up Email',   icon: Mail,          color: '#3b82f6', desc: 'Professional follow-up email after applying' },
]

const POLL_INTERVAL_MS = 2000
const MAX_POLLS = 30

const card = {
  background: 'linear-gradient(135deg, rgba(13,21,38,0.95) 0%, rgba(8,15,31,0.98) 100%)',
  border: '1px solid rgba(255,255,255,0.07)',
  borderRadius: 16,
  boxShadow: '0 4px 24px rgba(0,0,0,0.4)',
  padding: '1.5rem',
}

const inputStyle = {
  width: '100%',
  background: 'rgba(255,255,255,0.04)',
  border: '1px solid rgba(255,255,255,0.1)',
  borderRadius: 10,
  color: 'rgba(226,232,240,0.9)',
  fontSize: 13,
  padding: '10px 14px',
  outline: 'none',
  resize: 'vertical',
  fontFamily: 'inherit',
  transition: 'border-color 0.2s',
}

function TypeButton({ type, selected, onClick }) {
  const Icon = type.icon
  const isSelected = selected === type.id
  return (
    <button
      onClick={() => onClick(type.id)}
      style={{
        display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 8,
        padding: '14px 10px',
        borderRadius: 14,
        background: isSelected
          ? `linear-gradient(135deg, ${type.color}22 0%, ${type.color}11 100%)`
          : 'rgba(255,255,255,0.03)',
        border: `1px solid ${isSelected ? type.color + '55' : 'rgba(255,255,255,0.08)'}`,
        cursor: 'pointer', flex: 1, minWidth: 0,
        transition: 'all 0.2s',
        boxShadow: isSelected ? `0 0 20px ${type.color}22` : 'none',
      }}
    >
      <Icon size={20} style={{ color: isSelected ? type.color : 'rgba(148,163,184,0.6)' }} />
      <span style={{
        fontSize: 11.5, fontWeight: 600,
        color: isSelected ? type.color : 'rgba(148,163,184,0.7)',
        textAlign: 'center', lineHeight: 1.3,
      }}>
        {type.label}
      </span>
    </button>
  )
}

function HistoryCard({ item }) {
  const [copied, setCopied] = useState(false)
  const type = GEN_TYPES.find(t => t.id === item.generation_type) || GEN_TYPES[0]
  const Icon = type.icon

  const copy = () => {
    navigator.clipboard.writeText(item.response || '')
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <div style={{
      background: 'rgba(255,255,255,0.025)',
      border: '1px solid rgba(255,255,255,0.07)',
      borderRadius: 12,
      padding: '1rem',
      position: 'relative',
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 10 }}>
        <span style={{
          padding: '3px 10px', borderRadius: 20,
          background: `${type.color}22`, color: type.color,
          fontSize: 11, fontWeight: 600, display: 'flex', alignItems: 'center', gap: 5,
        }}>
          <Icon size={11} /> {type.label}
        </span>
        {item.cached && (
          <span style={{ fontSize: 10, color: 'rgba(148,163,184,0.4)', fontStyle: 'italic' }}>⚡ cached</span>
        )}
        <span style={{ fontSize: 11, color: 'rgba(148,163,184,0.4)', marginLeft: 'auto' }}>
          {item.created_at ? new Date(item.created_at).toLocaleString() : ''}
        </span>
      </div>
      <p style={{
        fontSize: 12.5, color: 'rgba(203,213,225,0.85)',
        lineHeight: 1.7, whiteSpace: 'pre-wrap', maxHeight: 160, overflow: 'hidden',
        maskImage: 'linear-gradient(180deg, rgba(0,0,0,1) 70%, rgba(0,0,0,0) 100%)',
      }}>
        {item.response}
      </p>
      <button
        onClick={copy}
        style={{
          marginTop: 10, display: 'flex', alignItems: 'center', gap: 6,
          padding: '6px 14px', borderRadius: 8,
          background: copied ? 'rgba(16,185,129,0.15)' : 'rgba(255,255,255,0.06)',
          border: `1px solid ${copied ? 'rgba(16,185,129,0.4)' : 'rgba(255,255,255,0.1)'}`,
          color: copied ? '#10b981' : 'rgba(148,163,184,0.8)',
          fontSize: 12, cursor: 'pointer', transition: 'all 0.2s',
        }}
      >
        {copied ? <CheckCircle2 size={13} /> : <Copy size={13} />}
        {copied ? 'Copied!' : 'Copy'}
      </button>
    </div>
  )
}

export default function AICopilotPage() {
  const [genType, setGenType]     = useState('cover_letter')
  const [jobTitle, setJobTitle]   = useState('')
  const [company, setCompany]     = useState('')
  const [skills, setSkills]       = useState('')
  const [question, setQuestion]   = useState('')
  const [generating, setGenerating] = useState(false)
  const [result, setResult]         = useState(null)
  const [copied, setCopied]         = useState(false)
  const [history, setHistory]       = useState([])
  const [histLoading, setHistLoading] = useState(true)
  const pollRef = useRef(null)

  useEffect(() => {
    api.aiHistory().then(h => {
      setHistory(Array.isArray(h) ? h : [])
    }).catch(() => setHistory([])).finally(() => setHistLoading(false))
    return () => { if (pollRef.current) clearInterval(pollRef.current) }
  }, [])

  const stopPoll = () => {
    if (pollRef.current) { clearInterval(pollRef.current); pollRef.current = null }
  }

  const generate = async () => {
    if (generating) return
    const context = {
      job_title: jobTitle || 'Software Engineer',
      company: company || 'the company',
      skills: skills || '',
      question: question || '',
    }
    setGenerating(true)
    setResult(null)
    try {
      const res = await api.aiGenerate(genType, context)
      const taskId = res?.task_id
      if (!taskId) throw new Error('No task ID returned')

      let polls = 0
      pollRef.current = setInterval(async () => {
        polls++
        if (polls > MAX_POLLS) {
          stopPoll()
          setGenerating(false)
          toast.error('Generation timed out — Celery worker may not be running')
          return
        }
        try {
          const r = await api.aiGenerateResult(taskId)
          if (r?.status === 'done') {
            stopPoll()
            setGenerating(false)
            const text = r.result?.response || r.result?.text || JSON.stringify(r.result)
            setResult(text)
            // Refresh history
            api.aiHistory().then(h => setHistory(Array.isArray(h) ? h : []))
            toast.success('AI content generated!')
          } else if (r?.status === 'failed') {
            stopPoll()
            setGenerating(false)
            toast.error(r.error || 'Generation failed')
          }
        } catch (_) {}
      }, POLL_INTERVAL_MS)
    } catch (e) {
      setGenerating(false)
      toast.error(e.message || 'Failed to start generation')
    }
  }

  const copy = () => {
    if (!result) return
    navigator.clipboard.writeText(result)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
    toast.success('Copied to clipboard!')
  }

  const currentType = GEN_TYPES.find(t => t.id === genType) || GEN_TYPES[0]

  return (
    <div className="space-y-6" style={{ animation: 'fadeIn 0.4s ease-out both' }}>
      <PageHeader
        title="AI Career Copilot"
        sub="Powered by Gemini — generate cover letters, pitches, interview answers & follow-ups"
      />

      <div className="grid" style={{ gridTemplateColumns: '1fr 1fr', gap: 20 }}>

        {/* ── Left: Generator ── */}
        <div style={{ ...card, display: 'flex', flexDirection: 'column', gap: 20 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <div style={{
              width: 36, height: 36, borderRadius: 10,
              background: 'linear-gradient(135deg, #6366f1, #4f46e5)',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              boxShadow: '0 0 16px rgba(99,102,241,0.4)',
            }}>
              <Sparkles size={18} className="text-white" />
            </div>
            <div>
              <p style={{ fontSize: 14, fontWeight: 700, color: 'rgba(226,232,240,0.95)' }}>Generate Content</p>
              <p style={{ fontSize: 11, color: 'rgba(148,163,184,0.6)' }}>{currentType.desc}</p>
            </div>
          </div>

          {/* Type selector */}
          <div style={{ display: 'flex', gap: 8 }}>
            {GEN_TYPES.map(t => (
              <TypeButton key={t.id} type={t} selected={genType} onClick={setGenType} />
            ))}
          </div>

          {/* Inputs */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
              <div>
                <label style={{ fontSize: 11, color: 'rgba(148,163,184,0.6)', fontWeight: 600, display: 'block', marginBottom: 5 }}>
                  JOB TITLE
                </label>
                <input
                  id="copilot-job-title"
                  value={jobTitle}
                  onChange={e => setJobTitle(e.target.value)}
                  placeholder="e.g. Senior QA Engineer"
                  style={inputStyle}
                  onFocus={e => e.target.style.borderColor = 'rgba(99,102,241,0.5)'}
                  onBlur={e => e.target.style.borderColor = 'rgba(255,255,255,0.1)'}
                />
              </div>
              <div>
                <label style={{ fontSize: 11, color: 'rgba(148,163,184,0.6)', fontWeight: 600, display: 'block', marginBottom: 5 }}>
                  COMPANY
                </label>
                <input
                  id="copilot-company"
                  value={company}
                  onChange={e => setCompany(e.target.value)}
                  placeholder="e.g. Razorpay"
                  style={inputStyle}
                  onFocus={e => e.target.style.borderColor = 'rgba(99,102,241,0.5)'}
                  onBlur={e => e.target.style.borderColor = 'rgba(255,255,255,0.1)'}
                />
              </div>
            </div>
            <div>
              <label style={{ fontSize: 11, color: 'rgba(148,163,184,0.6)', fontWeight: 600, display: 'block', marginBottom: 5 }}>
                RELEVANT SKILLS
              </label>
              <input
                id="copilot-skills"
                value={skills}
                onChange={e => setSkills(e.target.value)}
                placeholder="e.g. Python, Selenium, Playwright, REST APIs"
                style={inputStyle}
                onFocus={e => e.target.style.borderColor = 'rgba(99,102,241,0.5)'}
                onBlur={e => e.target.style.borderColor = 'rgba(255,255,255,0.1)'}
              />
            </div>
            {genType === 'interview_answer' && (
              <div>
                <label style={{ fontSize: 11, color: 'rgba(148,163,184,0.6)', fontWeight: 600, display: 'block', marginBottom: 5 }}>
                  INTERVIEW QUESTION
                </label>
                <textarea
                  id="copilot-question"
                  value={question}
                  onChange={e => setQuestion(e.target.value)}
                  placeholder="e.g. Tell me about your experience with test automation..."
                  rows={3}
                  style={inputStyle}
                  onFocus={e => e.target.style.borderColor = 'rgba(99,102,241,0.5)'}
                  onBlur={e => e.target.style.borderColor = 'rgba(255,255,255,0.1)'}
                />
              </div>
            )}
          </div>

          <button
            id="copilot-generate-btn"
            onClick={generate}
            disabled={generating}
            style={{
              display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8,
              padding: '12px 20px', borderRadius: 12, cursor: generating ? 'not-allowed' : 'pointer',
              background: generating
                ? 'rgba(99,102,241,0.2)'
                : 'linear-gradient(135deg, #6366f1 0%, #4f46e5 60%, #7c3aed 100%)',
              border: 'none', color: '#fff', fontWeight: 700, fontSize: 14,
              boxShadow: generating ? 'none' : '0 0 20px rgba(99,102,241,0.4)',
              transition: 'all 0.2s',
              opacity: generating ? 0.7 : 1,
            }}
          >
            {generating
              ? <><Loader2 size={16} style={{ animation: 'spin 1s linear infinite' }} /> Generating…</>
              : <><Sparkles size={16} /> Generate with Gemini</>}
          </button>

          {/* Result */}
          {result && (
            <div style={{
              background: 'rgba(99,102,241,0.06)',
              border: '1px solid rgba(99,102,241,0.2)',
              borderRadius: 12, padding: '1rem',
              animation: 'fadeIn 0.3s ease-out',
            }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 10 }}>
                <span style={{ fontSize: 12, fontWeight: 600, color: '#818cf8', display: 'flex', alignItems: 'center', gap: 6 }}>
                  <CheckCircle2 size={14} /> Result
                </span>
                <div style={{ display: 'flex', gap: 6 }}>
                  <button
                    onClick={copy}
                    style={{
                      display: 'flex', alignItems: 'center', gap: 5,
                      padding: '5px 12px', borderRadius: 8,
                      background: copied ? 'rgba(16,185,129,0.15)' : 'rgba(255,255,255,0.06)',
                      border: `1px solid ${copied ? 'rgba(16,185,129,0.4)' : 'rgba(255,255,255,0.1)'}`,
                      color: copied ? '#10b981' : 'rgba(148,163,184,0.8)',
                      fontSize: 12, cursor: 'pointer', transition: 'all 0.2s',
                    }}
                  >
                    {copied ? <CheckCircle2 size={12} /> : <Copy size={12} />}
                    {copied ? 'Copied!' : 'Copy'}
                  </button>
                  <button
                    onClick={generate}
                    style={{
                      display: 'flex', alignItems: 'center', gap: 5,
                      padding: '5px 12px', borderRadius: 8,
                      background: 'rgba(255,255,255,0.06)',
                      border: '1px solid rgba(255,255,255,0.1)',
                      color: 'rgba(148,163,184,0.8)',
                      fontSize: 12, cursor: 'pointer',
                    }}
                  >
                    <RefreshCw size={12} /> Regenerate
                  </button>
                </div>
              </div>
              <pre style={{
                fontSize: 12.5, color: 'rgba(203,213,225,0.9)',
                lineHeight: 1.75, whiteSpace: 'pre-wrap', fontFamily: 'inherit',
                maxHeight: 320, overflow: 'auto',
              }}>
                {result}
              </pre>
            </div>
          )}
        </div>

        {/* ── Right: History ── */}
        <div style={{ ...card, display: 'flex', flexDirection: 'column', gap: 16, maxHeight: 700, overflow: 'hidden' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <Clock size={16} style={{ color: 'rgba(148,163,184,0.5)' }} />
            <p style={{ fontSize: 13, fontWeight: 700, color: 'rgba(226,232,240,0.9)' }}>Generation History</p>
            <span style={{
              marginLeft: 'auto', fontSize: 11, fontWeight: 600,
              padding: '2px 8px', borderRadius: 20,
              background: 'rgba(99,102,241,0.15)', color: '#818cf8',
            }}>
              {history.length}
            </span>
          </div>

          <div style={{ flex: 1, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: 10 }}>
            {histLoading && (
              <div style={{ textAlign: 'center', padding: '2rem', color: 'rgba(148,163,184,0.4)' }}>
                <Loader2 size={20} style={{ animation: 'spin 1s linear infinite', margin: '0 auto 8px' }} />
                <p style={{ fontSize: 12 }}>Loading history…</p>
              </div>
            )}
            {!histLoading && history.length === 0 && (
              <div style={{ textAlign: 'center', padding: '3rem 1rem', color: 'rgba(148,163,184,0.4)' }}>
                <Sparkles size={32} style={{ margin: '0 auto 12px', opacity: 0.3 }} />
                <p style={{ fontSize: 13 }}>No generations yet</p>
                <p style={{ fontSize: 11, marginTop: 4 }}>Generate your first AI content using the form →</p>
              </div>
            )}
            {history.map((item, i) => (
              <HistoryCard key={item.id || i} item={item} />
            ))}
          </div>
        </div>

      </div>

      {/* Tips */}
      <div style={{
        ...card,
        background: 'linear-gradient(135deg, rgba(99,102,241,0.08) 0%, rgba(79,70,229,0.05) 100%)',
        border: '1px solid rgba(99,102,241,0.15)',
        display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 16,
      }}>
        {[
          { icon: '📝', title: 'Cover Letter', tip: 'Fill in job title + company for a targeted, recruiter-friendly letter.' },
          { icon: '🎯', title: 'Hire Me Pitch', tip: 'A punchy 3-sentence pitch you can paste into application portals.' },
          { icon: '💬', title: 'Interview Answer', tip: 'Paste the question for a structured STAR-method answer.' },
          { icon: '📧', title: 'Follow-up Email', tip: 'Auto-drafted 7-day follow-up — approve & send manually.' },
        ].map(tip => (
          <div key={tip.title} style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
            <span style={{ fontSize: 22 }}>{tip.icon}</span>
            <p style={{ fontSize: 12.5, fontWeight: 700, color: 'rgba(226,232,240,0.9)' }}>{tip.title}</p>
            <p style={{ fontSize: 11.5, color: 'rgba(148,163,184,0.65)', lineHeight: 1.5 }}>{tip.tip}</p>
          </div>
        ))}
      </div>
    </div>
  )
}
