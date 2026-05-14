// src/components/PreferenceInsights.jsx — Phase C Intelligence UI
import { useEffect, useState } from 'react'
import { BrainCircuit, TrendingUp, TrendingDown, RefreshCcw } from 'lucide-react'
import { api } from '../api.js'

export default function PreferenceInsights() {
  // In a full implementation, this would fetch from a new endpoint: /api/intelligence/insights
  // For now, we mock the insights structure based on the adaptive_memory architecture.
  
  const [insights, setInsights] = useState([
    { type: 'penalty', label: 'HR Roles', reason: 'Consistently rejected in the past 7 days', impact: '-15%' },
    { type: 'boost', label: 'Backend Development', reason: 'High approval rate & explicit goal', impact: '+25%' },
    { type: 'boost', label: 'Remote', reason: 'Matches preferred work style', impact: '+10%' }
  ])

  return (
    <div
      className="p-5 rounded-2xl"
      style={{
        background: 'linear-gradient(135deg, rgba(13,21,38,0.92) 0%, rgba(8,15,31,0.96) 100%)',
        border: '1px solid rgba(255,255,255,0.07)',
        boxShadow: '0 4px 24px rgba(0,0,0,0.4), inset 0 1px 0 rgba(255,255,255,0.04)',
      }}
    >
      <div className="flex items-center justify-between mb-4">
        <p className="text-sm font-semibold text-slate-200 flex items-center gap-2">
          <BrainCircuit size={16} className="text-purple-400" /> Adaptive Memory Insights
        </p>
        <button className="text-slate-500 hover:text-slate-300 transition-colors">
          <RefreshCcw size={14} />
        </button>
      </div>

      <div className="space-y-3">
        {insights.map((insight, idx) => (
          <div key={idx} className="flex items-center justify-between p-3 rounded-xl bg-white/[0.02] border border-white/[0.03]">
            <div>
              <p className="text-xs font-bold text-slate-300">{insight.label}</p>
              <p className="text-[10px] text-slate-500 mt-0.5">{insight.reason}</p>
            </div>
            <div className={`flex items-center gap-1 text-xs font-bold ${insight.type === 'boost' ? 'text-emerald-400' : 'text-red-400'}`}>
              {insight.type === 'boost' ? <TrendingUp size={14} /> : <TrendingDown size={14} />}
              {insight.impact}
            </div>
          </div>
        ))}
        
        {insights.length === 0 && (
          <p className="text-xs text-slate-500 italic text-center py-4">
            The AI is learning your preferences. Review more jobs to generate insights.
          </p>
        )}
      </div>
    </div>
  )
}
