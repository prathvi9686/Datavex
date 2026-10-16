"""
DataVex Pipeline — Schema Validation Tests
Validates all Pydantic models with sample data (no LLM calls needed).
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from models import (
    UserIntent, DealProfile, CandidateCompany,
    EvidenceItem, Signal, CompanySignals,
    OpportunityScore, PriorityProfile, DecisionMaker, DecisionMakerOutput,
    OutreachKit, PipelineResult,
)


def test_user_intent():
    intent = UserIntent(raw_text="fintech companies in India")
    assert intent.raw_text == "fintech companies in India"
    print("  ✓ UserIntent")


def test_deal_profile():
    dp = DealProfile()
    assert dp.min_deal_usd == 500_000
    assert dp.max_deal_usd == 10_000_000
    assert "India" in dp.target_regions
    assert "small" in dp.preferred_company_sizes

    dp2 = DealProfile(min_deal_usd=100_000, target_regions=["US"])
    assert dp2.min_deal_usd == 100_000
    print("  ✓ DealProfile")


def test_candidate_company():
    cc = CandidateCompany(
        company_name="TestCo",
        domain="testco.com",
        industry="SaaS",
        size="mid",
        estimated_employees=500,
        region="India",
        capability_score=0.8,
        size_fit=1.0,
        geo_fit=1.0,
        industry_fit=0.7,
        initial_match_score=0.85,
        notes="Strong match",
    )
    assert cc.initial_match_score == 0.85
    assert cc.size == "mid"
    print("  ✓ CandidateCompany")


def test_evidence_item():
    e = EvidenceItem(text="Hiring ML engineers", source="careers", recency_days=7)
    assert e.recency_days == 7

    e2 = EvidenceItem(text="News article", source="news")
    assert e2.recency_days is None
    print("  ✓ EvidenceItem")


def test_signal():
    s = Signal(
        label="AI pivot", confidence=0.7,
        evidence=[EvidenceItem(text="Hiring ML eng", source="careers", recency_days=5)],
    )
    assert s.confidence == 0.7
    assert len(s.evidence) == 1
    print("  ✓ Signal")


def test_company_signals():
    cs = CompanySignals(
        company_name="TestCo",
        pivot=Signal(label="Expanding enterprise", confidence=0.6, evidence=[]),
        tech_debt=None,
        fiscal_pressure=None,
        why_now_triggers=[{"event": "Series A", "recency_days": 30, "impact": "high"}],
        company_state="GROWTH",
        raw_texts=[{"text": "sample", "source": "careers"}],
    )
    assert cs.company_state == "GROWTH"
    assert cs.pivot is not None
    assert cs.tech_debt is None
    print("  ✓ CompanySignals")


def test_opportunity_score():
    os_obj = OpportunityScore(
        company_name="TestCo",
        opportunity_score=0.82,
        priority="HIGH",
        timing_window="next 1-3 months",
        company_state="GROWTH",
        capability_alignment=0.9,
        urgency_score=0.75,
        strategic_summary="Strong AI opportunity",
        why_we_win=["Strong data eng capability", "Market timing"],
        risks=["Small team", "Budget uncertainty"],
        confidence=0.8,
    )
    assert os_obj.priority == "HIGH"
    assert os_obj.opportunity_score == 0.82
    print("  ✓ OpportunityScore")


def test_priority_profile():
    pp = PriorityProfile(
        primary_focus="innovation",
        secondary_focus="speed",
        risk_tolerance="high",
        innovation_bias="high",
        communication_style="visionary",
    )
    assert pp.primary_focus == "innovation"
    print("  ✓ PriorityProfile")


def test_decision_maker():
    dm = DecisionMaker(
        name="Priya Sharma",
        role="CTO",
        priority_profile=PriorityProfile(),
        psychographic_signals=["innovation-biased", "velocity-focused"],
        messaging_angle="Your AI infra needs an upgrade",
        pain_points_aligned=["Scaling ML pipelines", "Cloud costs"],
        persona_risks=["May prefer in-house solutions"],
        confidence=0.75,
    )
    assert dm.name == "Priya Sharma"
    assert dm.confidence <= 1.0
    print("  ✓ DecisionMaker")


def test_decision_maker_output():
    dm = DecisionMaker(name="Test", role="CTO", confidence=0.7)
    dmo = DecisionMakerOutput(
        company_name="TestCo",
        decision_maker=dm,
        role_selection_rationale="GROWTH state → Head of Data",
    )
    assert dmo.company_name == "TestCo"
    print("  ✓ DecisionMakerOutput")


def test_outreach_kit():
    ok = OutreachKit(
        company_name="TestCo",
        decision_maker_name="Priya Sharma",
        decision_maker_role="CTO",
        email="Subject: AI Pipeline Support\n\nHi Priya...",
        linkedin_dm="Priya — saw your ML hiring push...",
        call_opener="Priya, quick question about your inference pipeline scaling...",
        personalization_notes=["Hook from careers signal"],
        tone="consultative",
        why_this_message=["Pivot signal drives framing"],
        risk_adjustments=["Softened CTA due to budget risk"],
        confidence=0.7,
    )
    assert ok.tone == "consultative"
    assert len(ok.personalization_notes) == 1
    print("  ✓ OutreachKit")


def test_pipeline_result():
    candidate = CandidateCompany(
        company_name="TestCo", domain="test.com", industry="SaaS",
        size="small", estimated_employees=100, region="India",
    )
    signals = CompanySignals(company_name="TestCo")
    opp = OpportunityScore(company_name="TestCo")
    dm_out = DecisionMakerOutput(
        company_name="TestCo",
        decision_maker=DecisionMaker(name="Test", role="CTO", confidence=0.5),
    )
    outreach = OutreachKit(
        company_name="TestCo", decision_maker_name="Test", decision_maker_role="CTO",
    )
    pr = PipelineResult(
        company_name="TestCo",
        candidate=candidate, signals=signals,
        opportunity=opp, decision_maker=dm_out, outreach=outreach,
    )
    assert pr.company_name == "TestCo"

    # Test serialization
    data = pr.model_dump()
    assert isinstance(data, dict)
    assert data["company_name"] == "TestCo"

    # Test roundtrip
    pr2 = PipelineResult(**data)
    assert pr2.company_name == pr.company_name
    print("  ✓ PipelineResult (including serialization roundtrip)")


def main():
    print("\n  DataVex Pipeline — Schema Validation Tests")
    print("  " + "─" * 45)

    test_user_intent()
    test_deal_profile()
    test_candidate_company()
    test_evidence_item()
    test_signal()
    test_company_signals()
    test_opportunity_score()
    test_priority_profile()
    test_decision_maker()
    test_decision_maker_output()
    test_outreach_kit()
    test_pipeline_result()

    print("\n  All 12 schema tests passed ✓\n")


if __name__ == "__main__":
    main()
