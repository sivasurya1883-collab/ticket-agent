import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'

import { api } from '../lib/api'

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

type FDListResponse = {
  items: FD[]
}

function toDate(s: string) {
  const d = new Date(s)
  return isNaN(d.getTime()) ? null : d
}

export default function DashboardPage() {
  const [items, setItems] = useState<FD[]>([])
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let mounted = true
    api
      .get<FDListResponse>('/fds')
      .then((res) => {
        if (mounted) setItems(res.data.items)
      })
      .catch((err) => {
        if (mounted) setError(err?.response?.data?.detail || 'Failed to load dashboard')
      })
    return () => {
      mounted = false
    }
  }, [])

  const active = items.filter((x) => x.status === 'ACTIVE')
  const closed = items.filter((x) => x.status === 'CLOSED')
  const totalDepositActive = active.reduce((sum, x) => sum + Number(x.deposit_amount || 0), 0)
  const totalMaturityActive = active.reduce((sum, x) => sum + Number(x.maturity_amount || 0), 0)
  const avgRateActive = active.length ? active.reduce((sum, x) => sum + Number(x.interest_rate || 0), 0) / active.length : 0

  const now = new Date()
  const in30 = new Date(now)
  in30.setDate(in30.getDate() + 30)
  const upcoming = active
    .map((x) => ({ fd: x, m: toDate(x.maturity_date) }))
    .filter((x) => x.m && x.m >= now && x.m <= in30)
    .sort((a, b) => (a.m!.getTime() > b.m!.getTime() ? 1 : -1))
    .slice(0, 5)

  const recent = [...items]
    .sort((a, b) => (a.start_date < b.start_date ? 1 : -1))
    .slice(0, 6)

  return (
    <div>
      <div className="page-header">
        <h1 className="page-title">Dashboard</h1>
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
          <Link className="btn primary" to="/fds/new">
            + New FD
          </Link>
          <Link className="btn" to="/fds">
            View Register
          </Link>
        </div>
      </div>

      {error ? <div className="error">{error}</div> : null}

      <div className="grid-3">
        <div className="card stat">
          <div className="stat-label">Active FDs</div>
          <div className="stat-value">{active.length}</div>
        </div>
        <div className="card stat">
          <div className="stat-label">Active Deposit Total</div>
          <div className="stat-value">{totalDepositActive.toFixed(2)}</div>
        </div>
        <div className="card stat">
          <div className="stat-label">Active Maturity Total</div>
          <div className="stat-value">{totalMaturityActive.toFixed(2)}</div>
        </div>
      </div>

      <div className="grid-2" style={{ marginTop: 12 }}>
        <div className="card">
          <div className="page-header" style={{ marginBottom: 8 }}>
            <h2 className="section-title">Portfolio Overview</h2>
            <div className="muted">Quick breakdown</div>
          </div>

          <div className="kv">
            <div className="k">Closed FDs</div>
            <div className="v">{closed.length}</div>
          </div>
          <div className="kv">
            <div className="k">Average Interest Rate (Active)</div>
            <div className="v">{avgRateActive.toFixed(2)}%</div>
          </div>
          <div className="kv">
            <div className="k">Active Interest (Total)</div>
            <div className="v">{Math.max(0, totalMaturityActive - totalDepositActive).toFixed(2)}</div>
          </div>
        </div>

        <div className="card">
          <div className="page-header" style={{ marginBottom: 8 }}>
            <h2 className="section-title">Upcoming Maturities (30 days)</h2>
            <div className="muted">Top 5</div>
          </div>

          {upcoming.length === 0 ? <div className="muted">No upcoming maturities in next 30 days.</div> : null}

          {upcoming.map(({ fd }) => (
            <div key={fd.id} className="kv">
              <div className="k">{fd.fd_number}</div>
              <div className="v">
                {fd.maturity_date} · {Number(fd.maturity_amount).toFixed(2)}
              </div>
            </div>
          ))}
        </div>
      </div>

      <div className="card table-wrap" style={{ marginTop: 12 }}>
        <div className="page-header" style={{ padding: '12px 12px 0 12px', marginBottom: 0 }}>
          <h2 className="section-title">Recent FDs</h2>
          <div className="muted">Latest {recent.length}</div>
        </div>

        <table className="table">
          <thead>
            <tr>
              <th>FD Number</th>
              <th>Customer</th>
              <th>Start</th>
              <th>Maturity</th>
              <th>Maturity Amount</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            {recent.map((fd) => (
              <tr key={fd.id}>
                <td>{fd.fd_number}</td>
                <td>{fd.customer_name}</td>
                <td>{fd.start_date}</td>
                <td>{fd.maturity_date}</td>
                <td>{Number(fd.maturity_amount).toFixed(2)}</td>
                <td>
                  <span className={fd.status === 'ACTIVE' ? 'pill green' : 'pill'}>{fd.status}</span>
                </td>
              </tr>
            ))}
            {recent.length === 0 ? (
              <tr>
                <td colSpan={6} className="empty">
                  No records
                </td>
              </tr>
            ) : null}
          </tbody>
        </table>
      </div>
    </div>
  )
}
