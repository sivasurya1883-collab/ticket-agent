import { useMemo, useState } from 'react'

import { api } from '../lib/api'

type CustomerAIProfileV2Response = {
  customer_id: string
  last_risk_score: number
  last_analysis_date: string
  loyalty_score: number
  penalty_reduction_percent: number
}

function pretty(ts: string) {
  const d = new Date(ts)
  return isNaN(d.getTime()) ? ts : d.toLocaleString()
}

export default function CustomerAIAnalysisPage() {
  const [customerId, setCustomerId] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [data, setData] = useState<CustomerAIProfileV2Response | null>(null)

  const canAnalyze = useMemo(() => customerId.trim().length > 2 && !loading, [customerId, loading])

  async function analyze() {
    const id = customerId.trim()
    if (!id) return

    setLoading(true)
    setError(null)
    setData(null)

    try {
      const res = await api.get<CustomerAIProfileV2Response>(`/customer-ai-profile-v2/${encodeURIComponent(id)}`)
      setData(res.data)
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Analysis failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div>
      <div className="page-head">
        <div>
          <div className="page-title">Customer AI Analysis</div>
          <div className="page-sub">Enter Customer ID to fetch stored analysis (V2).</div>
        </div>
      </div>

      <div className="card" style={{ marginTop: 12 }}>
        <div className="grid" style={{ gridTemplateColumns: '1.2fr 0.8fr', alignItems: 'end' }}>
          <div className="field">
            <label>Customer ID</label>
            <input
              className="input"
              placeholder="e.g. ABCDE1234F / Aadhaar / internal customer id"
              value={customerId}
              onChange={(e) => setCustomerId(e.target.value)}
            />
          </div>

          <div className="actions" style={{ justifyContent: 'flex-end' }}>
            <button className="btn" onClick={analyze} disabled={!canAnalyze}>
              {loading ? 'Analyzing…' : 'Analyze'}
            </button>
          </div>
        </div>

        {error ? (
          <div className="error" style={{ marginTop: 10 }}>
            {error}
          </div>
        ) : null}

        {data ? (
          <div style={{ marginTop: 12 }}>
            <div className="pill" style={{ marginBottom: 10 }}>
              Last analysis: {pretty(data.last_analysis_date)}
            </div>

            <div className="grid" style={{ gridTemplateColumns: '1fr 1fr 1fr' }}>
              <div className="card" style={{ background: 'rgba(255,255,255,0.65)' }}>
                <div style={{ fontWeight: 800, marginBottom: 6 }}>Risk Score</div>
                <div className="muted">Last risk score</div>
                <div style={{ fontWeight: 900, fontSize: 22, marginTop: 8 }}>{data.last_risk_score}/100</div>
              </div>

              <div className="card" style={{ background: 'rgba(255,255,255,0.65)' }}>
                <div style={{ fontWeight: 800, marginBottom: 6 }}>Loyalty Score</div>
                <div className="muted">Customer loyalty</div>
                <div style={{ fontWeight: 900, fontSize: 22, marginTop: 8 }}>{data.loyalty_score}/100</div>
              </div>

              <div className="card" style={{ background: 'rgba(255,255,255,0.65)' }}>
                <div style={{ fontWeight: 800, marginBottom: 6 }}>Penalty Reduction</div>
                <div className="muted">Eligible reduction</div>
                <div style={{ fontWeight: 900, fontSize: 22, marginTop: 8 }}>{Number(data.penalty_reduction_percent || 0).toFixed(2)}%</div>
              </div>
            </div>
          </div>
        ) : null}

        {!loading && !data ? <div className="empty">Enter a Customer ID and click Analyze.</div> : null}
      </div>
    </div>
  )
}
