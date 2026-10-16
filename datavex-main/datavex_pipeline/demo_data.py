"""
DataVex Pipeline — Demo Data
3 hardcoded Indian companies with realistic signal data.
Designed to produce: 1 HIGH, 1 MEDIUM, 1 LOW opportunity.
"""

DEMO_COMPANIES = [
    {
        "company_name": "Krea.ai",
        "domain": "krea.ai",
        "industry": "AI SaaS",
        "size": "small",
        "estimated_employees": 150,
        "region": "India",
        "tech_signals": ["AI hiring", "ML platform", "Kubernetes", "cloud modernization", "data pipeline", "NLP"],
        "raw_signals": {
            "careers": [
                {"text": "Hiring Senior ML Engineer — build real-time inference pipelines for enterprise clients. Experience with K8s, Ray Serve, and model monitoring required.", "source": "careers", "recency_days": 7},
                {"text": "Platform Engineer (DevOps) — migrate monolithic training infra to cloud-native microservices on AWS EKS. Terraform + Helm experience mandatory.", "source": "careers", "recency_days": 14},
                {"text": "Data Engineer — design and maintain ETL pipelines processing 50M+ events/day. Apache Beam, BigQuery, and Airflow.", "source": "careers", "recency_days": 21},
                {"text": "Head of Enterprise Sales — drive 6-figure ACV deals with Fortune 500 clients. Track record in AI/ML SaaS required.", "source": "careers", "recency_days": 10},
            ],
            "news": [
                {"text": "Krea.ai raises $12M Series A to expand enterprise AI platform into US market. CEO says 'We're targeting $5M ARR by Q4 2026.'", "source": "news", "recency_days": 30},
                {"text": "Krea.ai partners with AWS to offer GPU-optimized inference endpoints. Enterprise customers get dedicated model hosting.", "source": "news", "recency_days": 45},
            ],
            "tech_stack": [
                {"text": "GitHub org shows 8 active repos: ML inference framework, K8s operators, data pipeline tools. 340+ stars on main repo. CI/CD with GitHub Actions.", "source": "tech_stack", "recency_days": 5},
            ],
            "blog": [
                {"text": "CTO blog post: 'Why we moved from monolithic model serving to a composable inference mesh — 4x throughput, 60% cost reduction on AWS.'", "source": "blog", "recency_days": 20},
            ],
        },
        "why_now_triggers": [
            {"event": "Series A closed — $12M, expanding enterprise", "recency_days": 30, "impact": "high"},
            {"event": "AWS partnership for GPU inference", "recency_days": 45, "impact": "med"},
            {"event": "Hiring Head of Enterprise Sales", "recency_days": 10, "impact": "high"},
        ],
    },
    {
        "company_name": "Slice",
        "domain": "sliceit.com",
        "industry": "Fintech",
        "size": "mid",
        "estimated_employees": 800,
        "region": "India",
        "tech_signals": ["legacy modernization", "cloud modernization", "data warehouse", "ETL", "DevOps", "data pipeline"],
        "raw_signals": {
            "careers": [
                {"text": "Staff Engineer — decompose monolithic payment processing engine into event-driven microservices. Java/Kotlin + Kafka experience.", "source": "careers", "recency_days": 14},
                {"text": "Data Warehouse Architect — migrate from on-prem MySQL cluster to Snowflake. Must optimize for regulatory reporting.", "source": "careers", "recency_days": 21},
                {"text": "SRE Lead — reduce P0 incident rate by 50%. Currently averaging 4 production incidents per week.", "source": "careers", "recency_days": 7},
            ],
            "news": [
                {"text": "Slice lays off 10% of workforce amid funding winter. CEO memo: 'Focus on profitability path, reduce burn by 30%.'", "source": "news", "recency_days": 60},
                {"text": "Slice migrating core banking stack from legacy Java monolith to cloud-native architecture. Estimated 18-month timeline.", "source": "news", "recency_days": 90},
            ],
            "tech_stack": [
                {"text": "GitHub shows legacy Java repos with 200+ open issues. Recent PRs reference 'strangler fig migration' pattern. CI builds averaging 28 minutes.", "source": "tech_stack", "recency_days": 10},
            ],
            "blog": [
                {"text": "VP Engineering post: 'Our technical debt is our biggest blocker to profitability — every feature takes 3x longer than it should.'", "source": "blog", "recency_days": 35},
            ],
        },
        "why_now_triggers": [
            {"event": "10% layoff + cost cutting mandate", "recency_days": 60, "impact": "high"},
            {"event": "Legacy monolith migration started", "recency_days": 90, "impact": "med"},
            {"event": "4 P0 incidents/week driving SRE hiring", "recency_days": 7, "impact": "med"},
        ],
    },
    {
        "company_name": "Sarvam AI",
        "domain": "sarvam.ai",
        "industry": "AI Infrastructure",
        "size": "small",
        "estimated_employees": 80,
        "region": "India",
        "tech_signals": ["AI hiring", "NLP", "computer vision", "data science", "infrastructure"],
        "raw_signals": {
            "careers": [
                {"text": "Research Scientist — develop multilingual LLMs for Indian languages. PhD preferred. Publishing record at top ML venues.", "source": "careers", "recency_days": 5},
                {"text": "Infra Engineer — build GPU cluster management platform for 1000+ A100 nodes. SLURM + K8s hybrid scheduling.", "source": "careers", "recency_days": 12},
            ],
            "news": [
                {"text": "Sarvam AI wins ₹200Cr government contract to build India's sovereign AI stack. Focus on healthcare and agriculture NLP.", "source": "news", "recency_days": 15},
                {"text": "Sarvam AI announces Sarvam-1, a 7B parameter multilingual model trained on 22 Indian languages.", "source": "news", "recency_days": 40},
            ],
            "tech_stack": [
                {"text": "Private repos — limited visibility. Public model cards on HuggingFace show active ML research. No public infra repos.", "source": "tech_stack", "recency_days": 10},
            ],
            "blog": [
                {"text": "CEO interview: 'We're building India's AI infrastructure layer — government-first, enterprise later. Revenue is secondary to impact right now.'", "source": "blog", "recency_days": 25},
            ],
        },
        "why_now_triggers": [
            {"event": "₹200Cr government AI contract won", "recency_days": 15, "impact": "high"},
            {"event": "Sarvam-1 model launch", "recency_days": 40, "impact": "low"},
        ],
    },
]

# Company dataset for Agent 1 filtering
# Primary targets: Fractal Analytics, Databricks, MindsDB
SAMPLE_COMPANIES = [
    # ── PRIMARY TARGETS ──
    {"company_name": "Fractal Analytics", "domain": "fractal.ai", "industry": "AI Analytics", "size": "large", "estimated_employees": 4000, "region": "India",
     "tech_signals": ["AI analytics", "cloud modernization", "data engineering", "machine learning", "data pipeline", "enterprise AI"]},
    {"company_name": "Databricks", "domain": "databricks.com", "industry": "AI Analytics", "size": "large", "estimated_employees": 7000, "region": "US",
     "tech_signals": ["data engineering", "data lake", "ML platform", "cloud", "ETL", "data pipeline", "AI", "Spark"]},
    {"company_name": "MindsDB", "domain": "mindsdb.com", "industry": "AI/ML Database", "size": "small", "estimated_employees": 100, "region": "US",
     "tech_signals": ["AI", "machine learning", "database", "data engineering", "cloud", "NLP"]},
    # ── OTHER COMPANIES ──
    {"company_name": "Razorpay", "domain": "razorpay.com", "industry": "Fintech", "size": "large", "estimated_employees": 3500, "region": "India"},
    {"company_name": "Postman", "domain": "postman.com", "industry": "DevTools", "size": "mid", "estimated_employees": 900, "region": "India"},
    {"company_name": "Zoho", "domain": "zoho.com", "industry": "Enterprise SaaS", "size": "large", "estimated_employees": 15000, "region": "India"},
    {"company_name": "Darwinbox", "domain": "darwinbox.com", "industry": "HR Tech", "size": "mid", "estimated_employees": 600, "region": "India"},
    {"company_name": "Hasura", "domain": "hasura.io", "industry": "Developer Tools", "size": "small", "estimated_employees": 180, "region": "US"},
    {"company_name": "SingleStore", "domain": "singlestore.com", "industry": "Database", "size": "mid", "estimated_employees": 500, "region": "US"},
    {"company_name": "Anyscale", "domain": "anyscale.com", "industry": "AI Infrastructure", "size": "mid", "estimated_employees": 300, "region": "US"},
    {"company_name": "dbt Labs", "domain": "getdbt.com", "industry": "Data Engineering", "size": "mid", "estimated_employees": 600, "region": "US"},
    {"company_name": "Yellow.ai", "domain": "yellow.ai", "industry": "AI SaaS", "size": "mid", "estimated_employees": 1100, "region": "India"},
]

