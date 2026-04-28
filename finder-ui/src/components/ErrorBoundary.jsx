import React from 'react'
import { AlertTriangle, RefreshCw } from 'lucide-react'

export default class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props)
    this.state = { hasError: false, error: null }
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error }
  }

  componentDidCatch(error, errorInfo) {
    console.error('ErrorBoundary caught an error:', error, errorInfo)
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="min-h-screen flex items-center justify-center p-6 bg-navy-950">
          <div 
            className="max-w-md w-full p-8 rounded-3xl text-center space-y-6"
            style={{
              background: 'linear-gradient(135deg, rgba(248,113,113,0.1) 0%, rgba(13,21,38,0.95) 100%)',
              border: '1px solid rgba(248,113,113,0.25)',
              boxShadow: '0 0 40px rgba(0,0,0,0.5), 0 0 20px rgba(248,113,113,0.05)',
              animation: 'scaleIn 0.4s cubic-bezier(0.34,1.56,0.64,1) both'
            }}
          >
            <div className="w-20 h-20 bg-red-500/10 rounded-full flex items-center justify-center mx-auto">
              <AlertTriangle size={40} className="text-red-500" />
            </div>
            <div className="space-y-2">
              <h2 className="text-2xl font-bold text-white">Something went wrong</h2>
              <p className="text-slate-400 text-sm leading-relaxed">
                A critical rendering error occurred. This has been logged and we're looking into it.
              </p>
            </div>
            {process.env.NODE_ENV === 'development' && (
              <div className="p-4 bg-black/40 rounded-xl overflow-x-auto text-left">
                <p className="text-red-400 font-mono text-xs whitespace-pre-wrap">
                  {this.state.error?.toString()}
                </p>
              </div>
            )}
            <button 
              onClick={() => window.location.reload()}
              className="btn-primary w-full py-3 flex items-center justify-center gap-2"
            >
              <RefreshCw size={18} />
              Reload Application
            </button>
          </div>
        </div>
      )
    }

    return this.props.children
  }
}
