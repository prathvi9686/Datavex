import { CAPABILITIES } from './data';

export default function CapabilityMatch({ company }) {
    const match = company.strongestMatch;

    return (
        <div>
            {/* Strongest match summary */}
            <div style={{
                background: 'var(--accent-tint)', border: '1px solid var(--accent)',
                borderRadius: '24px', padding: '28px 36px', marginBottom: '40px',
                display: 'flex', alignItems: 'center', gap: '28px',
            }}>
                <span style={{ fontFamily: 'var(--font-display)', fontSize: '52px', color: 'var(--accent)', lineHeight: 1 }}>
                    {match.score}%
                </span>
                <div>
                    <span style={{ fontFamily: 'var(--font-mono)', fontSize: '10px', letterSpacing: '0.1em', textTransform: 'uppercase', color: 'var(--accent)' }}>
                        STRONGEST MATCH
                    </span>
                    <p style={{ fontFamily: 'var(--font-body)', fontSize: '16px', fontWeight: 500, color: 'var(--text-primary)', marginTop: '6px' }}>
                        {match.capability} →  {match.pain}
                    </p>
                    <p style={{ fontFamily: 'var(--font-mono)', fontSize: '11px', color: 'var(--text-muted)', marginTop: '8px' }}>
                        GAP: {match.gap}
                    </p>
                </div>
            </div>

            {/* Full-width capability cards */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                {CAPABILITIES.map((cap) => {
                    const matches = company.capabilityMatch.filter(cm => cm.capability === cap.name);
                    const hasMatch = matches.length > 0;

                    return (
                        <div key={cap.name} style={{
                            background: 'var(--surface)', border: '1px solid var(--border)',
                            borderRadius: '24px', padding: '28px 32px',
                            boxShadow: 'var(--shadow)',
                        }}>
                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: '20px' }}>
                                <div style={{ flex: 1 }}>
                                    <h4 style={{ fontFamily: 'var(--font-body)', fontSize: '16px', fontWeight: 600, color: 'var(--text-primary)', marginBottom: '6px' }}>
                                        {cap.name}
                                    </h4>
                                    <p style={{ fontFamily: 'var(--font-body)', fontSize: '13px', color: 'var(--text-muted)', lineHeight: 1.5 }}>
                                        {cap.desc}
                                    </p>
                                </div>
                                <span style={{
                                    fontFamily: 'var(--font-mono)', fontSize: '12px', fontWeight: 500,
                                    padding: '6px 14px', borderRadius: '20px', flexShrink: 0,
                                    border: '1px solid',
                                    borderColor: cap.score >= 80 ? 'var(--accent)' : 'var(--warning)',
                                    color: cap.score >= 80 ? 'var(--accent)' : 'var(--warning)',
                                }}>
                                    {cap.score}%
                                </span>
                            </div>

                            {hasMatch && (
                                <div style={{ marginTop: '14px', paddingTop: '14px', borderTop: '1px solid var(--border)' }}>
                                    <span style={{ fontFamily: 'var(--font-body)', fontSize: '13px', color: 'var(--text-muted)' }}>
                                        Matches: {matches.map(m => m.pain).join(' · ')}
                                    </span>
                                </div>
                            )}
                            {!hasMatch && (
                                <div style={{ marginTop: '14px', paddingTop: '14px', borderTop: '1px solid var(--border)' }}>
                                    <span style={{ fontFamily: 'var(--font-body)', fontSize: '13px', color: 'var(--text-muted)', fontStyle: 'italic' }}>
                                        No matching pain signal detected
                                    </span>
                                </div>
                            )}
                        </div>
                    );
                })}
            </div>
        </div>
    );
}
