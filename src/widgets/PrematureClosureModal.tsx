import { useEffect, useMemo, useState } from 'react'

import { api } from '../lib/api'
import FDAssistant from './FDAssistant'

type FD = {
  id: string
  fd_number: string
  customer_name: string
  deposit_amount: number
  interest_rate: number
  tenure_months: number
  start_date: string
  maturity_date: string
  maturity_amount: number
  status: 'ACTIVE' | 'CLOSED'
}

type SimResponse = {
  accrued_interest: number
  penalty: number
  penalty_percent_used: number
  net_interest: number
  payable_amount: number
  elapsed_years: number
}

export default function PrematureClosureModal({
  fd,
  onClose,
  onConfirmed,
}: {
  fd: FD
  onClose: () => void
  onConfirmed: () => void
}) {
  const [closureDate, setClosureDate] = useState(() => new Date().toISOString().slice(0, 10))
  const [sim, setSim] = useState<SimResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [confirming, setConfirming] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const canSimulate = useMemo(() => Boolean(closureDate), [closureDate])

  async function simulate() {
    if (!canSimulate) return
    setError(null)
    setLoading(true)
    try {
      const res = await api.post<SimResponse>(`/simulate-closure/${fd.id}`, { closure_date: closureDate })
      setSim(res.data)
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Simulation failed')
      setSim(null)
    } finally {
      setLoading(false)
    }
  }

  async function confirm() {
    setError(null)
    setConfirming(true)
    try {
      await api.post(`/confirm-closure/${fd.id}`, { closure_date: closureDate })
      onConfirmed()
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Confirm failed')
    } finally {
      setConfirming(false)
    }
  }

  useEffect(() => {
    simulate()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  return (
    <div className="modal-backdrop" role="dialog" aria-modal="true">
      <div className="modal">
        <div className="modal-header">
          <div>
            <div className="modal-title">Premature Closure</div>
            <div className="muted">
              {fd.fd_number} · {fd.customer_name}
            </div>
          </div>
          <button className="btn" onClick={onClose}>
            Close
          </button>
        </div>

        <div className="modal-body">
          <label className="field">
            <div className="label">Closure Date</div>
            <input className="input" type="date" value={closureDate} onChange={(e) => setClosureDate(e.target.value)} />
          </label>

          <button className="btn" onClick={simulate} disabled={loading}>
            {loading ? 'Calculating…' : 'Simulate'}
          </button>

          {error ? <div className="error" style={{ marginTop: 12 }}>
            {error}
          </div> : null}

          {sim ? (
            <div className="sim-grid">
              <div className="kv">
                <div className="k">Accrued Interest</div>
                <div className="v">{sim.accrued_interest.toFixed(2)}</div>
              </div>
              <div className="kv">
                <div className="k">Penalty ({Number(sim.penalty_percent_used).toFixed(2)}%)</div>
                <div className="v">{sim.penalty.toFixed(2)}</div>
              </div>
              <div className="kv">
                <div className="k">Net Interest</div>
                <div className="v">{sim.net_interest.toFixed(2)}</div>
              </div>
              <div className="kv">
                <div className="k">Payable Amount</div>
                <div className="v">{sim.payable_amount.toFixed(2)}</div>
              </div>
            </div>
          ) : null}

          {sim ? (
            <FDAssistant
              defaultContext={`Premature Closure Summary\nFD: ${fd.fd_number}\nCustomer: ${fd.customer_name}\nClosure Date: ${closureDate}\nElapsed Years: ${sim.elapsed_years.toFixed(4)}\nAccrued Interest: ${sim.accrued_interest.toFixed(2)}\nPenalty: ${sim.penalty.toFixed(2)}\nNet Interest: ${sim.net_interest.toFixed(2)}\nPayable Amount: ${sim.payable_amount.toFixed(2)}\nExplain the impact to the customer in simple terms.`}
            />
          ) : null}
        </div>

        <div className="modal-footer">
          <button className="btn" onClick={onClose}>
            Cancel
          </button>
          <button className="btn primary" onClick={confirm} disabled={!sim || confirming}>
            {confirming ? 'Confirming…' : 'Confirm Closure'}
          </button>
        </div>
      </div>
    </div>
  )
}
