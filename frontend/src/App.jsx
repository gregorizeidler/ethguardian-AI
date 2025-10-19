import React from 'react'
import { InvestigationProvider } from './contexts/InvestigationContext.jsx'
import DashboardView from './components/DashboardView.jsx'

export default function App() {
  return (
    <InvestigationProvider>
      <div className="app">
        <header className="header">
          <div style={{display:'flex', alignItems:'center', gap:16}}>
            <div className="badge">🛡️ EthGuardian AI</div>
            <div style={{color:'var(--muted)', fontSize: 13, fontWeight: 500}}>Protecting Ethereum, One Block at a Time</div>
          </div>
        </header>
        <DashboardView/>
      </div>
    </InvestigationProvider>
  )
}
