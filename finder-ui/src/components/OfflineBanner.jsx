// src/components/OfflineBanner.jsx
// Shows when backend API is unreachable — with Render cold-start awareness
import { memo, useState, useEffect } from 'react'
import { WifiOff, RefreshCw, Coffee } from 'lucide-react'

const OfflineBanner = memo(function OfflineBanner({ onRetry }) {
  const [seconds, setSeconds] = useState(0)

  // Track how long we've been offline so we can show a cold-start hint
  useEffect(() => {
    setSeconds(0)
    const t = setInterval(() => setSeconds(s => s + 1), 1000)
    return () => clearInterval(t)
  }, [])

  // After 5 s offline → likely a Render cold start (free tier sleeps)
  const isColdStart = seconds >= 5

  return (
    <div
      className="flex items-center justify-between px-4 py-2.5 gap-3"
      style={{
        background: isColdStart
          ? 'linear-gradient(90deg, rgba(251,191,36,0.1) 0%, rgba(13,21,38,0.95) 100%)'
          : 'linear-gradient(90deg, rgba(248,113,113,0.12) 0%, rgba(13,21,38,0.95) 100%)',
        borderBottom: `1px solid ${isColdStart ? 'rgba(251,191,36,0.25)' : 'rgba(248,113,113,0.2)'}`,
        animation: 'fadeIn 0.3s ease-out both',
        transition: 'background 0.6s, border-color 0.6s',
      }}
      role="alert"
      aria-live="polite"
    >
      <div className="flex items-center gap-2.5">
        {isColdStart
          ? <Coffee size={14} className="flex-shrink-0" style={{ color: '#fbbf24' }} />
          : <WifiOff  size={14} className="flex-shrink-0" style={{ color: '#f87171' }} />
        }
        <span style={{ fontSize: 12, fontWeight: 500, color: isColdStart ? '#fde68a' : '#fca5a5' }}>
          {isColdStart
            ? 'Server is waking up (cold start) — this takes ~30 s on the free tier'
            : 'Backend offline — showing last known data'
          }
        </span>
      </div>
      <button
        onClick={onRetry}
        aria-label="Retry connection"
        className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs font-semibold transition-all"
        style={{
          background: isColdStart ? 'rgba(251,191,36,0.1)' : 'rgba(248,113,113,0.1)',
          border: `1px solid ${isColdStart ? 'rgba(251,191,36,0.3)' : 'rgba(248,113,113,0.25)'}`,
          color: isColdStart ? '#fbbf24' : '#f87171',
        }}
        onMouseEnter={e => {
          e.currentTarget.style.background = isColdStart ? 'rgba(251,191,36,0.2)' : 'rgba(248,113,113,0.2)'
        }}
        onMouseLeave={e => {
          e.currentTarget.style.background = isColdStart ? 'rgba(251,191,36,0.1)' : 'rgba(248,113,113,0.1)'
        }}
      >
        <RefreshCw size={11} />
        {seconds > 0 ? `Retry (${seconds}s)` : 'Retry'}
      </button>
    </div>
  )
})

export default OfflineBanner
