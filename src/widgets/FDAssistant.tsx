import { useEffect, useState } from 'react'

import { api } from '../lib/api'

type ExplanationResponse = {
  explanation: string
}

export default function FDAssistant({ defaultContext }: { defaultContext: string }) {
  const [context, setContext] = useState(defaultContext)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [text, setText] = useState<string | null>(null)

  useEffect(() => {
    setContext(defaultContext)
  }, [defaultContext])

  async function generate() {
    setError(null)
    setText(null)
    setLoading(true)
    try {
      const res = await api.post<ExplanationResponse>('/generate-explanation', { context })
      setText(res.data.explanation)
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Failed to generate explanation')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="card">
      <div className="page-header" style={{ marginBottom: 8 }}>
        <h2 className="section-title">FD Explanation Assistant</h2>
        <button className="btn" onClick={generate} disabled={loading}>
          {loading ? 'Generating…' : 'Generate'}
        </button>
      </div>

      <label className="field">
        <div className="label">Context</div>
        <textarea
          className="input"
          rows={6}
          value={context}
          onChange={(e) => setContext(e.target.value)}
          placeholder="Paste FD details or ask for an explanation"
        />
      </label>

      {error ? <div className="error">{error}</div> : null}
      {text ? (
        <div className="success" style={{ whiteSpace: 'pre-wrap' }}>
          {text}
        </div>
      ) : null}
    </div>
  )
}
