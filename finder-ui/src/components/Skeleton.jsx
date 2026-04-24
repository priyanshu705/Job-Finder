// src/components/Skeleton.jsx — Loading skeleton components (no blank UI)
import React from 'react'

function SkeletonBox({ w = '100%', h = 16, radius = 6, mb = 0 }) {
  return (
    <div style={{
      width: w, height: h, borderRadius: radius,
      background: 'linear-gradient(90deg, var(--bg-glass) 25%, rgba(255,255,255,0.08) 50%, var(--bg-glass) 75%)',
      backgroundSize: '200% 100%',
      animation: 'shimmer 1.5s infinite',
      marginBottom: mb,
      flexShrink: 0,
    }} />
  )
}

export function SkeletonStat() {
  return (
    <div className="stat-card" style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
      <SkeletonBox w="60%" h={10} />
      <SkeletonBox w="40%" h={32} />
      <SkeletonBox w="50%" h={10} />
    </div>
  )
}

export function SkeletonTable({ rows = 5 }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 8, padding: '8px 0' }}>
      {/* Header */}
      <div style={{ display: 'flex', gap: 12, padding: '0 14px', marginBottom: 4 }}>
        {[60, 120, 160, 100, 80].map((w, i) => (
          <SkeletonBox key={i} w={w} h={10} />
        ))}
      </div>
      {Array.from({ length: rows }, (_, i) => (
        <div key={i} style={{ display: 'flex', gap: 12, padding: '8px 14px', borderBottom: '1px solid var(--border)' }}>
          {[60, 120, 160, 100, 80].map((w, j) => (
            <SkeletonBox key={j} w={w} h={13} />
          ))}
        </div>
      ))}
    </div>
  )
}

export function SkeletonCard() {
  return (
    <div className="card" style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
      <SkeletonBox w="40%" h={12} />
      <SkeletonBox h={70} radius={8} />
      <SkeletonBox w="60%" h={10} />
    </div>
  )
}

// Global shimmer keyframes (injected once)
const style = document.createElement('style')
style.textContent = `
@keyframes shimmer {
  0%   { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}
`
document.head.appendChild(style)
