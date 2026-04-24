export default function StatCard({ label, value, icon: Icon, color = 'blue', sub, trend, loading }) {
  const colors = {
    blue:   { bg: 'bg-blue-500/10',    border: 'border-blue-500/20',    icon: 'text-blue-400',    val: 'text-blue-400' },
    green:  { bg: 'bg-emerald-500/10', border: 'border-emerald-500/20', icon: 'text-emerald-400', val: 'text-emerald-400' },
    yellow: { bg: 'bg-amber-500/10',   border: 'border-amber-500/20',   icon: 'text-amber-400',   val: 'text-amber-400' },
    red:    { bg: 'bg-red-500/10',     border: 'border-red-500/20',     icon: 'text-red-400',     val: 'text-red-400' },
    orange: { bg: 'bg-orange-500/10',  border: 'border-orange-500/20',  icon: 'text-orange-400',  val: 'text-orange-400' },
    slate:  { bg: 'bg-slate-500/10',   border: 'border-slate-500/20',   icon: 'text-slate-400',   val: 'text-slate-300' },
    purple: { bg: 'bg-purple-500/10',  border: 'border-purple-500/20',  icon: 'text-purple-400',  val: 'text-purple-400' },
  }
  const c = colors[color] || colors.blue

  if (loading) return (
    <div className="card p-5 space-y-3">
      <div className="skeleton h-4 w-24" />
      <div className="skeleton h-8 w-16" />
      <div className="skeleton h-3 w-32" />
    </div>
  )

  return (
    <div className={`card-hover p-5 flex flex-col gap-3`}>
      <div className="flex items-start justify-between">
        <p className="text-sm font-medium text-slate-400">{label}</p>
        {Icon && (
          <div className={`p-2 rounded-xl ${c.bg} border ${c.border}`}>
            <Icon size={16} className={c.icon} />
          </div>
        )}
      </div>
      <div>
        <p className={`text-3xl font-bold ${c.val}`}>{value ?? '—'}</p>
        {sub && <p className="text-xs text-slate-500 mt-1">{sub}</p>}
      </div>
      {trend !== undefined && (
        <div className={`text-xs font-medium ${trend >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
          {trend >= 0 ? '↑' : '↓'} {Math.abs(trend)}% vs yesterday
        </div>
      )}
    </div>
  )
}
