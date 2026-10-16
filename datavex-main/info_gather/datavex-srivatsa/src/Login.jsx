import { useState } from 'react';

export default function LoginScreen({ onComplete }) {
    const [user, setUser] = useState('');
    const [pass, setPass] = useState('');
    const [error, setError] = useState('');

    const handleLogin = () => {
        if (user === 'admin' && pass === 'admin') {
            localStorage.setItem('datavex_auth', 'true');
            onComplete();
        } else {
            setError('Invalid credentials. Try admin / admin.');
        }
    };

    const handleKeyDown = (e) => {
        if (e.key === 'Enter') handleLogin();
    };

    return (
        <div style={{
            minHeight: '100vh', background: 'var(--bg)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            padding: '40px 24px',
        }}>
            <div style={{ width: '100%', maxWidth: '440px', animation: 'contentFade 200ms ease-out' }}>
                {/* Brand */}
                <div style={{ textAlign: 'center', marginBottom: '56px' }}>
                    <div style={{ display: 'inline-flex', alignItems: 'center', gap: '10px', marginBottom: '10px' }}>
                        <div style={{ width: '12px', height: '12px', borderRadius: '50%', background: 'var(--accent)' }} />
                        <span style={{ fontFamily: 'var(--font-display)', fontSize: '36px', color: 'var(--text-primary)' }}>
                            DataVex AI
                        </span>
                    </div>
                    <p style={{ fontFamily: 'var(--font-body)', fontSize: '15px', color: 'var(--text-muted)', marginTop: '6px' }}>
                        Sales Intelligence Platform
                    </p>
                </div>

                {/* Card */}
                <div style={{
                    background: 'var(--surface)', border: '1px solid var(--border)',
                    borderRadius: '24px', padding: '48px 40px',
                    boxShadow: '0 2px 8px rgba(0,0,0,0.06)',
                }}>
                    <h2 style={{
                        fontFamily: 'var(--font-display)', fontSize: '28px', fontWeight: 400,
                        marginBottom: '40px', textAlign: 'center',
                    }}>
                        Sign in
                    </h2>

                    <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
                        <div>
                            <label style={{
                                display: 'block', fontFamily: 'var(--font-body)', fontSize: '13px',
                                fontWeight: 500, color: 'var(--text-primary)', marginBottom: '8px',
                            }}>
                                Username
                            </label>
                            <input
                                type="text" value={user}
                                onChange={(e) => { setUser(e.target.value); setError(''); }}
                                onKeyDown={handleKeyDown}
                                placeholder="admin"
                                autoFocus
                                style={{ borderRadius: '12px', padding: '14px 18px', fontSize: '15px' }}
                            />
                        </div>

                        <div>
                            <label style={{
                                display: 'block', fontFamily: 'var(--font-body)', fontSize: '13px',
                                fontWeight: 500, color: 'var(--text-primary)', marginBottom: '8px',
                            }}>
                                Password
                            </label>
                            <input
                                type="password" value={pass}
                                onChange={(e) => { setPass(e.target.value); setError(''); }}
                                onKeyDown={handleKeyDown}
                                placeholder="••••••"
                                style={{ borderRadius: '12px', padding: '14px 18px', fontSize: '15px' }}
                            />
                        </div>

                        {error && (
                            <p style={{
                                fontFamily: 'var(--font-body)', fontSize: '13px',
                                color: 'var(--warning)', textAlign: 'center',
                            }}>
                                {error}
                            </p>
                        )}

                        <button
                            onClick={handleLogin}
                            style={{
                                fontFamily: 'var(--font-body)', fontSize: '15px', fontWeight: 500,
                                color: 'var(--surface)', background: 'var(--accent)',
                                padding: '14px 24px', borderRadius: '12px',
                                cursor: 'pointer', transition: 'opacity 150ms', marginTop: '8px',
                                width: '100%',
                            }}
                            onMouseEnter={(e) => e.currentTarget.style.opacity = '0.9'}
                            onMouseLeave={(e) => e.currentTarget.style.opacity = '1'}
                        >
                            Sign in
                        </button>
                    </div>
                </div>

                <p style={{
                    fontFamily: 'var(--font-mono)', fontSize: '10px',
                    color: 'var(--text-muted)', textAlign: 'center', marginTop: '36px',
                    letterSpacing: '0.04em',
                }}>
                    DataVex AI · v2.4.1 · Synth Layer Active
                </p>
            </div>
        </div>
    );
}
