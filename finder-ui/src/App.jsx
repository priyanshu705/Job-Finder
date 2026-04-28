// src/App.jsx — AutoApply AI root component
import { useState, useEffect, useCallback, useRef } from 'react'
import toast from 'react-hot-toast'
import { api } from './api.js'
import Sidebar from './components/Sidebar.jsx'
import Navbar  from './components/Navbar.jsx'
import DashboardPage  from './pages/DashboardPage.jsx'
import QueuePage      from './pages/QueuePage.jsx'
import GoalsPage      from './pages/GoalsPage.jsx'
import ActivityPage   from './pages/ActivityPage.jsx'
import AnalyticsPage  from './pages/AnalyticsPage.jsx'
import SettingsPage   from './pages/SettingsPage.jsx'
import AgentConsole  from './components/AgentConsole.jsx'
import OfflineBanner from './components/OfflineBanner.jsx'

const POLL_MS = 4000

export default function App() {
  const [page, setPage]           = useState('dashboard')
  const [status, setStatus]       = useState(null)
  const [summary, setSummary]     = useState(null)
  const [loading, setLoading]     = useState(true)
  const [running, setRunning]     = useState(false)
  const [agentStatus, setAgentStatus] = useState(null)
  const [lastUpdated, setLastUpdated] = useState(null)
  const [sidebarOpen, setSidebarOpen] = useState(true)
  const [pageKey, setPageKey]     = useState(0)
  const [isOffline, setIsOffline] = useState(false)
  const timerRef = useRef(null)
  const isFetchingRef = useRef(false)
  const isMountedRef = useRef(true)
  const isCyclingRef = useRef(false)

  const fetchStatus = useCallback(async () => {
    if (isFetchingRef.current) return  // prevent concurrent duplicate calls
    isFetchingRef.current = true
    try {
      const [s, sum, agent] = await Promise.all([
        api.status(),
        api.statsSummary(),
        api.agentStatus()
      ])
      if (!isMountedRef.current) return  // component unmounted, skip state update
      setStatus(s)
      setSummary(sum)
      setAgentStatus(agent)
      if (agent) setRunning(!!agent.running)
      setLastUpdated(new Date())
      setIsOffline(false)  // ← back online
    } catch (e) {
      if (isMountedRef.current) setIsOffline(true)  // ← mark offline
    } finally {
      isFetchingRef.current = false
      if (isMountedRef.current) setLoading(false)
    }
  }, [])

  useEffect(() => {
    isMountedRef.current = true
    fetchStatus()
    timerRef.current = setInterval(fetchStatus, POLL_MS)
    return () => {
      isMountedRef.current = false
      clearInterval(timerRef.current)
    }
  }, [fetchStatus])

  // Re-trigger page enter animation on nav change
  const handleSetPage = (p) => {
    setPage(p)
    setPageKey(k => k + 1)
  }

  const handleCycle = async () => {
    if (running || isCyclingRef.current) return
    isCyclingRef.current = true
    toast.loading('Initiating full cycle…', { id: 'cycle' })
    try {
      await api.runCycle()
      toast.success('Cycle started! Agent is running.', { id: 'cycle' })
      fetchStatus()
    } catch (e) {
      if (e.isTimeout) {
        toast.error('Server is waking up — please wait 30 s and try again', { id: 'cycle', duration: 6000 })
      } else if (e.isNetwork) {
        toast.error('Backend unavailable — check connection', { id: 'cycle' })
      } else {
        toast.error(e.message || 'Failed to start cycle', { id: 'cycle' })
      }
    } finally {
      isCyclingRef.current = false
    }
  }

  const handlePause = async () => {
    try {
      await api.pause()
      toast.success('Agent paused')
      fetchStatus()
    } catch (e) { toast.error(e.message) }
  }

  const handleResume = async () => {
    try {
      await api.resume()
      toast.success('Agent resumed')
      fetchStatus()
    } catch (e) { toast.error(e.message) }
  }

  const isPaused = status?.paused === true || status?.paused === 'true'
  const sharedProps = { status, summary, loading, fetchStatus, agentStatus }

  return (
    <div className="flex h-screen overflow-hidden dark" style={{ background: 'var(--bg-base)' }}>
      {/* Animated ambient background blobs — fixed behind everything */}
      <div className="fixed inset-0 pointer-events-none overflow-hidden" style={{ zIndex: 0 }}>
        <div style={{
          position: 'absolute', top: '-20%', left: '-10%',
          width: '60%', height: '60%',
          background: 'radial-gradient(ellipse, rgba(99,102,241,0.06) 0%, transparent 70%)',
          animation: 'float 12s ease-in-out infinite',
        }} />
        <div style={{
          position: 'absolute', bottom: '-15%', right: '-5%',
          width: '50%', height: '50%',
          background: 'radial-gradient(ellipse, rgba(168,85,247,0.05) 0%, transparent 70%)',
          animation: 'float 15s ease-in-out infinite reverse',
        }} />
        <div style={{
          position: 'absolute', top: '40%', left: '30%',
          width: '40%', height: '40%',
          background: 'radial-gradient(ellipse, rgba(34,211,238,0.03) 0%, transparent 70%)',
          animation: 'float 18s ease-in-out infinite',
        }} />
      </div>

      {/* Sidebar */}
      <div style={{ position: 'relative', zIndex: 50 }}>
        <Sidebar page={page} setPage={handleSetPage} open={sidebarOpen} setOpen={setSidebarOpen} />
      </div>

      {/* Main content area */}
      <div className="flex-1 flex flex-col overflow-hidden min-w-0" style={{ position: 'relative', zIndex: 10 }}>
        <Navbar
          page={page}
          running={running}
          isPaused={isPaused}
          lastUpdated={lastUpdated}
          onCycle={handleCycle}
          onPause={handlePause}
          onResume={handleResume}
          onRefresh={fetchStatus}
          onMenuToggle={() => setSidebarOpen(o => !o)}
        />
        {isOffline && <OfflineBanner onRetry={fetchStatus} />}

        <main
          className="flex-1 overflow-y-auto p-6"
          style={{ background: 'transparent' }}
        >
          {/* Page wrapper — re-animates on nav */}
          <div
            key={pageKey}
            style={{ animation: 'fadeIn 0.35s ease-out both' }}
          >
            <AgentConsole agent={agentStatus} />
            {page === 'dashboard'  && <DashboardPage  {...sharedProps} onCycle={handleCycle} running={running} />}
            {page === 'queue'      && <QueuePage      {...sharedProps} />}
            {page === 'goals'      && <GoalsPage      {...sharedProps} />}
            {page === 'activity'   && <ActivityPage   {...sharedProps} />}
            {page === 'analytics'  && <AnalyticsPage  {...sharedProps} />}
            {page === 'settings'   && <SettingsPage   {...sharedProps} />}
          </div>
        </main>
      </div>
    </div>
  )
}
