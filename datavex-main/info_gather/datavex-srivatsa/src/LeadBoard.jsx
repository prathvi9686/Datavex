import { COMPANIES } from './data';

const tagStyle = (tag) => {
    if (tag === 'HIGH PAIN') return { border: '1px solid #C2601F', color: '#C2601F' };
    if (tag === 'MED PAIN') return { border: '1px solid #9B9489', color: '#9B9489' };
    return { border: '1px solid #E8E4DE', color: '#9B9489' };
};

export default function LeadBoard({ onSelectCompany, activeCompany }) {
    return (
        <div style={{ animation: 'contentFade 160ms ease-out' }}>
            {/* Header */}
            <div style={{ display: 'flex', alignItems: 'flex-end', justifyContent: 'space-between', marginBottom: '48px' }}>
                <div>
                    <h1 style={{ fontFamily: 'var(--font-display)', fontSize: '40px', fontWeight: 400, color: 'var(--text-primary)' }}>
                        Lead Intelligence Board
                    </h1>
                    <p style={{ fontFamily: 'var(--font-body)', fontSize: '15px', color: '#9B9489', marginTop: '6px' }}>
                        Prioritized accounts via multi-agent signal synthesis.
                    </p>
                </div>
                <div style={{ display: 'flex', gap: '12px' }}>
                    <button style={{
                        border: '1px solid var(--border)', borderRadius: '20px',
                        padding: '12px 28px', fontFamily: 'var(--font-body)', fontSize: '14px',
                        color: 'var(--text-primary)', background: 'transparent',
                        transition: 'background 150ms', cursor: 'pointer',
                    }}
                        onMouseEnter={(e) => e.currentTarget.style.background = 'var(--hover-bg)'}
                        onMouseLeave={(e) => e.currentTarget.style.background = 'transparent'}>
                        Export Config
                    </button>
                    <button style={{
                        border: 'none', borderRadius: '20px',
                        padding: '12px 28px', fontFamily: 'var(--font-body)', fontSize: '14px',
                        fontWeight: 500, color: '#FFFFFF', background: 'var(--accent)',
                        boxShadow: 'var(--shadow-button)',
                        transition: 'background 150ms, box-shadow 150ms', cursor: 'pointer',
                    }}
                        onMouseEnter={(e) => { e.currentTarget.style.background = 'var(--accent-hover)'; e.currentTarget.style.boxShadow = '0 3px 12px rgba(26,107,71,0.35)'; }}
                        onMouseLeave={(e) => { e.currentTarget.style.background = 'var(--accent)'; e.currentTarget.style.boxShadow = 'var(--shadow-button)'; }}>
                        Run Full Scan
                    </button>
                </div>
            </div>

            {/* 3-column card grid */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '24px' }}>
                {COMPANIES.map((c, i) => {
                    const isActive = activeCompany === i;
                    return (
                        <div
                            key={c.id}
                            onClick={() => onSelectCompany(i)}
                            style={{
                                padding: '40px', cursor: 'pointer',
                                background: 'var(--surface)',
                                border: isActive ? '2px solid var(--accent)' : '1px solid var(--border)',
                                borderRadius: '24px',
                                boxShadow: 'var(--shadow)',
                                transition: 'box-shadow 150ms, border-color 150ms',
                                display: 'flex', flexDirection: 'column',
                            }}
                            onMouseEnter={(e) => { e.currentTarget.style.boxShadow = 'var(--shadow-hover)'; if (!isActive) e.currentTarget.style.borderColor = 'var(--accent)'; }}
                            onMouseLeave={(e) => { e.currentTarget.style.boxShadow = 'var(--shadow)'; if (!isActive) e.currentTarget.style.borderColor = 'var(--border)'; }}
                        >
                            {/* Top: name + score */}
                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '8px' }}>
                                <div>
                                    <h3 style={{ fontFamily: 'var(--font-display)', fontSize: '28px', fontWeight: 400, color: 'var(--text-primary)', lineHeight: 1.2 }}>
                                        {c.name}
                                    </h3>
                                    <p style={{ fontFamily: 'var(--font-body)', fontSize: '12px', color: 'var(--text-muted)', marginTop: '8px' }}>
                                        {c.descriptor.split('·').slice(0, 2).map(s => s.trim()).join(' · ')}
                                    </p>
                                </div>
                                <div style={{ textAlign: 'right', flexShrink: 0 }}>
                                    <span style={{
                                        fontFamily: 'var(--font-display)', fontSize: '52px',
                                        color: c.score >= 80 ? 'var(--accent)' : c.score >= 60 ? 'var(--warning)' : 'var(--text-muted)',
                                        lineHeight: 1,
                                    }}>
                                        {c.score}
                                    </span>
                                    <div style={{ fontFamily: 'var(--font-mono)', fontSize: '9px', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.12em', marginTop: '2px' }}>SCORE</div>
                                </div>
                            </div>

                            {/* Pain tags */}
                            <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap', marginTop: '16px' }}>
                                {c.painTags.map((tag, j) => (
                                    <span key={j} style={{
                                        fontFamily: 'var(--font-body)', fontSize: '11px', fontWeight: 500,
                                        padding: '6px 12px', borderRadius: '20px',
                                        background: 'transparent',
                                        ...tagStyle(tag),
                                    }}>
                                        {tag}
                                    </span>
                                ))}
                            </div>

                            {/* DM Target — with 32px breathing room */}
                            <div style={{ marginTop: '32px' }}>
                                <span style={{ fontFamily: 'var(--font-mono)', fontSize: '10px', color: '#9B9489', textTransform: 'uppercase', letterSpacing: '0.1em' }}>DM TARGET</span>
                                <div style={{ fontFamily: 'var(--font-body)', fontSize: '16px', fontWeight: 700, color: 'var(--text-primary)', marginTop: '4px' }}>
                                    {c.decisionMaker.name}
                                </div>
                            </div>

                            {/* Profile link */}
                            <div style={{ marginTop: 'auto', paddingTop: '20px', textAlign: 'right' }}>
                                <span
                                    className="profile-link"
                                    style={{
                                        fontFamily: 'var(--font-body)', fontSize: '13px', color: 'var(--accent)',
                                        display: 'inline-block', transition: 'transform 150ms',
                                    }}
                                    onMouseEnter={(e) => e.currentTarget.style.transform = 'translateX(3px)'}
                                    onMouseLeave={(e) => e.currentTarget.style.transform = 'translateX(0)'}
                                >
                                    Profile →
                                </span>
                            </div>
                        </div>
                    );
                })}
            </div>
        </div>
    );
}
