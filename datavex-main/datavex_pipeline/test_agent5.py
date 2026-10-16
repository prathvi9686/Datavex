from agent1_discovery import run as run_agent1
from agent2_signals import run as run_agent2
from agent3_scoring import run as run_agent3
from agent4_decision_maker import run as run_agent4
from agent5_outreach import run as run_agent5


def main():
    candidates = run_agent1("AI infra companies")
    signals = run_agent2(candidates)
    scored = run_agent3(candidates, signals)
    decisions = run_agent4(scored)
    outreach = run_agent5(decisions)

    print("\n==============================")
    print("      AGENT 5 OUTREACH")
    print("==============================\n")

    print("Total outputs:", len(outreach), "\n")

    for o in outreach:
        print(o["company_name"])
        print("Strategy:", o["strategy"])
        print("Persona:", o["persona"])
        print("Channel:", o["channel"])
        print("Subject:", o["subject"])
        print("\nMessage:\n")
        print(o["message"])
        print("\n" + "-" * 60 + "\n")


if __name__ == "__main__":
    main()