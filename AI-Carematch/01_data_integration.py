# 01_data_integration.py
# AICareMatch — Data Integration Pipeline
#
# Merges all three public government datasets into one master analysis table:
#
#   SAMHSA NSDUH 2023  — mental health DEMAND: who needs care and where
#   HRSA BHW 2024      — provider SUPPLY: who is available and where
#   FCC Broadband 2024 — telehealth INFRASTRUCTURE: who can access care digitally
#
# The business question this answers:
# "Which NY counties should AICareMatch launch in first to have the
#  highest impact — where need is greatest, providers are fewest,
#  and broadband makes telehealth delivery feasible?"
#
# How to replace with real data:
#   SAMHSA: https://www.samhsa.gov/data/nsduh/state-reports-NSDUH-2023
#   HRSA:   https://data.hrsa.gov/tools/shortage-area/hpsa-find
#   FCC:    https://broadbandmap.fcc.gov/data-download
#
# Author: Dharani Bhumireddy
# Project: AICareMatch — AI-Driven Mental Health Matching Platform
# Fellowship: RISE Fellowship, University at Albany, SUNY (2025)

import os
import pandas as pd
import numpy as np

os.makedirs("outputs", exist_ok=True)
os.makedirs("outputs/figures", exist_ok=True)
os.makedirs("outputs/reports", exist_ok=True)

# ── load all three public datasets ────────────────────────────────────────
print("Loading 3 public datasets...")
df_samhsa = pd.read_csv("data/samhsa_nsduh_ny_2023.csv")
df_hrsa   = pd.read_csv("data/hrsa_provider_ny_2024.csv")
df_fcc    = pd.read_csv("data/fcc_broadband_ny_2024.csv")

print(f"  SAMHSA NSDUH 2023  : {df_samhsa.shape[0]} counties | {df_samhsa.shape[1]} features")
print(f"  HRSA Workforce 2024: {df_hrsa.shape[0]} counties | {df_hrsa.shape[1]} features")
print(f"  FCC Broadband 2024 : {df_fcc.shape[0]} counties | {df_fcc.shape[1]} features")

# ── merge all three on county ──────────────────────────────────────────────
# Standardize the county column name across datasets
df_hrsa_m = df_hrsa.rename(columns={"COUNTY_NAME": "COUNTY",
                                      "URBAN_RURAL": "URBAN_RURAL_HRSA"})
df_fcc_m  = df_fcc.rename(columns={"URBAN_RURAL": "URBAN_RURAL_FCC"})

master = (df_samhsa
          .merge(df_hrsa_m, on="COUNTY", suffixes=("", "_HRSA"))
          .merge(df_fcc_m,  on="COUNTY", suffixes=("", "_FCC")))

# Drop duplicate columns created by suffix merging
master = master.loc[:, ~master.columns.duplicated()]

print(f"\nMaster dataset after merge: {master.shape[0]} counties | {master.shape[1]} columns")

# ── derived metrics for AICareMatch business logic ─────────────────────────

# 1. Treatment Gap (%) — % of those who need care but do not receive it
master["TREATMENT_GAP_PCT"] = (
    master["UNTREATED_COUNT_ESTIMATED"] /
    master["AMI_COUNT_ESTIMATED"] * 100
).round(2)

# 2. Provider Deficit — gap vs HRSA recommended 33 providers per 100k
RECOMMENDED = 33.0
master["PROVIDER_DEFICIT_PER_100K"] = (
    RECOMMENDED - master["PROVIDERS_PER_100K_POP"]
).clip(lower=0).round(1)

# 3. Telehealth Opportunity — untreated patients who can access telehealth
master["TELEHEALTH_REACHABLE_PATIENTS"] = (
    master["UNTREATED_COUNT_ESTIMATED"] *
    master["TELEHEALTH_CAPABLE_PCT"] / 100
).astype(int)

# 4. AICareMatch Priority Score (0–100)
# This score directly answers: "Where should AICareMatch deploy first?"
# Weights designed to balance impact (gap + shortage) with feasibility (broadband)
#
#   35% Treatment gap    — unmet mental health need
#   25% HPSA score       — HRSA-certified shortage severity
#   20% Telehealth access — broadband enables digital matching
#   12% AMI prevalence   — raw demand magnitude
#    8% Poverty rate     — economic barriers to care

hpsa_n    = master["HPSA_SCORE"] / 25
bb_n      = master["TELEHEALTH_CAPABLE_PCT"] / 100
gap_n     = master["TREATMENT_GAP_PCT"] / 100
ami_min, ami_max = master["AMI_PERCENT"].min(), master["AMI_PERCENT"].max()
ami_n     = (master["AMI_PERCENT"] - ami_min) / (ami_max - ami_min)
pov_n     = master["POVERTY_RATE_PCT"] / 100

master["AICAREMATCH_PRIORITY_SCORE"] = (
    gap_n  * 0.35 +
    hpsa_n * 0.25 +
    bb_n   * 0.20 +
    ami_n  * 0.12 +
    pov_n  * 0.08
).round(4) * 100

master["AICAREMATCH_PRIORITY_SCORE"] = master["AICAREMATCH_PRIORITY_SCORE"].round(2)

# 5. Launch tier classification
master["LAUNCH_TIER"] = pd.cut(
    master["AICAREMATCH_PRIORITY_SCORE"],
    bins=[0, 35, 50, 65, 100],
    labels=["Tier 4 — Deprioritize", "Tier 3 — Watch",
            "Tier 2 — Priority",     "Tier 1 — Launch Now"]
)

# 6. Telehealth viability label
master["TELEHEALTH_VIABILITY"] = pd.cut(
    master["BROADBAND_25_3_COVERAGE_PCT"],
    bins=[0, 50, 70, 85, 100],
    labels=["Poor (<50%)", "Moderate (50-70%)",
            "Good (70-85%)", "Excellent (>85%)"]
)

# ── save master dataset ────────────────────────────────────────────────────
master.to_csv("outputs/ny_carematch_master.csv", index=False)

# ── print summary ──────────────────────────────────────────────────────────
print("\n── AICareMatch Priority Score — Top 15 Counties ──")
cols_show = ["COUNTY", "REGION", "AICAREMATCH_PRIORITY_SCORE", "LAUNCH_TIER",
             "TREATMENT_GAP_PCT", "PROVIDERS_PER_100K_POP",
             "TELEHEALTH_CAPABLE_PCT", "AMI_PERCENT"]
top15 = master.sort_values("AICAREMATCH_PRIORITY_SCORE", ascending=False).head(15)
print(top15[cols_show].to_string(index=False))

print("\n── Launch Tier Breakdown ──")
print(master["LAUNCH_TIER"].value_counts().sort_index())

print(f"\n── Key Numbers ──")
print(f"Total adults with mental illness in NY:  {master['AMI_COUNT_ESTIMATED'].sum():,}")
print(f"Total untreated (not receiving care):    {master['UNTREATED_COUNT_ESTIMATED'].sum():,}")
print(f"Reachable via telehealth:                {master['TELEHEALTH_REACHABLE_PATIENTS'].sum():,}")
print(f"HPSA-designated shortage counties:      {(master['HPSA_STATUS']=='Designated').sum()}")
print(f"\nMaster dataset saved: outputs/ny_carematch_master.csv")
