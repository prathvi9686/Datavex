"""
DataVex Pipeline — Configuration
LLM client, capability graph, role maps, and all constants.
Supports OFFLINE demo mode when no API key is available.
"""
import os, json, logging, time
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env"))

logger = logging.getLogger("datavex_pipeline")

# ── LLM Setup ───────────────────────────────────────────────
LLM_MODEL = os.getenv("LLM_MODEL", "openai/gpt-4.1")
OPENAI_API_KEY = os.getenv("BYTEZ_API_KEY", os.getenv("OPENAI_API_KEY", ""))
OPENAI_BASE_URL = os.getenv("BYTEZ_BASE_URL", "https://api.bytez.com/models/v2/openai/v1")

# Detect offline mode — 'ollama' counts as a valid key
OFFLINE_MODE = not OPENAI_API_KEY or OPENAI_API_KEY.strip() == ""

client = None
if not OFFLINE_MODE:
    from openai import OpenAI
    client = OpenAI(api_key=OPENAI_API_KEY, base_url=OPENAI_BASE_URL)
else:
    logger.warning("No API key found — running in OFFLINE demo mode (deterministic fallbacks)")


def llm_call_with_retry(prompt: str, system: str = "", retries: int = 2) -> dict:
    """
    Call LLM with strict JSON output. Retries on parse failure.
    Falls back to deterministic responses in OFFLINE mode.
    """
    if OFFLINE_MODE:
        return _offline_fallback(prompt, system)

    messages = []
    if system:
        messages.append({"role": "system", "content": system + "\n\nReturn ONLY valid JSON. No markdown, no preamble, no explanation."})
    messages.append({"role": "user", "content": prompt})

    for attempt in range(retries + 1):
        try:
            resp = client.chat.completions.create(
                model=LLM_MODEL,
                messages=messages,
                temperature=0.4,
                max_completion_tokens=4096,
                response_format={"type": "json_object"},
            )
            raw = resp.choices[0].message.content.strip()
            # Clean markdown fences
            if raw.startswith("```json"):
                raw = raw[7:]
            if raw.startswith("```"):
                raw = raw[3:]
            if raw.endswith("```"):
                raw = raw[:-3]
            raw = raw.strip()
            return json.loads(raw)
        except (json.JSONDecodeError, Exception) as e:
            logger.warning(f"LLM call attempt {attempt+1} failed: {e}")
            if attempt == retries:
                try:
                    start = raw.find("{")
                    end = raw.rfind("}") + 1
                    if start >= 0 and end > start:
                        return json.loads(raw[start:end])
                except Exception:
                    pass
                raise Exception(f"LLM JSON parse failed after {retries+1} attempts: {e}")
            time.sleep(0.5)
    return {}


def _offline_fallback(prompt: str, system: str) -> dict:
    """Deterministic fallback for demo mode — parses prompt to return sensible defaults."""
    p = prompt.lower()

    # Agent 1: Intent parsing
    if "parse" in p and "intent" in p:
        return {
            "industries": ["fintech", "AI SaaS", "AI Infrastructure"],
            "tech_focus": ["data engineering", "cloud modernization", "AI", "ML"],
            "regions": ["India"],
            "size_preference": ["small", "mid"],
        }

    # Agent 2: Signal classification
    if "classify" in p and ("pivot" in p or "tech_debt" in p or "signal" in p):
        if "krea" in p:
            return {
                "pivot": {"label": "Enterprise AI expansion — Series A + AWS partnership + enterprise sales hiring", "evidence_indices": [0, 3]},
                "tech_debt": {"label": "Monolith to composable inference mesh migration underway", "evidence_indices": [1, 6]},
                "fiscal_pressure": None,
            }
        elif "slice" in p:
            return {
                "pivot": None,
                "tech_debt": {"label": "Legacy Java monolith blocking velocity — 28min CI builds, strangler fig migration stalled", "evidence_indices": [0, 1, 5]},
                "fiscal_pressure": {"label": "10% layoff, 30% burn reduction mandate, profitability pressure", "evidence_indices": [3, 6]},
            }
        elif "sarvam" in p:
            return {
                "pivot": {"label": "Government AI contract — sovereign AI stack for healthcare and agriculture", "evidence_indices": [2]},
                "tech_debt": None,
                "fiscal_pressure": None,
            }
        return {"pivot": None, "tech_debt": None, "fiscal_pressure": None}

    # Agent 3: Strategic summary
    if "strategic_summary" in p or "why_we_win" in p:
        if "krea" in p:
            return {
                "strategic_summary": "Krea.ai is expanding from product-led AI into enterprise accounts with a fresh $12M Series A. Their infrastructure migration from monolithic to composable inference and active K8s + data pipeline hiring signals strong alignment with DataVex cloud DevOps and data engineering capabilities.",
                "why_we_win": [
                    "Direct capability match: Krea needs K8s migration + data pipeline expertise — DataVex core strength",
                    "Timing: Series A capital + enterprise sales hire = budget allocated for infrastructure partners",
                    "CTO blog confirms composable architecture goals — DataVex has delivered similar transformations",
                    "Small team (150) means vendor decisions happen fast with fewer stakeholders",
                ],
                "risks": [
                    "Small company may prefer hiring in-house over consulting engagement",
                    "AI-native team may have strong opinions about architecture — need to demo engineering depth",
                    "Deal size may start below $500K minimum until enterprise revenue materializes",
                ],
            }
        elif "slice" in p:
            return {
                "strategic_summary": "Slice is under dual pressure: cost-cutting mandate from 10% layoffs and a stalled legacy Java monolith migration that's blocking engineering velocity. Their SRE hiring and 4 P0 incidents/week create urgency for DataVex's cloud modernization and data engineering capabilities.",
                "why_we_win": [
                    "Legacy modernization is DataVex's sweet spot — strangler fig pattern, cloud migration tooling",
                    "Cost pressure means they need a partner who delivers ROI, not a moonshot vendor",
                    "VP Eng blog post explicitly calls tech debt 'the biggest blocker to profitability' — they know the problem",
                ],
                "risks": [
                    "Budget may be constrained given layoffs and burn reduction goals",
                    "Internal politics: layoffs create fear, new vendor engagement may face resistance",
                ],
            }
        elif "sarvam" in p:
            return {
                "strategic_summary": "Sarvam AI has strong government backing but limited commercial urgency. Their focus is research-first with revenue as secondary. DataVex capability alignment is narrow — primarily AI analytics, not their core infrastructure need of GPU cluster management.",
                "why_we_win": [
                    "Government contracts require compliance and data engineering capabilities DataVex offers",
                ],
                "risks": [
                    "Revenue is secondary to impact — unlikely to prioritize vendor partnerships",
                    "80-person team with PhD-heavy culture may not value consulting partnerships",
                    "Government procurement cycles are slow and unpredictable",
                ],
            }
        return {"strategic_summary": "Opportunity identified.", "why_we_win": ["Capability match"], "risks": ["Limited data"]}

    # Agent 5: Outreach generation — MUST check BEFORE Agent 4 (Agent 5 prompts contain 'persona' as substring)
    if ("generate" in p and "outreach" in p) or ("email" in p and "linkedin" in p and "call_opener" in p):
        if "krea" in p:
            return {
                "email": "Subject: Re: Your inference mesh migration\n\nAnkit —\n\nYour CTO blog on moving from monolithic model serving to composable inference was sharp — 4x throughput and 60% cost reduction is exactly the kind of lift we build infrastructure for.\n\nWith 150 engineers scaling to enterprise and fresh Series A capital, the K8s migration and data pipeline build-out will define your next 12 months.\n\nWe've run this exact migration for 3 AI-native companies at your stage — shared artifact registries, sub-5-minute CI, production inference pipelines processing 50M+ events/day.\n\nWorth 20 minutes to compare architectures?\n\n— DataVex",
                "linkedin_dm": "Ankit — loved the composable inference mesh post. With Krea scaling to enterprise, the K8s + data pipeline build matters. We've done this exact migration for 3 similar-stage AI companies. Worth comparing notes?",
                "call_opener": "Ankit, quick question — with the enterprise push and 50M events/day pipeline target, how are you sequencing the K8s migration against the data infrastructure build-out?",
            }
        elif "slice" in p:
            return {
                "email": "Subject: Monolith migration — closing the 3x velocity gap\n\nRajesh —\n\n28-minute CI builds and 4 P0 incidents per week on a monolith that your VP Eng calls 'the biggest blocker to profitability.' That math doesn't improve on its own.\n\nWe've run strangler-fig decompositions at 4 fintech companies at your scale — average outcome: CI under 8 minutes, P0s down 70%, feature velocity 3x in 90 days.\n\nWith the 30% burn reduction mandate, you need a partner that delivers measurable ROI, not a 18-month consulting engagement. We scope to 90-day milestones.\n\n20 minutes to walk through the decomposition playbook?\n\n— DataVex",
                "linkedin_dm": "Rajesh — 28-minute CI builds and 4 P0 incidents/week on a monolith is rough. We helped 4 similar fintechs hit sub-8-minute builds and 70% fewer incidents in 90 days. Worth a quick look?",
                "call_opener": "Rajesh, with the 30% burn reduction mandate and the monolith migration on an 18-month timeline — how are you prioritizing which services to decompose first?",
            }
        elif "sarvam" in p:
            return {
                "email": "Subject: Data infrastructure for sovereign AI\n\nVivek —\n\nCongratulations on the ₹200Cr government AI contract. Building India's sovereign AI stack for healthcare and agriculture is ambitious — and the data engineering layer between Sarvam-1 and production deployment will make or break the timeline.\n\nWe build production-grade data pipelines and compliance infrastructure for AI teams — the layer that turns research models into reliable government-grade deployments.\n\nHappy to share how we've built similar infrastructure — no commitment, just relevant architecture patterns.\n\n— DataVex",
                "linkedin_dm": "Vivek — congrats on the ₹200Cr government AI contract. The data pipeline layer between Sarvam-1 and production deployment is where we live. Happy to share relevant architecture patterns.",
                "call_opener": "Vivek, with the government AI contract and Sarvam-1 model — what does the production deployment pipeline look like for healthcare and agriculture use cases?",
            }
        return {"email": "", "linkedin_dm": "", "call_opener": ""}

    # Agent 4: Persona generation — check for 'target role' which is unique to Agent 4 prompts
    if "target role" in p or ("decision maker" in p and "messaging_angle" in p):
        if "krea" in p:
            return {
                "name": "Ankit Mehta",
                "messaging_angle": "Your inference mesh migration needs infrastructure partners who've scaled K8s + data pipelines for enterprise AI — DataVex has done this for 3 similar-stage companies.",
                "pain_points_aligned": ["K8s migration complexity", "Enterprise-grade data pipeline reliability", "Inference infrastructure scaling"],
                "persona_risks": ["CTO founded the company — strong ownership of architecture decisions", "May prefer open-source tooling over vendor solutions"],
            }
        elif "slice" in p:
            return {
                "name": "Rajesh Krishnamurthy",
                "messaging_angle": "Your tech debt is costing you 3x on every feature — DataVex can cut your monolith migration timeline by 60% and get CI builds under 8 minutes.",
                "pain_points_aligned": ["Monolith decomposition blocking feature velocity", "P0 incident rate eroding customer trust", "Cost pressure requiring ROI-positive vendor choices"],
                "persona_risks": ["Budget-constrained after layoffs — any engagement needs clear ROI framing", "May be defensive about existing architecture decisions"],
            }
        elif "sarvam" in p:
            return {
                "name": "Vivek Raghavan",
                "messaging_angle": "Your government AI contracts need production-grade data pipelines and compliance infrastructure — DataVex builds the layer between research and deployment.",
                "pain_points_aligned": ["GPU cluster management at scale", "Government compliance requirements", "Research-to-production pipeline gaps"],
                "persona_risks": ["Research-first culture may deprioritize infrastructure tooling", "Government procurement requires lengthy approval cycles"],
            }
        return {"name": "Unknown DM", "messaging_angle": "", "pain_points_aligned": [], "persona_risks": []}

    # Generic fallback
    return {}


# ── DataVex Capability Graph ────────────────────────────────
DATAVEX_CAPABILITIES = {
    "ai_analytics": ["AI", "AI analytics", "AI hiring", "ML platform", "machine learning", "data science", "NLP", "computer vision", "ML", "enterprise AI", "generative"],
    "cloud_devops": ["cloud", "Kubernetes", "AWS", "cloud modernization", "DevOps", "infrastructure", "k8s", "GCP", "Azure", "Spark"],
    "digital_transformation": ["legacy modernization", "digital strategy", "ERP migration", "digital transformation"],
    "data_engineering": ["data engineering", "data pipeline", "ETL", "data warehouse", "real-time analytics", "data lake", "database"],
}

# ── Role Mapping ────────────────────────────────────────────
ROLE_MAP = {
    "TECH_MODERNIZATION": "CTO",
    "COST_OPTIMIZATION": "CFO",
    "GROWTH": "Head of Data / VP Engineering",
    "RESTRUCTURING": "CTO",
    "STABLE": "VP Engineering",
}

# ── State → Capability Mapping ──────────────────────────────
STATE_CAPABILITY_MAP = {
    "TECH_MODERNIZATION": ["cloud_devops", "digital_transformation"],
    "COST_OPTIMIZATION": ["cloud_devops", "data_engineering"],
    "GROWTH": ["ai_analytics", "data_engineering"],
    "RESTRUCTURING": ["digital_transformation"],
    "STABLE": ["ai_analytics"],
}

# ── Psychographic Trait Map ─────────────────────────────────
TRAIT_MAP = {
    "cost": {"keywords": ["cost", "efficiency", "ROI", "budget", "savings", "optimize"], "profile": "cost-focused, ROI-driven"},
    "speed": {"keywords": ["velocity", "fast", "agile", "deployment", "rapid", "quick"], "profile": "velocity-focused"},
    "innovation": {"keywords": ["AI", "ML", "new", "platform", "cutting-edge", "innovation"], "profile": "innovation-biased"},
    "reliability": {"keywords": ["stability", "uptime", "security", "compliance", "reliable"], "profile": "risk-averse"},
}
