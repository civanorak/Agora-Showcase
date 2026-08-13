import { useState } from 'react'
import type { LeadSummary } from '../types'
import { API } from '../api'

const TOKEN_STORAGE_KEY = 'agora_admin_token'

function coverageColor(pct: number | null): string {
  if (pct === null) return '#71717a'
  return pct >= 70 ? '#166534' : pct >= 30 ? '#b45309' : '#b91c1c'
}

export function Admin() {
  const [token, setToken] = useState(() => localStorage.getItem(TOKEN_STORAGE_KEY) ?? '')
  const [leads, setLeads] = useState<LeadSummary[] | null>(null)
  const [status, setStatus] = useState<'idle' | 'loading' | 'error'>('idle')
  const [error, setError] = useState<string | null>(null)

  const loadLeads = () => {
    setStatus('loading')
    setError(null)
    fetch(`${API}/leads`, { headers: { Authorization: `Bearer ${token}` } })
      .then(r => {
        if (!r.ok) throw new Error(r.status === 403 ? 'Wrong admin token' : `Request failed (${r.status})`)
        return r.json()
      })
      .then((d: LeadSummary[]) => {
        localStorage.setItem(TOKEN_STORAGE_KEY, token)
        setLeads(d)
        setStatus('idle')
      })
      .catch(e => {
        setError(e.message || 'Failed to load leads')
        setStatus('idle')
      })
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '28px' }}>
      <div>
        <h1 style={{ fontSize: '20px', fontWeight: 700, color: '#09090b', margin: 0, letterSpacing: '-0.02em' }}>
          Leads
        </h1>
        <p style={{ fontSize: '13px', color: '#71717a', margin: '5px 0 0', lineHeight: 1.5 }}>
          Merchants who submitted an audit and left their email, sorted by worst agent-coverage gap first.
        </p>
      </div>

      <div style={{ background: '#fff', border: '1px solid #e4e4e7', borderRadius: '8px', padding: '20px 24px' }}>
        <div style={{ display: 'flex', gap: '12px', alignItems: 'center' }}>
          <input
            type="password"
            value={token}
            onChange={(e) => setToken(e.target.value)}
            placeholder="Admin token"
            style={{
              flex: 1, padding: '10px 14px', borderRadius: '6px', border: '1px solid #e4e4e7', fontSize: '13px',
              fontFamily: 'ui-monospace, monospace',
            }}
          />
          <button
            className="vbtn"
            onClick={loadLeads}
            disabled={status === 'loading' || !token.trim()}
            style={{
              padding: '10px 20px', borderRadius: '6px', fontSize: '13px', fontWeight: 600,
              background: '#09090b', color: '#fff', border: 'none', cursor: 'pointer',
              minWidth: '110px', textAlign: 'center',
            }}
          >
            {status === 'loading' ? 'Loading…' : 'Load leads'}
          </button>
        </div>
      </div>

      {error && (
        <div style={{ background: '#fef2f2', border: '1px solid #fecaca', color: '#b91c1c', padding: '14px 18px', borderRadius: '8px', fontSize: '13px' }}>
          <strong>Error:</strong> {error}
        </div>
      )}

      {leads && (
        <div style={{ background: '#fff', border: '1px solid #e4e4e7', borderRadius: '8px', overflow: 'hidden' }}>
          {leads.length === 0 ? (
            <div style={{ padding: '24px', fontSize: '13px', color: '#71717a' }}>No leads captured yet.</div>
          ) : (
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '12.5px' }}>
              <thead>
                <tr style={{ background: '#fafafa', borderBottom: '1px solid #e4e4e7' }}>
                  <th style={{ textAlign: 'left', padding: '10px 16px', color: '#71717a', fontWeight: 600 }}>Email</th>
                  <th style={{ textAlign: 'left', padding: '10px 16px', color: '#71717a', fontWeight: 600 }}>URL</th>
                  <th style={{ textAlign: 'right', padding: '10px 16px', color: '#71717a', fontWeight: 600 }}>Coverage</th>
                  <th style={{ textAlign: 'left', padding: '10px 16px', color: '#71717a', fontWeight: 600 }}>Captured</th>
                </tr>
              </thead>
              <tbody>
                {leads.map(lead => (
                  <tr key={lead.id} style={{ borderBottom: '1px solid #f4f4f5' }}>
                    <td style={{ padding: '10px 16px', color: '#09090b', fontWeight: 600 }}>{lead.email}</td>
                    <td style={{ padding: '10px 16px', color: '#52525b', fontFamily: 'ui-monospace, monospace' }}>{lead.url ?? '—'}</td>
                    <td style={{ padding: '10px 16px', textAlign: 'right', color: coverageColor(lead.coverage_pct), fontWeight: 700 }}>
                      {lead.coverage_pct !== null ? `${lead.coverage_pct}%` : '—'}
                    </td>
                    <td style={{ padding: '10px 16px', color: '#a1a1aa' }}>{lead.created_at}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}
    </div>
  )
}
