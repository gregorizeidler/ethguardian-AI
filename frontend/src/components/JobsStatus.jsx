import React, { useEffect, useState } from 'react'
import axios from 'axios'

export default function JobsStatus() {
  const [jobs, setJobs] = useState([])
  const [loading, setLoading] = useState(true)
  const [autoRefresh, setAutoRefresh] = useState(true)

  const fetchJobs = async () => {
    try {
      const res = await axios.get('/api/automation/jobs')
      setJobs(res.data.jobs || [])
    } catch (err) {
      console.error('Failed to fetch jobs:', err)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchJobs()
  }, [])

  useEffect(() => {
    if (!autoRefresh) return
    const interval = setInterval(fetchJobs, 5000) // Refresh every 5 seconds
    return () => clearInterval(interval)
  }, [autoRefresh])

  const getStatusIcon = (status) => {
    switch(status) {
      case 'started': return '⏳'
      case 'completed': return '✅'
      case 'failed': return '❌'
      default: return '❓'
    }
  }

  const getTypeIcon = (type) => {
    switch(type) {
      case 'crawler': return '🕷️'
      case 'monitor': return '📡'
      case 'expansion': return '🌳'
      default: return '🤖'
    }
  }

  if (loading) {
    return <div style={{padding: 16, color: 'var(--muted)'}}>Loading jobs...</div>
  }

  return (
    <div className="jobs-status">
      <div style={{display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12}}>
        <h4 style={{margin: 0}}>Active Jobs ({jobs.length})</h4>
        <label style={{fontSize: 12, display: 'flex', alignItems: 'center', gap: 6}}>
          <input 
            type="checkbox" 
            checked={autoRefresh}
            onChange={(e) => setAutoRefresh(e.target.checked)}
          />
          Auto-refresh
        </label>
      </div>

      {jobs.length === 0 ? (
        <div style={{padding: 16, textAlign: 'center', color: 'var(--muted)', fontSize: 12}}>
          No jobs running. Start one above!
        </div>
      ) : (
        <div className="jobs-list">
          {jobs.map(job => (
            <div key={job.job_id} className="job-item">
              <div style={{display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start'}}>
                <div>
                  <div style={{fontWeight: 700, marginBottom: 4}}>
                    {getTypeIcon(job.type)} {job.type.toUpperCase()}
                  </div>
                  <div style={{fontSize: 11, color: 'var(--muted)', fontFamily: 'monospace'}}>
                    {job.job_id}
                  </div>
                </div>
                <div className={`status-badge ${job.status}`}>
                  {getStatusIcon(job.status)} {job.status}
                </div>
              </div>

              {job.status === 'completed' && job.result && (
                <div style={{marginTop: 12, padding: 12, background: 'rgba(56, 211, 159, 0.1)', borderRadius: 6}}>
                  <div style={{fontSize: 12, fontWeight: 600, marginBottom: 6}}>Results:</div>
                  {job.result.stats && (
                    <div style={{fontSize: 11, lineHeight: 1.6}}>
                      {job.result.stats.addresses_analyzed && 
                        <div>📊 Analyzed: {job.result.stats.addresses_analyzed} addresses</div>
                      }
                      {job.result.stats.suspicious_found !== undefined && 
                        <div>🚨 Suspicious: {job.result.stats.suspicious_found}</div>
                      }
                      {job.result.stats.total_alerts !== undefined && 
                        <div>⚠️ Alerts: {job.result.stats.total_alerts}</div>
                      }
                    </div>
                  )}
                </div>
              )}

              {job.status === 'failed' && job.error && (
                <div style={{marginTop: 12, padding: 12, background: 'rgba(255, 93, 108, 0.1)', borderRadius: 6}}>
                  <div style={{fontSize: 11, color: 'var(--danger)'}}>
                    Error: {job.error}
                  </div>
                </div>
              )}

              <div style={{fontSize: 10, color: 'var(--muted)', marginTop: 8}}>
                Started: {new Date(job.started_at).toLocaleString()}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

