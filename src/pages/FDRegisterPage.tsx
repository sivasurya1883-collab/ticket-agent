import { useEffect, useMemo, useState } from 'react'

import { api } from '../lib/api'
import PrematureClosureModal from '../widgets/PrematureClosureModal'
import ReceiptButton from '../widgets/ReceiptButton'

type FD = {
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

type FDListResponse = {
  items: FD[]
}

export default function FDRegisterPage() {
  const [items, setItems] = useState<FD[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const [status, setStatus] = useState<string>('')
  const [customerName, setCustomerName] = useState('')
  const [startFrom, setStartFrom] = useState('')
  const [startTo, setStartTo] = useState('')

  const [closureFd, setClosureFd] = useState<FD | null>(null)

  const filteredCount = useMemo(() => items.length, [items])

  async function load() {
    setError(null)
    setLoading(true)
    try {
      const params: any = {}
      if (status) params.status = status
      if (customerName) params.customer_name = customerName
      if (startFrom) params.start_from = startFrom
      if (startTo) params.start_to = startTo

      const res = await api.get<FDListResponse>('/fds', { params })
      setItems(res.data.items)
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Failed to load FDs')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    load()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  return (
    <div>
      <div className="page-header">
        <h1 className="page-title">FD Register</h1>
        <div className="muted">{loading ? 'Loading…' : `${filteredCount} record(s)`}</div>
      </div>

      <div className="card filters">
        <div className="filters-row">
          <label className="field">
            <div className="label">Status</div>
            <select className="input" value={status} onChange={(e) => setStatus(e.target.value)}>
              <option value="">All</option>
              <option value="ACTIVE">ACTIVE</option>
              <option value="CLOSED">CLOSED</option>
            </select>
          </label>

          <label className="field">
            <div className="label">Customer</div>
            <input className="input" value={customerName} onChange={(e) => setCustomerName(e.target.value)} placeholder="Search by name" />
          </label>

          <label className="field">
            <div className="label">Start From</div>
            <input className="input" type="date" value={startFrom} onChange={(e) => setStartFrom(e.target.value)} />
          </label>

          <label className="field">
            <div className="label">Start To</div>
            <input className="input" type="date" value={startTo} onChange={(e) => setStartTo(e.target.value)} />
          </label>

          <div className="filters-actions">
            <button className="btn" onClick={load} disabled={loading}>
              Apply
            </button>
            <button
              className="btn"
              onClick={() => {
                setStatus('')
                setCustomerName('')
                setStartFrom('')
                setStartTo('')
                setTimeout(() => {
                  load()
                }, 0)
              }}
            >
              Reset
            </button>
          </div>
        </div>
      </div>

      {error ? <div className="error">{error}</div> : null}

      <div className="card table-wrap" style={{ marginTop: 12 }}>
        <table className="table">
          <thead>
            <tr>
              <th>FD Number</th>
              <th>Customer</th>
              <th>Start Date</th>
              <th>Tenure</th>
              <th>Rate</th>
              <th>Maturity Date</th>
              <th>Maturity Amount</th>
              <th>Status</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {items.map((fd) => (
              <tr key={fd.id}>
                <td>{fd.fd_number}</td>
                <td>{fd.customer_name}</td>
                <td>{fd.start_date}</td>
                <td>{fd.tenure_months}m</td>
                <td>{Number(fd.interest_rate).toFixed(2)}%</td>
                <td>{fd.maturity_date}</td>
                <td>{Number(fd.maturity_amount).toFixed(2)}</td>
                <td>
                  <span className={fd.status === 'ACTIVE' ? 'pill green' : 'pill'}>{fd.status}</span>
                </td>
                <td className="actions">
                  <ReceiptButton fd={fd} />
                  {fd.status === 'ACTIVE' ? (
                    <button className="btn" onClick={() => setClosureFd(fd)}>
                      Premature Closure
                    </button>
                  ) : null}
                </td>
              </tr>
            ))}

            {!loading && items.length === 0 ? (
              <tr>
                <td colSpan={9} className="empty">
                  No records
                </td>
              </tr>
            ) : null}
          </tbody>
        </table>
      </div>

      {closureFd ? (
        <PrematureClosureModal
          fd={closureFd}
          onClose={() => setClosureFd(null)}
          onConfirmed={() => {
            setClosureFd(null)
            load()
          }}
        />
      ) : null}
    </div>
  )
}
