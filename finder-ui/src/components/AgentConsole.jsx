import { RotateCcw, Play, CheckCircle, Clock, Target, Phone, X, Search, TrendingUp } from 'lucide-react'

export default function AgentConsole({ agent }) {
  if (!agent || !agent.running) return null

  return (
    <div className="mb-6 card overflow-hidden border-blue-500/30 bg-blue-500/[0.02] animate-in fade-in zoom-in duration-300">
       <div className="p-4 border-b border-slate-800 flex items-center justify-between">
          <div className="flex items-center gap-3">
             <div className="w-2 h-2 rounded-full bg-blue-500 animate-pulse" />
             <span className="text-xs font-bold uppercase tracking-widest text-blue-400">Agent Active</span>
          </div>
          <span className="text-[10px] text-slate-500 font-mono">{agent.phase}</span>
       </div>
       
       <div className="p-5 grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div className="space-y-4">
             <div>
                <p className="text-xs text-slate-500 uppercase font-bold tracking-wider mb-1">Current Task</p>
                <p className="text-lg font-bold text-white">{agent.progress}</p>
             </div>
             
             <div className="flex gap-3">
                {['scraper', 'matcher', 'queue', 'apply'].map((p) => {
                   const active = agent.phase === p
                   const done = ['done', 'scraper', 'matcher', 'queue', 'apply'].indexOf(agent.phase) > ['done', 'scraper', 'matcher', 'queue', 'apply'].indexOf(p)
                   return (
                      <div key={p} className="flex flex-col items-center gap-1">
                         <div className={`w-8 h-1 rounded-full transition-colors ${active ? 'bg-blue-500 shadow-glow' : done ? 'bg-emerald-500/50' : 'bg-slate-800'}`} />
                         <span className={`text-[8px] uppercase font-bold ${active ? 'text-blue-400' : 'text-slate-600'}`}>{p}</span>
                      </div>
                   )
                })}
             </div>
          </div>

          <div className="bg-slate-950/50 border border-slate-800 rounded-xl p-3 h-32 flex flex-col">
             <div className="flex items-center justify-between mb-2">
                <p className="text-[9px] uppercase font-bold text-slate-600 tracking-widest">Live Logs</p>
                <span className="text-[8px] text-slate-700 font-mono">STDOUT</span>
             </div>
             <div className="flex-1 overflow-y-auto font-mono text-[9px] space-y-1 custom-scrollbar">
                {(agent.logs || []).map((l, i) => (
                   <div key={i} className="flex gap-2 animate-in slide-in-from-left duration-300">
                      <span className="text-slate-600">[{l.time}]</span>
                      <span className="text-slate-300">{l.msg}</span>
                   </div>
                ))}
                {(!agent.logs || agent.logs.length === 0) && <p className="text-slate-700 italic">Initializing stream...</p>}
             </div>
          </div>
       </div>
    </div>
  )
}
