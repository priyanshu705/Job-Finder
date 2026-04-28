import { memo } from 'react'

const PageHeader = memo(function PageHeader({ title, sub, children }) {
  return (
    <div className="flex items-center justify-between pb-2" style={{ animation: 'fadeIn 0.3s ease-out both' }}>
      <div>
        <h1
          style={{
            fontSize: 24,
            fontWeight: 800,
            letterSpacing: '-0.02em',
            lineHeight: 1.1,
            background: 'linear-gradient(135deg, #e2e8f0 0%, #94a3b8 100%)',
            WebkitBackgroundClip: 'text',
            WebkitTextFillColor: 'transparent',
            backgroundClip: 'text',
          }}
        >
          {title}
        </h1>
        {sub && (
          <p style={{ fontSize: 13, color: 'rgba(100,116,139,0.8)', marginTop: 3 }}>
            {sub}
          </p>
        )}
      </div>
      {/* Right-side actions slot */}
      {children && (
        <div className="flex items-center gap-2">
          {children}
        </div>
      )}
    </div>
  )
})

export default PageHeader
