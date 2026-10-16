# DataVex AI — Full Project Context

> This document provides complete context for understanding, modifying, or extending the DataVex Intelligence Platform. Feed this to any AI assistant to give them full project understanding.

## What DataVex Is

DataVex AI is a **sales intelligence platform** that uses multi-agent AI synthesis to identify, score, and prioritize B2B target accounts. It scrapes public signals (GitHub issues, job postings, SEC filings, G2 reviews, Glassdoor, LinkedIn) and synthesizes them into actionable intelligence reports.

The product answers one question: **"Which company should I sell to, why, and how?"**

## Architecture

```
Frontend (React + Vite)  →  Static data layer (data.js)
                          →  Future: REST API (api.datavex.ai/v1)
```

- **Frontend**: React 18, Vite, vanilla CSS (no Tailwind), inline styles for components
- **State**: React `useState` + `useCallback`, `localStorage` for auth
- **Routing**: No router — two views (`leadboard` | `report`) managed via state
- **Charts**: Custom SVG (sparkline + arc ring) — no chart libraries
- **Data**: Static `data.js` with 3 fully-specified company targets

## Tech Stack

| Layer | Technology |
|---|---|
| Framework | React 18 (functional components, hooks) |
| Build | Vite |
| Styling | Vanilla CSS tokens + inline styles |
| Fonts | Instrument Serif (display), Geist Sans (body), Geist Mono (code) |
| Auth | `localStorage` token (`datavex_auth`) |
| Charts | Hand-rolled SVG (Sparkline, ScoreArc) |

## Design System — "Calm Editorial Intelligence"

### Color Palette
```
--bg:            #F9F7F4    (warm paper)
--surface:       #FFFFFF    (card backgrounds)
--border:        #E8E4DE    (subtle dividers)
--text-primary:  #181612    (near-black)
--text-muted:    #9B9489    (secondary text)
--accent:        #1A6B47    (editorial green — scores, CTAs, highlights)
--accent-hover:  #155C3D    (darker green on hover)
--warning:       #C2601F    (terracotta — declining metrics, pressure signals)
--accent-tint:   #F0F7F3    (green tint backgrounds)
--sidebar-bg:    #F2EFE9    (warm grey sidebar)
--hover-bg:      #F5F3F0    (row/card hover state)
```

### Typography
```
Display:  'Instrument Serif', serif    → headings, company names, scores
Body:     'Geist Sans', sans-serif     → paragraphs, labels, descriptions
Mono:     'Geist Mono', monospace      → data labels, traces, timestamps
```

### Radius Scale (V7 — premium soft)
```
Cards:            24px
Buttons (primary): 20px (pill)
Buttons (secondary): 12px
Pain tag chips:    20px (pill)
Input fields:      12px
Sidebar items:     12px
Minimum anywhere:  8px
```

### Shadow
```
Default:  0 2px 12px rgba(0,0,0,0.06), 0 1px 3px rgba(0,0,0,0.04)
Hover:    0 4px 16px rgba(0,0,0,0.08), 0 2px 4px rgba(0,0,0,0.04)
Button:   0 2px 8px rgba(26,107,71,0.25)
```

## File Structure

```
src/
├── App.jsx              Main app shell: sidebar, views, company report
├── Login.jsx            Admin login (admin/admin)
├── LeadBoard.jsx        3-column card grid of target companies
├── CapabilityMatch.jsx  Full-width capability cards with inline pain evidence
├── Charts.jsx           Sparkline (SVG) + ScoreArc (SVG ring)
├── data.js              Static company/capability data (3 companies, 5 capabilities)
├── index.css            Design tokens, reset, animations
└── main.jsx             React entry point
```

## Data Model

### Company Object
Each company in `COMPANIES` array has:
```
id               string        unique slug
name             string        display name (serif)
descriptor       string        "Industry · Employees · Stage · ARR"
score            number        0–100 opportunity score
confidence       string        HIGH | MEDIUM | LOW
coverage         number        0–100 data coverage percentage
receptivity      string        "HIGH — ACT WITHIN 90 DAYS"
painTags         string[]      ["HIGH PAIN", "MED PAIN", "LOW PAIN"]
financials       object        { quarters[], margin[], revenue[] }
hiring           object[]      { category, count, type: positive|warning|neutral }
scoreBreakdown   object[]      { label, value, max }
timeline         object[]      { date, type, label, source }
painClusters     object[]      { title, evidence[{source, text}] }
decisionMaker    object        { name, role, topics[], messaging{angle, vocab[], tone} }
outreach         object        { email, linkedin, opener, footnote }
capabilityMatch  object[]      { pain, source, severity, capability }
strongestMatch   object        { score, capability, pain, gap }
trace            object[]      { time, agent, action }
```

### Capability Object
```
name             string        capability name
score            number        0–100 strength score
desc             string        description
```

### Current Companies
1. **Meridian Systems** — Enterprise SaaS, score 87, HIGH confidence. Pain: pipeline failures, deployment velocity, observability gaps. DM: Marcus Rivera (VP Eng).
2. **Lattice Dynamics** — Fintech, score 64, MEDIUM confidence. Pain: compliance gaps, monolith decomposition, quant infra scaling. DM: Diana Kowalski (CTO).
3. **Aperture Robotics** — Industrial automation, score 41, LOW confidence. Pain: multi-system integration, talent retention, control plane unification. DM: James Okafor (SVP Platform Eng).

## User Flows

### Flow 1: Lead Board → Company Report
1. User logs in (admin/admin)
2. Lands on Lead Board — 3 premium cards showing company name, score, pain tags, DM target
3. Clicks a company card
4. Sidebar updates: shows company name + scroll anchor links (Signal Engine, Capability Match, Reasoning Log)
5. Main area shows single-page report. User scrolls through:
   - **Header**: Company name, descriptor, ScoreArc (88px SVG ring), confidence/coverage
   - **At a Glance**: Two-column — Operating Margin (inline sparkline) + Score Breakdown (table). Below: Hiring Signals (two-column text list)
   - **Why Now**: Receptivity badge + timeline (two-column, dot-connected events)
   - **Where It Hurts**: Two-column pain cluster cards with evidence sources
   - **Who to Talk To**: Two-column — DM profile + messaging card (angle, vocab, tone)
   - **Reach Out**: Tab switcher (EMAIL/LINKEDIN/OPENER) + copy button
   - **Capability Match**: Strongest match summary (green tint card, 52px score%) + full-width capability cards with inline "Matches: ..." evidence
   - **Reasoning Log**: Verdict header + trace box (timestamps, agents, actions)

### Flow 2: Sidebar Scroll Anchors
- When viewing a company report, sidebar shows jump links
- Clicking "Capability Match" smoothly scrolls to that section
- No page navigation — everything is one continuous scroll

## API Contract (Summary)

Full contract at: `api_contract.md` in the artifacts directory.

| Endpoint | Method | Purpose |
|---|---|---|
| `/auth/login` | POST | JWT authentication |
| `/companies` | GET | Lead Board list (sortable, filterable) |
| `/companies/:id` | GET | Full intelligence report |
| `/capabilities` | GET | Platform capability list |
| `/companies/:id/capability-match` | GET | Capability → pain mapping |
| `/companies/:id/trace` | GET | Multi-agent reasoning log |
| `/companies/:id/outreach/generate` | POST | Regenerate outreach drafts |
| `/scan` | POST | Trigger full intelligence scan |
| `/scan/:scan_id` | GET | Check scan progress |
| `/system/status` | GET | Platform health check |

## Multi-Agent System

DataVex uses 6 specialized agents that run in sequence:

1. **RESEARCH_AGENT** — Fetches raw data (earnings, filings, job posts, reviews)
2. **FINANCE_AGENT** — Analyzes margin trends, burn rate, revenue trajectory
3. **TECH_AGENT** — Scans GitHub issues, tech stack signals, infrastructure patterns
4. **CONFLICT_AGENT** — Identifies contradictions between signals
5. **SYNTHESIS_AGENT** — Resolves conflicts, builds unified narrative
6. **DECISION_AGENT** — Issues final verdict (HIGH/MEDIUM/LOW), window, persona

## Coding Conventions

- **No external UI libraries** — everything is hand-built with inline styles
- **Design tokens** are CSS custom properties in `index.css`
- **Components** are functional with hooks (`useState`, `useEffect`, `useCallback`)
- **No prop drilling** — data flows from `App.jsx` down max 2 levels
- **Animations** use CSS keyframes (`sectionUp`, `contentFade`, `traceIn`)
- **All radii** use the V7 premium scale (24px cards, 20px pills, 12px inputs)
- **Full-width layout** — no max-width constraints, content fills viewport with `padding: 40px 64px`

## Important Design Rules

1. **Nothing floats in the center** — all content fills available width
2. **Pain tags are bordered pills, never filled blobs** — `1px solid` with matching text color
3. **Scores use Instrument Serif** — large, green for HIGH (≥80), terracotta for MEDIUM (≥60), muted for LOW
4. **Evidence sources get pill badges** — `background: var(--accent-tint)`, mono font
5. **Section labels** have a small green dot prefix + uppercase mono tracking
6. **Hover states** are subtle — background shift to `#F5F3F0`, border color to accent, 150ms
7. **No chart library aesthetic** — sparklines and arcs only, no axes, no chrome
