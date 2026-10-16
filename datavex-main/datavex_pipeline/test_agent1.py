from agent1_discovery import run

def main():
    results = run("AI infra companies")

    print("\nAGENT 1 OUTPUT\n")
    for c in results:
        print(c.company_name, "|", c.industry, "|", c.region)

if __name__ == "__main__":
    main()