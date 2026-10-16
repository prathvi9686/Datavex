from agent1_discovery import run as run_agent1
from agent2_signals import run as run_agent2
from agent3_scoring import run as run_agent3
from agent35_strategy import run as run_agent35

def main():

    candidates = run_agent1("AI infra companies")
    signals = run_agent2(candidates)
    opps = run_agent3(candidates, signals)
    strategies = run_agent35(opps, signals)

    print("\nAGENT 3.5 OUTPUT\n")

    for s in strategies:
        print(s["company_name"])
        print("Style:", s["buying_style"])
        print("Offer:", s["offer"])
        print("Entry:", s["entry_point"])
        print("-"*40)

if __name__ == "__main__":
    main()