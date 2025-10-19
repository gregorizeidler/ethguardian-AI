import React, { useState } from 'react'
import axios from 'axios'

export default function AutomationPanel() {
  const [activeTab, setActiveTab] = useState('crawler')
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState(null)

  // Crawler form state
  const [crawlerForm, setCrawlerForm] = useState({
    seed_addresses: '',
    max_depth: 3,
    min_value_eth: 1.0,
    min_risk_score: 60.0,
    max_addresses: 5000
  })

  // Monitor form state
  const [monitorForm, setMonitorForm] = useState({
    min_value_usd: 100000,
    check_interval_minutes: 60,
    duration_hours: 24
  })

  // Expansion form state
  const [expansionForm, setExpansionForm] = useState({
    address: '',
    trigger_score: 70.0,
    expansion_depth: 2,
    min_value_eth: 0.5
  })

  const startCrawler = async () => {
    setLoading(true)
    setResult(null)
    try {
      const addresses = crawlerForm.seed_addresses.split(',').map(a => a.trim()).filter(a => a)
      const res = await axios.post('/api/automation/crawler', {
        seed_addresses: addresses,
        max_depth: parseInt(crawlerForm.max_depth),
        min_value_eth: parseFloat(crawlerForm.min_value_eth),
        min_risk_score: parseFloat(crawlerForm.min_risk_score),
        max_addresses: parseInt(crawlerForm.max_addresses),
        run_async: true
      })
      setResult({ success: true, data: res.data })
    } catch (err) {
      setResult({ success: false, error: err.response?.data?.detail || err.message })
    } finally {
      setLoading(false)
    }
  }

  const startMonitor = async () => {
    setLoading(true)
    setResult(null)
    try {
      const res = await axios.post('/api/automation/monitor', {
        min_value_usd: parseFloat(monitorForm.min_value_usd),
        check_interval_minutes: parseInt(monitorForm.check_interval_minutes),
        duration_hours: parseInt(monitorForm.duration_hours),
        run_async: true
      })
      setResult({ success: true, data: res.data })
    } catch (err) {
      setResult({ success: false, error: err.response?.data?.detail || err.message })
    } finally {
      setLoading(false)
    }
  }

  const startExpansion = async () => {
    setLoading(true)
    setResult(null)
    try {
      const res = await axios.post('/api/automation/expansion', {
        address: expansionForm.address.trim(),
        trigger_score: parseFloat(expansionForm.trigger_score),
        expansion_depth: parseInt(expansionForm.expansion_depth),
        min_value_eth: parseFloat(expansionForm.min_value_eth),
        run_async: true
      })
      setResult({ success: true, data: res.data })
    } catch (err) {
      setResult({ success: false, error: err.response?.data?.detail || err.message })
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="automation-panel">
      <div className="tabs">
        <button 
          className={`tab ${activeTab === 'crawler' ? 'active' : ''}`}
          onClick={() => setActiveTab('crawler')}
        >
          🕷️ Crawler
        </button>
        <button 
          className={`tab ${activeTab === 'monitor' ? 'active' : ''}`}
          onClick={() => setActiveTab('monitor')}
        >
          📡 Monitor
        </button>
        <button 
          className={`tab ${activeTab === 'expansion' ? 'active' : ''}`}
          onClick={() => setActiveTab('expansion')}
        >
          🌳 Expansion
        </button>
      </div>

      <div className="tab-content">
        {activeTab === 'crawler' && (
          <div className="form">
            <h4>🕷️ Blockchain Crawler</h4>
            <p style={{fontSize: 12, color: 'var(--muted)', marginBottom: 16}}>
              Explore blockchain connections from seed addresses
            </p>
            
            <label>Seed Addresses (comma-separated)</label>
            <input
              type="text"
              placeholder="0xabc..., 0xdef..."
              value={crawlerForm.seed_addresses}
              onChange={(e) => setCrawlerForm({...crawlerForm, seed_addresses: e.target.value})}
            />

            <div style={{display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12}}>
              <div>
                <label>Max Depth</label>
                <input
                  type="number"
                  value={crawlerForm.max_depth}
                  onChange={(e) => setCrawlerForm({...crawlerForm, max_depth: e.target.value})}
                />
              </div>
              <div>
                <label>Min Value (ETH)</label>
                <input
                  type="number"
                  step="0.1"
                  value={crawlerForm.min_value_eth}
                  onChange={(e) => setCrawlerForm({...crawlerForm, min_value_eth: e.target.value})}
                />
              </div>
              <div>
                <label>Min Risk Score</label>
                <input
                  type="number"
                  value={crawlerForm.min_risk_score}
                  onChange={(e) => setCrawlerForm({...crawlerForm, min_risk_score: e.target.value})}
                />
              </div>
              <div>
                <label>Max Addresses</label>
                <input
                  type="number"
                  value={crawlerForm.max_addresses}
                  onChange={(e) => setCrawlerForm({...crawlerForm, max_addresses: e.target.value})}
                />
              </div>
            </div>

            <button className="btn-primary" onClick={startCrawler} disabled={loading}>
              {loading ? '⏳ Starting...' : '🚀 Start Crawler'}
            </button>
          </div>
        )}

        {activeTab === 'monitor' && (
          <div className="form">
            <h4>📡 Blockchain Monitor</h4>
            <p style={{fontSize: 12, color: 'var(--muted)', marginBottom: 16}}>
              Monitor real-time transactions above threshold
            </p>

            <label>Min Transaction Value (USD)</label>
            <input
              type="number"
              placeholder="100000"
              value={monitorForm.min_value_usd}
              onChange={(e) => setMonitorForm({...monitorForm, min_value_usd: e.target.value})}
            />

            <div style={{display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12}}>
              <div>
                <label>Check Interval (minutes)</label>
                <input
                  type="number"
                  value={monitorForm.check_interval_minutes}
                  onChange={(e) => setMonitorForm({...monitorForm, check_interval_minutes: e.target.value})}
                />
              </div>
              <div>
                <label>Duration (hours)</label>
                <input
                  type="number"
                  value={monitorForm.duration_hours}
                  onChange={(e) => setMonitorForm({...monitorForm, duration_hours: e.target.value})}
                />
              </div>
            </div>

            <button className="btn-primary" onClick={startMonitor} disabled={loading}>
              {loading ? '⏳ Starting...' : '🚀 Start Monitor'}
            </button>
          </div>
        )}

        {activeTab === 'expansion' && (
          <div className="form">
            <h4>🌳 Auto-Expansion</h4>
            <p style={{fontSize: 12, color: 'var(--muted)', marginBottom: 16}}>
              Deep investigation with automatic expansion
            </p>

            <label>Initial Address</label>
            <input
              type="text"
              placeholder="0xabc123..."
              value={expansionForm.address}
              onChange={(e) => setExpansionForm({...expansionForm, address: e.target.value})}
            />

            <div style={{display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12}}>
              <div>
                <label>Trigger Score</label>
                <input
                  type="number"
                  value={expansionForm.trigger_score}
                  onChange={(e) => setExpansionForm({...expansionForm, trigger_score: e.target.value})}
                />
              </div>
              <div>
                <label>Expansion Depth</label>
                <input
                  type="number"
                  value={expansionForm.expansion_depth}
                  onChange={(e) => setExpansionForm({...expansionForm, expansion_depth: e.target.value})}
                />
              </div>
            </div>

            <label>Min Connection Value (ETH)</label>
            <input
              type="number"
              step="0.1"
              value={expansionForm.min_value_eth}
              onChange={(e) => setExpansionForm({...expansionForm, min_value_eth: e.target.value})}
            />

            <button className="btn-primary" onClick={startExpansion} disabled={loading}>
              {loading ? '⏳ Starting...' : '🚀 Start Expansion'}
            </button>
          </div>
        )}

        {result && (
          <div className={`result ${result.success ? 'success' : 'error'}`}>
            {result.success ? (
              <>
                <div style={{fontWeight: 700, marginBottom: 8}}>✅ Job Started!</div>
                <div style={{fontSize: 12}}>
                  Job ID: <code>{result.data.job?.job_id}</code>
                </div>
                <div style={{fontSize: 11, marginTop: 8, color: 'var(--muted)'}}>
                  Check status in Jobs panel below
                </div>
              </>
            ) : (
              <>
                <div style={{fontWeight: 700, marginBottom: 8}}>❌ Error</div>
                <div style={{fontSize: 12}}>{result.error}</div>
              </>
            )}
          </div>
        )}
      </div>
    </div>
  )
}

