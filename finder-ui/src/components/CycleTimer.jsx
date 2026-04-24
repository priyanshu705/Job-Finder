// src/components/CycleTimer.jsx
// Live stopwatch that shows current cycle phase and elapsed time
import React, { useState, useEffect, useRef } from 'react'
import { api } from '../api'

function fmt(sec) {
  const m = Math.floor(sec / 60)
  const s = Math.floor(sec % 60)
  return `${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`
}

const PHASES = [
  { key: 'scraper', label: 'Scraping Jobs',   icon: '🕷️', max: 300 },
  { key: 'matcher', label: 'Scoring Jobs',     icon: '🎯', max: 60  },
  { key: 'queue',   label: 'Ranking Queue',    icon: '📊', max: 30  },
  { key: 'apply',   label: 'Applying',         icon: '✉️', max: 120 },
]

export default function CycleTimer({ isRunning, onComplete }) {
  const [elapsed, setElapsed]   = useState(0)
  const [phase,   setPhase]     = useState(0)
  const intervalRef = useRef(null)
  const startRef    = useRef(null)

  // Poll action status to detect phase changes
  useEffect(() => {
    if (!isRunning) {
      setElapsed(0)
      setPhase(0)
      if (intervalRef.current) clearInterval(intervalRef.current)
      return
    }

    startRef.current = Date.now()
    setElapsed(0)
    setPhase(0)

    intervalRef.current = setInterval(() => {
      const secs = (Date.now() - startRef.current) / 1000
      setElapsed(secs)
      // Estimate phase from elapsed time
      if      (secs < 300) setPhase(0)  // 0-5min  → scraping
      else if (secs < 360) setPhase(1)  // 5-6min  → matching
      else if (secs < 390) setPhase(2)  // 6-6.5m  → ranking
      else                 setPhase(3)  // 6.5min+ → applying
    }, 500)

    return () => clearInterval(intervalRef.current)
  }, [isRunning])

  if (!isRunning) return null

  const totalBudget = 420 // 7 min total estimate
  const pct = Math.min((elapsed / totalBudget) * 100, 100)
  const currentPhase = PHASES[phase] || PHASES[0]

  return (
    <div style={{
      background:  'var(--bg-card)',
      border:      '1px solid var(--accent)',
      borderRadius:'var(--radius-lg)',
      padding:     '18px 22px',
      boxShadow:   'var(--shadow-glow)',
    }}>
      {/* Header */}
      <div style={{ display:'flex', justifyContent:'space-between', alignItems:'center', marginBottom:14 }}>
        <div style={{ display:'flex', alignItems:'center', gap:10 }}>
          <div style={{ width:8, height:8, borderRadius:'50%', background:'var(--green)', animation:'pulse 1s infinite' }} />
          <span style={{ fontWeight:700, fontSize:14, color:'var(--text-primary)' }}>Cycle Running</span>
        </div>
        <div style={{
          fontFamily:'JetBrains Mono, monospace',
          fontSize:24,
          fontWeight:800,
          color:'var(--accent-light)',
          letterSpacing:2,
        }}>
          {fmt(elapsed)}
        </div>
      </div>

      {/* Progress bar */}
      <div style={{ background:'rgba(255,255,255,0.06)', borderRadius:20, height:8, overflow:'hidden', marginBottom:14 }}>
        <div style={{
          height:'100%', borderRadius:20,
          background:'linear-gradient(90deg, var(--accent), var(--purple))',
          width:`${pct}%`,
          transition:'width 0.5s ease',
          boxShadow:'0 0 10px var(--accent-glow)',
        }} />
      </div>

      {/* Phases */}
      <div style={{ display:'flex', gap:6 }}>
        {PHASES.map((p, i) => (
          <div key={p.key} style={{
            flex:1,
            padding:'8px 6px',
            borderRadius:6,
            textAlign:'center',
            background: i === phase ? 'var(--accent-dim)' : i < phase ? 'var(--green-dim)' : 'var(--bg-glass)',
            border: `1px solid ${i === phase ? 'var(--accent)' : i < phase ? 'var(--green)' : 'var(--border)'}`,
            transition:'all 0.3s',
          }}>
            <div style={{ fontSize:16 }}>{i < phase ? '✅' : p.icon}</div>
            <div style={{
              fontSize:10, fontWeight:600, marginTop:3,
              color: i === phase ? 'var(--accent-light)' : i < phase ? 'var(--green)' : 'var(--text-muted)',
              letterSpacing:'0.3px',
            }}>
              {p.label}
            </div>
          </div>
        ))}
      </div>

      {/* Current phase label */}
      <div style={{ marginTop:12, fontSize:12, color:'var(--text-secondary)', textAlign:'center' }}>
        {currentPhase.icon} <strong>{currentPhase.label}</strong>
        <span style={{ color:'var(--text-muted)', marginLeft:6 }}>· auto-stops at 5 min scrape budget</span>
      </div>
    </div>
  )
}
