import { jsPDF } from 'jspdf'

import { useAuth } from '../auth/AuthContext'

type FD = {
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
}

export default function ReceiptButton({ fd }: { fd: FD }) {
  const { user } = useAuth()

  function generate() {
    const doc = new jsPDF()

    doc.setFontSize(16)
    doc.text('Fixed Deposit Opening Receipt', 14, 16)

    doc.setFontSize(11)

    const lines: Array<[string, string]> = [
      ['FD Number', fd.fd_number],
      ['Customer Name', fd.customer_name],
      ['ID Type', fd.id_type],
      ['ID Number', fd.id_number],
      ['Deposit Amount', Number(fd.deposit_amount).toFixed(2)],
      ['Interest Rate (%)', Number(fd.interest_rate).toFixed(2)],
      ['Tenure (months)', String(fd.tenure_months)],
      ['Start Date', fd.start_date],
      ['Maturity Date', fd.maturity_date],
      ['Maturity Amount', Number(fd.maturity_amount).toFixed(2)],
      ['Officer', user?.email || '-'],
    ]

    let y = 28
    for (const [k, v] of lines) {
      doc.text(`${k}:`, 14, y)
      doc.text(String(v), 70, y)
      y += 7
    }

    y += 8
    doc.text('Signature: ____________________________', 14, y)

    doc.save(`${fd.fd_number}-receipt.pdf`)
  }

  return (
    <button className="btn" onClick={generate}>
      PDF Receipt
    </button>
  )
}
