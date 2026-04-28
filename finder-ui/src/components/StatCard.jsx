import { memo } from 'react'

const StatCard = memo(function StatCard({ label, value, icon: Icon, color = 'blue', sub, trend, loading }) {
  // Premium color configurations with glow variants
  const colors = {
    blue:   {
      gradient: 'linear-gradient(135deg, rgba(99,102,241,0.18) 0%, rgba(79,79,241,0.06) 100%)',
      border:   'rgba(99,102,241,0.3)',
      glow:     'rgba(99,102,241,0.2)',
      iconBg:   'rgba(99,102,241,0.15)',
      iconBorder:'rgba(99,102,241,0.25)',
      iconColor: '#818cf8',
      val:      '#818cf8',
      valGlow:  'rgba(129,140,248,0.5)',
    },
    green:  {
      gradient: 'linear-gradient(135deg, rgba(52,211,153,0.12) 0%, rgba(16,185,129,0.04) 100%)',
      border:   'rgba(52,211,153,0.25)',
      glow:     'rgba(52,211,153,0.15)',
      iconBg:   'rgba(52,211,153,0.12)',
      iconBorder:'rgba(52,211,153,0.2)',
      iconColor: '#34d399',
      val:      '#34d399',
      valGlow:  'rgba(52,211,153,0.5)',
    },
    yellow: {
      gradient: 'linear-gradient(135deg, rgba(251,191,36,0.12) 0%, rgba(245,158,11,0.04) 100%)',
      border:   'rgba(251,191,36,0.25)',
      glow:     'rgba(251,191,36,0.12)',
      iconBg:   'rgba(251,191,36,0.12)',
      iconBorder:'rgba(251,191,36,0.2)',
      iconColor: '#fbbf24',
      val:      '#fbbf24',
      valGlow:  'rgba(251,191,36,0.5)',
    },
    red:    {
      gradient: 'linear-gradient(135deg, rgba(248,113,113,0.12) 0%, rgba(239,68,68,0.04) 100%)',
      border:   'rgba(248,113,113,0.25)',
      glow:     'rgba(248,113,113,0.12)',
      iconBg:   'rgba(248,113,113,0.12)',
      iconBorder:'rgba(248,113,113,0.2)',
      iconColor: '#f87171',
      val:      '#f87171',
      valGlow:  'rgba(248,113,113,0.5)',
    },
    orange: {
      gradient: 'linear-gradient(135deg, rgba(251,146,60,0.12) 0%, rgba(249,115,22,0.04) 100%)',
      border:   'rgba(251,146,60,0.25)',
      glow:     'rgba(251,146,60,0.12)',
      iconBg:   'rgba(251,146,60,0.12)',
      iconBorder:'rgba(251,146,60,0.2)',
      iconColor: '#fb923c',
      val:      '#fb923c',
      valGlow:  'rgba(251,146,60,0.5)',
    },
    slate:  {
      gradient: 'linear-gradient(135deg, rgba(148,163,184,0.08) 0%, rgba(100,116,139,0.03) 100%)',
      border:   'rgba(148,163,184,0.2)',
      glow:     'rgba(148,163,184,0.08)',
      iconBg:   'rgba(148,163,184,0.08)',
      iconBorder:'rgba(148,163,184,0.15)',
      iconColor: '#94a3b8',
      val:      '#cbd5e1',
      valGlow:  'rgba(148,163,184,0.3)',
    },
    purple: {
      gradient: 'linear-gradient(135deg, rgba(168,85,247,0.15) 0%, rgba(139,92,246,0.05) 100%)',
      border:   'rgba(168,85,247,0.3)',
      glow:     'rgba(168,85,247,0.15)',
      iconBg:   'rgba(168,85,247,0.12)',
      iconBorder:'rgba(168,85,247,0.25)',
      iconColor: '#c084fc',
      val:      '#c084fc',
      valGlow:  'rgba(192,132,252,0.5)',
    },
    cyan: {
      gradient: 'linear-gradient(135deg, rgba(34,211,238,0.12) 0%, rgba(6,182,212,0.04) 100%)',
      border:   'rgba(34,211,238,0.25)',
      glow:     'rgba(34,211,238,0.12)',
      iconBg:   'rgba(34,211,238,0.1)',
      iconBorder:'rgba(34,211,238,0.2)',
      iconColor: '#22d3ee',
      val:      '#22d3ee',
      valGlow:  'rgba(34,211,238,0.5)',
    },
  }

  const c = colors[color] || colors.blue

  /* ── Loading skeleton ── */
  if (loading) return (
    <div
      className="p-5 rounded-2xl flex flex-col gap-3"
      style={{ background: 'rgba(13,21,38,0.8)', border: '1px solid rgba(255,255,255,0.06)' }}
    >
      <div className="skeleton h-3.5 w-24 rounded-lg" />
      <div className="skeleton h-9 w-16 rounded-lg" />
      <div className="skeleton h-2.5 w-28 rounded-lg" />
    </div>
  )

  return (
    <div
      className="p-5 rounded-2xl flex flex-col gap-3 relative overflow-hidden"
      style={{
        background: `linear-gradient(135deg, rgba(13,21,38,0.92) 0%, rgba(8,15,31,0.96) 100%)`,
        border: `1px solid ${c.border}`,
        boxShadow: `0 4px 24px rgba(0,0,0,0.4), 0 0 0 0 ${c.glow}, inset 0 1px 0 rgba(255,255,255,0.05)`,
        transition: 'transform 0.25s ease, box-shadow 0.25s ease, border-color 0.25s ease',
        cursor: 'default',
      }}
      onMouseEnter={e => {
        const el = e.currentTarget
        el.style.transform = 'translateY(-5px) scale(1.02)'
        el.style.boxShadow = `0 16px 48px rgba(0,0,0,0.55), 0 0 24px ${c.glow}, inset 0 1px 0 rgba(255,255,255,0.08)`
        el.style.borderColor = c.border.replace('0.3', '0.55').replace('0.25', '0.5')
      }}
      onMouseLeave={e => {
        const el = e.currentTarget
        el.style.transform = 'translateY(0) scale(1)'
        el.style.boxShadow = `0 4px 24px rgba(0,0,0,0.4), 0 0 0 0 ${c.glow}, inset 0 1px 0 rgba(255,255,255,0.05)`
        el.style.borderColor = c.border
      }}
    >
      {/* Accent gradient overlay */}
      <div
        className="absolute inset-0 pointer-events-none rounded-2xl"
        style={{ background: c.gradient, opacity: 0.8 }}
      />

      {/* Top shine */}
      <div
        className="absolute inset-x-0 top-0 h-px pointer-events-none rounded-t-2xl"
        style={{ background: `linear-gradient(90deg, transparent, ${c.iconColor}40, transparent)` }}
      />

      {/* Fix 2 — label: lowercase, lighter weight, no uppercase */}
      <div className="flex items-start justify-between relative">
        <p style={{ fontSize: 11, fontWeight: 500, color: 'rgba(148,163,184,0.6)', letterSpacing: '0.01em' }}>
          {label}
        </p>
        {Icon && (
          <div
            className="flex items-center justify-center rounded-xl"
            style={{
              width: 34, height: 34,
              background: c.iconBg,
              border: `1px solid ${c.iconBorder}`,
              boxShadow: `0 0 12px ${c.glow}`,
              color: c.iconColor,
            }}
          >
            <Icon size={15} />
          </div>
        )}
      </div>

      {/* Fix 2 — label: lowercase, softer; value: larger, tighter tracking */}
      <div className="relative">
        <p
          style={{
            fontSize: 34,
            fontWeight: 800,
            lineHeight: 1,
            color: c.val,
            textShadow: `0 0 20px ${c.valGlow}`,
            letterSpacing: '-0.03em',
          }}
        >
          {value ?? '—'}
        </p>
        {sub && (
          <p className="text-xs mt-1.5" style={{ color: 'rgba(100,116,139,0.8)' }}>
            {sub}
          </p>
        )}
      </div>

      {/* Trend indicator */}
      {trend !== undefined && (
        <div
          className="flex items-center gap-1 text-xs font-semibold relative"
          style={{ color: trend >= 0 ? '#34d399' : '#f87171' }}
        >
          <span style={{ fontSize: 14 }}>{trend >= 0 ? '↑' : '↓'}</span>
          {Math.abs(trend)}% vs yesterday
        </div>
      )}
    </div>
  )
})

export default StatCard
