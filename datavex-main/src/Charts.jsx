/* Inline sparkline — 40px tall, 120px wide, SVG stroke only */

export function Sparkline({ data, color = 'var(--accent)' }) {
    const W = 120, H = 40, PAD = 4;
    const min = Math.min(...data);
    const max = Math.max(...data);
    const range = max - min || 1;

    const pts = data.map((v, i) => ({
        x: PAD + (i / (data.length - 1)) * (W - PAD * 2),
        y: PAD + (1 - (v - min) / range) * (H - PAD * 2),
    }));

    const path = pts.map((p, i) => `${i === 0 ? 'M' : 'L'}${p.x},${p.y}`).join(' ');

    return (
        <svg viewBox={`0 0 ${W} ${H}`} style={{ width: '120px', height: '40px' }}>
            <path d={path} fill="none" stroke={color} strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
            <circle cx={pts[pts.length - 1].x} cy={pts[pts.length - 1].y} r="2" fill={color} />
        </svg>
    );
}

/* Thin arc indicator beside the score */
export function ScoreArc({ score, max = 100 }) {
    const R = 38, CX = 44, CY = 44, SW = 3;
    const C = 2 * Math.PI * R;
    const pct = score / max;

    return (
        <svg viewBox="0 0 88 88" style={{ width: '88px', height: '88px' }}>
            <circle cx={CX} cy={CY} r={R} fill="none" stroke="var(--border)" strokeWidth={SW} />
            <circle cx={CX} cy={CY} r={R} fill="none" stroke="var(--accent)" strokeWidth={SW}
                strokeDasharray={`${pct * C} ${C - pct * C}`}
                strokeDashoffset={0}
                strokeLinecap="round"
                transform={`rotate(-90 ${CX} ${CY})`}
            />
            <text x={CX} y={CY + 1} textAnchor="middle" dominantBaseline="middle"
                fontSize="24" fontFamily="var(--font-display)" fill="var(--accent)">
                {score}
            </text>
        </svg>
    );
}
