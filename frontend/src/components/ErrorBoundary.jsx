import React from 'react'

export default class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props)
    this.state = { hasError: false, error: null }
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error }
  }

  componentDidCatch(error, errorInfo) {
    console.error('ErrorBoundary caught:', error, errorInfo)
  }

  render() {
    if (this.state.hasError) {
      return (
        <div style={{padding: 32, textAlign: 'center', color: 'var(--muted)'}}>
          <div style={{fontSize: 48, marginBottom: 16}}>⚠️</div>
          <div style={{marginBottom: 12, fontWeight: 600}}>Graph Visualization Unavailable</div>
          <div style={{fontSize: 12, marginBottom: 24, color: 'var(--danger)'}}>
            {this.state.error?.message || 'Unknown error'}
          </div>
          <div style={{fontSize: 11, padding: 16, background: '#0d0f15', borderRadius: 8, textAlign: 'left', maxWidth: 400, margin: '0 auto'}}>
            <div style={{marginBottom: 12}}>
              <strong>💡 Workaround:</strong>
            </div>
            <div style={{marginBottom: 8}}>
              Use the API directly to get graph data:
            </div>
            <div style={{fontFamily: 'monospace', background: '#000', padding: 8, borderRadius: 4, fontSize: 10}}>
              GET /api/address/{'<address>'}/graph
            </div>
            <div style={{marginTop: 12, fontSize: 10, color: 'var(--muted)'}}>
              The issue is with the react-force-graph library loading AFRAME (WebVR) unnecessarily.
            </div>
          </div>
        </div>
      )
    }

    return this.props.children
  }
}

