import React, { useEffect, useRef, useState } from 'react'
import axios from 'axios'
import { useInvestigation } from '../contexts/InvestigationContext.jsx'

// Importação dinâmica para evitar erro no top-level
let ForceGraph2D = null
import('react-force-graph').then(module => {
  ForceGraph2D = module.ForceGraph2D
}).catch(err => {
  console.error('Failed to load react-force-graph:', err)
})

export default function GraphVisualizer({ address }) {
  const [data, setData] = useState({ nodes: [], links: [] })
  const [loading, setLoading] = useState(true)
  const { setInvestigation } = useInvestigation()
  const fgRef = useRef()

  useEffect(() => {
    let cancel = false
    setLoading(true)
    setData({ nodes: [], links: [] })
    
    axios.get(`/api/address/${address}/graph?hops=2`)
      .then(res => {
        if (cancel) return
        setData(res.data)
        setLoading(false)
      })
      .catch(() => {
        setData({ nodes: [], links: [] })
        setLoading(false)
      })
    return () => { cancel = true }
  }, [address])

  const nodeRelSize = 6

  // Se não tiver dados, mostra placeholder
  if (loading) {
    return (
      <div style={{
        padding: 64, 
        textAlign: 'center', 
        color: 'var(--text)',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        height: '100%'
      }}>
        <div style={{
          fontSize: 64, 
          marginBottom: 24,
          animation: 'float 2s ease-in-out infinite'
        }}>🔄</div>
        <div style={{
          fontSize: 18,
          fontWeight: 700,
          background: 'linear-gradient(90deg, var(--accent), var(--cyan))',
          WebkitBackgroundClip: 'text',
          WebkitTextFillColor: 'transparent',
          backgroundClip: 'text'
        }}>Loading graph data...</div>
        <div style={{
          marginTop: 12,
          fontSize: 13,
          color: 'var(--muted)'
        }}>Building network visualization</div>
      </div>
    )
  }

  if (data.nodes.length === 0) {
    return (
      <div style={{
        padding: 64, 
        textAlign: 'center', 
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        height: '100%'
      }}>
        <div style={{fontSize: 64, marginBottom: 24}}>📊</div>
        <div style={{
          marginBottom: 16,
          fontSize: 18,
          fontWeight: 700,
          color: 'var(--text)'
        }}>No graph data available</div>
        <div style={{fontSize: 13, color: 'var(--muted)'}}>
          Run analysis first: <code style={{
            padding: '4px 8px',
            background: 'rgba(168, 85, 247, 0.2)',
            borderRadius: '4px',
            fontFamily: 'monospace'
          }}>POST /api/analyze/{'{address}'}</code>
        </div>
      </div>
    )
  }

  // Se ForceGraph2D não carregou ainda, mostra lista
  if (!ForceGraph2D) {
    return (
      <div style={{padding: 32}}>
        <div style={{textAlign: 'center', color: 'var(--muted)', marginBottom: 24}}>
          <div style={{fontSize: 48, marginBottom: 16}}>🕸️</div>
          <div style={{marginBottom: 12}}>Graph Library Loading...</div>
          <div style={{fontSize: 12}}>
            Nodes: {data.nodes.length} | Links: {data.links.length}
          </div>
        </div>
        <div style={{maxHeight: 400, overflow: 'auto', background: '#0d0f15', borderRadius: 8, padding: 16}}>
          <strong style={{fontSize: 14, marginBottom: 12, display: 'block'}}>Nodes:</strong>
          {data.nodes.map(n => (
            <div 
              key={n.id} 
              style={{
                padding: 8, 
                marginBottom: 8, 
                background: '#1a1d2e', 
                borderRadius: 6,
                cursor: 'pointer',
                fontSize: 12
              }}
              onClick={() => setInvestigation(n.id)}
            >
              <div style={{fontWeight: 600}}>{n.label || n.id}</div>
              <div style={{color: 'var(--muted)', fontSize: 11}}>
                Risk: {n.risk_score || 0}
              </div>
            </div>
          ))}
        </div>
      </div>
    )
  }

  return (
    <ForceGraph2D
      ref={fgRef}
      width={window.innerWidth - 360}
      height={window.innerHeight - 280}
      graphData={data}
      nodeId="id"
      linkSource="source"
      linkTarget="target"
      nodeRelSize={nodeRelSize}
      cooldownTicks={60}
      backgroundColor="transparent"
      linkColor={() => 'rgba(168, 85, 247, 0.3)'}
      linkWidth={2}
      linkDirectionalParticles={2}
      linkDirectionalParticleWidth={3}
      linkDirectionalParticleColor={() => 'rgba(6, 182, 212, 0.6)'}
      onNodeClick={(node) => {
        if (node?.id) setInvestigation(node.id)
      }}
      onNodeHover={(node) => {
        document.body.style.cursor = node ? 'pointer' : 'default'
      }}
      nodeCanvasObject={(node, ctx, globalScale) => {
        const label = node.label || node.id
        const size = nodeRelSize
        
        // cor baseada no risco com cores neon
        const risk = Number(node.risk_score || 0)
        let color, glowColor
        if (risk > 70) {
          color = '#f43f5e'
          glowColor = 'rgba(244, 63, 94, 0.6)'
        } else if (risk > 50) {
          color = '#FFA94D'
          glowColor = 'rgba(255, 169, 77, 0.6)'
        } else if (risk > 30) {
          color = '#06b6d4'
          glowColor = 'rgba(6, 182, 212, 0.6)'
        } else {
          color = '#10b981'
          glowColor = 'rgba(16, 185, 129, 0.6)'
        }
        
        // Draw glow effect
        ctx.shadowBlur = 15
        ctx.shadowColor = glowColor
        
        // Draw outer ring
        ctx.strokeStyle = color
        ctx.lineWidth = 2
        ctx.beginPath()
        ctx.arc(node.x, node.y, size + 2, 0, 2 * Math.PI, false)
        ctx.stroke()
        
        // Draw node
        ctx.fillStyle = color
        ctx.beginPath()
        ctx.arc(node.x, node.y, size, 0, 2 * Math.PI, false)
        ctx.fill()
        
        // Draw inner highlight
        const gradient = ctx.createRadialGradient(
          node.x - size / 3, 
          node.y - size / 3, 
          0, 
          node.x, 
          node.y, 
          size
        )
        gradient.addColorStop(0, 'rgba(255, 255, 255, 0.8)')
        gradient.addColorStop(1, 'rgba(255, 255, 255, 0)')
        ctx.fillStyle = gradient
        ctx.beginPath()
        ctx.arc(node.x, node.y, size, 0, 2 * Math.PI, false)
        ctx.fill()
        
        // Reset shadow
        ctx.shadowBlur = 0

        // Draw label with better styling
        const fontSize = 11 / globalScale
        ctx.font = `600 ${fontSize}px Inter, sans-serif`
        ctx.textAlign = 'center'
        ctx.textBaseline = 'top'
        
        // Label background
        const labelY = node.y + size + 4
        const textWidth = ctx.measureText(label).width
        ctx.fillStyle = 'rgba(10, 1, 24, 0.8)'
        ctx.fillRect(
          node.x - textWidth / 2 - 4,
          labelY - 2,
          textWidth + 8,
          fontSize + 4
        )
        
        // Label text
        ctx.fillStyle = '#f0f0ff'
        ctx.fillText(label, node.x, labelY)
      }}
    />
  )
}
