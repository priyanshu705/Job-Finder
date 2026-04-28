// src/components/Sidebar.jsx — UPGRADED: glassmorphism sidebar with glow active states
import { LayoutDashboard, ListOrdered, Target, Activity, BarChart2, Settings, Zap, ChevronLeft, ChevronRight } from 'lucide-react'

const NAV = [
  { id: 'dashboard', label: 'Dashboard',  icon: LayoutDashboard },
  { id: 'queue',     label: 'Queue',       icon: ListOrdered },
  { id: 'goals',     label: 'Goals',       icon: Target },
  { id: 'activity',  label: 'Activity',    icon: Activity },
  { id: 'analytics', label: 'Analytics',   icon: BarChart2 },
  { id: 'settings',  label: 'Settings',    icon: Settings },
]

export default function Sidebar({ page, setPage, open, setOpen }) {
  return (
    <aside
      className="flex-shrink-0 flex flex-col overflow-hidden relative"
      style={{
        width: open ? 224 : 68,
        transition: 'width 0.3s cubic-bezier(0.34,1.56,0.64,1)',
        background: 'linear-gradient(180deg, rgba(8,15,31,0.97) 0%, rgba(13,21,38,0.98) 100%)',
        borderRight: '1px solid rgba(99,102,241,0.12)',
        backdropFilter: 'blur(24px)',
        WebkitBackdropFilter: 'blur(24px)',
        boxShadow: '4px 0 32px rgba(0,0,0,0.4), inset -1px 0 0 rgba(255,255,255,0.04)',
      }}
    >
      {/* Ambient glow blob */}
      <div
        className="absolute pointer-events-none"
        style={{
          top: -60, left: -60, width: 200, height: 200,
          background: 'radial-gradient(circle, rgba(99,102,241,0.12) 0%, transparent 70%)',
          borderRadius: '50%',
        }}
      />

      {/* Logo header */}
      <div
        className="h-16 flex items-center px-3 flex-shrink-0 gap-3"
        style={{ borderBottom: '1px solid rgba(255,255,255,0.06)' }}
      >
        {/* Logo icon with animated glow */}
        <div
          className="flex-shrink-0 flex items-center justify-center rounded-xl"
          style={{
            width: 38, height: 38,
            background: 'linear-gradient(135deg, #6366f1 0%, #4f46e5 60%, #7c3aed 100%)',
            boxShadow: '0 0 20px rgba(99,102,241,0.5), 0 0 40px rgba(99,102,241,0.2), inset 0 1px 0 rgba(255,255,255,0.2)',
            animation: 'glowPulse 3s ease-in-out infinite',
          }}
        >
          <Zap size={18} className="text-white" style={{ filter: 'drop-shadow(0 0 4px rgba(255,255,255,0.5))' }} />
        </div>

        {open && (
          <div className="min-w-0 overflow-hidden" style={{ animation: 'fadeIn 0.25s ease-out' }}>
            <p
              className="text-sm font-bold truncate"
              style={{
                background: 'linear-gradient(135deg, #818cf8, #6366f1, #a78bfa)',
                WebkitBackgroundClip: 'text',
                WebkitTextFillColor: 'transparent',
                backgroundClip: 'text',
                letterSpacing: '-0.01em',
              }}
            >
              AutoApply AI
            </p>
            <p className="text-xs truncate" style={{ color: 'rgba(148,163,184,0.6)', fontSize: 10 }}>
              Smart Agent v3
            </p>
          </div>
        )}
      </div>

      {/* Navigation items */}
      <nav className="flex-1 px-2 py-4 space-y-1 overflow-hidden">
        {NAV.map(({ id, label, icon: Icon }, idx) => {
          const isActive = page === id
          return (
            <button
              key={id}
              onClick={() => setPage(id)}
              title={!open ? label : undefined}
              className={`nav-item w-full ${isActive ? 'active' : ''} ${!open ? 'justify-center' : ''}`}
              style={{
                animationDelay: `${idx * 0.04}s`,
                animation: 'fadeIn 0.35s ease-out both',
              }}
            >
              {/* Icon with glow when active */}
              <span
                className="flex-shrink-0 nav-icon"
                style={isActive ? { filter: 'drop-shadow(0 0 6px rgba(99,102,241,0.8))' } : {}}
              >
                <Icon size={18} />
              </span>

              {open && (
                <span className="truncate font-medium" style={{ fontSize: 13.5 }}>
                  {label}
                </span>
              )}

              {/* Active indicator bar (right edge) */}
              {isActive && open && (
                <span
                  className="ml-auto flex-shrink-0 rounded-full"
                  style={{
                    width: 3, height: 16,
                    background: 'linear-gradient(180deg, #818cf8, #6366f1)',
                    boxShadow: '0 0 8px rgba(99,102,241,0.8)',
                  }}
                />
              )}
            </button>
          )
        })}
      </nav>

      {/* Divider */}
      <div style={{ height: 1, background: 'rgba(255,255,255,0.05)', margin: '0 12px' }} />

      {/* Collapse toggle */}
      <button
        onClick={() => setOpen(o => !o)}
        className="m-2 flex items-center justify-center rounded-xl transition-all duration-200"
        style={{
          height: 36,
          background: 'rgba(255,255,255,0.03)',
          border: '1px solid rgba(255,255,255,0.07)',
          color: 'rgba(148,163,184,0.6)',
        }}
        onMouseEnter={e => {
          e.currentTarget.style.background = 'rgba(99,102,241,0.1)'
          e.currentTarget.style.borderColor = 'rgba(99,102,241,0.3)'
          e.currentTarget.style.color = '#818cf8'
        }}
        onMouseLeave={e => {
          e.currentTarget.style.background = 'rgba(255,255,255,0.03)'
          e.currentTarget.style.borderColor = 'rgba(255,255,255,0.07)'
          e.currentTarget.style.color = 'rgba(148,163,184,0.6)'
        }}
      >
        {open ? <ChevronLeft size={15} /> : <ChevronRight size={15} />}
      </button>
    </aside>
  )
}
