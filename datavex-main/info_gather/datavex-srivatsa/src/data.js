/* Company intelligence data — 3 fully specific targets, zero generic copy */

export const CAPABILITIES = [
    { name: 'Real-Time Pipeline Repair', score: 96, desc: 'Automated detection and self-healing of broken data connectors. Reduces MTTR from hours to minutes.' },
    { name: 'Legacy Stack Migration', score: 84, desc: 'Structured migration from monolithic warehouses to composable architectures with zero-downtime cutover.' },
    { name: 'Schema Evolution Management', score: 88, desc: 'Automatic schema drift detection and downstream contract enforcement.' },
    { name: 'Data Observability Layer', score: 91, desc: 'End-to-end lineage tracking, anomaly detection, and SLA alerting across all pipeline stages.' },
    { name: 'Vector Search Infrastructure', score: 73, desc: 'Production-grade embedding pipelines and vector index management for AI-native data products.' },
];

export const COMPANIES = [
    {
        id: 'meridian',
        name: 'Meridian Systems',
        descriptor: 'Enterprise SaaS · 2,400 employees · Series D · $180M ARR',
        score: 87,
        confidence: 'HIGH',
        coverage: 73,
        receptivity: 'HIGH — ACT WITHIN 90 DAYS',
        painTags: ['HIGH PAIN', 'HIGH PAIN', 'MED PAIN'],
        capabilityMatch: [
            { pain: 'Connector failures causing 4hr delays', source: 'GITHUB ISSUES', severity: 'HIGH', capability: 'Real-Time Pipeline Repair' },
            { pain: 'Monolithic warehouse costs exploding', source: 'INVESTOR REPORT', severity: 'HIGH', capability: 'Legacy Stack Migration' },
            { pain: 'Schema drift breaking downstream BI', source: 'GLASSDOOR', severity: 'MED', capability: 'Schema Evolution Management' },
            { pain: 'Manual migration failing', source: 'TECH BLOG', severity: 'HIGH', capability: 'Legacy Stack Migration' },
            { pain: 'Stale data on dashboards', source: 'GITHUB ISSUES', severity: 'LOW', capability: 'Data Observability Layer' },
            { pain: 'No visibility into lineage', source: 'LINKEDIN JOBS', severity: 'MED', capability: 'Data Observability Layer' },
        ],
        strongestMatch: { score: 75, capability: 'Real-Time Pipeline Repair', pain: 'Connector failures causing 4hr delays', gap: 'Vector Search (no detected need)' },
        financials: {
            quarters: ['Q1 24', 'Q2 24', 'Q3 24', 'Q4 24', 'Q1 25', 'Q2 25'],
            margin: [18.2, 17.4, 16.8, 15.9, 15.1, 14.6],
            revenue: [38.2, 40.1, 42.1, 41.3, 43.8, 44.2],
        },
        hiring: [
            { category: 'Engineering', count: 24, type: 'positive' },
            { category: 'Enterprise Sales', count: 14, type: 'positive' },
            { category: 'DevOps / SRE', count: 9, type: 'positive' },
            { category: 'Leadership', count: 3, type: 'warning' },
            { category: 'SMB Sales', count: 0, type: 'neutral' },
        ],
        scoreBreakdown: [
            { label: 'Tech Signals', value: 32, max: 35 },
            { label: 'Financial', value: 22, max: 25 },
            { label: 'Market Timing', value: 18, max: 20 },
            { label: 'Leadership', value: 15, max: 20 },
        ],
        timeline: [
            { date: '2025.11', type: 'positive', label: 'CEO keynote at SaaStr Annual: "Enterprise-first by end of 2026." Three public commitments to upmarket shift in 90 days.', source: 'SAASTR ANNUAL' },
            { date: '2025.10', type: 'pressure', label: 'Q3 earnings miss — revenue $42.1M against a $44.8M consensus estimate. Stock dropped 9% intraday, recovered to –4% by close.', source: 'SEC FILING' },
            { date: '2025.09', type: 'positive', label: '14 enterprise Account Executive roles posted across LinkedIn and Lever within a 3-week window. No corresponding SMB backfills.', source: 'JOB BOARDS' },
            { date: '2025.08', type: 'pressure', label: 'CTO Sarah Chen departs after 6 years. No successor named for 45 days. Engineering blog goes silent.', source: 'LINKEDIN' },
            { date: '2025.07', type: 'pressure', label: 'Glassdoor engineering satisfaction score drops from 4.1 to 3.4. Three reviews cite "unclear technical direction."', source: 'GLASSDOOR' },
            { date: '2025.06', type: 'positive', label: '9 Kubernetes migration roles opened on Greenhouse — infra overhaul confirmed. Jenkins deprecation RFC merged January 14.', source: 'GREENHOUSE' },
        ],
        painClusters: [
            {
                title: 'Data Pipeline Failures', evidence: [
                    { source: 'GH', text: '22 issues tagged "legacy-pipeline" — 14 marked P0 — average resolution time 11.3 days, up from 4.7 days in Q1.' },
                    { source: 'G2', text: '"Data sync breaks every time we scale past 10K events/sec." — Verified buyer review, posted September 12, 2025.' },
                    { source: 'JD', text: 'Senior Data Engineer role description: "Rebuild batch processing layer, migrate from Airflow 1.x to Dagster. Immediate start."' },
                ]
            },
            {
                title: 'Deployment Velocity', evidence: [
                    { source: 'GH', text: 'CI/CD pipeline average build time: 34 minutes. Six PRs reference "flaky test" in the last 30 days.' },
                    { source: 'JD', text: 'DevOps Lead role: "Reduce deployment cycle from weekly to daily releases. Must have experience with trunk-based development."' },
                ]
            },
            {
                title: 'Observability Gaps', evidence: [
                    { source: 'G2', text: '"No centralized logging — teams use 3 different tools and nobody trusts any of them." — IT Director review, August 20, 2025.' },
                    { source: 'GH', text: 'RFC #847: "Unified observability stack" — 43 comments, still in draft after 90 days. No owner assigned.' },
                    { source: 'JD', text: 'SRE Manager: "Implement SLO-based alerting. Consolidate from Datadog + Grafana + custom scripts into a single pane."' },
                ]
            },
        ],
        decisionMaker: {
            name: 'Marcus Rivera', role: 'VP Engineering · Reports to interim CTO',
            topics: ['Platform Migration', 'Developer Velocity', 'Cost-per-Deploy'],
            messaging: { angle: 'Your infra migration is exposed — 22 legacy pipeline issues and a 34-minute CI cycle will bottleneck the enterprise pivot before Q3.', vocab: ['deployment velocity', 'platform consolidation', 'eng leverage'], tone: 'Direct' },
        },
        outreach: {
            email: "Marcus —\n\nMeridian posted 9 Kubernetes roles in 60 days while carrying 22 open legacy-pipeline issues on GitHub. Your CI builds are averaging 34 minutes.\n\nThat math doesn't close before the enterprise launch.\n\nWe cut that migration timeline by 60% for teams at your stage — consolidated infra, sub-8-minute builds, one observability layer instead of three.\n\nWorth 20 minutes this week to show you the before/after from a $160M ARR SaaS company that faced the same wall?\n\n— DataVex",
            linkedin: "Marcus — noticed Meridian's 9 Kubernetes roles + the legacy pipeline backlog on GitHub. That infra gap will bottleneck the enterprise pivot.\n\nWe helped a similar-stage company cut migration time 60% and drop CI builds from 35 min to 7. Happy to share the breakdown if useful.",
            opener: '"Marcus, quick question — with Sarah\'s departure and 22 legacy pipeline issues still open, who\'s owning the infra migration timeline for the enterprise launch?"',
            footnote: 'GENERATED FROM: Q3 margin signal + CTO departure + 9 Kubernetes roles + 22 legacy-pipeline GitHub issues',
        },
        trace: [
            { time: '2026.02.21 09:14:02', agent: 'RESEARCH_AGENT ', action: 'fetched Q2–Q4 2024 earnings transcripts for Meridian Systems' },
            { time: '2026.02.21 09:14:04', agent: 'FINANCE_AGENT  ', action: 'detected operating margin decline: –2.3% over 3 quarters' },
            { time: '2026.02.21 09:14:06', agent: 'TECH_AGENT     ', action: '9 Kubernetes roles + 22 legacy pipeline GitHub issues filed' },
            { time: '2026.02.21 09:14:08', agent: 'CONFLICT_AGENT ', action: 'contradiction: hiring spend rising despite cost pressure signal' },
            { time: '2026.02.21 09:14:10', agent: 'SYNTHESIS_AGENT', action: 'resolved: budget shifting ops→transformation — confirms receptivity' },
            { time: '2026.02.21 09:14:11', agent: 'DECISION_AGENT ', action: 'verdict: HIGH. Window: 60–90 days. Recommended persona: VP Eng.' },
        ],
    },
    {
        id: 'lattice',
        name: 'Lattice Dynamics',
        descriptor: 'Fintech / Capital Markets · 890 employees · Series C · $67M ARR',
        score: 64, confidence: 'MEDIUM', coverage: 58,
        receptivity: 'MEDIUM — MONITOR FOR 30 DAYS',
        painTags: ['HIGH PAIN', 'MED PAIN', 'MED PAIN'],
        capabilityMatch: [
            { pain: 'SOC2 audit control failures', source: 'AUDIT REPORT', severity: 'HIGH', capability: 'Data Observability Layer' },
            { pain: 'Monolith blocking multi-asset launch', source: 'G2 REVIEWS', severity: 'HIGH', capability: 'Legacy Stack Migration' },
            { pain: 'Backtesting OOM at 500K instruments', source: 'GITHUB ISSUES', severity: 'MED', capability: 'Vector Search Infrastructure' },
            { pain: 'No continuous compliance monitoring', source: 'LINKEDIN JOBS', severity: 'MED', capability: 'Data Observability Layer' },
        ],
        strongestMatch: { score: 68, capability: 'Data Observability Layer', pain: 'SOC2 audit control failures', gap: 'Schema Evolution (low signal)' },
        financials: {
            quarters: ['Q1 24', 'Q2 24', 'Q3 24', 'Q4 24', 'Q1 25', 'Q2 25'],
            margin: [12.1, 11.8, 10.9, 9.7, 8.4, 7.2],
            revenue: [14.2, 15.1, 15.8, 16.3, 16.1, 16.9],
        },
        hiring: [
            { category: 'Security / Compliance', count: 6, type: 'warning' },
            { category: 'Staff Engineering', count: 3, type: 'positive' },
            { category: 'Quant Research', count: 8, type: 'positive' },
            { category: 'DevOps', count: 2, type: 'neutral' },
        ],
        scoreBreakdown: [
            { label: 'Tech Signals', value: 24, max: 35 },
            { label: 'Financial', value: 18, max: 25 },
            { label: 'Market Timing', value: 12, max: 20 },
            { label: 'Leadership', value: 10, max: 20 },
        ],
        timeline: [
            { date: '2025.12', type: 'pressure', label: 'SOC2 Type II audit returns 3 control failures. Remediation deadline: 90 days. Board notified same week.', source: 'AUDIT REPORT' },
            { date: '2025.11', type: 'pressure', label: 'Customer acquisition cost increased 31%. Average sales cycle extended from 45 to 68 days. Pipeline velocity declining.', source: 'BOARD DECK' },
            { date: '2025.10', type: 'positive', label: 'Multi-asset expansion announced internally — 4 new asset class teams formed. 8 quant researcher roles posted.', source: 'LINKEDIN' },
            { date: '2025.08', type: 'pressure', label: '14 CVEs across 3 public repos flagged by external security researcher on GitHub Advisory. 6 rated HIGH severity.', source: 'GITHUB ADVISORY' },
            { date: '2025.07', type: 'positive', label: 'Series C closed: $67M at $340M valuation. Lead investor: Ribbit Capital.', source: 'CRUNCHBASE' },
        ],
        painClusters: [
            {
                title: 'Compliance Gaps', evidence: [
                    { source: 'JD', text: 'Head of Compliance role: "Remediate SOC2 failures and build continuous compliance monitoring from scratch."' },
                    { source: 'GH', text: '14 CVEs across 3 public repos — 6 rated HIGH severity — oldest has been open for 140 days with no assignee.' },
                ]
            },
            {
                title: 'Monolith Decomposition', evidence: [
                    { source: 'GH', text: 'RFC #312: "Strangler fig migration plan" — filed June 2025. Zero PRs linked. Status: stalled.' },
                    { source: 'JD', text: '3 Staff Engineer roles posted: "Decompose trading engine monolith into event-driven services."' },
                    { source: 'G2', text: '"Every feature deployment risks the entire platform. We held our breath on every release." — Engineering team lead, October 2025.' },
                ]
            },
            {
                title: 'Quant Infrastructure Scaling', evidence: [
                    { source: 'JD', text: 'Quant Platform Engineer: "Build real-time feature store for multi-asset pricing models. Must handle 500K+ instruments."' },
                    { source: 'GH', text: 'Issue #1847: "Backtesting pipeline OOM at 500K instruments" — open 45 days, no proposed solution.' },
                ]
            },
        ],
        decisionMaker: {
            name: 'Diana Kowalski', role: 'CTO · Co-founder · 7 years tenure',
            topics: ['Event-Driven Architecture', 'Regulatory Tech', 'Quant Infrastructure'],
            messaging: { angle: 'Your SOC2 failures and stalled monolith RFC will block the multi-asset launch unless decomposition accelerates — the compliance clock is ticking.', vocab: ['event-driven', 'continuous compliance', 'strangler fig'], tone: 'Consultative' },
        },
        outreach: {
            email: "Diana —\n\n3 SOC2 control failures, 14 open CVEs, and a monolith decomposition RFC that's been stalled since June. Meanwhile, 4 new multi-asset teams need a platform that doesn't exist yet.\n\nWe've run this exact remediation at 6 fintech companies — average SOC2 compliance in 47 days, and the decomposition tooling cuts strangler-fig timelines by 45%.\n\n20 minutes to walk through the compliance-to-launch sequence?\n\n— DataVex",
            linkedin: "Diana — saw Lattice's SOC2 audit results and the stalled monolith RFC. Multi-asset expansion on a monolith with 14 open CVEs is a compounding risk.\n\nWe helped 6 similar fintechs hit compliance in 47 days while decomposing in parallel. Happy to share specifics.",
            opener: '"Diana, with the SOC2 remediation and multi-asset launch both targeting 2026 — how are you sequencing the monolith decomposition against the compliance timeline?"',
            footnote: 'GENERATED FROM: SOC2 audit failures + stalled RFC #312 + 14 CVEs + multi-asset expansion signal',
        },
        trace: [
            { time: '2026.02.21 09:16:01', agent: 'RESEARCH_AGENT ', action: 'scanned 3 public repos, 8 job posts, 2 G2 reviews for Lattice' },
            { time: '2026.02.21 09:16:03', agent: 'FINANCE_AGENT  ', action: 'CAC up 31%, burn multiple 1.8x — profitability pressure confirmed' },
            { time: '2026.02.21 09:16:05', agent: 'TECH_AGENT     ', action: '14 CVEs, monolith RFC stalled 6 months, 3 staff eng roles open' },
            { time: '2026.02.21 09:16:07', agent: 'CONFLICT_AGENT ', action: 'tension: multi-asset expansion vs compliance remediation timeline' },
            { time: '2026.02.21 09:16:09', agent: 'SYNTHESIS_AGENT', action: 'compliance must precede expansion — creates tooling window' },
            { time: '2026.02.21 09:16:10', agent: 'DECISION_AGENT ', action: 'verdict: MEDIUM. Window: 30–60 days. Recommended persona: CTO.' },
        ],
    },
    {
        id: 'aperture',
        name: 'Aperture Robotics',
        descriptor: 'Industrial Automation · 5,100 employees · Public (NASD: APRT) · $420M revenue',
        score: 41, confidence: 'LOW', coverage: 81,
        receptivity: 'LOW — LONG CYCLE, PLANT SEEDS',
        painTags: ['HIGH PAIN', 'MED PAIN', 'LOW PAIN'],
        capabilityMatch: [
            { pain: '3 CI systems with no shared registry', source: 'GLASSDOOR', severity: 'HIGH', capability: 'Legacy Stack Migration' },
            { pain: 'VectorFlow talent attrition', source: 'LINKEDIN JOBS', severity: 'MED', capability: null },
            { pain: 'No unified control plane', source: 'SEC FILING', severity: 'MED', capability: 'Real-Time Pipeline Repair' },
            { pain: '47 integration blockers growing', source: 'GITHUB ISSUES', severity: 'LOW', capability: 'Data Observability Layer' },
        ],
        strongestMatch: { score: 52, capability: 'Legacy Stack Migration', pain: '3 CI systems with no shared registry', gap: 'Vector Search + Schema Evolution (no signal)' },
        financials: {
            quarters: ['Q1 24', 'Q2 24', 'Q3 24', 'Q4 24', 'Q1 25', 'Q2 25'],
            margin: [62.4, 62.1, 61.8, 62.0, 61.2, 60.4],
            revenue: [98.0, 102.3, 105.1, 108.7, 104.2, 101.8],
        },
        hiring: [
            { category: 'Integration / PM', count: 6, type: 'positive' },
            { category: 'Platform Eng', count: 4, type: 'positive' },
            { category: 'Backfills', count: 11, type: 'warning' },
            { category: 'Controls Eng', count: 3, type: 'neutral' },
        ],
        scoreBreakdown: [
            { label: 'Tech Signals', value: 14, max: 35 },
            { label: 'Financial', value: 12, max: 25 },
            { label: 'Market Timing', value: 8, max: 20 },
            { label: 'Leadership', value: 7, max: 20 },
        ],
        timeline: [
            { date: '2025.12', type: 'pressure', label: 'Stock drops 14% post-acquisition announcement. Two analyst downgrades citing integration risk and margin dilution.', source: '10-K FILING' },
            { date: '2025.11', type: 'positive', label: 'MotionIQ acquisition closes — $28M, 120 engineers absorbed. Integration timeline set at 18 months.', source: 'SEC FILING' },
            { date: '2025.09', type: 'positive', label: 'VectorFlow acquisition closes — $34M, 85 engineers. Unified control plane is the stated goal by Q4 2026.', source: 'SEC FILING' },
            { date: '2025.08', type: 'pressure', label: 'Internal memo leaks to Glassdoor: "3 CI systems, no shared artifact registry, no unified auth. Integration is behind."', source: 'GLASSDOOR' },
            { date: '2025.06', type: 'pressure', label: 'Board approves $18M integration budget over 4 quarters. CFO calls it "necessary but painful."', source: 'BOARD MINUTES' },
        ],
        painClusters: [
            {
                title: 'Multi-System Integration', evidence: [
                    { source: 'JD', text: 'Integration Architect: "Unify 3 CI/CD systems, establish shared artifact registry, implement cross-org auth. Urgent."' },
                    { source: 'GH', text: '47 Jira tickets tagged "integration-blocker" — 12 marked critical — average age: 67 days and growing.' },
                ]
            },
            {
                title: 'Talent Retention Risk', evidence: [
                    { source: 'G2', text: '"Acquisition killed our velocity — 3 layers of approval for every deploy now." — Former VectorFlow engineer, November 2025.' },
                    { source: 'JD', text: '11 backfill roles posted for VectorFlow team positions within 60 days of close. Attrition accelerating.' },
                ]
            },
            {
                title: 'Control Plane Unification', evidence: [
                    { source: 'JD', text: 'Principal Engineer — Control Systems: "Design unified control plane spanning 3 robot firmware architectures."' },
                    { source: 'GH', text: 'RFC #201: "Cross-subsidiary API gateway" — 89 comments, 4 competing proposals, no decision after 120 days.' },
                ]
            },
        ],
        decisionMaker: {
            name: 'James Okafor', role: 'SVP Platform Engineering · Joined via VectorFlow acquisition',
            topics: ['Post-Merger Integration', 'Platform Unification', 'Engineering Culture'],
            messaging: { angle: 'Three CI systems and 47 integration blockers at 67-day average age — the unified control plane will miss the 2026 Q4 deadline without consolidation tooling.', vocab: ['integration velocity', 'platform unification', 'cross-org governance'], tone: 'Conceptual' },
        },
        outreach: {
            email: "James —\n\n47 integration-blocker tickets averaging 67 days open, 3 CI systems with no shared registry, and 11 VectorFlow backfills posted in 60 days. The integration clock is running.\n\nWe unified CI across 3 entities at two public industrials in 90 days — shared artifact registry, cross-org auth, single deployment pipeline. Cut integration-blocker resolution time by 70%.\n\nThis is a longer conversation, but worth starting now. 20 minutes to compare architectures?\n\n— DataVex",
            linkedin: "James — having led the VectorFlow integration, you're seeing the 3-CI-system problem firsthand. 47 blockers at 67-day avg age compounds fast.\n\nWe ran very similar unification at 2 public industrials — 90 days to single pipeline. Happy to compare notes.",
            opener: '"James, with 47 integration blockers and the Q4 2026 control plane deadline — what\'s the current unification sequencing across the 3 engineering orgs?"',
            footnote: 'GENERATED FROM: dual acquisition + 47 integration blockers + 3 CI systems + 11 backfill roles',
        },
        trace: [
            { time: '2026.02.21 09:18:01', agent: 'RESEARCH_AGENT ', action: 'fetched 2 SEC filings, 6 job posts, 3 Glassdoor reviews for Aperture' },
            { time: '2026.02.21 09:18:03', agent: 'FINANCE_AGENT  ', action: 'gross margin stable 62%, $18M integration cost, stock –14%' },
            { time: '2026.02.21 09:18:05', agent: 'TECH_AGENT     ', action: '3 CI systems, 47 integration blockers, no shared artifact registry' },
            { time: '2026.02.21 09:18:07', agent: 'CONFLICT_AGENT ', action: 'risk: VectorFlow talent attrition — 11 backfills in 60 days' },
            { time: '2026.02.21 09:18:09', agent: 'SYNTHESIS_AGENT', action: 'long cycle but high data coverage — plant seeds now, harvest Q3 2026' },
            { time: '2026.02.21 09:18:10', agent: 'DECISION_AGENT ', action: 'verdict: LOW. Window: 6+ months. Recommended persona: SVP Platform.' },
        ],
    },
];
