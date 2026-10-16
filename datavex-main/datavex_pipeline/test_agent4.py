from agent1_discovery import run as run_agent1
from agent2_signals import run as run_agent2
from agent3_scoring import run as run_agent3
from agent4_decision_maker import run as run_agent4


def main():
    candidates = run_agent1("AI infra companies")
    signals = run_agent2(candidates)
    scored = run_agent3(candidates, signals)
    decisions = run_agent4(scored)

    print("\n==============================")
    print("      AGENT 4 DECISIONS")
    print("==============================\n")

    for d in decisions:
        print(d["company_name"])
        print("Priority:", d["priority"])
        print("Strategy:", d["strategy"])
        print("Offer:", d["recommended_offer"])
        print("Entry Point:", d["entry_point"])

        print(
            "Intent:", d["intent_score"],
            "| Conversion:", d["conversion_score"],
            "| Deal Size:", d["deal_size_score"],
            "| Risk:", d["risk_score"]
        )

        print("-" * 50)


if __name__ == "__main__":
    main()