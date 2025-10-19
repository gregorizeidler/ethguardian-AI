import { useState } from 'react'
import AlertQueue from './AlertQueue.jsx'
import InvestigationView from './InvestigationView.jsx'
import AutomationPanel from './AutomationPanel.jsx'
import JobsStatus from './JobsStatus.jsx'
import Dashboard from './AdvancedDashboard.jsx'
import PatternDetection from './PatternDetection.jsx'
import FraudDetection from './FraudDetection.jsx'
import { useInvestigation } from '../contexts/InvestigationContext'

export default function DashboardView() {
  const [activeView, setActiveView] = useState('investigation')
  const { currentInvestigation } = useInvestigation()
  
  const address = currentInvestigation?.address

  return (
    <>
      <aside className="sidebar">
        <div className="panel">
          <h3>🤖 Automation</h3>
          <AutomationPanel />
        </div>
        <div className="panel" style={{marginTop: 16}}>
          <h3>📊 Jobs</h3>
          <JobsStatus />
        </div>
        <div className="panel" style={{marginTop: 16}}>
          <h3>🚨 Alerts</h3>
          <AlertQueue />
        </div>
      </aside>
      <main className="main">
        {/* View Tabs */}
        <div style={{display: 'flex', gap: 8, marginBottom: 24, borderBottom: '2px solid var(--border)', paddingBottom: 12}}>
          <button 
            className="tab"
            onClick={() => setActiveView('investigation')}
            style={{
              background: activeView === 'investigation' ? 'linear-gradient(135deg, var(--accent), var(--cyan))' : 'transparent',
              color: activeView === 'investigation' ? 'white' : 'var(--text)'
            }}
          >
            🔍 Investigation
          </button>
          <button 
            className="tab"
            onClick={() => setActiveView('dashboard')}
            style={{
              background: activeView === 'dashboard' ? 'linear-gradient(135deg, var(--accent), var(--cyan))' : 'transparent',
              color: activeView === 'dashboard' ? 'white' : 'var(--text)'
            }}
          >
            📊 Dashboard
          </button>
          <button 
            className="tab"
            onClick={() => setActiveView('patterns')}
            style={{
              background: activeView === 'patterns' ? 'linear-gradient(135deg, var(--accent), var(--cyan))' : 'transparent',
              color: activeView === 'patterns' ? 'white' : 'var(--text)'
            }}
          >
            🎯 Patterns
          </button>
          <button 
            className="tab"
            onClick={() => setActiveView('fraud')}
            style={{
              background: activeView === 'fraud' ? 'linear-gradient(135deg, var(--accent), var(--cyan))' : 'transparent',
              color: activeView === 'fraud' ? 'white' : 'var(--text)'
            }}
          >
            🚨 Fraud
          </button>
        </div>

        {/* Content */}
        {activeView === 'investigation' && <InvestigationView />}
        {activeView === 'dashboard' && <Dashboard />}
        {activeView === 'patterns' && <PatternDetection address={address} />}
        {activeView === 'fraud' && <FraudDetection address={address} />}
      </main>
    </>
  )
}
