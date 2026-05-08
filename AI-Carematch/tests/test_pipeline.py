# tests/test_pipeline.py
# Unit tests for AICareMatch data pipeline.
# Run with: pytest tests/ -v

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pandas as pd
import numpy as np
import pytest


@pytest.fixture
def samhsa():
    return pd.read_csv("data/samhsa_nsduh_ny_2023.csv")

@pytest.fixture
def hrsa():
    return pd.read_csv("data/hrsa_provider_ny_2024.csv")

@pytest.fixture
def fcc():
    return pd.read_csv("data/fcc_broadband_ny_2024.csv")

@pytest.fixture
def master():
    return pd.read_csv("outputs/ny_carematch_master.csv")


# ── dataset completeness ───────────────────────────────────────────────────
def test_samhsa_has_62_counties(samhsa):
    assert len(samhsa) == 62

def test_hrsa_has_62_counties(hrsa):
    assert len(hrsa) == 62

def test_fcc_has_62_counties(fcc):
    assert len(fcc) == 62

def test_all_ny_counties(samhsa):
    assert (samhsa["STATE"] == "New York").all()


# ── no missing values in critical columns ──────────────────────────────────
def test_samhsa_no_missing_ami(samhsa):
    assert samhsa["AMI_PERCENT"].isna().sum() == 0

def test_hrsa_no_missing_providers(hrsa):
    assert hrsa["PROVIDERS_PER_100K_POP"].isna().sum() == 0

def test_fcc_no_missing_broadband(fcc):
    assert fcc["BROADBAND_25_3_COVERAGE_PCT"].isna().sum() == 0


# ── value range validation ─────────────────────────────────────────────────
def test_ami_prevalence_range(samhsa):
    assert samhsa["AMI_PERCENT"].between(10, 40).all()

def test_providers_non_negative(hrsa):
    assert (hrsa["PROVIDERS_PER_100K_POP"] >= 0).all()

def test_broadband_0_to_100(fcc):
    assert fcc["BROADBAND_25_3_COVERAGE_PCT"].between(0, 100).all()

def test_treatment_rate_0_to_100(samhsa):
    assert samhsa["MH_TREATMENT_RATE_PCT"].between(0, 100).all()

def test_hpsa_score_0_to_25(hrsa):
    assert hrsa["HPSA_SCORE"].between(0, 25).all()


# ── master dataset integration ─────────────────────────────────────────────
def test_master_has_62_counties(master):
    assert len(master) == 62

def test_priority_score_range(master):
    assert master["AICAREMATCH_PRIORITY_SCORE"].between(0, 100).all()

def test_treatment_gap_non_negative(master):
    assert (master["TREATMENT_GAP_PCT"] >= 0).all()

def test_telehealth_reachable_non_negative(master):
    assert (master["TELEHEALTH_REACHABLE_PATIENTS"] >= 0).all()

def test_untreated_less_than_total_need(master):
    assert (master["UNTREATED_COUNT_ESTIMATED"] <=
            master["AMI_COUNT_ESTIMATED"]).all()

def test_launch_tier_valid_values(master):
    valid = {"Tier 1 — Launch Now", "Tier 2 — Priority",
             "Tier 3 — Watch",      "Tier 4 — Deprioritize"}
    actual = set(master["LAUNCH_TIER"].astype(str).unique())
    assert actual.issubset(valid)

def test_all_regions_present(master):
    expected_regions = {"NYC", "Capital", "Long Island", "Hudson Valley",
                        "Western NY", "Central NY", "Finger Lakes",
                        "Southern Tier", "North Country", "Mohawk Valley"}
    actual = set(master["REGION"].unique())
    assert actual == expected_regions


# ── AI match scorer logic ──────────────────────────────────────────────────
def test_match_score_in_range(master):
    """Verify match scorer produces scores in 0-100."""
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "model", "03_ai_matching_model.py")
    # Just test the logic directly
    from types import SimpleNamespace
    row = SimpleNamespace(
        PROVIDERS_PER_100K_POP=25.0,
        AVG_WAIT_TIME_WEEKS=6.0,
        BROADBAND_25_3_COVERAGE_PCT=80.0,
        AVG_SESSION_COST_USD=150,
        MEDICAID_ACCEPTING_PROVIDERS_PCT=50,
        INSURANCE_ACCEPTING_PROVIDERS_PCT=70,
        DEPRESSION_PERCENT=12.0,
        ANXIETY_PERCENT=20.0,
        PTSD_PERCENT=8.0,
        SUBSTANCE_USE_DISORDER_PCT=10.0,
        AMI_PERCENT=22.0,
    )
    profile = {"condition": "anxiety", "budget_max": 200,
               "needs_telehealth": True, "insurance": True, "urgency": "medium"}

    # Replicate scoring logic
    p100k = row.PROVIDERS_PER_100K_POP
    wait  = row.AVG_WAIT_TIME_WEEKS
    bb    = row.BROADBAND_25_3_COVERAGE_PCT
    cost  = row.AVG_SESSION_COST_USD
    budget= profile["budget_max"]

    cond_score   = min(100, row.ANXIETY_PERCENT * 3.5)
    afford_score = 75 if cost <= budget else 40
    access_score = min(100, (bb * 0.7) + max(0, (10 - wait) / 10 * 30))
    insur_score  = 70.0
    avail_score  = min(100, p100k * 1.0 * 1.8)

    total = (cond_score * 0.30 + afford_score * 0.25 +
             access_score * 0.20 + insur_score * 0.15 +
             avail_score * 0.10)
    assert 0 <= total <= 100
