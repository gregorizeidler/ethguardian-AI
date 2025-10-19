import { useState, useEffect } from 'react'

export default function Dashboard() {
  const [stats, setStats] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetch('http://localhost:8000/api/alerts')
      .then(r => r.json())
      .then(data => {
        setStats({
          totalAlerts: data.length || 0,
          highRisk: data.filter(a => a.score > 70).length || 0,
          mediumRisk: data.filter(a => a.score > 50 && a.score <= 70).length || 0,
          lowRisk: data.filter(a => a.score <= 50).length || 0
        })
        setLoading(false)
      })
      .catch(err => {
        console.error(err)
        setLoading(false)
      })
  }, [])

  if (loading) {
    return (
      <div className="panel" style={{padding: 40, textAlign: 'center'}}>
        <div style={{fontSize: 48, marginBottom: 16}}>📊</div>
        <div style={{fontSize: 16, fontWeight: 600}}>Loading Analytics Dashboard...</div>
      </div>
    )
  }

  return (
    <div style={{display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))', gap: 24, marginBottom: 24}}>
      {/* Total Alerts */}
      <div className="panel" style={{
        background: 'linear-gradient(135deg, rgba(168, 85, 247, 0.1), rgba(139, 92, 246, 0.05))',
        border: '2px solid rgba(168, 85, 247, 0.3)',
        position: 'relative',
        overflow: 'hidden'
      }}>
        <div style={{
          position: 'absolute',
          top: -20,
          right: -20,
          fontSize: 120,
          opacity: 0.1
        }}>🔔</div>
        <h3 style={{fontSize: 14, fontWeight: 600, color: 'var(--muted)', marginBottom: 8}}>TOTAL ALERTS</h3>
        <div style={{fontSize: 48, fontWeight: 800, background: 'linear-gradient(135deg, var(--accent), var(--cyan))', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent'}}>
          {stats?.totalAlerts || 0}
        </div>
        <div style={{fontSize: 12, color: 'var(--muted)', marginTop: 8}}>All time</div>
      </div>

      {/* High Risk */}
      <div className="panel" style={{
        background: 'linear-gradient(135deg, rgba(239, 68, 68, 0.1), rgba(220, 38, 38, 0.05))',
        border: '2px solid rgba(239, 68, 68, 0.3)',
        position: 'relative',
        overflow: 'hidden'
      }}>
        <div style={{
          position: 'absolute',
          top: -20,
          right: -20,
          fontSize: 120,
          opacity: 0.1
        }}>⚠️</div>
        <h3 style={{fontSize: 14, fontWeight: 600, color: 'var(--muted)', marginBottom: 8}}>HIGH RISK</h3>
        <div style={{fontSize: 48, fontWeight: 800, color: 'var(--danger)'}}>
          {stats?.highRisk || 0}
        </div>
        <div style={{fontSize: 12, color: 'var(--muted)', marginTop: 8}}>Score {'>'} 70</div>
      </div>

      {/* Medium Risk */}
      <div className="panel" style={{
        background: 'linear-gradient(135deg, rgba(255, 169, 77, 0.1), rgba(255, 140, 66, 0.05))',
        border: '2px solid rgba(255, 169, 77, 0.3)',
        position: 'relative',
        overflow: 'hidden'
      }}>
        <div style={{
          position: 'absolute',
          top: -20,
          right: -20,
          fontSize: 120,
          opacity: 0.1
        }}>⚡</div>
        <h3 style={{fontSize: 14, fontWeight: 600, color: 'var(--muted)', marginBottom: 8}}>MEDIUM RISK</h3>
        <div style={{fontSize: 48, fontWeight: 800, color: '#FFA94D'}}>
          {stats?.mediumRisk || 0}
        </div>
        <div style={{fontSize: 12, color: 'var(--muted)', marginTop: 8}}>Score 50-70</div>
      </div>

      {/* Low Risk */}
      <div className="panel" style={{
        background: 'linear-gradient(135deg, rgba(16, 185, 129, 0.1), rgba(5, 150, 105, 0.05))',
        border: '2px solid rgba(16, 185, 129, 0.3)',
        position: 'relative',
        overflow: 'hidden'
      }}>
        <div style={{
          position: 'absolute',
          top: -20,
          right: -20,
          fontSize: 120,
          opacity: 0.1
        }}>✅</div>
        <h3 style={{fontSize: 14, fontWeight: 600, color: 'var(--muted)', marginBottom: 8}}>LOW RISK</h3>
        <div style={{fontSize: 48, fontWeight: 800, color: 'var(--ok)'}}>
          {stats?.lowRisk || 0}
        </div>
        <div style={{fontSize: 12, color: 'var(--muted)', marginTop: 8}}>Score {'<'} 50</div>
      </div>
    </div>
  )
}

