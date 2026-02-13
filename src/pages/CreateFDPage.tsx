import { useEffect, useMemo, useState } from 'react'

import { api } from '../lib/api'
import FDAssistant from '../widgets/FDAssistant'

type SettingsResponse = {
  id: string
  interest_type: 'SIMPLE' | 'COMPOUND'
  penalty_percent: number
  default_interest_rates?: Record<string, number>
}

type CompetitorBankCard = {
  bank: string
  fd_rate_detected?: string | null
  source_url?: string | null
  status: string
  features?: string[]
  min_tenure_months?: number | null
  max_tenure_years?: number | null
  premature_penalty_percent?: number | null
  senior_citizen_extra?: number | null
  security?: string | null
}

type FDCompetitorComparisonResponse = {
  our_bank: any
  competitors: CompetitorBankCard[]
  why_choose_our_bank: string[]
  best_fit_customers: string[]
  officer_pitch: string
}

type FDCreateRequest = {
  customer_name: string
  id_type: string
  id_number: string
  deposit_amount: number
  interest_rate: number
  tenure_months: number
  start_date: string
}

type FDResponse = {
  id: string
  fd_number: string
  customer_name: string
  id_type: string
  id_number: string
  deposit_amount: number
  interest_rate: number
  tenure_months: number
  start_date: string
  maturity_date: string
  maturity_amount: number
  status: 'ACTIVE' | 'CLOSED'
  created_by?: string
  created_at?: string
}

function addMonths(start: Date, months: number) {
  const d = new Date(start)
  const day = d.getDate()
  d.setMonth(d.getMonth() + months)
  if (d.getDate() !== day) {
    d.setDate(0)
  }
  return d
}

function calcMaturity(principal: number, ratePct: number, tenureMonths: number, interestType: 'SIMPLE' | 'COMPOUND') {
  const years = tenureMonths / 12
  const r = ratePct / 100
  if (interestType === 'SIMPLE') {
    return principal * (1 + r * years)
  }
  return principal * Math.pow(1 + r, years)
}

export default function CreateFDPage() {
  const [settings, setSettings] = useState<SettingsResponse | null>(null)
  const [form, setForm] = useState({
    customer_name: '',
    id_type: 'PAN',
    id_number: '',
    deposit_amount: 0,
    interest_rate: 7,
    tenure_months: 12,
    start_date: new Date().toISOString().slice(0, 10),
  })
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [created, setCreated] = useState<FDResponse | null>(null)

  const [cmpLoading, setCmpLoading] = useState(false)
  const [cmpError, setCmpError] = useState<string | null>(null)
  const [cmpData, setCmpData] = useState<FDCompetitorComparisonResponse | null>(null)

  async function runCompetitorComparison() {
    setCmpError(null)
    setCmpData(null)
    setCmpLoading(true)
    try {
      const res = await api.post<FDCompetitorComparisonResponse>('/fd-competitor-comparison', {
        deposit_amount: Number(form.deposit_amount),
        interest_rate: Number(form.interest_rate),
        tenure_months: Number(form.tenure_months),
      })
      setCmpData(res.data)
    } catch (err: any) {
      setCmpError(err?.response?.data?.detail || 'Failed to generate comparison')
    } finally {
      setCmpLoading(false)
    }
  }

  useEffect(() => {
    api
      .get<SettingsResponse>('/settings')
      .then((res) => setSettings(res.data))
      .catch(() => setSettings(null))
  }, [])

  const defaultRate = useMemo(() => {
    const rates = settings?.default_interest_rates
    if (!rates) return null

    const exact = rates[String(form.tenure_months)]
    if (typeof exact === 'number' && !Number.isNaN(exact)) return exact

    const parsed = Object.entries(rates)
      .map(([k, v]) => ({ months: Number(k), rate: Number(v) }))
      .filter((x) => Number.isFinite(x.months) && Number.isFinite(x.rate))
      .sort((a, b) => Math.abs(a.months - Number(form.tenure_months)) - Math.abs(b.months - Number(form.tenure_months)))

    return parsed.length ? parsed[0].rate : null
  }, [settings, form.tenure_months])

  useEffect(() => {
    if (defaultRate == null) return
    setForm((prev) => ({ ...prev, interest_rate: Number(defaultRate) }))
  }, [defaultRate])

  const preview = useMemo(() => {
    const sDate = new Date(form.start_date)
    const mDate = addMonths(sDate, Number(form.tenure_months))
    const it = settings?.interest_type || 'SIMPLE'
    const maturity = calcMaturity(Number(form.deposit_amount), Number(form.interest_rate), Number(form.tenure_months), it)
    return {
      maturityDate: mDate.toISOString().slice(0, 10),
      maturityAmount: maturity,
      interestType: it,
    }
  }, [form, settings])

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError(null)
    setCreated(null)

    if (Number(form.deposit_amount) <= 0) return setError('Deposit amount must be > 0')
    if (Number(form.interest_rate) < 0 || Number(form.interest_rate) > 20) return setError('Interest rate must be between 0 and 20')
    if (Number(form.tenure_months) <= 0) return setError('Tenure must be > 0')

    setLoading(true)
    try {
      const payload: FDCreateRequest = {
        ...form,
        deposit_amount: Number(form.deposit_amount),
        interest_rate: Number(form.interest_rate),
        tenure_months: Number(form.tenure_months),
      }
      const res = await api.post<FDResponse>('/create-fd', payload)
      setCreated(res.data)
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Failed to create FD')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div>
      <div className="page-header">
        <h1 className="page-title">Create FD</h1>
        <div className="muted">Interest type: {preview.interestType}</div>
      </div>

      <div className="grid-2">
        <form className="card" onSubmit={onSubmit}>
          <div className="form-grid">
            <label className="field">
              <div className="label">Customer Name</div>
              <input className="input" value={form.customer_name} onChange={(e) => setForm({ ...form, customer_name: e.target.value })} required />
            </label>

            <label className="field">
              <div className="label">ID Type</div>
              <input className="input" value={form.id_type} onChange={(e) => setForm({ ...form, id_type: e.target.value })} required />
            </label>

            <label className="field">
              <div className="label">ID Number</div>
              <input className="input" value={form.id_number} onChange={(e) => setForm({ ...form, id_number: e.target.value })} required />
            </label>

            <label className="field">
              <div className="label">Deposit Amount</div>
              <input className="input" type="number" value={form.deposit_amount} onChange={(e) => setForm({ ...form, deposit_amount: Number(e.target.value) })} min={0} step="0.01" required />
            </label>

            <label className="field">
              <div className="label">Interest Rate (%)</div>
              <input className="input" disabled type="number" value={form.interest_rate} onChange={(e) => setForm({ ...form, interest_rate: Number(e.target.value) })} min={0} max={20} step="0.01" required />
              {defaultRate != null ? <div className="muted" style={{ marginTop: 6 }}>Default for {form.tenure_months} months: {Number(defaultRate).toFixed(2)}%</div> : null}
            </label>

            <label className="field">
              <div className="label">Tenure (months)</div>
              <input className="input" type="number" value={form.tenure_months} onChange={(e) => setForm({ ...form, tenure_months: Number(e.target.value) })} min={1} step="1" required />
            </label>

            <label className="field">
              <div className="label">Start Date</div>
              <input className="input" type="date" value={form.start_date} onChange={(e) => setForm({ ...form, start_date: e.target.value })} required />
            </label>
          </div>

          {error ? <div className="error">{error}</div> : null}

          <button className="btn primary" type="submit" disabled={loading}>
            {loading ? 'Creating…' : 'Create FD'}
          </button>
        </form>

        <div className="card">
          <h2 className="section-title">Auto-calculation preview</h2>
          <div className="kv">
            <div className="k">Maturity Date</div>
            <div className="v">{preview.maturityDate}</div>
          </div>
          <div className="kv">
            <div className="k">Maturity Amount</div>
            <div className="v">{preview.maturityAmount.toFixed(2)}</div>
          </div>

          {created ? (
            <div className="success-box">
              <div className="success-title">FD created</div>
              <div className="kv">
                <div className="k">FD Number</div>
                <div className="v">{created.fd_number}</div>
              </div>
              <div className="kv">
                <div className="k">Maturity Amount</div>
                <div className="v">{created.maturity_amount.toFixed(2)}</div>
              </div>
            </div>
          ) : null}
        </div>

        <FDAssistant
          defaultContext={`FD Opening Details\nCustomer: ${form.customer_name}\nDeposit: ${Number(form.deposit_amount).toFixed(2)}\nRate: ${Number(form.interest_rate).toFixed(2)}%\nTenure: ${form.tenure_months} months\nStart: ${form.start_date}\nMaturity Date: ${preview.maturityDate}\nMaturity Amount: ${preview.maturityAmount.toFixed(2)}\nExplain the calculation in customer-friendly terms.`}
        />

        <div className="card">
          <div className="page-header" style={{ padding: 0, marginBottom: 10 }}>
            <h2 className="section-title" style={{ margin: 0 }}>Competitor Comparison</h2>
            <div className="muted">Compare other banks' FD features and rate signals vs our offer</div>
          </div>

          {cmpError ? <div className="error">{cmpError}</div> : null}

          <button className="btn" type="button" onClick={runCompetitorComparison} disabled={cmpLoading || Number(form.deposit_amount) <= 0}>
            {cmpLoading ? 'Analyzing…' : 'Run Comparison'}
          </button>

          {!cmpLoading && !cmpError && !cmpData ? <div className="muted" style={{ marginTop: 10 }}>No comparison run yet.</div> : null}

          {cmpData ? (
            <div style={{ marginTop: 14 }}>
              <div className="grid" style={{ gridTemplateColumns: 'repeat(2, minmax(0, 1fr))', gap: 12 }}>
                {cmpData.competitors.map((b) => (
                  <div key={b.bank} className="card" style={{ margin: 0 }}>
                    <div className="section-title" style={{ marginBottom: 6 }}>{b.bank}</div>
                    <div className="kv">
                      <div className="k">Rate detected</div>
                      <div className="v">{b.fd_rate_detected || '—'}</div>
                    </div>
                    <div className="kv">
                      <div className="k">Status</div>
                      <div className="v">{b.status}</div>
                    </div>
                    {b.security ? (
                      <div className="kv">
                        <div className="k">Security</div>
                        <div className="v">{b.security}</div>
                      </div>
                    ) : null}
                    {b.features?.length ? (
                      <div style={{ marginTop: 8 }}>
                        <div className="muted" style={{ marginBottom: 6 }}>Features</div>
                        <div className="pill-row">
                          {b.features.slice(0, 6).map((f) => (
                            <span className="pill" key={f}>{f}</span>
                          ))}
                        </div>
                      </div>
                    ) : null}
                    {b.source_url ? (
                      <div style={{ marginTop: 10 }}>
                        <a className="muted" href={b.source_url} target="_blank" rel="noreferrer">
                          Source
                        </a>
                      </div>
                    ) : null}
                  </div>
                ))}

                <div className="card" style={{ margin: 0 }}>
                  <div className="section-title" style={{ marginBottom: 6 }}>Why choose our bank</div>
                  {cmpData.why_choose_our_bank?.length ? (
                    <div style={{ display: 'grid', gap: 8 }}>
                      {cmpData.why_choose_our_bank.map((t, idx) => (
                        <div key={idx} className="muted">- {t}</div>
                      ))}
                    </div>
                  ) : (
                    <div className="muted">—</div>
                  )}
                </div>

                <div className="card" style={{ margin: 0 }}>
                  <div className="section-title" style={{ marginBottom: 6 }}>Officer pitch</div>
                  <div className="muted">{cmpData.officer_pitch || '—'}</div>
                  {cmpData.best_fit_customers?.length ? (
                    <div style={{ marginTop: 10 }}>
                      <div className="muted" style={{ marginBottom: 6 }}>Best fit customers</div>
                      <div style={{ display: 'grid', gap: 8 }}>
                        {cmpData.best_fit_customers.map((t, idx) => (
                          <div key={idx} className="muted">- {t}</div>
                        ))}
                      </div>
                    </div>
                  ) : null}
                </div>
              </div>
            </div>
          ) : null}
        </div>
      </div>
    </div>
  )
}
