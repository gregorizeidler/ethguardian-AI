import React from 'react'
import { useInvestigation } from '../contexts/InvestigationContext.jsx'
import GraphVisualizer from './GraphVisualizer.jsx'
import AddressProfile from './AddressProfile.jsx'
import ErrorBoundary from './ErrorBoundary.jsx'

export default function InvestigationView() {
  const { currentInvestigation } = useInvestigation()

  if (!currentInvestigation?.address) {
    return (
      <div className="placeholder">
        <div>
          <div style={{textAlign:'center', marginBottom:12, fontSize:20, fontWeight: 600}}>Select an alert to start investigation</div>
          <div style={{textAlign:'center', color:'var(--muted)', fontSize: 14}}>Or call <code style={{padding: '2px 6px', background: 'rgba(168, 85, 247, 0.2)', borderRadius: '4px'}}>POST /api/ingest/&lt;address&gt;</code> then <code style={{padding: '2px 6px', background: 'rgba(168, 85, 247, 0.2)', borderRadius: '4px'}}>POST /api/analyze/&lt;address&gt;</code></div>
        </div>
      </div>
    )
  }

  const { address } = currentInvestigation
  return (
    <>
      <section className="panel" style={{borderBottom:'2px solid var(--border)', borderRadius: 0, margin: 0}}>
        <h3>🔍 Address Profile</h3>
        <AddressProfile address={address} />
      </section>
      <section className="graph-container">
        <ErrorBoundary>
          <GraphVisualizer address={address} />
        </ErrorBoundary>
      </section>
    </>
  )
}
