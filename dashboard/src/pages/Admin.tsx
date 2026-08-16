import { useState } from 'react'
import type { LeadSummary } from '../types'
import { API } from '../api'
import { useI18n } from '../i18n'

const TOKEN_STORAGE_KEY = 'agora_admin_token'

function coverageColor(pct: number | null): string {
  if (pct === null) return '#71717a'
  return pct >= 70 ? '#166534' : pct >= 30 ? '#b45309' : '#b91c1c'
}

export function Admin() {
  const { t } = useI18n()
  const [token, setToken] = useState(() => localStorage.getItem(TOKEN_STORAGE_KEY) ?? '')
  const [leads, setLeads] = useState<LeadSummary[] | null>(null)
  const [status, setStatus] = useState<'idle' | 'loading' | 'error'>('idle')
  const [error, setError] = useState<string | null>(null)

  const loadLeads = () => {
    setStatus('loading')
    setError(null)
    fetch(`${API}/leads`, { headers: { Authorization: `Bearer ${token}` } })
      .then(r => {
        if (!r.ok) throw new Error(r.status === 403 ? t('Wrong admin token', 'Yanlış yönetici anahtarı') : t(`Request failed (${r.status})`, `İstek başarısız (${r.status})`))
        return r.json()
      })
      .then((d: LeadSummary[]) => {
        localStorage.setItem(TOKEN_STORAGE_KEY, token)
        setLeads(d)
        setStatus('idle')
      })
      .catch(e => {
        setError(e.message || t('Failed to load leads', 'Kayıtlar yüklenemedi'))
        setStatus('idle')
      })
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '28px' }}>
      <div>
        <h1 style={{ fontSize: '20px', fontWeight: 700, color: 'var(--ink)', margin: 0, letterSpacing: '-0.02em' }}>
          {t('Leads', 'Kayıtlar')}
        </h1>
        <p style={{ fontSize: '13px', color: '#71717a', margin: '5px 0 0', lineHeight: 1.5 }}>
          {t(
            'Merchants who submitted an audit and left their email, sorted by worst agent-coverage gap first.',
            'Bir denetim gönderip e-postasını bırakan satıcılar; en kötü ajan-kapsama açığı önce olacak şekilde sıralanır.',
          )}
        </p>
      </div>

      <div style={{
        background: '#fff', border: '1px dashed #d4d4d8', borderRadius: '12px',
        padding: '28px 32px', textAlign: 'center',
      }}>
        <div style={{ fontSize: '26px', marginBottom: '10px' }}>🔒</div>
        <h3 style={{ fontSize: '15px', fontWeight: 700, color: 'var(--ink)', margin: '0 0 8px' }}>
          {t('Admin-only · coming soon', 'Yalnızca yönetici · yakında')}
        </h3>
        <p style={{ fontSize: '13px', color: '#71717a', lineHeight: 1.6, margin: '0 auto', maxWidth: '520px' }}>
          {t(
            'Captured leads are private and require an admin token. In the public sandbox this inbox is disabled — audit visitors can still leave their email, and the team reviews them from a secured deployment.',
            'Toplanan kayıtlar özeldir ve bir yönetici anahtarı gerektirir. Herkese açık deneme alanında bu gelen kutusu devre dışıdır — denetim ziyaretçileri yine e-posta bırakabilir, ekip bunları güvenli bir dağıtımdan inceler.',
          )}
        </p>
      </div>

      <div style={{ background: '#fff', border: '1px solid #e4e4e7', borderRadius: '8px', padding: '20px 24px' }}>
        <div style={{ display: 'flex', gap: '12px', alignItems: 'center' }}>
          <input
            type="password"
            value={token}
            onChange={(e) => setToken(e.target.value)}
            placeholder={t('Admin token', 'Yönetici anahtarı')}
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
              background: 'var(--accent)', color: 'var(--on-accent)', border: 'none', cursor: 'pointer',
              minWidth: '110px', textAlign: 'center',
            }}
          >
            {status === 'loading' ? t('Loading…', 'Yükleniyor…') : t('Load leads', 'Kayıtları yükle')}
          </button>
        </div>
      </div>

      {error && (
        <div style={{ background: '#fef2f2', border: '1px solid #fecaca', color: '#b91c1c', padding: '14px 18px', borderRadius: '8px', fontSize: '13px' }}>
          <strong>{t('Error:', 'Hata:')}</strong> {error}
        </div>
      )}

      {leads && (
        <div style={{ background: '#fff', border: '1px solid #e4e4e7', borderRadius: '8px', overflow: 'hidden' }}>
          {leads.length === 0 ? (
            <div style={{ padding: '24px', fontSize: '13px', color: '#71717a' }}>{t('No leads captured yet.', 'Henüz kayıt toplanmadı.')}</div>
          ) : (
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '12.5px' }}>
              <thead>
                <tr style={{ background: '#fafafa', borderBottom: '1px solid #e4e4e7' }}>
                  <th style={{ textAlign: 'left', padding: '10px 16px', color: '#71717a', fontWeight: 600 }}>{t('Email', 'E-posta')}</th>
                  <th style={{ textAlign: 'left', padding: '10px 16px', color: '#71717a', fontWeight: 600 }}>URL</th>
                  <th style={{ textAlign: 'right', padding: '10px 16px', color: '#71717a', fontWeight: 600 }}>{t('Coverage', 'Kapsam')}</th>
                  <th style={{ textAlign: 'left', padding: '10px 16px', color: '#71717a', fontWeight: 600 }}>{t('Captured', 'Toplandı')}</th>
                </tr>
              </thead>
              <tbody>
                {leads.map(lead => (
                  <tr key={lead.id} style={{ borderBottom: '1px solid #f4f4f5' }}>
                    <td style={{ padding: '10px 16px', color: 'var(--ink)', fontWeight: 600 }}>{lead.email}</td>
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
