import { Search, X, SlidersHorizontal } from 'lucide-react'

const STATUSES = ['', 'pending', 'applied', 'failed', 'uncertain', 'skip', 'external_skip']
const SORTS    = [
  { value: 'priority',    label: 'Priority ↓' },
  { value: 'score_desc',  label: 'Score ↓' },
  { value: 'score_asc',   label: 'Score ↑' },
  { value: 'newest',      label: 'Newest' },
  { value: 'oldest',      label: 'Oldest' },
]

export default function FiltersBar({ filters, onChange }) {
  const set = (k, v) => onChange({ ...filters, [k]: v })
  const hasActive = filters.q || filters.status || filters.sort !== 'priority' || filters.min_score || filters.company

  return (
    <div className="card p-3 flex flex-wrap gap-2 items-center">
      <SlidersHorizontal size={15} className="text-slate-500 flex-shrink-0" />

      {/* Search */}
      <div className="relative flex-1 min-w-48">
        <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
        <input
          className="input-field pl-8"
          placeholder="Search by role, company, keyword…"
          value={filters.q || ''}
          onChange={e => set('q', e.target.value)}
        />
      </div>

      {/* Status filter */}
      <select className="select-field w-36" value={filters.status || ''} onChange={e => set('status', e.target.value)}>
        <option value="">All statuses</option>
        {STATUSES.filter(Boolean).map(s => (
          <option key={s} value={s}>{s.replace('_', ' ')}</option>
        ))}
      </select>

      {/* Sort */}
      <select className="select-field w-36" value={filters.sort || 'priority'} onChange={e => set('sort', e.target.value)}>
        {SORTS.map(s => <option key={s.value} value={s.value}>{s.label}</option>)}
      </select>

      {/* Min score */}
      <div className="flex items-center gap-2">
        <label className="text-xs text-slate-500 whitespace-nowrap">Min score</label>
        <input
          type="number" min="0" max="100"
          className="input-field w-20"
          placeholder="0"
          value={filters.min_score || ''}
          onChange={e => set('min_score', e.target.value)}
        />
      </div>

      {/* Company */}
      <input
        className="input-field w-36"
        placeholder="Company…"
        value={filters.company || ''}
        onChange={e => set('company', e.target.value)}
      />

      {/* Clear */}
      {hasActive && (
        <button
          className="btn-secondary px-3 py-2"
          onClick={() => onChange({ q: '', status: '', sort: 'priority', min_score: '', company: '' })}
        >
          <X size={14} /> Clear
        </button>
      )}
    </div>
  )
}
