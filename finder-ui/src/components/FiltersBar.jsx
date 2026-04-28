// src/components/FiltersBar.jsx — UPGRADED: glass search bar with neon focus ring + gradient filter chips
import { Search, X, SlidersHorizontal } from 'lucide-react'

const STATUSES = ['', 'pending', 'applied', 'failed', 'uncertain', 'skip', 'external_skip']
const SORTS    = [
  { value: 'priority', label: 'Priority ↓' },
  { value: 'latest',   label: 'Newest First' },
]

export default function FiltersBar({ filters, onChange }) {
  const set = (k, v) => onChange({ ...filters, [k]: v })
  const hasActive = filters.q || filters.status || filters.sort !== 'priority' || filters.min_score || filters.company

  return (
    <div
      className="rounded-2xl p-3 flex flex-wrap gap-2 items-center"
      style={{
        background: 'linear-gradient(135deg, rgba(13,21,38,0.9) 0%, rgba(8,15,31,0.95) 100%)',
        border: '1px solid rgba(255,255,255,0.07)',
        backdropFilter: 'blur(16px)',
        boxShadow: '0 4px 20px rgba(0,0,0,0.35), inset 0 1px 0 rgba(255,255,255,0.04)',
      }}
    >
      {/* Icon */}
      <div
        className="flex-shrink-0 rounded-lg flex items-center justify-center"
        style={{ width: 30, height: 30, background: 'rgba(99,102,241,0.1)', border: '1px solid rgba(99,102,241,0.2)', color: '#818cf8' }}
      >
        <SlidersHorizontal size={14} />
      </div>

      {/* Search input */}
      <div className="relative flex-1 min-w-48">
        <Search size={13} className="absolute left-3 top-1/2 -translate-y-1/2" style={{ color: 'rgba(99,102,241,0.6)' }} />
        <input
          className="input-field pl-8"
          placeholder="Search by role, company, keyword…"
          aria-label="Search jobs"
          value={filters.q || ''}
          onChange={e => set('q', e.target.value)}
        />
      </div>

      {/* Status filter */}
      <select className="select-field w-36" aria-label="Filter by status" value={filters.status || ''} onChange={e => set('status', e.target.value)}>
        <option value="">All statuses</option>
        {STATUSES.filter(Boolean).map(s => (
          <option key={s} value={s}>{s.replace('_', ' ')}</option>
        ))}
      </select>

      {/* Sort */}
      <select className="select-field w-36" aria-label="Sort by" value={filters.sort || 'priority'} onChange={e => set('sort', e.target.value)}>
        {SORTS.map(s => <option key={s.value} value={s.value}>{s.label}</option>)}
      </select>

      {/* Min score */}
      <div className="flex items-center gap-2">
        <label className="text-xs whitespace-nowrap font-medium" style={{ color: 'rgba(100,116,139,0.8)' }}>Min score</label>
        <input
          type="number" min="0" max="100"
          className="input-field w-20"
          placeholder="0"
          aria-label="Minimum match score"
          value={filters.min_score || ''}
          onChange={e => set('min_score', e.target.value)}
        />
      </div>

      {/* Company */}
      <input
        className="input-field w-36"
        placeholder="Company…"
        aria-label="Filter by company"
        value={filters.company || ''}
        onChange={e => set('company', e.target.value)}
      />

      {/* Clear filter chip */}
      {hasActive && (
        <button
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-semibold transition-all duration-200"
          style={{
            background: 'rgba(248,113,113,0.1)',
            border: '1px solid rgba(248,113,113,0.25)',
            color: '#f87171',
          }}
          onMouseEnter={e => { e.currentTarget.style.background = 'rgba(248,113,113,0.18)'; e.currentTarget.style.boxShadow = '0 0 12px rgba(248,113,113,0.15)' }}
          onMouseLeave={e => { e.currentTarget.style.background = 'rgba(248,113,113,0.1)'; e.currentTarget.style.boxShadow = 'none' }}
          onClick={() => onChange({ q: '', status: '', sort: 'priority', min_score: '', company: '' })}
        >
          <X size={12} /> Clear
        </button>
      )}
    </div>
  )
}
