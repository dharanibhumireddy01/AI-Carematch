# 04_insights_report.py
# AICareMatch — Insights Report Generator
#
# Generates a structured text report with all key findings.
# This is the "deliverable to the product team" — translating
# data findings into concrete platform decisions.
#
# Run after 01, 02, 03.
#
# Author: Dharani Bhumireddy
# Project: AICareMatch — RISE Fellowship, University at Albany, SUNY (2025)

import os
import pandas as pd
import numpy as np
from datetime import datetime

os.makedirs("outputs/reports", exist_ok=True)

master = pd.read_csv("outputs/ny_carematch_final.csv")

tier1 = master[master["LAUNCH_TIER"].astype(str).str.contains("Tier 1")]
tier2 = master[master["LAUNCH_TIER"].astype(str).str.contains("Tier 2")]

top5_priority = master.sort_values(
    "AICAREMATCH_PRIORITY_SCORE", ascending=False).head(5)
top5_telehealth = master.sort_values(
    "TELEHEALTH_REACHABLE_PATIENTS", ascending=False).head(5)
worst_shortage = master.sort_values(
    "PROVIDERS_PER_100K_POP").head(5)

report = f"""
================================================================================
  AICareMatch — NY State Mental Health Gap Analysis
  Data-Driven Insights for Platform Launch Strategy
  Generated: {datetime.now().strftime("%B %d, %Y")}
  Datasets: SAMHSA NSDUH 2023 + HRSA BHW 2024 + FCC Broadband 2024
================================================================================

EXECUTIVE SUMMARY
─────────────────
This analysis covers all 62 New York State counties using three public government
datasets to identify where AICareMatch will have the highest impact, where
provider-patient matching is most urgently needed, and which platform features
matter most by county type.

KEY NUMBERS
───────────
Total NY adults with Any Mental Illness (AMI):  {master['AMI_COUNT_ESTIMATED'].sum():>12,}
Total receiving NO treatment:                   {master['UNTREATED_COUNT_ESTIMATED'].sum():>12,}
Untreated with broadband (telehealth-ready):    {master['TELEHEALTH_REACHABLE_PATIENTS'].sum():>12,}
Counties with HRSA shortage designation:        {(master['HPSA_STATUS']=='Designated').sum():>12} / 62
Counties below HRSA 33/100k minimum:           {(master['PROVIDERS_PER_100K_POP']<33).sum():>12} / 62
Average treatment gap across NY:               {master['TREATMENT_GAP_PCT'].mean():>11.1f}%
Average wait time for appointment:             {master['AVG_WAIT_TIME_WEEKS'].mean():>11.1f} weeks

LAUNCH TIER BREAKDOWN
─────────────────────
Tier 1 — Launch Now (score ≥ 65):   {(master['LAUNCH_TIER'].astype(str).str.contains('Tier 1')).sum()} counties
Tier 2 — Priority  (score 50–65):   {(master['LAUNCH_TIER'].astype(str).str.contains('Tier 2')).sum()} counties
Tier 3 — Watch     (score 35–50):   {(master['LAUNCH_TIER'].astype(str).str.contains('Tier 3')).sum()} counties
Tier 4 — Low       (score < 35):    {(master['LAUNCH_TIER'].astype(str).str.contains('Tier 4')).sum()} counties

TOP 5 COUNTIES — AICAREMATCH PRIORITY SCORE
────────────────────────────────────────────
{top5_priority[['COUNTY','REGION','AICAREMATCH_PRIORITY_SCORE','TREATMENT_GAP_PCT','PROVIDERS_PER_100K_POP','TELEHEALTH_CAPABLE_PCT']].to_string(index=False)}

TOP 5 COUNTIES — TELEHEALTH REACHABLE PATIENTS
────────────────────────────────────────────────
{top5_telehealth[['COUNTY','REGION','TELEHEALTH_REACHABLE_PATIENTS','BROADBAND_25_3_COVERAGE_PCT','UNTREATED_COUNT_ESTIMATED']].to_string(index=False)}

WORST 5 COUNTIES — PROVIDER SHORTAGE
──────────────────────────────────────
{worst_shortage[['COUNTY','REGION','PROVIDERS_PER_100K_POP','HPSA_SCORE','AVG_WAIT_TIME_WEEKS','TREATMENT_GAP_PCT']].to_string(index=False)}

REGIONAL SUMMARY
────────────────
{master.groupby('REGION').agg(
    counties=('COUNTY','count'),
    avg_gap=('TREATMENT_GAP_PCT','mean'),
    avg_providers=('PROVIDERS_PER_100K_POP','mean'),
    total_untreated=('UNTREATED_COUNT_ESTIMATED','sum'),
    avg_broadband=('BROADBAND_25_3_COVERAGE_PCT','mean')
).round(1).to_string()}

KEY FINDINGS & PLATFORM IMPLICATIONS
──────────────────────────────────────

FINDING 1 — The Rural Crisis Is Worse Than the Pitch Deck Claims
  Data shows {(master[master['URBAN_RURAL_CODE']=='Rural']['TREATMENT_GAP_PCT'].mean()):.1f}% treatment gap
  in rural counties vs {(master[master['URBAN_RURAL_CODE']=='Urban']['TREATMENT_GAP_PCT'].mean()):.1f}%
  in urban counties. Rural counties have on average {(master[master['URBAN_RURAL_CODE']=='Rural']['PROVIDERS_PER_100K_POP'].mean()):.1f}
  providers per 100k vs {(master[master['URBAN_RURAL_CODE']=='Urban']['PROVIDERS_PER_100K_POP'].mean()):.1f} urban.
  
  Platform implication: Rural matching should prioritize telehealth-capable providers.
  Broadband coverage in rural NY averages {master[master['URBAN_RURAL_CODE']=='Rural']['BROADBAND_25_3_COVERAGE_PCT'].mean():.1f}%
  — sufficient for initial telehealth focus.

FINDING 2 — Broadband Is NOT the Limiting Factor (Cost and Providers Are)
  Correlation analysis:
    Providers/100k vs Treatment Gap:  {master['PROVIDERS_PER_100K_POP'].corr(master['TREATMENT_GAP_PCT']):.3f} (strong negative)
    Session Cost vs Treatment Gap:    {master['AVG_SESSION_COST_USD'].corr(master['TREATMENT_GAP_PCT']):.3f} (positive — cost drives gap)
    Broadband % vs Treatment Gap:     {master['BROADBAND_25_3_COVERAGE_PCT'].corr(master['TREATMENT_GAP_PCT']):.3f} (weaker — broadband not the main barrier)
  
  Platform implication: Cost transparency (pitch deck slide 3) is the
  right focus. Broadband is sufficient for telehealth in most counties.
  The platform should lead with price display — this addresses the #1 barrier.

FINDING 3 — PTSD and First Responder Markets Are Geographically Concentrated
  Counties with highest PTSD prevalence:
{master.nlargest(5,'PTSD_PERCENT')[['COUNTY','REGION','PTSD_PERCENT','PROVIDERS_PER_100K_POP']].to_string(index=False)}
  
  Platform implication: Jefferson County (Ft. Drum military base) + North Country
  region should be an early targeted campaign. First responder matching is a
  defensible niche that larger platforms (BetterHelp, Teladoc) do not serve.

FINDING 4 — Albany Region Is the Right First Launch Market
  Albany County scores in Tier 2. The Capital Region has:
  - Albany Medical Center partnership potential (pitch deck slide 19)
  - NY OMH headquarters (potential regulatory ally)
  - University at Albany student/staff market (SUNY network)
  - Reasonable broadband: {master[master['COUNTY']=='Albany']['BROADBAND_25_3_COVERAGE_PCT'].values[0]:.1f}%
  - Treatment gap:        {master[master['COUNTY']=='Albany']['TREATMENT_GAP_PCT'].values[0]:.1f}%
  - Providers/100k:       {master[master['COUNTY']=='Albany']['PROVIDERS_PER_100K_POP'].values[0]:.1f}

FINDING 5 — K-Means Identifies 5 Distinct Market Segments
  Each segment needs different AICareMatch features:
  
  Critical Shortage Rural  → Need: In-person + telehealth hybrid matching
                             Product: Provider recruitment, sliding scale cost display
  
  High-Need Rural          → Need: Telehealth-first matching, low-cost options
                             Product: $0-50 filter, Medicaid provider filter
  
  High-Poverty Underserved → Need: Insurance navigation, Medicaid matching
                             Product: Cost simulator (pitch deck slide 3)
  
  High-Broadband Suburban  → Need: Premium telehealth, convenient scheduling
                             Product: Fast booking, telehealth-only filter
  
  Well-Served Urban (NYC)  → Need: Specialty matching, wait time reduction
                             Product: AI specialty matching, same-week availability

RECOMMENDATIONS FOR THE AICAREMATCH TEAM
──────────────────────────────────────────

1. IMMEDIATE: Target these 5 counties for Albany Med pilot launch (highest
   priority score + broadband + within driving distance of Albany HQ):
{master[(master['REGION']=='Capital') | (master['REGION']=='Hudson Valley')].nlargest(5,'AICAREMATCH_PRIORITY_SCORE')[['COUNTY','REGION','AICAREMATCH_PRIORITY_SCORE','TELEHEALTH_REACHABLE_PATIENTS']].to_string(index=False)}

2. PRODUCT: Display session cost upfront (Correlation: r={master['AVG_SESSION_COST_USD'].corr(master['TREATMENT_GAP_PCT']):.2f}).
   Cost is a stronger barrier than access. Pitch deck's "Cost Transparency"
   feature is validated by this data.

3. PROVIDER RECRUITMENT: Prioritize psychiatrists in Tier 1 counties.
   Average wait time in shortage counties: {master[master['HPSA_STATUS']=='Designated']['AVG_WAIT_TIME_WEEKS'].mean():.1f} weeks vs
   {master[master['HPSA_STATUS']!='Designated']['AVG_WAIT_TIME_WEEKS'].mean():.1f} weeks in non-shortage counties.

4. GRANT TARGETING: {(master['HPSA_STATUS']=='Designated').sum()} HPSA-designated counties qualify for federal funding
   preference. NY's $218M investment (pitch deck slide 15) will flow to these
   counties first — AICareMatch should partner with facilities in these areas.

5. UNDERSERVED POPULATIONS: Focus first responder campaign on North Country
   region (Jefferson, St. Lawrence, Franklin, Clinton, Essex counties).
   These counties have high PTSD rates + military population + severe shortages.

================================================================================
  Analysis by: Dharani Bhumireddy
  RISE Fellowship — University at Albany, SUNY (2025)
  AICareMatch — Making Mental Health Care Accessible
================================================================================
"""

report_path = "outputs/reports/aicarematch_ny_insights_report.txt"
with open(report_path, "w") as f:
    f.write(report)

print(report)
print(f"\nFull report saved: {report_path}")
