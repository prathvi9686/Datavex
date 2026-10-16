const priorityColor = (p) => {
    if (p === 'HIGH') return { border: '1px solid var(--accent)', color: 'var(--accent)' };
    if (p === 'MEDIUM') return { border: '1px solid var(--warning)', color: 'var(--warning)' };
    return { border: '1px solid var(--border)', color: 'var(--text-muted)' };
};

const painColor = (p) => {
    if (p === 'HIGH') return 'var(--accent)';
    if (p === 'MEDIUM') return 'var(--warning)';
    return 'var(--text-muted)';
};

import { useState } from 'react';

export default function LeadBoard({ companies = [], onSelectCompany, onScan, onSearchDiscover, scanState }) {
    const [searchQuery, setSearchQuery] = useState('');
    const visible = searchQuery.trim()
        ? companies.filter(c => c.name.toLowerCase().includes(searchQuery.toLowerCase()))
        : companies;

    // Whether the typed query matches any existing company
    const hasMatch = visible.length > 0;
    const canScanNew = searchQuery.trim().length >= 2 && !hasMatch && !scanState;

    const handleSearchKeyDown = (e) => {
        if (e.key === 'Enter' && searchQuery.trim()) {
            if (canScanNew && onSearchDiscover) {
                onSearchDiscover(searchQuery.trim());
                setSearchQuery('');
            }
        }
    };

    return (
        <div style={{ animation: 'contentFade 160ms ease-out' }}>
            {/* Header */}
            <div style={{ display: 'flex', alignItems: 'flex-end', justifyContent: 'space-between', marginBottom: '48px' }}>
                <div>
                    <h1 style={{ fontFamily: 'var(--font-display)', fontSize: '40px', fontWeight: 400, color: 'var(--text-primary)' }}>
                        Lead Intelligence Board
                    </h1>
                    <p style={{ fontFamily: 'var(--font-body)', fontSize: '15px', color: '#9B9489', marginTop: '6px' }}>
                        Prioritized accounts via 5-agent signal synthesis.
                    </p>
                </div>
                <button
                    onClick={onScan}
                    disabled={!!scanState}
                    style={{
                        border: 'none', borderRadius: '16px',
                        padding: '16px 32px', fontFamily: 'var(--font-body)', fontSize: '15px',
                        fontWeight: 600, color: '#FFFFFF',
                        background: scanState ? '#9B9489' : 'var(--accent)',
                        boxShadow: 'var(--shadow-button)',
                        transition: 'background 150ms, box-shadow 150ms',
                        cursor: scanState ? 'not-allowed' : 'pointer',
                        whiteSpace: 'nowrap',
                    }}
                    onMouseEnter={(e) => { if (!scanState) { e.currentTarget.style.background = 'var(--accent-hover)'; } }}
                    onMouseLeave={(e) => { if (!scanState) { e.currentTarget.style.background = 'var(--accent)'; } }}
                >
                    {scanState ? 'Scanning...' : 'Run Scan'}
                </button>
            </div>

            {/* ═══════ SEARCH BAR ═══════ */}
            <div style={{ marginBottom: '32px', position: 'relative' }}>
                <span style={{
                    position: 'absolute', left: '18px', top: '50%', transform: 'translateY(-50%)',
                    fontSize: '16px', pointerEvents: 'none', opacity: 0.5,
                }}>🔍</span>
                <input
                    type="text"
                    placeholder="Search or type a company name and press Enter to scan..."
                    value={searchQuery}
                    onChange={e => setSearchQuery(e.target.value)}
                    onKeyDown={handleSearchKeyDown}
                    style={{
                        width: '100%', boxSizing: 'border-box',
                        padding: '14px 20px 14px 48px',
                        background: 'var(--surface)', border: `1px solid ${canScanNew ? 'var(--accent)' : 'var(--border)'}`,
                        borderRadius: '16px', outline: 'none',
                        fontFamily: 'var(--font-body)', fontSize: '15px',
                        color: 'var(--text-primary)',
                        transition: 'border-color 150ms, box-shadow 150ms',
                        boxShadow: canScanNew ? '0 0 0 3px var(--accent-tint)' : 'none',
                    }}
                    onFocus={e => { e.currentTarget.style.borderColor = 'var(--accent)'; e.currentTarget.style.boxShadow = '0 0 0 3px var(--accent-tint)'; }}
                    onBlur={e => { if (!canScanNew) { e.currentTarget.style.borderColor = 'var(--border)'; e.currentTarget.style.boxShadow = 'none'; } }}
                />
                {canScanNew && (
                    <button
                        onClick={() => { if (onSearchDiscover) { onSearchDiscover(searchQuery.trim()); setSearchQuery(''); } }}
                        style={{
                            position: 'absolute', right: '12px', top: '50%', transform: 'translateY(-50%)',
                            background: 'var(--accent)', border: 'none', cursor: 'pointer',
                            color: '#fff', fontSize: '12px', fontFamily: 'var(--font-mono)',
                            fontWeight: 600, padding: '6px 14px', borderRadius: '10px',
                            letterSpacing: '0.04em',
                        }}
                    >↵ SCAN</button>
                )}
                {searchQuery && !canScanNew && (
                    <button
                        onClick={() => setSearchQuery('')}
                        style={{
                            position: 'absolute', right: '16px', top: '50%', transform: 'translateY(-50%)',
                            background: 'none', border: 'none', cursor: 'pointer',
                            color: 'var(--text-muted)', fontSize: '18px', lineHeight: 1,
                        }}
                    >×</button>
                )}
            </div>

            {/* ─── hint when typed company not found ─── */}
            {searchQuery.trim().length >= 2 && !hasMatch && !scanState && (
                <div style={{
                    marginBottom: '20px', padding: '12px 18px',
                    background: 'var(--accent-tint)', border: '1px solid var(--accent)',
                    borderRadius: '12px', display: 'flex', alignItems: 'center', gap: '10px',
                    fontFamily: 'var(--font-body)', fontSize: '13px', color: 'var(--accent)',
                }}>
                    <span style={{ fontSize: '16px' }}>🤖</span>
                    <span>
                        <strong>"{searchQuery}"</strong> not in database —{' '}
                        press <strong>Enter</strong> or click <strong>↵ SCAN</strong> to run the 5-agent pipeline on it.
                    </span>
                </div>
            )}

            {/* ═══════ SCAN PROGRESS ═══════ */}
            {scanState && (
                <div style={{
                    background: 'var(--surface)', border: '1px solid var(--accent)',
                    borderRadius: '20px', padding: '24px 32px', marginBottom: '32px',
                    animation: 'contentFade 200ms ease-out',
                }}>
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '12px' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                            <div style={{
                                width: '8px', height: '8px', borderRadius: '50%',
                                background: scanState.status === 'failed' ? 'var(--warning)' : 'var(--accent)',
                                animation: (scanState.status === 'running' || scanState.status === 'queued') ? 'pulse 1.5s ease-in-out infinite' : 'none',
                            }} />
                            <span style={{ fontFamily: 'var(--font-display)', fontSize: '16px', color: 'var(--text-primary)' }}>
                                {scanState.status === 'completed' ? '✓ Scan Complete' :
                                    scanState.status === 'failed' ? '✗ Scan Failed' :
                                        `Running: ${scanState.company_name || 'Pipeline...'}`}
                            </span>
                        </div>
                        <span style={{ fontFamily: 'var(--font-mono)', fontSize: '12px', color: 'var(--accent)' }}>
                            {Math.round((scanState.progress || 0) * 100)}%
                        </span>
                    </div>

                    {/* Progress bar */}
                    <div style={{ height: '4px', background: 'var(--border)', borderRadius: '2px', overflow: 'hidden' }}>
                        <div style={{
                            height: '100%',
                            background: scanState.status === 'failed' ? 'var(--warning)' : 'var(--accent)',
                            width: `${Math.max(5, (scanState.progress || 0) * 100)}%`,
                            borderRadius: '2px', transition: 'width 500ms ease-out',
                        }} />
                    </div>

                    {/* Agent badges */}
                    {((scanState.agents_completed?.length > 0) || (scanState.agents_pending?.length > 0)) && (
                        <div style={{ display: 'flex', gap: '8px', marginTop: '14px', flexWrap: 'wrap' }}>
                            {(scanState.agents_completed || []).map((a) => (
                                <span key={a} style={{
                                    fontFamily: 'var(--font-mono)', fontSize: '10px',
                                    padding: '4px 10px', borderRadius: '12px',
                                    background: 'var(--accent-tint)', color: 'var(--accent)', border: '1px solid var(--accent)',
                                }}>{a} ✓</span>
                            ))}
                            {(scanState.agents_pending || []).map((a) => (
                                <span key={a} style={{
                                    fontFamily: 'var(--font-mono)', fontSize: '10px',
                                    padding: '4px 10px', borderRadius: '12px',
                                    background: 'transparent', color: 'var(--text-muted)', border: '1px solid var(--border)',
                                }}>{a}</span>
                            ))}
                        </div>
                    )}

                    {scanState.error_message && (
                        <p style={{ fontFamily: 'var(--font-body)', fontSize: '13px', color: 'var(--warning)', marginTop: '12px' }}>
                            Error: {scanState.error_message}
                        </p>
                    )}
                </div>
            )}

            {/* ═══════ COMPANY CARDS ═══════ */}
            {searchQuery && visible.length === 0 ? (
                <div style={{ textAlign: 'center', padding: '60px 20px', color: 'var(--text-muted)', fontFamily: 'var(--font-body)' }}>
                    No companies match &ldquo;{searchQuery}&rdquo;
                </div>
            ) : companies.length > 0 ? (
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '24px' }}>
                    {visible.map((c) => {
                        const data = c.data || {};
                        const a2 = data.agent2 || {};
                        const a4 = data.agent4 || {};
                        const a5 = data.agent5 || {};
                        const painLevel = a2.pain_level || data.pain_level || '—';
                        const strategy = a4.strategy || '—';
                        const persona = a5.persona || '—';
                        const priority = a4.priority || c.confidence || 'LOW';
                        const descriptor = (c.descriptor || '').split('·').slice(0, 2).map(s => s.trim()).join(' · ');

                        const isCompetitor = data.competitor === true;

                        return (
                            <div
                                key={c.id}
                                onClick={() => onSelectCompany(c.id)}
                                style={{
                                    padding: '36px', cursor: 'pointer',
                                    background: isCompetitor ? 'rgba(255,160,0,0.04)' : 'var(--surface)',
                                    border: isCompetitor ? '2px solid var(--warning)' : '1px solid var(--border)',
                                    borderRadius: '24px', boxShadow: 'var(--shadow)',
                                    transition: 'box-shadow 150ms, border-color 150ms',
                                    display: 'flex', flexDirection: 'column',
                                }}
                                onMouseEnter={(e) => { e.currentTarget.style.boxShadow = 'var(--shadow-hover)'; e.currentTarget.style.borderColor = isCompetitor ? 'var(--warning)' : 'var(--accent)'; }}
                                onMouseLeave={(e) => { e.currentTarget.style.boxShadow = 'var(--shadow)'; e.currentTarget.style.borderColor = isCompetitor ? 'var(--warning)' : 'var(--border)'; }}
                            >
                                {/* Competitor banner */}
                                {isCompetitor && (
                                    <div style={{ marginBottom: '16px', display: 'flex', alignItems: 'center', gap: '6px', background: 'rgba(255,160,0,0.10)', border: '1px solid var(--warning)', borderRadius: '10px', padding: '6px 12px' }}>
                                        <span style={{ fontSize: '14px' }}>⚠️</span>
                                        <span style={{ fontFamily: 'var(--font-mono)', fontSize: '10px', color: 'var(--warning)', fontWeight: 600, letterSpacing: '0.05em' }}>
                                            POTENTIAL COMPETITOR — NOT A TARGET CLIENT
                                        </span>
                                    </div>
                                )}

                                {/* Name + score */}
                                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '8px' }}>
                                    <div>
                                        <h3 style={{ fontFamily: 'var(--font-display)', fontSize: '26px', fontWeight: 400, color: 'var(--text-primary)', lineHeight: 1.2 }}>
                                            {c.name}
                                        </h3>
                                        <p style={{ fontFamily: 'var(--font-body)', fontSize: '12px', color: 'var(--text-muted)', marginTop: '6px' }}>
                                            {descriptor || 'Analysis in progress...'}
                                        </p>
                                    </div>
                                    <div style={{ textAlign: 'right', flexShrink: 0 }}>
                                        <span style={{
                                            fontFamily: 'var(--font-display)', fontSize: '48px',
                                            color: c.score >= 80 ? 'var(--accent)' : c.score >= 60 ? 'var(--warning)' : 'var(--text-muted)',
                                            lineHeight: 1,
                                        }}>
                                            {c.score}
                                        </span>
                                        <div style={{ fontFamily: 'var(--font-mono)', fontSize: '9px', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.12em', marginTop: '2px' }}>SCORE</div>
                                    </div>
                                </div>

                                {/* Priority + pain badges */}
                                <div style={{ display: 'flex', gap: '8px', marginTop: '10px', flexWrap: 'wrap' }}>
                                    <span style={{ fontFamily: 'var(--font-mono)', fontSize: '10px', fontWeight: 600, padding: '4px 10px', borderRadius: '12px', ...priorityColor(priority) }}>
                                        {priority}
                                    </span>
                                    {painLevel !== '—' && (
                                        <span style={{ fontFamily: 'var(--font-mono)', fontSize: '10px', padding: '4px 10px', borderRadius: '12px', border: `1px solid ${painColor(painLevel)}`, color: painColor(painLevel) }}>
                                            {painLevel} PAIN
                                        </span>
                                    )}
                                    <span style={{ fontFamily: 'var(--font-mono)', fontSize: '10px', color: 'var(--text-muted)', padding: '4px 0' }}>
                                        {c.coverage}% coverage
                                    </span>
                                </div>

                                {/* Strategy */}
                                {strategy !== '—' && (
                                    <div style={{ marginTop: '20px' }}>
                                        <div style={{ fontFamily: 'var(--font-mono)', fontSize: '9px', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.1em' }}>STRATEGY</div>
                                        <div style={{ fontFamily: 'var(--font-body)', fontSize: '14px', color: 'var(--text-primary)', fontWeight: 600, marginTop: '4px' }}>
                                            {strategy}
                                        </div>
                                    </div>
                                )}

                                {/* Persona */}
                                {persona !== '—' && (
                                    <div style={{ marginTop: '14px' }}>
                                        <div style={{ fontFamily: 'var(--font-mono)', fontSize: '9px', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.1em' }}>TARGET PERSONA</div>
                                        <div style={{ fontFamily: 'var(--font-body)', fontSize: '13px', color: 'var(--text-primary)', marginTop: '4px' }}>
                                            {persona}
                                        </div>
                                    </div>
                                )}

                                {/* Profile link */}
                                <div style={{ marginTop: 'auto', paddingTop: '20px', textAlign: 'right' }}>
                                    <span style={{
                                        fontFamily: 'var(--font-body)', fontSize: '13px', color: 'var(--accent)',
                                        display: 'inline-block', transition: 'transform 150ms',
                                    }}
                                        onMouseEnter={(e) => e.currentTarget.style.transform = 'translateX(3px)'}
                                        onMouseLeave={(e) => e.currentTarget.style.transform = 'translateX(0)'}
                                    >
                                        View Report →
                                    </span>
                                </div>
                            </div>
                        );
                    })}
                </div>
            ) : !scanState && (
                <div style={{
                    display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center',
                    padding: '80px 40px', background: 'var(--surface)', border: '1px solid var(--border)',
                    borderRadius: '24px', boxShadow: 'var(--shadow)',
                }}>
                    <div style={{
                        width: '64px', height: '64px', borderRadius: '50%',
                        background: 'var(--accent-tint)', border: '2px solid var(--accent)',
                        display: 'flex', alignItems: 'center', justifyContent: 'center', marginBottom: '24px',
                    }}>
                        <span style={{ fontSize: '28px' }}>🔍</span>
                    </div>
                    <h2 style={{ fontFamily: 'var(--font-display)', fontSize: '24px', fontWeight: 400, color: 'var(--text-primary)', marginBottom: '8px' }}>
                        No targets discovered yet
                    </h2>
                    <p style={{ fontFamily: 'var(--font-body)', fontSize: '14px', color: 'var(--text-muted)', textAlign: 'center', maxWidth: '400px' }}>
                        Click <strong>Run Scan</strong> to launch the 5-agent pipeline and auto-discover target companies.
                    </p>
                </div>
            )}
        </div>
    );
}
