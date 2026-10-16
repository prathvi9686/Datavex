from agent1_discovery import run as run_agent1
from agent2_signals import run as run_agent2


def main():
    candidates = run_agent1("AI infra companies")
    results = run_agent2(candidates)

    print("\n==============================")
    print("       AGENT 2 OUTPUT")
    print("==============================\n")

    for r in results:
        print(r["company_name"])
        print("Fit:", r["fit_type"], "| State:", r["company_state"])

        print("Expansion Score:", r["expansion_score"])
        print("Strain Score:", r["strain_score"])
        print("Risk Score:", r["risk_score"])

        print("Pain Level:", r["pain_level"], "| Pain Score:", r["pain_score"])

        print("Signals:")
        for s in r["signals"]:
            print(f"  - [{s['type']}] recency={s.get('recency_days')}")

        print("-" * 50)


if __name__ == "__main__":
    main()