import React, { useEffect, useState } from 'react'
import axios from 'axios'

export default function AddressProfile({ address }) {
  const [profile, setProfile] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let cancel = false
    setLoading(true)
    axios.get(`/api/address/${address}/profile`)
      .then(res => { if (!cancel) setProfile(res.data) })
      .finally(() => { if (!cancel) setLoading(false) })
    return () => { cancel = true }
  }, [address])

  if (loading) {
    return <div className="kv"><div className="k">Loading...</div><div className="v"></div></div>
  }
  if (!profile) {
    return <div className="kv"><div className="k">Error</div><div className="v">Unable to load profile.</div></div>
  }

  const f = profile.features || {}
  const s = profile.stats || {}

  return (
    <div className="kv">
      <div className="k">Address</div><div className="v" style={{fontFamily: 'monospace', fontSize: 12}}>{profile.address}</div>
      <div className="k">Risk Score</div><div className="v" style={{color: profile.risk_score > 70 ? 'var(--danger)' : profile.risk_score > 50 ? '#FFA94D' : 'var(--ok)', fontWeight: 700}}>{Math.round(profile.risk_score)}</div>
      <div className="k">Total In (ETH)</div><div className="v">{(s.total_in_eth ?? 0).toFixed(4)}</div>
      <div className="k">Total Out (ETH)</div><div className="v">{(s.total_out_eth ?? 0).toFixed(4)}</div>
      <div className="k">Fanin / Fanout</div><div className="v">{(s.fanin_addresses ?? 0)} / {(s.fanout_addresses ?? 0)}</div>
      <div className="k">PageRank</div><div className="v">{(f.pagerank ?? 0).toExponential(3)}</div>
      <div className="k">Degree</div><div className="v">{Math.round(f.degree ?? 0)}</div>
      <div className="k">In Degree / Out Degree</div><div className="v">{Math.round(f.inDegree ?? 0)} / {Math.round(f.outDegree ?? 0)}</div>
      <div className="k">Louvain Community</div><div className="v">{f.louvain ?? 0}</div>
      <div className="k">Triangles</div><div className="v">{Math.round(f.triangles ?? 0)}</div>
    </div>
  )
}
