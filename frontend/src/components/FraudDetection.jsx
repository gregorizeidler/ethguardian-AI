import { useState } from 'react'

export default function FraudDetection({ address }) {
  const [fraudData, setFraudData] = useState(null)
  const [loading, setLoading] = useState(false)

  const analyzeFraud = () => {
    if (!address) return
    setLoading(true)
    
    fetch(`http://localhost:8000/api/fraud/${address}`)
      .then(r => r.json())
      .then(data => {
        setFraudData(data)
        setLoading(false)
      })
      .catch(err => {
        console.error(err)
        setLoading(false)
      })
  }

  const fraudTypes = [
    { key: 'rug_pull', name: 'Rug Pull', icon: '💸', endpoint: 'rug-pull' },
    { key: 'ponzi', name: 'Ponzi Scheme', icon: '🔺', endpoint: 'ponzi' },
    { key: 'phishing', name: 'Phishing', icon: '🎣', endpoint: 'phishing' },
    { key: 'mev_bot', name: 'MEV Bot', icon: '🤖', endpoint: 'mev-bot' }
  ]

  const analyzeSpecific = (endpoint) => {
    if (!address) return
    setLoading(true)
    
    fetch(`http://localhost:8000/api/fraud/${address}/${endpoint}`)
      .then(r => r.json())
      .then(data => {
        setFraudData({[endpoint.replace('-', '_')]: data})
        setLoading(false)
      })
      .catch(err => {
        console.error(err)
        setLoading(false)
      })
  }

  return (
    <div className="panel">
      <h3>🚨 Fraud Detection</h3>
      
      <div style={{display: 'flex', flexWrap: 'wrap', gap: 12, marginBottom: 20}}>
        <button className="btn-primary" onClick={analyzeFraud} disabled={loading || !address}>
          {loading ? 'Scanning...' : 'Scan All Fraud Types'}
        </button>
        {fraudTypes.map(type => (
          <button 
            key={type.key}
            className="btn-primary" 
            onClick={() => analyzeSpecific(type.endpoint)} 
            disabled={loading || !address}
            style={{minWidth: 120}}
          >
            {type.icon} {type.name}
          </button>
        ))}
      </div>

      {!address && (
        <div style={{padding: 40, textAlign: 'center', color: 'var(--muted)'}}>
          <div style={{fontSize: 48, marginBottom: 12}}>🚨</div>
          <div>Select an address to scan for fraud</div>
        </div>
      )}

      {fraudData && (
        <div style={{display: 'grid', gap: 16}}>
          {Object.entries(fraudData).map(([key, value]) => {
            if (!value || typeof value !== 'object') return null
            
            const fraudType = fraudTypes.find(t => t.key === key || t.endpoint === key) || {}
            
            return (
              <div 
                key={key} 
                className="panel" 
                style={{
                  background: value.detected ? 
                    'linear-gradient(135deg, rgba(239, 68, 68, 0.15), rgba(220, 38, 38, 0.05))' : 
                    'linear-gradient(135deg, rgba(16, 185, 129, 0.15), rgba(5, 150, 105, 0.05))',
                  border: value.detected ? 
                    '2px solid rgba(239, 68, 68, 0.5)' : 
                    '2px solid rgba(16, 185, 129, 0.3)',
                  position: 'relative',
                  overflow: 'hidden'
                }}
              >
                <div style={{
                  position: 'absolute',
                  top: -30,
                  right: -30,
                  fontSize: 150,
                  opacity: 0.05
                }}>
                  {fraudType.icon || '🚨'}
                </div>

                <div style={{display: 'flex', alignItems: 'flex-start', gap: 16}}>
                  <div style={{fontSize: 48}}>{fraudType.icon || '🚨'}</div>
                  
                  <div style={{flex: 1}}>
                    <h4 style={{
                      fontSize: 18,
                      fontWeight: 800,
                      textTransform: 'uppercase',
                      marginBottom: 8,
                      background: 'linear-gradient(135deg, var(--accent), var(--cyan))',
                      WebkitBackgroundClip: 'text',
                      WebkitTextFillColor: 'transparent'
                    }}>
                      {value.fraud_type || fraudType.name || key}
                    </h4>
                    
                    <div style={{
                      display: 'inline-block',
                      padding: '6px 12px',
                      borderRadius: '999px',
                      background: value.detected ? 
                        'linear-gradient(135deg, var(--danger), #dc2626)' : 
                        'linear-gradient(135deg, var(--ok), #059669)',
                      color: 'white',
                      fontWeight: 700,
                      fontSize: 12,
                      marginBottom: 16,
                      boxShadow: value.detected ? '0 0 20px var(--danger-glow)' : '0 0 10px var(--ok-glow)',
                      animation: value.detected ? 'pulse-glow 2s infinite' : 'none'
                    }}>
                      {value.detected ? '⚠️ DETECTED' : '✅ NOT DETECTED'}
                    </div>

                    {value.risk_score !== undefined && value.risk_score > 0 && (
                      <div style={{marginBottom: 12}}>
                        <div style={{fontSize: 12, fontWeight: 600, color: 'var(--muted)', marginBottom: 6}}>
                          RISK SCORE
                        </div>
                        <div style={{display: 'flex', alignItems: 'center', gap: 12}}>
                          <div style={{
                            flex: 1,
                            height: 12,
                            background: 'rgba(10, 1, 24, 0.5)',
                            borderRadius: 999,
                            overflow: 'hidden',
                            border: '1px solid rgba(168, 85, 247, 0.3)'
                          }}>
                            <div style={{
                              height: '100%',
                              width: `${value.risk_score}%`,
                              background: value.risk_score > 70 ? 
                                'linear-gradient(90deg, var(--danger), #dc2626)' : 
                                value.risk_score > 50 ? 
                                'linear-gradient(90deg, #FFA94D, #FF8C42)' : 
                                'linear-gradient(90deg, var(--ok), #059669)',
                              transition: 'width 0.5s ease',
                              boxShadow: value.risk_score > 70 ? '0 0 10px var(--danger-glow)' : 'none'
                            }}></div>
                          </div>
                          <div style={{
                            fontSize: 18,
                            fontWeight: 800,
                            color: value.risk_score > 70 ? 'var(--danger)' : 
                                   value.risk_score > 50 ? '#FFA94D' : 'var(--ok)',
                            minWidth: 40,
                            textAlign: 'right'
                          }}>
                            {value.risk_score}
                          </div>
                        </div>
                      </div>
                    )}

                    {value.explanation && (
                      <div style={{
                        padding: 12,
                        background: 'rgba(10, 1, 24, 0.6)',
                        borderRadius: 8,
                        marginTop: 12,
                        borderLeft: '3px solid var(--accent)'
                      }}>
                        <div style={{fontSize: 13, lineHeight: 1.6, color: '#e0e0ff'}}>
                          {value.explanation}
                        </div>
                      </div>
                    )}

                    {value.recommendation && (
                      <div style={{
                        padding: 12,
                        background: 'rgba(239, 68, 68, 0.1)',
                        borderRadius: 8,
                        marginTop: 12,
                        border: '1px solid rgba(239, 68, 68, 0.3)'
                      }}>
                        <div style={{fontSize: 11, fontWeight: 700, color: 'var(--danger)', marginBottom: 4}}>
                          ⚠️ RECOMMENDATION
                        </div>
                        <div style={{fontSize: 13, lineHeight: 1.6}}>
                          {value.recommendation}
                        </div>
                      </div>
                    )}

                    {value.evidence && value.evidence.length > 0 && (
                      <div style={{marginTop: 12}}>
                        <div style={{fontSize: 11, fontWeight: 700, color: 'var(--muted)', marginBottom: 8}}>
                          EVIDENCE ({value.evidence.length})
                        </div>
                        {value.evidence.slice(0, 3).map((evidence, idx) => (
                          <div key={idx} style={{
                            padding: 8,
                            background: 'rgba(168, 85, 247, 0.1)',
                            borderRadius: 6,
                            marginBottom: 6,
                            fontSize: 11
                          }}>
                            {typeof evidence === 'string' ? evidence : JSON.stringify(evidence)}
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}

