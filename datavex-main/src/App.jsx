import { useState, useEffect, useCallback, useRef } from 'react';
import LoginScreen from './Login';
import LeadBoard from './LeadBoard';
import { Sparkline, ScoreArc } from './Charts';
import { getCompanies, getCompany, triggerDiscovery, getDiscoveryStatus, searchDiscover } from './api';

export default function App() {
  const [loggedIn, setLoggedIn] = useState(false);
  const [view, setView] = useState('leadboard');
  const [companies, setCompanies] = useState([]);
  const [activeCompanyId, setActiveCompanyId] = useState(null);
  const [companyDetail, setCompanyDetail] = useState(null);
  const [loading, setLoading] = useState(false);
  const [scanState, setScanState] = useState(null);
  const pollRef = useRef(null);

  useEffect(() => {
    if (localStorage.getItem('datavex_auth')) setLoggedIn(true);
  }, []);

  useEffect(() => {
    if (loggedIn) fetchCompanies();
  }, [loggedIn]);

  const fetchCompanies = useCallback(async () => {
    try {
      const res = await getCompanies();
      setCompanies(res.data || []);
    } catch (e) {
      console.error('Failed to fetch companies:', e);
    }
  }, []);

  const handleCompanySelect = useCallback(async (companyId) => {
    setActiveCompanyId(companyId);
    setView('report');
    setLoading(true);
    try {
      const detail = await getCompany(companyId);
      setCompanyDetail(detail);
    } catch (e) {
      console.error('Failed to fetch company detail:', e);
    } finally {
      setLoading(false);
    }
  }, []);

  const handleScan = useCallback(async () => {
    try {
      setScanState({ status: 'queued', progress: 0, company_name: 'Auto-Discovery', agents_completed: [], agents_pending: [] });
      const res = await triggerDiscovery();
      const scanId = res.scan_id;

      pollRef.current = setInterval(async () => {
        try {
          const status = await getDiscoveryStatus(scanId);
          setScanState({
            scanId,
            status: status.status,
            progress: status.progress,
            company_name: status.company_name || 'Running pipeline...',
            agents_completed: status.agents_completed || [],
            agents_pending: status.agents_pending || [],
            error_message: status.error_message,
          });

          if (status.status === 'completed' || status.status === 'failed') {
            clearInterval(pollRef.current);
            pollRef.current = null;
            if (status.status === 'completed') await fetchCompanies();
            setTimeout(() => setScanState(null), 4000);
          }
        } catch (e) {
          console.error('Poll error:', e);
        }
      }, 2000);
    } catch (e) {
      console.error('Discovery failed:', e);
      setScanState({ status: 'failed', error_message: e.message, progress: 0, agents_completed: [], agents_pending: [] });
      setTimeout(() => setScanState(null), 5000);
    }
  }, [fetchCompanies]);

  // ── Search-Discover: run pipeline on a specific company ─────
  const handleSearchDiscover = useCallback(async (companyName) => {
    if (!companyName.trim() || scanState) return;
    try {
      setScanState({ status: 'queued', progress: 0, company_name: companyName, agents_completed: [], agents_pending: [] });
      const res = await searchDiscover(companyName.trim());
      const scanId = res.scan_id;

      pollRef.current = setInterval(async () => {
        try {
          const status = await getDiscoveryStatus(scanId);
          const compName = (status.company_name || '').startsWith('DONE:')
            ? companyName
            : (status.company_name || companyName);
          setScanState({
            scanId,
            status: status.status,
            progress: status.progress,
            company_name: compName,
            agents_completed: status.agents_completed || [],
            agents_pending: status.agents_pending || [],
            error_message: status.error_message,
          });

          if (status.status === 'completed' || status.status === 'failed') {
            clearInterval(pollRef.current);
            pollRef.current = null;
            if (status.status === 'completed') {
              await fetchCompanies();
              // If backend returns slug in DONE:{slug}, auto-open the company report
              const raw = status.company_name || '';
              if (raw.startsWith('DONE:')) {
                const slug = raw.replace('DONE:', '');
                await handleCompanySelect(slug);
              }
            }
            setTimeout(() => setScanState(null), 4000);
          }
        } catch (e) {
          console.error('Poll error:', e);
        }
      }, 2000);
    } catch (e) {
      console.error('Search-discover failed:', e);
      setScanState({ status: 'failed', error_message: e.message, progress: 0, agents_completed: [], agents_pending: [] });
      setTimeout(() => setScanState(null), 5000);
    }
  }, [scanState, fetchCompanies, handleCompanySelect]);

  useEffect(() => {
    return () => { if (pollRef.current) clearInterval(pollRef.current); };
  }, []);

  const scrollTo = useCallback((id) => {
    const el = document.getElementById(id);
    if (el) el.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }, []);

  if (!loggedIn) return <LoginScreen onComplete={() => setLoggedIn(true)} />;

  return (
    <div style={{ display: 'flex', height: '100vh', overflow: 'hidden' }}>
      {/* ═══════ SIDEBAR ═══════ */}
      <aside style={{
        width: '220px', flexShrink: 0, height: '100vh',
        background: 'var(--sidebar-bg)', borderRight: '1px solid var(--border)',
        padding: '24px 12px', display: 'flex', flexDirection: 'column', overflowY: 'auto',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', padding: '0 12px', marginBottom: '6px' }}>
          <div style={{ width: '8px', height: '8px', borderRadius: '50%', background: 'var(--accent)' }} />
          <span style={{ fontFamily: 'var(--font-display)', fontSize: '18px', color: 'var(--text-primary)' }}>DataVex AI</span>
        </div>
        <div style={{ fontFamily: 'var(--font-mono)', fontSize: '9px', letterSpacing: '0.08em', color: 'var(--text-muted)', padding: '0 12px', marginBottom: '24px' }}>
          v2.4.1 — Synth Layer Active
        </div>

        <button onClick={() => setView('leadboard')} style={{
          textAlign: 'left', padding: '10px 12px', borderRadius: '12px',
          border: 'none', cursor: 'pointer',
          background: view === 'leadboard' ? 'var(--surface)' : 'transparent',
          borderLeft: view === 'leadboard' ? '3px solid var(--accent)' : '3px solid transparent',
          transition: 'all 150ms',
        }}>
          <span style={{ fontFamily: 'var(--font-body)', fontSize: '13px', color: view === 'leadboard' ? 'var(--accent)' : 'var(--text-primary)', fontWeight: view === 'leadboard' ? 600 : 400 }}>
            Lead Board
          </span>
        </button>

        {/* Section anchors when in report view */}
        {view === 'report' && companyDetail && (
          <div style={{ marginTop: '24px' }}>
            <div style={{ fontFamily: 'var(--font-display)', fontSize: '15px', color: 'var(--text-primary)', padding: '0 12px', marginBottom: '16px' }}>
              {companyDetail.name}
            </div>
            {[
              { id: 'section-discovery', label: 'Discovery' },
              { id: 'section-signals', label: 'Signal Engine' },
              { id: 'section-scoring', label: 'Opportunity Score' },
              { id: 'section-strategy', label: 'Strategy' },
              { id: 'section-decision', label: 'GTM Decision' },
              { id: 'section-outreach', label: 'Outreach' },
              { id: 'section-reasoning', label: 'Reasoning Log' },
            ].map((item) => (
              <button key={item.id} onClick={() => scrollTo(item.id)} style={{
                display: 'block', width: '100%', textAlign: 'left',
                padding: '8px 12px', border: 'none', cursor: 'pointer',
                background: 'transparent', borderRadius: '8px',
                fontFamily: 'var(--font-body)', fontSize: '12px', color: 'var(--text-muted)',
                transition: 'color 120ms, background 120ms',
              }}
                onMouseEnter={(e) => { e.currentTarget.style.color = 'var(--accent)'; e.currentTarget.style.background = 'rgba(0,0,0,0.03)'; }}
                onMouseLeave={(e) => { e.currentTarget.style.color = 'var(--text-muted)'; e.currentTarget.style.background = 'transparent'; }}>
                {item.label}
              </button>
            ))}
          </div>
        )}

        <div style={{ margin: '20px 0', height: '1px', background: 'var(--border)' }} />

        {/* Active targets list */}
        <div style={{ fontFamily: 'var(--font-mono)', fontSize: '10px', letterSpacing: '0.12em', textTransform: 'uppercase', color: 'var(--text-muted)', paddingLeft: '12px', marginBottom: '8px' }}>
          Active Targets ({companies.length})
        </div>
        {companies.map((c) => {
          const isActive = activeCompanyId === c.id && view === 'report';
          return (
            <button key={c.id} onClick={() => handleCompanySelect(c.id)} style={{
              textAlign: 'left', padding: '8px 12px', borderRadius: '8px',
              border: 'none', cursor: 'pointer',
              background: isActive ? 'var(--surface)' : 'transparent',
              transition: 'all 150ms', display: 'flex', alignItems: 'center', justifyContent: 'space-between',
            }}>
              <span style={{ fontFamily: 'var(--font-body)', fontSize: '13px', color: 'var(--text-primary)' }}>{c.name}</span>
              <span style={{ fontFamily: 'var(--font-mono)', fontSize: '11px', fontWeight: 600, color: c.score >= 80 ? 'var(--accent)' : c.score >= 60 ? 'var(--warning)' : 'var(--text-muted)' }}>
                {c.score}
              </span>
            </button>
          );
        })}

        {companies.length === 0 && (
          <div style={{ padding: '12px', fontFamily: 'var(--font-body)', fontSize: '12px', color: 'var(--text-muted)', textAlign: 'center' }}>
            No targets yet.<br />Click <strong>Run Scan</strong> to discover targets.
          </div>
        )}

        <div style={{ marginTop: 'auto', padding: '12px', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <span style={{ fontFamily: 'var(--font-mono)', fontSize: '10px', color: 'var(--text-muted)' }}>SYSTEM STATUS</span>
          <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
            <div style={{ width: '6px', height: '6px', borderRadius: '50%', background: 'var(--accent)' }} />
            <span style={{ fontFamily: 'var(--font-mono)', fontSize: '10px', color: 'var(--accent)' }}>Online</span>
          </span>
        </div>
      </aside>

      {/* ═══════ MAIN ═══════ */}
      <main id="main-scroll" key={`${view}-${activeCompanyId}`} style={{
        flex: 1, overflowY: 'auto', padding: '40px 64px 96px',
        animation: 'contentFade 160ms ease-out',
      }}>
        {view === 'leadboard' && (
          <LeadBoard
            companies={companies}
            onSelectCompany={handleCompanySelect}
            onScan={handleScan}
            onSearchDiscover={handleSearchDiscover}
            scanState={scanState}
          />
        )}
        {view === 'report' && loading && (
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '60vh' }}>
            <div style={{ textAlign: 'center' }}>
              <div style={{ width: '32px', height: '32px', border: '3px solid var(--border)', borderTop: '3px solid var(--accent)', borderRadius: '50%', animation: 'spin 1s linear infinite', margin: '0 auto 16px' }} />
              <p style={{ fontFamily: 'var(--font-body)', color: 'var(--text-muted)', fontSize: '14px' }}>Loading intelligence report...</p>
            </div>
          </div>
        )}
        {view === 'report' && !loading && companyDetail && (
          <CompanyReport company={companyDetail} />
        )}
      </main>
    </div>
  );
}


/* ═══════════════════════════════════════════════════
   COMPANY REPORT — 6-SECTION LAYOUT FROM AGENT OUTPUTS
   ═══════════════════════════════════════════════════ */

function CompanyReport({ company }) {
  const a1 = company.agent1 || {};
  const a2 = company.agent2 || {};
  const a3 = company.agent3 || {};
  const a35 = company.agent35 || {};
  const a4 = company.agent4 || {};
  const a5 = company.agent5 || {};
  const trace = company.trace || [];
  const scoreBreakdown = company.score_breakdown || company.scoreBreakdown || [];
  const isCompetitor = company.competitor === true;
  const signalCounts = company.signal_counts || {};

  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    navigator.clipboard.writeText(a5.message || '').then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  };

  const priorityColor = (p) => p === 'HIGH' ? 'var(--accent)' : p === 'MEDIUM' ? 'var(--warning)' : 'var(--text-muted)';
  const pct = (v) => `${Math.round((v || 0) * 100)}%`;
  const score100 = (v) => Math.round((v || 0) * 100);

  return (
    <>
      {/* ════════ COMPETITOR WARNING BANNER ════════ */}
      {isCompetitor && (
        <Section index={0}>
          <div style={{
            background: 'rgba(255, 160, 0, 0.08)',
            border: '2px solid var(--warning)',
            borderRadius: '20px',
            padding: '28px 36px',
            marginBottom: '16px',
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '12px' }}>
              <span style={{ fontSize: '28px' }}>⚠️</span>
              <span style={{ fontFamily: 'var(--font-display)', fontSize: '22px', color: 'var(--warning)' }}>
                Potential Competitor — Not a Target Client
              </span>
            </div>
            <p style={{ fontFamily: 'var(--font-body)', fontSize: '14px', color: 'var(--text-primary)', lineHeight: 1.7 }}>
              {company.competitor_note || 'This company has been flagged as a potential competitor. Do not initiate outreach. Use as competitive intelligence only.'}
            </p>
            {signalCounts.total > 0 && (
              <div style={{ display: 'flex', gap: '16px', marginTop: '16px', fontFamily: 'var(--font-mono)', fontSize: '11px' }}>
                <span style={{ color: 'var(--accent)' }}>✓ {signalCounts.verified || 0} VERIFIED signals</span>
                <span style={{ color: 'var(--warning)' }}>⚠ {signalCounts.unverified || 0} UNVERIFIED signals</span>
                <span style={{ color: 'var(--text-muted)' }}>Total: {signalCounts.total || 0}</span>
              </div>
            )}
          </div>
        </Section>
      )}

      {/* ════════ HEADER ════════ */}
      <Section index={0}>
        <h1 style={{ fontFamily: 'var(--font-display)', fontSize: '48px', fontWeight: 400, color: 'var(--text-primary)', lineHeight: 1.1 }}>
          {company.name}
        </h1>
        <p style={{ fontFamily: 'var(--font-body)', fontSize: '15px', color: 'var(--text-muted)', marginTop: '8px' }}>
          {company.descriptor}
        </p>
        <div style={{ display: 'flex', alignItems: 'center', gap: '24px', marginTop: '32px' }}>
          <ScoreArc score={isCompetitor ? 0 : company.score} />
          <div>
            <div style={{ fontFamily: 'var(--font-mono)', fontSize: '11px', letterSpacing: '0.1em', textTransform: 'uppercase', color: 'var(--text-muted)' }}>
              PRIORITY · <span style={{ color: isCompetitor ? 'var(--warning)' : priorityColor(a3.priority) }}>{isCompetitor ? 'COMPETITOR' : (a3.priority || company.confidence)}</span>
            </div>
            <div style={{ fontFamily: 'var(--font-mono)', fontSize: '11px', color: 'var(--text-muted)', marginTop: '4px' }}>
              COVERAGE: {company.coverage}%
            </div>
            <div style={{ fontFamily: 'var(--font-mono)', fontSize: '11px', color: 'var(--text-muted)', marginTop: '4px' }}>
              RECEPTIVITY: {company.receptivity}
            </div>
          </div>
        </div>
      </Section>

      {/* ════════ 1. DISCOVERY (Agent 1) ════════ */}
      <div id="section-discovery">
        <Section index={1} label="DISCOVERY — AGENT 1">
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '16px' }}>
            {[
              { label: 'INDUSTRY', value: a1.industry || '—' },
              { label: 'DOMAIN', value: a1.domain || '—' },
              { label: 'SIZE', value: a1.size || '—' },
              { label: 'EMPLOYEES', value: a1.estimated_employees ? `~${a1.estimated_employees.toLocaleString()}` : '—' },
              { label: 'REGION', value: a1.region || '—' },
              { label: 'COMPANY', value: a1.company_name || company.name },
            ].map((row) => (
              <div key={row.label} style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: '16px', padding: '20px 24px', boxShadow: 'var(--shadow)' }}>
                <MiniLabel>{row.label}</MiniLabel>
                <div style={{ fontFamily: 'var(--font-display)', fontSize: '20px', color: 'var(--text-primary)', marginTop: '6px' }}>
                  {row.value}
                </div>
              </div>
            ))}
          </div>
        </Section>
      </div>

      {/* ════════ 2. SIGNAL ENGINE (Agent 2) ════════ */}
      <div id="section-signals">
        <Section index={2} label="SIGNAL ENGINE — AGENT 2">
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '24px' }}>
            {/* Score bars */}
            <div style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: '20px', padding: '28px 32px', boxShadow: 'var(--shadow)' }}>
              <MiniLabel>SIGNAL SCORES</MiniLabel>
              {[
                { label: 'Expansion', value: a2.expansion_score || 0, color: 'var(--accent)' },
                { label: 'Strain', value: a2.strain_score || 0, color: 'var(--warning)' },
                { label: 'Risk', value: a2.risk_score || 0, color: '#e05050' },
                { label: 'Pain', value: a2.pain_score || 0, color: 'var(--accent)' },
              ].map((bar) => (
                <div key={bar.label} style={{ marginTop: '16px' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '6px' }}>
                    <span style={{ fontFamily: 'var(--font-body)', fontSize: '13px', color: 'var(--text-primary)' }}>{bar.label}</span>
                    <span style={{ fontFamily: 'var(--font-mono)', fontSize: '13px', color: bar.color, fontWeight: 600 }}>{pct(bar.value)}</span>
                  </div>
                  <div style={{ height: '6px', background: 'var(--border)', borderRadius: '3px', overflow: 'hidden' }}>
                    <div style={{ height: '100%', width: pct(bar.value), background: bar.color, borderRadius: '3px', transition: 'width 600ms ease-out' }} />
                  </div>
                </div>
              ))}
            </div>

            {/* Pain level + signals */}
            <div style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: '20px', padding: '28px 32px', boxShadow: 'var(--shadow)' }}>
              <MiniLabel>PAIN LEVEL</MiniLabel>
              <div style={{ fontFamily: 'var(--font-display)', fontSize: '36px', color: priorityColor(a2.pain_level), marginTop: '8px', marginBottom: '24px' }}>
                {a2.pain_level || '—'}
              </div>

              <MiniLabel>DETECTED SIGNALS</MiniLabel>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', marginTop: '10px' }}>
                {(a2.signals || []).length === 0 && (
                  <span style={{ fontFamily: 'var(--font-body)', fontSize: '13px', color: 'var(--text-muted)', fontStyle: 'italic' }}>No signals detected</span>
                )}
                {(a2.signals || []).slice(0, 6).map((sig, i) => (
                  <div key={i} style={{ background: 'var(--surface-inner, rgba(0,0,0,0.03))', border: '1px solid var(--border)', borderRadius: '12px', padding: '10px 14px' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '4px', flexWrap: 'wrap' }}>
                      <span style={{
                        fontFamily: 'var(--font-mono)', fontSize: '10px', flexShrink: 0,
                        padding: '2px 8px', borderRadius: '10px', background: 'var(--accent-tint)',
                        color: 'var(--accent)', border: '1px solid var(--accent)',
                      }}>{sig.type}</span>
                      {sig.verified === true ? (
                        <span style={{ fontFamily: 'var(--font-mono)', fontSize: '9px', padding: '2px 8px', borderRadius: '10px', background: 'rgba(0,180,100,0.08)', color: '#00b464', border: '1px solid #00b464', letterSpacing: '0.08em' }}>✓ VERIFIED</span>
                      ) : sig.verified === false ? (
                        <span style={{ fontFamily: 'var(--font-mono)', fontSize: '9px', padding: '2px 8px', borderRadius: '10px', background: 'rgba(255,160,0,0.08)', color: 'var(--warning)', border: '1px solid var(--warning)', letterSpacing: '0.08em' }}>⚠ UNVERIFIED</span>
                      ) : null}
                      {sig.source && (
                        <span style={{ fontFamily: 'var(--font-mono)', fontSize: '9px', color: 'var(--text-muted)', marginLeft: 'auto' }}>{sig.source.split(' (')[0].slice(0, 40)}</span>
                      )}
                    </div>
                    <span style={{ fontFamily: 'var(--font-body)', fontSize: '12px', color: 'var(--text-primary)', lineHeight: 1.5 }}>
                      {sig.text}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </Section>
      </div>

      {/* ════════ 3. OPPORTUNITY SCORE (Agent 3) ════════ */}
      <div id="section-scoring">
        <Section index={3} label="OPPORTUNITY SCORE — AGENT 3">
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '24px' }}>
            {/* Score breakdown */}
            <div style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: '20px', padding: '28px 32px', boxShadow: 'var(--shadow)' }}>
              <MiniLabel>SCORE BREAKDOWN</MiniLabel>
              {[
                { label: 'Intent', value: a3.intent_score, max: 1 },
                { label: 'Conversion', value: a3.conversion_score, max: 1 },
                { label: 'Deal Size', value: a3.deal_size_score, max: 1 },
                { label: 'Expansion', value: a3.expansion_score, max: 1 },
                { label: 'Strain', value: a3.strain_score, max: 1 },
              ].map((row, i, arr) => (
                <div key={row.label} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '10px 0', borderBottom: i < arr.length - 1 ? '1px solid var(--border)' : 'none' }}>
                  <span style={{ fontFamily: 'var(--font-body)', fontSize: '14px', color: 'var(--text-primary)' }}>{row.label}</span>
                  <span style={{ fontFamily: 'var(--font-mono)', fontSize: '14px', color: 'var(--text-primary)', fontWeight: 600 }}>{score100(row.value)}/100</span>
                </div>
              ))}
            </div>

            {/* Summary + key signals */}
            <div style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: '20px', padding: '28px 32px', boxShadow: 'var(--shadow)' }}>
              <MiniLabel>SUMMARY</MiniLabel>
              <p style={{ fontFamily: 'var(--font-body)', fontSize: '14px', color: 'var(--text-primary)', lineHeight: 1.65, marginTop: '10px', marginBottom: '24px' }}>
                {a3.summary || '—'}
              </p>

              <MiniLabel>KEY SIGNALS</MiniLabel>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px', marginTop: '10px' }}>
                {(a3.key_signals || []).map((sig, i) => (
                  <span key={i} style={{ fontFamily: 'var(--font-mono)', fontSize: '11px', padding: '4px 12px', borderRadius: '20px', border: '1px solid var(--accent)', color: 'var(--accent)' }}>
                    {sig}
                  </span>
                ))}
                {(a3.key_signals || []).length === 0 && (
                  <span style={{ fontFamily: 'var(--font-body)', fontSize: '12px', color: 'var(--text-muted)', fontStyle: 'italic' }}>None detected</span>
                )}
              </div>
            </div>
          </div>
        </Section>
      </div>

      {/* ════════ 4. STRATEGY (Agent 3.5) ════════ */}
      <div id="section-strategy">
        <Section index={4} label="STRATEGY — AGENT 3.5">
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '16px' }}>
            {[
              { label: 'BUYING STYLE', value: a35.buying_style || '—' },
              { label: 'OFFER', value: a35.offer || '—' },
              { label: 'ENTRY POINT', value: a35.entry_point || '—' },
              { label: 'TECH STRENGTH', value: a35.tech_strength != null ? pct(a35.tech_strength) : '—' },
              { label: 'STRATEGY NOTE', value: a35.strategy_note || '—', span: 2 },
            ].map((row) => (
              <div key={row.label} style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: '16px', padding: '20px 24px', boxShadow: 'var(--shadow)', gridColumn: row.span === 2 ? 'span 2' : undefined }}>
                <MiniLabel>{row.label}</MiniLabel>
                <div style={{ fontFamily: 'var(--font-display)', fontSize: '18px', color: 'var(--text-primary)', marginTop: '6px' }}>
                  {row.value}
                </div>
              </div>
            ))}
          </div>
        </Section>
      </div>

      {/* ════════ 5. GTM DECISION (Agent 4) ════════ */}
      <div id="section-decision">
        <Section index={5} label="GTM DECISION — AGENT 4">
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '24px' }}>
            {/* Strategy + offer */}
            <div style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: '20px', padding: '28px 32px', boxShadow: 'var(--shadow)' }}>
              <MiniLabel>STRATEGY</MiniLabel>
              <div style={{ fontFamily: 'var(--font-display)', fontSize: '32px', color: 'var(--accent)', marginTop: '8px' }}>
                {a4.strategy || '—'}
              </div>
              <div style={{ marginTop: '24px' }}>
                <MiniLabel>RECOMMENDED OFFER</MiniLabel>
                <p style={{ fontFamily: 'var(--font-body)', fontSize: '15px', color: 'var(--text-primary)', lineHeight: 1.6, marginTop: '8px' }}>
                  {a4.recommended_offer || '—'}
                </p>
              </div>
              <div style={{ marginTop: '20px' }}>
                <MiniLabel>ENTRY POINT</MiniLabel>
                <p style={{ fontFamily: 'var(--font-body)', fontSize: '14px', color: 'var(--text-primary)', lineHeight: 1.6, marginTop: '8px' }}>
                  {a4.entry_point || '—'}
                </p>
              </div>
            </div>

            {/* Scores at a glance */}
            <div style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: '20px', padding: '28px 32px', boxShadow: 'var(--shadow)' }}>
              <MiniLabel>SCORES AT A GLANCE</MiniLabel>
              {[
                { label: 'Priority', value: a4.priority || '—', isTag: true },
                { label: 'Intent', value: pct(a4.intent_score) },
                { label: 'Conversion', value: pct(a4.conversion_score) },
                { label: 'Deal Size', value: pct(a4.deal_size_score) },
                { label: 'Risk', value: pct(a4.risk_score) },
              ].map((row, i, arr) => (
                <div key={row.label} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '12px 0', borderBottom: i < arr.length - 1 ? '1px solid var(--border)' : 'none' }}>
                  <span style={{ fontFamily: 'var(--font-body)', fontSize: '14px', color: 'var(--text-primary)' }}>{row.label}</span>
                  {row.isTag ? (
                    <span style={{ fontFamily: 'var(--font-mono)', fontSize: '11px', padding: '4px 12px', borderRadius: '20px', border: `1px solid ${priorityColor(row.value)}`, color: priorityColor(row.value) }}>
                      {row.value}
                    </span>
                  ) : (
                    <span style={{ fontFamily: 'var(--font-mono)', fontSize: '14px', fontWeight: 600, color: 'var(--text-primary)' }}>{row.value}</span>
                  )}
                </div>
              ))}

              {(a4.key_signals || []).length > 0 && (
                <div style={{ marginTop: '20px' }}>
                  <MiniLabel>KEY SIGNALS</MiniLabel>
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px', marginTop: '8px' }}>
                    {a4.key_signals.map((sig, i) => (
                      <span key={i} style={{ fontFamily: 'var(--font-mono)', fontSize: '10px', padding: '3px 10px', borderRadius: '10px', background: 'var(--accent-tint)', color: 'var(--accent)', border: '1px solid var(--accent)' }}>
                        {sig}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>
        </Section>
      </div>

      {/* ════════ 6. OUTREACH (Agent 5) ════════ */}
      <div id="section-outreach">
        <Section index={6} label="OUTREACH — AGENT 5">
          {/* Persona + channel + priority */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '16px', marginBottom: '24px' }}>
            {[
              { label: 'TARGET PERSONA', value: a5.persona || '—' },
              { label: 'CHANNEL', value: a5.channel ? a5.channel.replace(/_/g, ' ').toUpperCase() : '—' },
              { label: 'PRIORITY', value: a5.priority || '—' },
            ].map((row) => (
              <div key={row.label} style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: '16px', padding: '20px 24px', boxShadow: 'var(--shadow)' }}>
                <MiniLabel>{row.label}</MiniLabel>
                <div style={{ fontFamily: 'var(--font-display)', fontSize: '18px', color: 'var(--text-primary)', marginTop: '6px' }}>{row.value}</div>
              </div>
            ))}
          </div>

          {/* Subject */}
          {a5.subject && (
            <div style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: '16px', padding: '20px 28px', marginBottom: '16px', boxShadow: 'var(--shadow)' }}>
              <MiniLabel>SUBJECT LINE</MiniLabel>
              <div style={{ fontFamily: 'var(--font-body)', fontSize: '15px', color: 'var(--text-primary)', marginTop: '8px', fontStyle: 'italic' }}>
                {a5.subject}
              </div>
            </div>
          )}

          {/* Message */}
          <div style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: '20px', padding: '32px', boxShadow: 'var(--shadow)' }}>
            <MiniLabel>MESSAGE</MiniLabel>
            <p style={{ fontFamily: 'var(--font-body)', fontSize: '14px', color: 'var(--text-primary)', lineHeight: 1.85, whiteSpace: 'pre-wrap', marginTop: '12px' }}>
              {a5.message || 'No message generated.'}
            </p>
          </div>

          <div style={{ marginTop: '20px' }}>
            <button onClick={handleCopy} style={{
              borderRadius: '20px', padding: '10px 24px',
              fontFamily: 'var(--font-body)', fontSize: '13px', fontWeight: 500,
              color: copied ? '#fff' : 'var(--text-primary)',
              background: copied ? 'var(--accent)' : 'transparent',
              border: copied ? 'none' : '1px solid var(--border)',
              transition: 'all 150ms', cursor: 'pointer',
            }}>
              {copied ? '✓ Copied' : 'Copy message'}
            </button>
          </div>
        </Section>
      </div>

      {/* ════════ REASONING LOG (Trace) ════════ */}
      {trace.length > 0 && (
        <div id="section-reasoning">
          <Section index={7} label="REASONING LOG">
            <div style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: '24px', padding: '28px 32px', boxShadow: 'var(--shadow)' }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'flex-end', gap: '6px', marginBottom: '20px' }}>
                <div style={{ width: '6px', height: '6px', borderRadius: '50%', background: 'var(--accent)' }} />
                <span style={{ fontFamily: 'var(--font-mono)', fontSize: '9px', color: 'var(--text-muted)', letterSpacing: '0.1em', textTransform: 'uppercase' }}>LIVE</span>
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                {trace.map((line, i) => (
                  <div key={i} style={{ fontFamily: 'var(--font-mono)', fontSize: '12px', lineHeight: 1.7, display: 'flex', gap: '16px' }}>
                    <span style={{ color: 'var(--text-muted)', flexShrink: 0 }}>{line.time}</span>
                    <span style={{ color: 'var(--accent)', flexShrink: 0, minWidth: '160px', fontWeight: 500 }}>{line.agent}</span>
                    <span style={{ color: 'var(--text-primary)' }}>→ {line.action}</span>
                  </div>
                ))}
              </div>
            </div>
          </Section>
        </div>
      )}
    </>
  );
}


/* ═══════ HELPERS ═══════ */

function Section({ children, index, label }) {
  return (
    <section style={{ marginBottom: '64px', animation: 'sectionUp 200ms ease-out both', animationDelay: `${index * 60}ms` }}>
      {label && (
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '24px' }}>
          <div style={{ width: '5px', height: '5px', borderRadius: '50%', background: 'var(--accent)' }} />
          <span style={{ fontFamily: 'var(--font-mono)', fontSize: '10px', letterSpacing: '0.12em', textTransform: 'uppercase', color: 'var(--text-muted)' }}>{label}</span>
        </div>
      )}
      {children}
    </section>
  );
}

function MiniLabel({ children }) {
  return (
    <div style={{ fontFamily: 'var(--font-mono)', fontSize: '10px', letterSpacing: '0.1em', textTransform: 'uppercase', color: 'var(--text-muted)' }}>
      {children}
    </div>
  );
}
