import { useEffect, useState } from 'react'

import { api } from '../lib/api'

type SettingsResponse = {
  id: string
  interest_type: 'SIMPLE' | 'COMPOUND'
  penalty_percent: number
  default_interest_rates?: Record<string, number>
}

const TENURES = [6, 12, 24, 36, 60]

export default function SettingsPage() {
  const [data, setData] = useState<SettingsResponse | null>(null)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [saved, setSaved] = useState<string | null>(null)

  useEffect(() => {
    api
      .get<SettingsResponse>('/settings')
      .then((res) => setData(res.data))
      .catch((err) => setError(err?.response?.data?.detail || 'Failed to load settings'))
  }, [])

  async function onSave() {
    if (!data) return
    setError(null)
    setSaved(null)
    setSaving(true)
    try {
      const res = await api.put<SettingsResponse>('/settings', {
        interest_type: data.interest_type,
        penalty_percent: Number(data.penalty_percent),
        default_interest_rates: data.default_interest_rates || {},
      })
      setData(res.data)
      setSaved('Saved')
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Failed to save')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div>
      <div className="page-header">
        <h1 className="page-title">Supervisor Settings</h1>
      </div>

      {error ? <div className="error">{error}</div> : null}
      {saved ? <div className="success">{saved}</div> : null}

      <div className="card" style={{ maxWidth: 520 }}>
        <label className="field">
          <div className="label">Interest Type</div>
          <select
            className="input"
            value={data?.interest_type || 'SIMPLE'}
            onChange={(e) => setData((prev) => (prev ? { ...prev, interest_type: e.target.value as any } : prev))}
          >
            <option value="SIMPLE">SIMPLE</option>
            <option value="COMPOUND">COMPOUND</option>
          </select>
        </label>

        <div className="field">
          <div className="label">Default Interest Rates by Tenure (% p.a.)</div>
          <div className="grid" style={{ gridTemplateColumns: '1fr 1fr', gap: 10 }}>
            {TENURES.map((m) => {
              const key = String(m)
              const value = data?.default_interest_rates?.[key] ?? ''
              return (
                <label key={key} className="field" style={{ margin: 0 }}>
                  <div className="label">{m} months</div>
                  <input
                    className="input"
                    type="number"
                    min={0}
                    max={20}
                    step="0.01"
                    value={value as any}
                    onChange={(e) =>
                      setData((prev) =>
                        prev
                          ? {
                              ...prev,
                              default_interest_rates: {
                                ...(prev.default_interest_rates || {}),
                                [key]: Number(e.target.value),
                              },
                            }
                          : prev,
                      )
                    }
                  />
                </label>
              )
            })}
          </div>
        </div>

        <label className="field">
          <div className="label">Penalty (%)</div>
          <input
            className="input"
            type="number"
            min={0}
            max={100}
            step="0.01"
            value={data?.penalty_percent ?? 1}
            onChange={(e) => setData((prev) => (prev ? { ...prev, penalty_percent: Number(e.target.value) } : prev))}
          />
        </label>

        <button className="btn primary" onClick={onSave} disabled={saving || !data}>
          {saving ? 'Saving…' : 'Save'}
        </button>
      </div>
    </div>
  )
}
