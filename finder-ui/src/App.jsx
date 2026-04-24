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
  const timerRef = useRef(null)

  const fetchStatus = useCallback(async () => {
    try {
      const [s, sum, agent] = await Promise.all([
        api.status(), 
        api.statsSummary(),
        api.agentStatus()
      ])
      setStatus(s)
      setSummary(sum)
      setAgentStatus(agent)
      setRunning(agent.running)
      setLastUpdated(new Date())
    } catch (e) {
      // silent background poll failure
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchStatus()
    timerRef.current = setInterval(fetchStatus, POLL_MS)
    return () => clearInterval(timerRef.current)
  }, [fetchStatus])

  const handleCycle = async () => {
    if (running) return
    toast.loading('Initiating full cycle...', { id: 'cycle' })
    try {
      await api.runCycle()
      toast.success('Cycle initiated!', { id: 'cycle' })
      fetchStatus()
    } catch (e) {
      toast.error(e.message, { id: 'cycle' })
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
    <div className="flex h-screen overflow-hidden dark">
      <Sidebar page={page} setPage={setPage} open={sidebarOpen} setOpen={setSidebarOpen} />
      <div className="flex-1 flex flex-col overflow-hidden min-w-0">
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
        <main className="flex-1 overflow-y-auto bg-navy-950 p-6">
          <AgentConsole agent={agentStatus} />
          {page === 'dashboard'  && <DashboardPage  {...sharedProps} onCycle={handleCycle} running={running} />}
          {page === 'queue'      && <QueuePage      {...sharedProps} />}
          {page === 'goals'      && <GoalsPage      {...sharedProps} />}
          {page === 'activity'   && <ActivityPage   {...sharedProps} />}
          {page === 'analytics'  && <AnalyticsPage  {...sharedProps} />}
          {page === 'settings'   && <SettingsPage   {...sharedProps} />}
        </main>
      </div>
    </div>
  )
}
