// src/components/Shared.jsx — reusable UI atoms
import React from 'react'

export function Spinner() {
  return <div className="spinner" />
}

export function Loading() {
  return (
    <div className="loading">
      <Spinner /> Loading...
    </div>
  )
}

export function Empty({ icon = '📭', msg = 'No data yet' }) {
  return (
    <div className="empty">
      <div className="empty-icon">{icon}</div>
      {msg}
    </div>
  )
}

export function Toast({ toasts }) {
  return (
    <div className="toast-wrap">
      {toasts.map(t => (
        <div key={t.id} className={`toast ${t.type}`}>
          <span>{t.type === 'success' ? '✅' : t.type === 'error' ? '❌' : 'ℹ️'}</span>
          {t.msg}
        </div>
      ))}
    </div>
  )
}

export function Score({ value }) {
  if (value == null) return <span className="td-mono" style={{color:'var(--text-muted)'}}>—</span>
  const cls = value >= 60 ? 'high' : value >= 40 ? 'medium' : 'low'
  return <span className={`score ${cls}`}>{value.toFixed(1)}%</span>
}

export function StatusBadge({ status }) {
  const map = {
    applied:       ['badge-green',  '✅'],
    uncertain:     ['badge-yellow', '⚠️'],
    failed:        ['badge-red',    '❌'],
    skip:          ['badge-muted',  '⏭️'],
    pending:       ['badge-blue',   '⏳'],
    external_skip: ['badge-purple', '🔗'],
    already_applied:['badge-muted','♻️'],
    running:       ['badge-green',  '▶'],
    paused:        ['badge-yellow', '⏸'],
  }
  const [cls, icon] = map[status] || ['badge-muted', '❓']
  return <span className={`badge ${cls}`}>{icon} {status}</span>
}

export function ProgressBar({ value, max, color = '' }) {
  const pct = Math.min((value / Math.max(max, 1)) * 100, 100)
  return (
    <div className="progress-wrap">
      <div className={`progress-fill ${color}`} style={{ width: `${pct}%` }} />
    </div>
  )
}

export function MiniChart({ data = [], color = 'var(--accent)' }) {
  const max = Math.max(...data.map(d => d.value || 0), 1)
  return (
    <div className="chart-area">
      {data.map((d, i) => (
        <div
          key={i}
          className="chart-bar"
          style={{ height: `${Math.max((d.value / max) * 100, 4)}%`, borderColor: color, background: `${color}20` }}
        >
          <div className="tooltip">{d.label}: {d.value}</div>
        </div>
      ))}
    </div>
  )
}

export function SectionCard({ title, icon, children, action }) {
  return (
    <div className="card">
      <div className="card-title" style={{ justifyContent: 'space-between' }}>
        <span>{icon && <span style={{ marginRight: 6 }}>{icon}</span>}{title}</span>
        {action}
      </div>
      {children}
    </div>
  )
}
