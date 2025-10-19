import React, { useEffect, useState } from 'react'
import axios from 'axios'
import { useInvestigation } from '../contexts/InvestigationContext.jsx'

export default function AlertQueue() {
  const [alerts, setAlerts] = useState([])
  const { setInvestigation } = useInvestigation()

  useEffect(() => {
    let mounted = true
    axios.get('/api/alerts')
      .then(res => {
        if (!mounted) return
        setAlerts(res.data.alerts ?? [])
      })
      .catch(() => setAlerts([]))
    return () => { mounted = false }
  }, [])

  return (
    <div className="list">
      {alerts.length === 0 && (
        <div className="list-item" style={{cursor:'default', textAlign: 'center'}}>
          <div style={{fontSize: 13, marginBottom: 8}}>No alerts yet.</div>
          <div style={{fontSize: 11, color: 'var(--muted)'}}>
            Start with <code style={{padding: '2px 4px', background: 'rgba(168, 85, 247, 0.2)', borderRadius: '3px'}}>POST /api/ingest/&lt;address&gt;</code> then <code style={{padding: '2px 4px', background: 'rgba(168, 85, 247, 0.2)', borderRadius: '3px'}}>POST /api/analyze</code>
          </div>
        </div>
      )}
      {alerts.map(a => (
        <div key={a.id} className="list-item" onClick={() => setInvestigation(a.address)}>
          <div style={{display:'flex',justifyContent:'space-between', alignItems:'center', marginBottom: 8}}>
            <div style={{fontWeight:700, fontSize: 14}}>{a.type}</div>
            <div style={{
              padding: '4px 10px',
              borderRadius: '999px',
              fontSize: 11,
              fontWeight: 700,
              background: a.score > 70 ? 'linear-gradient(135deg, var(--danger), #dc2626)' : a.score > 50 ? 'linear-gradient(135deg, #FFA94D, #FF8C42)' : 'linear-gradient(135deg, var(--ok), #059669)',
              color: 'white',
              boxShadow: a.score > 70 ? '0 0 10px var(--danger-glow)' : a.score > 50 ? '0 0 10px rgba(255, 169, 77, 0.4)' : '0 0 10px var(--ok-glow)'
            }}>
              Score {Math.round(a.score)}
            </div>
          </div>
          <div style={{fontSize:11, color:'var(--muted)', marginTop:6, fontFamily: 'monospace'}}>
            {a.address}
          </div>
          <div style={{fontSize:10, color:'#8b7baa', marginTop:6}}>
            {new Date(a.created_at).toLocaleString()}
          </div>
        </div>
      ))}
    </div>
  )
}
