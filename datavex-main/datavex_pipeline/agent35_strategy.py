def run(opps, signals):

    results = []

    for opp in opps:

        tech_strength = 0.8 if "MindsDB" in opp["company_name"] else 0.85

        if tech_strength > 0.75:
            style = "BUILD_HEAVY"
            offer = "specialized AI infra optimization"
            entry = "ML pipeline performance audit"
        else:
            style = "HYBRID"
            offer = "co-build platform"
            entry = "architecture review"

        results.append({
            "company_name": opp["company_name"],
            "buying_style": style,
            "tech_strength": tech_strength,
            "offer": offer,
            "entry_point": entry,
            "strategy_note": f"{opp['company_name']} → {style}"
        })

    return results