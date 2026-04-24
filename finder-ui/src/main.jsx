import React from 'react'
import ReactDOM from 'react-dom/client'
import { Toaster } from 'react-hot-toast'
import App from './App.jsx'
import './index.css'

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <App />
    <Toaster
      position="bottom-right"
      toastOptions={{
        style: {
          background: '#1e293b',
          color: '#e2e8f0',
          border: '1px solid rgba(148,163,184,0.2)',
          borderRadius: '12px',
          fontSize: '14px',
        },
        success: { iconTheme: { primary: '#10b981', secondary: '#1e293b' } },
        error:   { iconTheme: { primary: '#ef4444', secondary: '#1e293b' } },
      }}
    />
  </React.StrictMode>
)
