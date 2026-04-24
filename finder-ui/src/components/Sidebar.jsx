import { LayoutDashboard, ListOrdered, Target, Activity, BarChart2, Settings, Zap, ChevronLeft, ChevronRight } from 'lucide-react'

const NAV = [
  { id: 'dashboard', label: 'Dashboard',  icon: LayoutDashboard },
  { id: 'queue',     label: 'Queue',      icon: ListOrdered },
  { id: 'goals',     label: 'Goals',      icon: Target },
  { id: 'activity',  label: 'Activity',   icon: Activity },
  { id: 'analytics', label: 'Analytics',  icon: BarChart2 },
  { id: 'settings',  label: 'Settings',   icon: Settings },
]

export default function Sidebar({ page, setPage, open, setOpen }) {
  return (
    <aside className={`${open ? 'w-56' : 'w-16'} flex-shrink-0 bg-navy-900 border-r border-slate-700/50 flex flex-col transition-all duration-200 overflow-hidden`}>
      {/* Logo */}
      <div className="h-16 flex items-center px-4 border-b border-slate-700/50 gap-3 flex-shrink-0">
        <div className="w-8 h-8 rounded-xl bg-gradient-to-br from-blue-500 to-cyan-500 flex items-center justify-center flex-shrink-0 shadow-glow">
          <Zap size={16} className="text-white" />
        </div>
        {open && (
          <div className="min-w-0">
            <p className="text-sm font-bold text-gradient truncate">Finder AI</p>
            <p className="text-xs text-slate-500">V6 Agent</p>
          </div>
        )}
      </div>

      {/* Nav items */}
      <nav className="flex-1 px-2 py-4 space-y-1">
        {NAV.map(({ id, label, icon: Icon }) => (
          <button
            key={id}
            onClick={() => setPage(id)}
            className={`nav-item w-full ${page === id ? 'active' : ''} ${!open ? 'justify-center' : ''}`}
            title={!open ? label : undefined}
          >
            <Icon size={18} className="flex-shrink-0" />
            {open && <span className="truncate">{label}</span>}
          </button>
        ))}
      </nav>

      {/* Collapse toggle */}
      <button
        onClick={() => setOpen(o => !o)}
        className="m-2 p-2 rounded-xl text-slate-500 hover:text-slate-300 hover:bg-white/5 transition-all duration-150 flex items-center justify-center"
      >
        {open ? <ChevronLeft size={16} /> : <ChevronRight size={16} />}
      </button>
    </aside>
  )
}
