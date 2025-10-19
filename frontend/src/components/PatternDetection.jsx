import { useState } from 'react'

export default function PatternDetection({ address }) {
  const [patterns, setPatterns] = useState(null)
  const [loading, setLoading] = useState(false)
  const [activeTab, setActiveTab] = useState('all')

  const analyzePatterns = () => {
    if (!address) return
    setLoading(true)
    
    fetch(`http://localhost:8000/api/patterns/${address}`)
      .then(r => r.json())
      .then(data => {
        setPatterns(data)
        setLoading(false)
      })
      .catch(err => {
        console.error(err)
        setLoading(false)
      })
  }

  const analyzeSpecific = (type) => {
    if (!address) return
    setLoading(true)
    
    fetch(`http://localhost:8000/api/patterns/${address}/${type}`)
      .then(r => r.json())
      .then(data => {
        setPatterns({[type]: data})
        setLoading(false)
      })
      .catch(err => {
        console.error(err)
        setLoading(false)
      })
  }

  const getIcon = (type) => {
    const icons = {
      'layering': '🔄',
      'peel_chain': '⛓️',
      'wash_trading': '♻️',
      'round_amount': '💰',
      'time_anomaly': '⏰',
      'dust_attack': '💨'
    }
    return icons[type] || '🔍'
  }

  return (
    <div className="panel">
      <h3>🎯 Pattern Detection</h3>
      
      <div style={{display: 'flex', gap: 12, marginBottom: 20}}>
        <button className="btn-primary" onClick={analyzePatterns} disabled={loading || !address}>
          {loading ? 'Analyzing...' : 'Analyze All Patterns'}
        </button>
        <button className="btn-primary" onClick={() => analyzeSpecific('layering')} disabled={loading || !address}>
          Layering
        </button>
        <button className="btn-primary" onClick={() => analyzeSpecific('peel-chains')} disabled={loading || !address}>
          Peel Chains
        </button>
        <button className="btn-primary" onClick={() => analyzeSpecific('wash-trading')} disabled={loading || !address}>
          Wash Trading
        </button>
      </div>

      {!address && (
        <div style={{padding: 40, textAlign: 'center', color: 'var(--muted)'}}>
          <div style={{fontSize: 48, marginBottom: 12}}>🎯</div>
          <div>Select an address to analyze patterns</div>
        </div>
      )}

      {patterns && (
        <div>
          {Object.entries(patterns).map(([key, value]) => {
            if (!value || typeof value !== 'object') return null
            
            return (
              <div key={key} className="panel" style={{marginTop: 16, background: 'rgba(168, 85, 247, 0.05)', border: '1px solid rgba(168, 85, 247, 0.2)'}}>
                <div style={{display: 'flex', alignItems: 'center', gap: 12, marginBottom: 12}}>
                  <div style={{fontSize: 32}}>{getIcon(value.pattern_type || key)}</div>
                  <div>
                    <h4 style={{fontSize: 16, fontWeight: 700, textTransform: 'uppercase', marginBottom: 4}}>
                      {value.pattern_type || key}
                    </h4>
                    <div style={{fontSize: 12, color: 'var(--muted)'}}>
                      Status: {value.detected ? '⚠️ DETECTED' : '✅ Not Found'}
                    </div>
                  </div>
                  {value.risk_score !== undefined && (
                    <div style={{
                      marginLeft: 'auto',
                      padding: '8px 16px',
                      borderRadius: '999px',
                      background: value.risk_score > 70 ? 'linear-gradient(135deg, var(--danger), #dc2626)' : 
                                  value.risk_score > 50 ? 'linear-gradient(135deg, #FFA94D, #FF8C42)' : 
                                  'linear-gradient(135deg, var(--ok), #059669)',
                      color: 'white',
                      fontWeight: 700,
                      fontSize: 14,
                      boxShadow: value.risk_score > 70 ? '0 0 20px var(--danger-glow)' : '0 0 10px rgba(168, 85, 247, 0.3)'
                    }}>
                      Risk: {value.risk_score}
                    </div>
                  )}
                </div>
                
                {value.explanation && (
                  <div style={{padding: 12, background: 'rgba(10, 1, 24, 0.5)', borderRadius: 8, marginTop: 12}}>
                    <div style={{fontSize: 13, lineHeight: 1.6}}>{value.explanation}</div>
                  </div>
                )}
                
                {value.chains && value.chains.length > 0 && (
                  <div style={{marginTop: 12}}>
                    <div style={{fontSize: 12, fontWeight: 600, color: 'var(--muted)', marginBottom: 8}}>
                      DETECTED CHAINS: {value.chains.length}
                    </div>
                    {value.chains.slice(0, 3).map((chain, idx) => (
                      <div key={idx} style={{
                        padding: 8,
                        background: 'rgba(168, 85, 247, 0.1)',
                        borderRadius: 6,
                        marginBottom: 8,
                        fontSize: 11,
                        fontFamily: 'monospace'
                      }}>
                        Depth: {chain.depth} | Value: {chain.total_value?.toFixed(4)} ETH
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}

