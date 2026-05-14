import { useState, useEffect } from 'react'
import { CheckCircle2, MessageSquare, Briefcase, FileText, Download, X, Play, Loader } from 'lucide-react'
import { api, getRaw } from '../api.js'
import toast from 'react-hot-toast'
import { socket } from '../services/socket.js'

export default function InterviewPrepModal({ jobId, onClose }) {
  const [prep, setPrep] = useState(null)
  const [loading, setLoading] = useState(true)
  const [generating, setGenerating] = useState(false)

  const fetchPrep = async () => {
    try {
      const res = await getRaw(`/api/jobs/${jobId}/interview-prep`)
      if (res.status === 'ready') {
        setPrep(res.data)
        setGenerating(false)
      } else {
        setPrep(null)
      }
    } catch (e) {
      console.error(e)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchPrep()
    
    socket.on('ai:prep_completed', (data) => {
        if (data.job_url) fetchPrep() // Simplified check
    })
    
    return () => socket.off('ai:prep_completed')
  }, [jobId])

  const handleGenerate = async () => {
    setGenerating(true)
    try {
      await api.triggerAction(`/api/jobs/${jobId}/interview-prep`, {})
      toast.success("AI is generating your interview prep...")
    } catch (e) {
      toast.error("Failed to start generation")
      setGenerating(false)
    }
  }
  
  const handleExport = () => {
      window.print() // Simplest zero-budget export requested
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm" style={{ animation: 'fadeIn 0.2s ease-out' }}>
      <div 
        className="w-full max-w-3xl max-h-[85vh] flex flex-col rounded-2xl overflow-hidden"
        style={{
          background: 'linear-gradient(135deg, rgba(13,21,38,0.95) 0%, rgba(8,15,31,0.98) 100%)',
          border: '1px solid rgba(255,255,255,0.08)',
          boxShadow: '0 24px 64px rgba(0,0,0,0.6), inset 0 1px 0 rgba(255,255,255,0.05)',
        }}
      >
        <div className="flex items-center justify-between p-5 border-b border-white/[0.06]">
          <h2 className="text-xl font-bold text-white flex items-center gap-2">
            <MessageSquare size={20} className="text-indigo-400" />
            AI Interview Prep
          </h2>
          <div className="flex items-center gap-2">
              {prep && (
                  <button onClick={handleExport} className="p-2 rounded-lg hover:bg-white/[0.05] text-slate-400 hover:text-white transition-colors">
                      <Download size={18} />
                  </button>
              )}
              <button onClick={onClose} className="p-2 rounded-lg hover:bg-white/[0.05] text-slate-400 hover:text-white transition-colors">
                <X size={18} />
              </button>
          </div>
        </div>

        <div className="p-6 overflow-y-auto flex-1">
          {loading ? (
            <div className="flex flex-col items-center justify-center h-48 space-y-3">
              <Loader className="animate-spin text-indigo-500" size={32} />
              <p className="text-sm text-slate-400">Checking prep status...</p>
            </div>
          ) : !prep ? (
            <div className="flex flex-col items-center justify-center h-64 space-y-4 text-center">
              <div className="w-16 h-16 rounded-full bg-indigo-500/10 flex items-center justify-center border border-indigo-500/20 mb-2">
                <Play size={24} className="text-indigo-400 ml-1" />
              </div>
              <h3 className="text-lg font-bold text-white">No Prep Generated Yet</h3>
              <p className="text-sm text-slate-400 max-w-sm">
                Generate a custom mock interview based on your exact resume and this job's requirements.
              </p>
              <button 
                onClick={handleGenerate}
                disabled={generating}
                className="mt-4 px-6 py-2.5 rounded-xl font-bold text-sm bg-indigo-500 hover:bg-indigo-400 text-white transition-all disabled:opacity-50 flex items-center gap-2"
              >
                {generating ? <Loader size={16} className="animate-spin" /> : <Play size={16} />}
                {generating ? "Generating..." : "Generate Interview Prep"}
              </button>
            </div>
          ) : (
            <div className="space-y-8 pb-8 print:text-black">
                <div className="space-y-4">
                    <h3 className="text-lg font-bold text-emerald-400 flex items-center gap-2 border-b border-emerald-500/20 pb-2">
                        <Briefcase size={18} /> Technical Questions
                    </h3>
                    <ul className="space-y-3">
                        {prep.technical_questions?.map((q, i) => (
                            <li key={i} className="flex gap-3 text-slate-300 text-sm leading-relaxed bg-white/[0.02] p-3 rounded-lg">
                                <span className="font-bold text-emerald-500/50 mt-0.5">{i+1}.</span> {q}
                            </li>
                        ))}
                    </ul>
                </div>
                
                <div className="space-y-4">
                    <h3 className="text-lg font-bold text-indigo-400 flex items-center gap-2 border-b border-indigo-500/20 pb-2">
                        <FileText size={18} /> Behavioral & HR
                    </h3>
                    <ul className="space-y-3">
                        {prep.behavioral_questions?.map((q, i) => (
                            <li key={i} className="flex gap-3 text-slate-300 text-sm leading-relaxed bg-white/[0.02] p-3 rounded-lg">
                                <span className="font-bold text-indigo-500/50 mt-0.5">{i+1}.</span> {q}
                            </li>
                        ))}
                        {prep.hr_questions?.map((q, i) => (
                            <li key={i} className="flex gap-3 text-slate-300 text-sm leading-relaxed bg-white/[0.02] p-3 rounded-lg border-l-2 border-amber-500/30">
                                <span className="font-bold text-amber-500/50 mt-0.5">HR.</span> {q}
                            </li>
                        ))}
                    </ul>
                </div>
                
                {prep.role_play_scenario && (
                    <div className="space-y-4">
                        <h3 className="text-lg font-bold text-amber-400 flex items-center gap-2 border-b border-amber-500/20 pb-2">
                            <Play size={18} /> Role-Play Scenario
                        </h3>
                        <div className="text-slate-300 text-sm leading-relaxed bg-amber-500/5 p-4 rounded-xl border border-amber-500/10 italic">
                            "{prep.role_play_scenario}"
                        </div>
                    </div>
                )}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
