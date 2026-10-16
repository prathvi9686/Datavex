"""
DataVex — Capability Knowledge Base
ChromaDB-backed RAG store of Datavex's services and case study patterns.
Falls back to keyword cosine similarity if ChromaDB/embeddings unavailable.

Usage:
    python knowledge_base.py --init    # create/reset collection
    python knowledge_base.py --query "high strain fintech scale-up"
"""
import json
import math
import logging
import os
import sys

logger = logging.getLogger("datavex.kb")

# ── Datavex Service Catalogue ────────────────────────────────────
DATAVEX_SERVICES = [
    {
        "id":          "ai_infra_buildout",
        "name":        "AI Infra Buildout",
        "description": (
            "Custom AI infrastructure build for SCALE_UP companies with BUILD_HEAVY strategy. "
            "Best for companies showing high strain scores (>0.6), hiring data/ML engineers, and "
            "lacking internal AI platform. Typical engagement: 3-6 months, dedicated team."
        ),
        "triggers":    ["BUILD_HEAVY", "high strain", "scale_up", "hiring engineers",
                         "ml infrastructure", "pipeline bottleneck", "data platform"],
        "upsell":      ["ml_pipeline_audit", "technical_advisory"],
        "deal_size":   "LARGE",
        "best_fit_states": ["SCALE_UP"],
        "best_fit_strategies": ["BUILD_HEAVY"],
    },
    {
        "id":          "ml_pipeline_audit",
        "name":        "ML Pipeline Audit",
        "description": (
            "Deep-dive audit of existing ML/data pipelines for companies with INFRA signals and "
            "medium conversion likelihood. Identifies bottlenecks, costs, and migration paths. "
            "Ideal entry point for companies evaluating Datavex before committing to a full build."
        ),
        "triggers":    ["infra signals", "legacy stack", "pipeline issues", "latency",
                         "CO_BUILD", "medium conversion", "tech debt", "wordpress", "legacy"],
        "upsell":      ["ai_infra_buildout", "technical_advisory"],
        "deal_size":   "MEDIUM",
        "best_fit_states": ["SCALE_UP", "MATURE"],
        "best_fit_strategies": ["CO_BUILD", "AUDIT"],
    },
    {
        "id":          "data_strategy_workshop",
        "name":        "Data Strategy Workshop",
        "description": (
            "Half-day workshop for decision makers to define their data/AI roadmap. "
            "Best for companies early in their data journey — small/mid size, low internal tech strength. "
            "Great entry point for construction, retail, and IT services companies. "
            "Converts to ongoing advisory or pipeline audit."
        ),
        "triggers":    ["small company", "low tech strength", "early stage", "MONITOR",
                         "retail", "construction", "IT services", "no data team",
                         "data strategy", "digital transformation"],
        "upsell":      ["technical_advisory", "ml_pipeline_audit"],
        "deal_size":   "SMALL",
        "best_fit_states": ["EARLY_GROWTH"],
        "best_fit_strategies": ["MONITOR", "CO_BUILD"],
    },
    {
        "id":          "technical_advisory",
        "name":        "Technical Advisory Retainer",
        "description": (
            "Monthly retainer for companies that need ongoing AI/data guidance without a full build. "
            "Best for MONITOR strategy companies to keep relationship warm. "
            "Also suits IT services firms who want to upskill their team. "
            "High recurrence, compounds into larger engagements over time."
        ),
        "triggers":    ["MONITOR", "ongoing", "retainer", "advisory", "IT services",
                         "relationship", "upskill", "recurring", "low conversion"],
        "upsell":      ["ml_pipeline_audit", "ai_infra_buildout"],
        "deal_size":   "SMALL",
        "best_fit_states": ["ANY"],
        "best_fit_strategies": ["MONITOR", "CO_BUILD"],
    },
    {
        "id":          "data_platform_integration",
        "name":        "Data Platform Integration",
        "description": (
            "Integrate disparate data sources into a unified modern data platform "
            "(Snowflake, dbt, Spark, or similar). Best for LARGE companies with existing infra "
            "but fragmented data sources. Pharma, engineering software, and agri-tech are ideal fits."
        ),
        "triggers":    ["data integration", "fragmented data", "multiple sources", "LARGE company",
                         "pharma", "agri-tech", "engineering software", "platform",
                         "snowflake", "dbt", "spark", "unified"],
        "upsell":      ["ml_pipeline_audit", "ai_infra_buildout"],
        "deal_size":   "LARGE",
        "best_fit_states": ["MATURE", "SCALE_UP"],
        "best_fit_strategies": ["PLATFORM", "BUILD_HEAVY", "CO_BUILD"],
    },
    {
        "id":          "ai_readiness_assessment",
        "name":        "AI Readiness Assessment",
        "description": (
            "Structured 2-week assessment of a company's data maturity, infrastructure, and team "
            "readiness for AI adoption. Deliverable: scored report + prioritised roadmap. "
            "Best for companies that have expressed AI interest but haven't started. "
            "Low barrier to entry, high conversion to larger engagements."
        ),
        "triggers":    ["assessment", "readiness", "not started", "exploring AI",
                         "data maturity", "roadmap", "early", "small", "medium"],
        "upsell":      ["data_strategy_workshop", "ml_pipeline_audit"],
        "deal_size":   "SMALL",
        "best_fit_states": ["EARLY_GROWTH", "SCALE_UP"],
        "best_fit_strategies": ["MONITOR", "CO_BUILD"],
    },
    {
        "id":          "real_time_streaming_build",
        "name":        "Real-Time Streaming Pipeline Build",
        "description": (
            "End-to-end Kafka/Flink/Spark Streaming pipeline for companies needing live data "
            "processing — e-commerce, fintech, streaming platforms. "
            "Best for companies with PRODUCT signals (new features needing real-time data). "
            "Spotify and similar companies with live listener analytics are ideal."
        ),
        "triggers":    ["real-time", "streaming", "kafka", "live data", "low latency",
                         "music", "e-commerce", "fintech", "product launch", "PRODUCT signal"],
        "upsell":      ["ai_infra_buildout", "ml_pipeline_audit"],
        "deal_size":   "LARGE",
        "best_fit_states": ["SCALE_UP", "MATURE"],
        "best_fit_strategies": ["BUILD_HEAVY", "CO_BUILD"],
    },
]

# Persist as JSON alongside this file for easy editing
_KB_PATH = os.path.join(os.path.dirname(__file__), "datavex_kb.json")


# ── Save/load catalogue ──────────────────────────────────────────

def save_catalogue():
    with open(_KB_PATH, "w") as f:
        json.dump(DATAVEX_SERVICES, f, indent=2)
    print(f"✅ Knowledge base saved: {_KB_PATH} ({len(DATAVEX_SERVICES)} services)")


def load_catalogue() -> list[dict]:
    if os.path.exists(_KB_PATH):
        with open(_KB_PATH) as f:
            return json.load(f)
    return DATAVEX_SERVICES


# ── Keyword Cosine Similarity (no-dep fallback) ──────────────────

def _tokenize(text: str) -> dict[str, int]:
    """Simple bag-of-words tokenizer."""
    import re
    words = re.findall(r"[a-z_]+", text.lower())
    freq  = {}
    for w in words:
        freq[w] = freq.get(w, 0) + 1
    return freq


def _cosine(a: dict, b: dict) -> float:
    common = set(a) & set(b)
    if not common:
        return 0.0
    dot  = sum(a[w] * b[w] for w in common)
    magA = math.sqrt(sum(v*v for v in a.values()))
    magB = math.sqrt(sum(v*v for v in b.values()))
    return dot / (magA * magB) if magA and magB else 0.0


def keyword_search(query: str, top_k: int = 3) -> list[dict]:
    """
    Cosine similarity retrieval over service descriptions.
    Returns top_k services sorted by relevance.
    """
    catalogue = load_catalogue()
    q_tokens  = _tokenize(query)
    scored = []
    for svc in catalogue:
        doc = svc["description"] + " " + " ".join(svc["triggers"])
        d_tokens = _tokenize(doc)
        sim = _cosine(q_tokens, d_tokens)
        scored.append((sim, svc))
    scored.sort(key=lambda x: -x[0])
    return [s for _, s in scored[:top_k]]


# ── ChromaDB-backed retrieval (enhanced, with Ollama embeddings) ──

def _get_chroma_collection():
    """Get or create ChromaDB collection. Returns None if chromadb unavailable."""
    try:
        import chromadb
        from chromadb.config import Settings

        db_path   = os.path.join(os.path.dirname(__file__), "chroma_db")
        client    = chromadb.PersistentClient(path=db_path)
        collection = client.get_or_create_collection(
            name="datavex_services",
            metadata={"hnsw:space": "cosine"},
        )
        return collection
    except ImportError:
        logger.info("chromadb not installed — using keyword fallback")
        return None
    except Exception as e:
        logger.warning("ChromaDB init failed: %s", e)
        return None


def init_knowledge_base(force: bool = False):
    """
    Initialise or reset the ChromaDB knowledge base.
    Call once before running the pipeline.
    """
    save_catalogue()

    collection = _get_chroma_collection()
    if collection is None:
        print("⚠  ChromaDB unavailable — keyword search will be used as fallback")
        return

    if collection.count() > 0 and not force:
        print(f"ℹ  Knowledge base already has {collection.count()} entries (use --force to reset)")
        return

    if force and collection.count() > 0:
        collection.delete(ids=[s["id"] for s in DATAVEX_SERVICES if True])

    catalogue = load_catalogue()

    # Try Ollama embeddings first, fall back to chromadb default
    from ollama_client import ollama_embed

    for svc in catalogue:
        doc = svc["description"] + " " + " ".join(svc["triggers"])
        embedding = ollama_embed(doc)

        kwargs: dict = {
            "ids":        [svc["id"]],
            "documents":  [doc],
            "metadatas":  [{
                "name":       svc["name"],
                "deal_size":  svc["deal_size"],
                "strategies": ",".join(svc.get("best_fit_strategies", [])),
                "upsell":     ",".join(svc.get("upsell", [])),
            }],
        }
        if embedding:
            kwargs["embeddings"] = [embedding]

        collection.upsert(**kwargs)

    print(f"✅ Knowledge base initialised: {len(catalogue)} services in ChromaDB")


def retrieve(query: str, top_k: int = 3) -> list[dict]:
    """
    Retrieve top_k relevant Datavex services for a given company query.
    Uses ChromaDB if available, falls back to keyword cosine.

    query: natural language description of the company
    Returns: list of service dicts with added 'relevance_score' field
    """
    collection = _get_chroma_collection()

    if collection and collection.count() > 0:
        from ollama_client import ollama_embed
        embedding = ollama_embed(query)

        if embedding:
            results = collection.query(
                query_embeddings=[embedding],
                n_results=min(top_k, collection.count()),
                include=["metadatas", "distances", "documents"],
            )
            catalogue = {s["id"]: s for s in load_catalogue()}
            out = []
            for i, doc_id in enumerate(results["ids"][0]):
                svc = catalogue.get(doc_id, {})
                svc["relevance_score"] = round(1 - results["distances"][0][i], 3)
                out.append(svc)
            return out
        else:
            # Ollama embed down — use chromadb text query
            results = collection.query(
                query_texts=[query],
                n_results=min(top_k, collection.count()),
                include=["metadatas", "distances"],
            )
            catalogue = {s["id"]: s for s in load_catalogue()}
            out = []
            for i, doc_id in enumerate(results["ids"][0]):
                svc = catalogue.get(doc_id, {})
                svc["relevance_score"] = round(1 - results["distances"][0][i], 3)
                out.append(svc)
            return out

    # Pure keyword fallback
    results = keyword_search(query, top_k)
    for r in results:
        r["relevance_score"] = 0.5  # unknown when keyword only
    return results


# ── CLI ──────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse
    logging.basicConfig(level=logging.INFO)

    parser = argparse.ArgumentParser()
    parser.add_argument("--init",  action="store_true", help="Initialise ChromaDB KB")
    parser.add_argument("--force", action="store_true", help="Force reset KB")
    parser.add_argument("--query", default="", help="Test query")
    args = parser.parse_args()

    if args.init or args.force:
        init_knowledge_base(force=args.force)

    if args.query:
        print(f"\nQuery: {args.query}\n")
        hits = retrieve(args.query, top_k=3)
        for h in hits:
            print(f"  [{h.get('relevance_score', 0):.2f}] {h['name']}")
            print(f"       {h['description'][:100]}...")
            print(f"       Upsell: {', '.join(h.get('upsell', []))}")
