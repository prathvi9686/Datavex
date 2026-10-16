#!/usr/bin/env python3
"""
DataVex Pipeline — Entry Point
Runs the full agent pipeline against the demo candidate universe and prints
results. This is the standalone CLI path — the live backend API calls the
same agent modules directly from backend/app/routers/discover.py.
"""
import sys
import os
import logging
import json

# Add pipeline dir to path so imports work
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from orchestrator import run_pipeline, print_detailed_results

# ── Logging ─────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s │ %(name)s │ %(message)s",
    datefmt="%H:%M:%S",
)


def main():
    print("+" + "-" * 62 + "+")
    print("|   DataVex Partner Discovery Pipeline" + " " * 24 + "|")
    print("|   Multi-Agent B2B Sales Intelligence System" + " " * 17 + "|")
    print("+" + "-" * 62 + "+")

    # Demo query — the discovery agent uses this to filter/rank the
    # candidate universe (it no longer ignores it).
    user_input = "mid-size fintech and AI SaaS companies in India looking for data engineering and cloud modernization"
    deal_profile = {
        "min_deal_usd": 500_000,
        "max_deal_usd": 10_000_000,
        "target_regions": ["India", "US"],
        "preferred_company_sizes": ["small", "mid"],
    }

    print(f"\n  Query: \"{user_input}\"")
    print(f"  Deal: ${deal_profile['min_deal_usd']:,}-${deal_profile['max_deal_usd']:,}")
    print(f"  Regions: {', '.join(deal_profile['target_regions'])}")
    print(f"  Sizes: {', '.join(deal_profile['preferred_company_sizes'])}")

    # Run pipeline
    results = run_pipeline(user_input, deal_profile)

    if not results:
        print("\n  No opportunities found. Try adjusting your query or deal profile.")
        return

    # Print detailed results
    print_detailed_results(results)

    # Save JSON output (results are already plain dicts)
    output_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "pipeline_output.json")
    with open(output_path, "w") as f:
        json.dump(results, f, indent=2, default=str)
    print(f"\n  Full JSON output saved to: {output_path}")

    # Print priority summary
    print("\n+" + "-" * 62 + "+")
    print("|  PRIORITY SUMMARY" + " " * 43 + "|")
    print("+" + "-" * 62 + "+")
    icon = {"HIGH": "[H]", "MEDIUM": "[M]", "LOW": "[L]"}
    for r in sorted(results, key=lambda x: x["opportunity"].get("opportunity_score", 0), reverse=True):
        priority = r["opportunity"].get("priority", "LOW")
        score = r["opportunity"].get("opportunity_score", 0)
        persona = r["outreach"].get("persona", "?")
        tag = icon.get(priority, "[?]")
        print(f"  {tag} {r['company_name']:20s}  {priority:6s}  score={score:.3f}  persona={persona}")

    print()


if __name__ == "__main__":
    main()
