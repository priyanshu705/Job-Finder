import ActivityFeed from '../components/ActivityFeed.jsx'

export default function ActivityPage() {
  return (
    <div className="space-y-4 animate-fade-in max-w-2xl">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="section-title">Activity Feed</h2>
          <p className="section-sub">Live log of every agent action — auto-refreshing</p>
        </div>
        <div className="flex items-center gap-2 text-xs text-emerald-400">
          <span className="live-dot" /> Live
        </div>
      </div>
      <div className="card p-5">
        <ActivityFeed limit={100} />
      </div>
    </div>
  )
}
