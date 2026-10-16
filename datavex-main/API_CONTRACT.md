# DataVex AI — API Contract

> REST API specification for the DataVex Intelligence Platform backend. Base URL: `https://api.datavex.ai/v1`

---

## Authentication

### `POST /auth/login`

Authenticate a user and receive a JWT.

**Request**
```json
{
  "username": "string",
  "password": "string"
}
```

**Response `200`**
```json
{
  "token": "string (JWT)",
  "expires_at": "2026-02-22T00:00:00Z",
  "user": {
    "id": "uuid",
    "username": "string",
    "role": "admin | analyst | viewer"
  }
}
```

**Response `401`**
```json
{ "error": "Invalid credentials" }
```

> All subsequent endpoints require `Authorization: Bearer <token>` header.

---

## Companies (Lead Board)

### `GET /companies`

List all tracked target companies with summary data for the Lead Board.

**Query Params**
| Param | Type | Default | Description |
|---|---|---|---|
| `sort_by` | string | `score` | `score`, `name`, `confidence`, `updated_at` |
| `order` | string | `desc` | `asc` or `desc` |
| `confidence` | string | — | Filter: `HIGH`, `MEDIUM`, `LOW` |
| `min_score` | int | — | Minimum opportunity score |
| `limit` | int | `50` | Max results |
| `offset` | int | `0` | Pagination offset |

**Response `200`**
```json
{
  "data": [
    {
      "id": "meridian",
      "name": "Meridian Systems",
      "descriptor": "Enterprise SaaS · 2,400 employees · Series D · $180M ARR",
      "score": 87,
      "confidence": "HIGH",
      "coverage": 73,
      "receptivity": "HIGH — ACT WITHIN 90 DAYS",
      "pain_tags": ["HIGH PAIN", "HIGH PAIN", "MED PAIN"],
      "decision_maker": {
        "name": "Marcus Rivera",
        "role": "VP Engineering · Reports to interim CTO"
      },
      "strongest_match": {
        "score": 75,
        "capability": "Real-Time Pipeline Repair",
        "pain": "Connector failures causing 4hr delays"
      },
      "updated_at": "2026-02-21T09:14:11Z"
    }
  ],
  "total": 3,
  "limit": 50,
  "offset": 0
}
```

---

### `GET /companies/:id`

Full intelligence report for a single company.

**Response `200`**
```json
{
  "id": "meridian",
  "name": "Meridian Systems",
  "descriptor": "Enterprise SaaS · 2,400 employees · Series D · $180M ARR",
  "score": 87,
  "confidence": "HIGH",
  "coverage": 73,
  "receptivity": "HIGH — ACT WITHIN 90 DAYS",
  "pain_tags": ["HIGH PAIN", "HIGH PAIN", "MED PAIN"],

  "financials": {
    "quarters": ["Q1 24", "Q2 24", "Q3 24", "Q4 24", "Q1 25", "Q2 25"],
    "margin": [18.2, 17.4, 16.8, 15.9, 15.1, 14.6],
    "revenue": [38.2, 40.1, 42.1, 41.3, 43.8, 44.2]
  },

  "hiring": [
    { "category": "Engineering", "count": 24, "type": "positive" },
    { "category": "Enterprise Sales", "count": 14, "type": "positive" },
    { "category": "DevOps / SRE", "count": 9, "type": "positive" },
    { "category": "Leadership", "count": 3, "type": "warning" },
    { "category": "SMB Sales", "count": 0, "type": "neutral" }
  ],

  "score_breakdown": [
    { "label": "Tech Signals", "value": 32, "max": 35 },
    { "label": "Financial", "value": 22, "max": 25 },
    { "label": "Market Timing", "value": 18, "max": 20 },
    { "label": "Leadership", "value": 15, "max": 20 }
  ],

  "timeline": [
    {
      "date": "2025.11",
      "type": "positive",
      "label": "CEO keynote at SaaStr Annual: \"Enterprise-first by end of 2026.\"",
      "source": "SAASTR ANNUAL"
    }
  ],

  "pain_clusters": [
    {
      "title": "Data Pipeline Failures",
      "evidence": [
        {
          "source": "GH",
          "text": "22 issues tagged \"legacy-pipeline\" — 14 marked P0 — avg resolution 11.3 days."
        }
      ]
    }
  ],

  "decision_maker": {
    "name": "Marcus Rivera",
    "role": "VP Engineering · Reports to interim CTO",
    "topics": ["Platform Migration", "Developer Velocity", "Cost-per-Deploy"],
    "messaging": {
      "angle": "Your infra migration is exposed — 22 legacy pipeline issues...",
      "vocab": ["deployment velocity", "platform consolidation", "eng leverage"],
      "tone": "Direct"
    }
  },

  "outreach": {
    "email": "string (full email draft)",
    "linkedin": "string (LinkedIn message)",
    "opener": "string (cold call opener)",
    "footnote": "GENERATED FROM: Q3 margin signal + CTO departure + ..."
  },

  "capability_match": [
    {
      "pain": "Connector failures causing 4hr delays",
      "source": "GITHUB ISSUES",
      "severity": "HIGH",
      "capability": "Real-Time Pipeline Repair"
    }
  ],

  "strongest_match": {
    "score": 75,
    "capability": "Real-Time Pipeline Repair",
    "pain": "Connector failures causing 4hr delays",
    "gap": "Vector Search (no detected need)"
  },

  "trace": [
    {
      "time": "2026.02.21 09:14:02",
      "agent": "RESEARCH_AGENT",
      "action": "fetched Q2–Q4 2024 earnings transcripts for Meridian Systems"
    }
  ]
}
```

---

## Capabilities

### `GET /capabilities`

List DataVex platform capabilities (for the Capability Match Layer).

**Response `200`**
```json
{
  "data": [
    {
      "id": "pipeline-repair",
      "name": "Real-Time Pipeline Repair",
      "score": 96,
      "description": "Automated detection and self-healing of broken data connectors."
    }
  ]
}
```

---

## Capability Match

### `GET /companies/:id/capability-match`

Capability match analysis for a specific company.

**Response `200`**
```json
{
  "company_id": "meridian",
  "strongest_match": {
    "score": 75,
    "capability": "Real-Time Pipeline Repair",
    "pain": "Connector failures causing 4hr delays",
    "gap": "Vector Search (no detected need)"
  },
  "matches": [
    {
      "capability": "Real-Time Pipeline Repair",
      "capability_score": 96,
      "matched_pains": [
        {
          "pain": "Connector failures causing 4hr delays",
          "source": "GITHUB ISSUES",
          "severity": "HIGH"
        }
      ]
    },
    {
      "capability": "Vector Search Infrastructure",
      "capability_score": 73,
      "matched_pains": []
    }
  ]
}
```

---

## Reasoning Trace

### `GET /companies/:id/trace`

Multi-agent synthesis trace log for a company analysis.

**Response `200`**
```json
{
  "company_id": "meridian",
  "verdict": "HIGH",
  "recommended_persona": "VP Engineering",
  "window": "60–90 days",
  "trace": [
    {
      "time": "2026.02.21 09:14:02",
      "agent": "RESEARCH_AGENT",
      "action": "fetched Q2–Q4 2024 earnings transcripts for Meridian Systems"
    },
    {
      "time": "2026.02.21 09:14:11",
      "agent": "DECISION_AGENT",
      "action": "verdict: HIGH. Window: 60–90 days. Recommended persona: VP Eng."
    }
  ]
}
```

---

## Outreach

### `POST /companies/:id/outreach/generate`

Regenerate outreach drafts for a company.

**Request**
```json
{
  "channels": ["email", "linkedin", "opener"],
  "tone": "Direct",
  "persona": "VP Engineering"
}
```

**Response `200`**
```json
{
  "email": "string",
  "linkedin": "string",
  "opener": "string",
  "footnote": "GENERATED FROM: ..."
}
```

---

## Scan

### `POST /scan`

Trigger a full intelligence scan across all sources.

**Request**
```json
{
  "company_ids": ["meridian", "lattice"],
  "sources": ["github", "g2", "linkedin", "job_boards", "sec_filings"],
  "depth": "full"
}
```

**Response `202`**
```json
{
  "scan_id": "uuid",
  "status": "queued",
  "estimated_duration_seconds": 120
}
```

### `GET /scan/:scan_id`

Check scan progress.

**Response `200`**
```json
{
  "scan_id": "uuid",
  "status": "running",
  "progress": 0.65,
  "agents_completed": ["RESEARCH_AGENT", "FINANCE_AGENT"],
  "agents_pending": ["TECH_AGENT", "SYNTHESIS_AGENT", "DECISION_AGENT"]
}
```

---

## System

### `GET /system/status`

Health check for the platform.

**Response `200`**
```json
{
  "status": "online",
  "version": "2.4.1",
  "synth_layer": "active",
  "agents": {
    "research": "online",
    "finance": "online",
    "tech": "online",
    "conflict": "online",
    "synthesis": "online",
    "decision": "online"
  },
  "last_scan": "2026-02-21T09:18:10Z"
}
```

---

## Error Format

All errors follow this shape:

```json
{
  "error": "string (human-readable message)",
  "code": "string (machine-readable error code)",
  "details": {}
}
```

| HTTP Code | Meaning |
|---|---|
| `400` | Bad request / validation error |
| `401` | Not authenticated |
| `403` | Insufficient permissions |
| `404` | Resource not found |
| `429` | Rate limited |
| `500` | Internal server error |

---

## Rate Limits

| Endpoint | Limit |
|---|---|
| `POST /auth/login` | 10 req/min |
| `GET /companies` | 60 req/min |
| `GET /companies/:id` | 60 req/min |
| `POST /scan` | 5 req/min |
| `POST /outreach/generate` | 20 req/min |

Rate limit headers: `X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset`.
