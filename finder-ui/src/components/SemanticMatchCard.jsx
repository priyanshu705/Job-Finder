import { useState } from 'react'
import { Brain, CheckCircle, Target, ShieldAlert, Cpu } from 'lucide-react'
import InterviewPrepModal from './InterviewPrepModal.jsx'

export default function SemanticMatchCard({ jobId, score, explanation, isRemote, goalAlignment, aiReasoning }) {
  const [showPrep, setShowPrep] = useState(false)
  const reasons = (explanation || "").split("\n- ").filter(r => r.trim())
  
  return (
    <div
      className="p-4 rounded-xl"
      style={{
        background: 'linear-gradient(135deg, rgba(99,102,241,0.1) 0%, rgba(13,21,38,0.95) 100%)',
        border: '1px solid rgba(99,102,241,0.25)',
        boxShadow: '0 4px 20px rgba(99,102,241,0.15), inset 0 1px 0 rgba(255,255,255,0.05)',
      }}
    >
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-lg flex items-center justify-center bg-indigo-500/20 text-indigo-400 border border-indigo-500/30">
            <Brain size={16} />
          </div>
          <div>
            <p className="text-xs font-bold uppercase tracking-wider text-indigo-400">Semantic AI Match</p>
            <p className="text-[10px] text-slate-500">Powered by all-MiniLM-L6-v2</p>
          </div>
        </div>
        <div className="text-right">
          <p className="text-xl font-black text-indigo-300 drop-shadow-md">{score || 0}<span className="text-sm font-medium text-slate-500">%</span></p>
        </div>
      </div>

      <div className="space-y-2 mt-2">
        {reasons.map((r, i) => {
          let Icon = CheckCircle
          let color = "text-emerald-400"
          
          if (r.toLowerCase().includes("semantic")) {
            Icon = Cpu
            color = "text-indigo-400"
          } else if (r.toLowerCase().includes("goal")) {
            Icon = Target
            color = "text-amber-400"
          } else if (r.toLowerCase().includes("adaptive") || r.toLowerCase().includes("penalty")) {
            Icon = ShieldAlert
            color = "text-red-400"
          }

          const cleanText = r.replace(/^Matched because:\s*/i, "")

          return (
            <div key={i} className="flex items-start gap-2 text-xs text-slate-300 leading-relaxed bg-white/[0.02] p-2 rounded-lg border border-white/[0.04]">
              <Icon size={14} className={`${color} mt-0.5 flex-shrink-0`} />
              <span>{cleanText}</span>
            </div>
          )
        })}
      </div>
      
      {aiReasoning && (
        <div className="mt-4 p-3 bg-indigo-500/10 border border-indigo-500/30 rounded-xl relative overflow-hidden">
          <div className="absolute top-0 right-0 p-2 opacity-10">
              <Brain size={48} />
          </div>
          <p className="text-xs font-medium text-indigo-300 leading-relaxed relative z-10 italic">
            "{aiReasoning}"
          </p>
        </div>
      )}
      
      {jobId && (
        <button 
            onClick={() => setShowPrep(true)}
            className="w-full mt-4 py-2 flex items-center justify-center gap-2 rounded-lg bg-indigo-500/10 hover:bg-indigo-500/20 text-indigo-400 font-bold text-xs border border-indigo-500/30 transition-colors"
        >
            <Brain size={14} />
            Prep for Interview
        </button>
      )}
      
      {showPrep && <InterviewPrepModal jobId={jobId} onClose={() => setShowPrep(false)} />}
    </div>
  )
}
