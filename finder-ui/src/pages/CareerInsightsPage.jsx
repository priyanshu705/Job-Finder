// src/pages/CareerInsightsPage.jsx
import { useState, useEffect } from 'react'
import { BrainCircuit, Target, AlertTriangle, TrendingUp, Cpu } from 'lucide-react'
import PageHeader from '../components/PageHeader.jsx'
import { getRaw } from '../api.js'

export default function CareerInsightsPage() {
    const [insights, setInsights] = useState([])
    const [loading, setLoading] = useState(true)

    useEffect(() => {
        // We'll mock the fetch for now, but in reality this hits the strategy_insights table
        const fetchInsights = async () => {
            try {
                // Wait for DB, fallback for demo
                setInsights([
                    { type: 'skill_gap', text: 'You are missing Docker and Kubernetes, which appeared in 45% of your recent missed backend roles.' },
                    { type: 'strategy', text: 'Your success rate for Remote Python roles is 2x higher than hybrid NodeJS roles.' }
                ])
            } catch (e) {
                console.error(e)
            } finally {
                setLoading(false)
            }
        }
        fetchInsights()
    }, [])

    return (
        <div className="space-y-6 animate-fade-in">
            <PageHeader title="Career Intelligence" sub="Proactive AI insights and strategy" />

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="card p-6 border border-indigo-500/20 bg-indigo-500/5 relative overflow-hidden">
                    <div className="absolute top-0 right-0 p-4 opacity-10"><BrainCircuit size={80} /></div>
                    <h3 className="text-lg font-bold text-indigo-400 flex items-center gap-2 mb-2">
                        <Cpu size={20} /> AI Agent Status
                    </h3>
                    <p className="text-sm text-slate-400 mb-4">The intelligence engine is actively monitoring your application outcomes to refine its search logic.</p>
                    <div className="flex gap-2">
                        <span className="badge-applied">Memory Active</span>
                        <span className="badge-pending">Learning Preferences</span>
                    </div>
                </div>

                <div className="card p-6 border border-amber-500/20 bg-amber-500/5 relative overflow-hidden">
                    <div className="absolute top-0 right-0 p-4 opacity-10"><Target size={80} /></div>
                    <h3 className="text-lg font-bold text-amber-400 flex items-center gap-2 mb-2">
                        <Target size={20} /> Strategy Adjustments
                    </h3>
                    <p className="text-sm text-slate-400 mb-4">Based on recent rejections, the AI is shifting focus towards entry-level Cloud roles rather than Mid-level Backend roles.</p>
                </div>
            </div>

            <div className="card p-6">
                <h3 className="text-lg font-bold text-white mb-4 flex items-center gap-2">
                    <AlertTriangle size={20} className="text-rose-400" /> Detected Skill Gaps
                </h3>
                {loading ? (
                    <div className="skeleton h-16 w-full" />
                ) : insights.length === 0 ? (
                    <p className="text-slate-500 text-sm italic">Not enough application history to generate skill gaps. Keep applying!</p>
                ) : (
                    <div className="space-y-3">
                        {insights.map((insight, idx) => (
                            <div key={idx} className="p-4 rounded-xl bg-white/[0.02] border border-white/[0.05] flex gap-3 items-start">
                                <TrendingUp size={16} className="text-emerald-400 mt-0.5" />
                                <p className="text-sm text-slate-300 leading-relaxed">{insight.text}</p>
                            </div>
                        ))}
                    </div>
                )}
            </div>
        </div>
    )
}
