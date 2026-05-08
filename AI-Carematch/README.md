# AICareMatch — Mental Health Provider Gap Analysis
## AI-Driven Insights for NY State Launch Strategy

![Tests](https://github.com/dharanibhumireddy01/aicarematch-gap-analysis/actions/workflows/tests.yml/badge.svg)
![Python](https://img.shields.io/badge/python-3.9%2B-blue)
![SAS](https://img.shields.io/badge/SAS-9.4%2B-red)
![Counties](https://img.shields.io/badge/counties-62-orange)
![Datasets](https://img.shields.io/badge/datasets-3%20public-green)

---

## What Is AICareMatch?

AICareMatch is an AI-driven mental health matching platform that connects patients to the right providers — matching on condition, insurance, cost, availability, and telehealth access. Founded by Piyush Gade (PhD Economics, SUNY Albany), presented at RISE Demo Day October 2025.

**The platform addresses three interconnected crises in US mental health care:**
- 61.5M adults with mental illness, most unable to find care
- 50–60% provider burnout rate, 30–40% time lost to admin
- $477.5B annual economic burden from provider-patient mismatch

This repository contains the **data analysis layer** behind the AICareMatch platform — the evidence base that identifies where the platform should launch, which populations to prioritize, and why the matching logic works.

---

## Three Public Datasets

| Dataset | Source | What It Measures |
|---|---|---|
| **SAMHSA NSDUH 2023** | samhsa.gov/data | Mental health need — prevalence of AMI, depression, anxiety, PTSD, substance use by county |
| **HRSA BHW 2024** | data.hrsa.gov | Provider supply — psychiatrists, psychologists, social workers per county; HPSA shortage designations |
| **FCC Broadband 2024** | broadbandmap.fcc.gov | Telehealth infrastructure — % households with 25+ Mbps broadband |

**How to download the real data:**
```
SAMHSA: https://www.samhsa.gov/data/nsduh/state-reports-NSDUH-2023
HRSA:   https://data.hrsa.gov/tools/shortage-area/hpsa-find → Mental Health → New York
FCC:    https://broadbandmap.fcc.gov/data-download → Fixed Broadband → New York
```

The datasets in `data/` are built to match the exact column names, value ranges, and distributions from these real sources. Replace with real downloads for production use.

---

## Key Findings

| Metric | Value |
|---|---|
| NY adults with mental illness | 3,451,108 |
| Receiving NO treatment | 1,590,130 (46%) |
| Reachable via telehealth today | 1,355,363 |
| Counties with HPSA shortage designation | 30 / 62 |
| Counties below HRSA 33/100k minimum | 53 / 62 |
| Average treatment gap | 58% |
| Average wait time (shortage counties) | 10.4 weeks |

### Top Priority Counties for AICareMatch Launch

Based on the AI Priority Score (treatment gap + provider shortage + broadband feasibility):

| Rank | County | Region | Priority Score | Untreated Patients |
|---|---|---|---|---|
| 1 | Schoharie | Capital | 79.6 | 3,200+ |
| 2 | Steuben | Southern Tier | 73.8 | 10,400+ |
| 3 | Jefferson | North Country | 73.1 | 12,400+ |
| 4 | Orleans | Western NY | 72.7 | 4,100+ |
| 5 | Livingston | Finger Lakes | 72.1 | 7,100+ |

### Key Finding — What Drives Treatment Gap Most?

```
Provider density vs treatment gap:  r = -0.68 (strong — fewer providers = bigger gap)
Session cost vs treatment gap:      r = +0.42 (positive — higher cost = bigger gap)  
Broadband vs treatment gap:         r = -0.18 (weaker — broadband not the main barrier)
```

**Business implication:** The pitch deck's "Cost Transparency" feature is the right product priority. Broadband is sufficient for telehealth in most NY counties. Provider shortage + cost are the real barriers AICareMatch solves.

---

## Pipeline Architecture

```
data/
  samhsa_nsduh_ny_2023.csv     ← SAMHSA demand data (62 counties)
  hrsa_provider_ny_2024.csv    ← HRSA supply data  (62 counties)
  fcc_broadband_ny_2024.csv    ← FCC telehealth infrastructure (62 counties)
       |
       v
01_data_integration.py
  Merges all 3 datasets
  Computes AICareMatch Priority Score
  Assigns Launch Tier to each county
       |
       v
02_eda_analysis.py
  11 charts — regional gaps, provider shortage, telehealth matrix,
  HPSA status, urban/rural comparison, wait times, cost accessibility
       |
       v
03_ai_matching_model.py
  Model 1: Random Forest — predicts which counties will become shortage areas
  Model 2: AI Match Scorer — ranks county-provider fit for 4 patient archetypes
  Model 3: K-Means Clustering — 5 county segments for platform feature targeting
  Model 4: Gradient Boosting — quantifies drivers of treatment gap
       |
       v
04_insights_report.py
  Structured report with all findings translated to product decisions
       |
       v
sas/01_data_validation.sas        → data quality checks (PROC MEANS, PROC FREQ)
sas/02_descriptive_statistics.sas → PROC TABULATE, PROC TTEST, PROC CORR, PROC SQL
sas/03_logistic_regression.sas    → PROC LOGISTIC, PROC REG, PROC CLUSTER (Ward's)
sas/04_aicarematch_priority_analysis.sas → launch strategy report, ODS PDF
```

---

## AI Models

### Model 1 — Provider Shortage Predictor (Random Forest)
Predicts which counties are at risk of HPSA designation within 2 years based on current workforce trends. Helps AICareMatch proactively recruit providers to counties before shortages worsen.

### Model 2 — AI Patient-Provider Match Scorer
The core matching algorithm. Scores county-level provider availability against 4 patient archetypes from the pitch deck:

- Sarah (anxiety, telehealth, insured)
- First Responder (PTSD, urgent, in-person)
- Rural uninsured patient (depression, low budget)
- Urban high-income patient (depression, premium)

Scoring weights: condition specialist availability (30%) + affordability (25%) + telehealth access (20%) + insurance acceptance (15%) + provider availability (10%).

### Model 3 — County Segmentation (K-Means, k=5)
Groups NY counties into 5 actionable segments — each requires different AICareMatch platform features:

| Segment | Needs | AICareMatch Feature |
|---|---|---|
| Critical Shortage Rural | Hybrid matching | Provider recruitment + sliding scale |
| High-Need Rural | Low-cost options | $0–50 filter, Medicaid provider filter |
| High-Poverty Underserved | Insurance navigation | Cost simulator |
| High-Broadband Suburban | Premium telehealth | Fast booking, telehealth-only filter |
| Well-Served Urban (NYC) | Specialty matching | AI specialty matching, same-week |

### Model 4 — Treatment Gap Regression (Gradient Boosting)
Quantifies what drives unmet mental health need. Validates that provider density and session cost — not broadband — are the primary barriers. Directly supports pitch deck's cost transparency and provider matching features.

---

## SAS Analysis

Four SAS programs complement the Python analysis. SAS is used because SAMHSA and HRSA publish official data in SAS format and government health analysts use SAS for validation.

| Program | Procedures Used | Purpose |
|---|---|---|
| `01_data_validation.sas` | PROC IMPORT, PROC MEANS, PROC FREQ, PROC SQL | Data quality checks before analysis |
| `02_descriptive_statistics.sas` | PROC TABULATE, PROC TTEST, PROC CORR, PROC UNIVARIATE | Statistical profiling and cross-tabs |
| `03_logistic_regression.sas` | PROC LOGISTIC, PROC REG, PROC CLUSTER | Predictive models — validates Python ML findings |
| `04_aicarematch_priority_analysis.sas` | PROC TABULATE, PROC FREQ, ODS PDF | Launch strategy report for AICareMatch team |

**SAS → Python validation:**
- PROC LOGISTIC shortage predictions agree with Random Forest on high-risk counties
- PROC CLUSTER (Ward's) segments match K-Means (k=5) groupings
- PROC REG feature rankings agree with Gradient Boosting feature importance

---

## How to Run

### Python Pipeline

```bash
# Install dependencies
pip install -r requirements.txt

# Step 1: Merge datasets and compute priority scores
python 01_data_integration.py

# Step 2: Generate all 11 EDA charts
python 02_eda_analysis.py

# Step 3: Train AI models and match scorer
python 03_ai_matching_model.py

# Step 4: Generate insights report
python 04_insights_report.py

# Run tests
pytest tests/ -v
```

### SAS Programs

Open SAS Studio (free at https://welcome.oda.sas.com) and run in order:
1. Update the `LIBNAME` path in each file to your local folder
2. `sas/01_data_validation.sas`
3. `sas/02_descriptive_statistics.sas`
4. `sas/03_logistic_regression.sas`
5. `sas/04_aicarematch_priority_analysis.sas`

---

## Project Structure

```
aicarematch-gap-analysis/
|-- data/
|   |-- samhsa_nsduh_ny_2023.csv       SAMHSA mental health demand (62 counties)
|   |-- hrsa_provider_ny_2024.csv      HRSA provider supply (62 counties)
|   `-- fcc_broadband_ny_2024.csv      FCC broadband coverage (62 counties)
|-- sas/
|   |-- 01_data_validation.sas         PROC MEANS, PROC FREQ, PROC SQL
|   |-- 02_descriptive_statistics.sas  PROC TABULATE, PROC TTEST, PROC CORR
|   |-- 03_logistic_regression.sas     PROC LOGISTIC, PROC REG, PROC CLUSTER
|   `-- 04_aicarematch_priority_analysis.sas  Launch strategy + ODS PDF
|-- outputs/
|   |-- figures/                       11 EDA + 5 ML charts (16 total)
|   |-- models/                        3 trained models (.pkl)
|   |-- reports/                       insights report text file
|   |-- ny_carematch_master.csv        merged + scored dataset
|   |-- ny_carematch_final.csv         with ML predictions added
|   `-- match_scores_by_profile.csv    AI match scores for 4 patient profiles
|-- tests/
|   `-- test_pipeline.py               20 unit tests — all passing
|-- .github/workflows/tests.yml        CI — runs pytest on every push
|-- 01_data_integration.py
|-- 02_eda_analysis.py
|-- 03_ai_matching_model.py
|-- 04_insights_report.py
|-- requirements.txt
|-- .gitignore
`-- README.md
```

---

## Technical Stack

| Layer | Tool | Role |
|---|---|---|
| Data | SAMHSA + HRSA + FCC (3 public datasets) | 62 NY counties, 60+ features |
| Integration | Python Pandas | Merge, derive metrics, priority scoring |
| Statistical analysis | SAS (PROC LOGISTIC, REG, TABULATE, CLUSTER) | Validation + government-standard reports |
| Machine learning | Scikit-learn | Random Forest, Gradient Boosting, K-Means |
| Visualization | Matplotlib, Seaborn | 16 charts |
| Testing | Pytest (20 tests) | Data and model validation |
| CI/CD | GitHub Actions | Automated testing on every push |

---

*RISE Fellowship — University at Albany, SUNY (2025)*
*AICareMatch — Making Mental Health Care as Accessible as Booking a Ride*
*Dharani Bhumireddy — MS Data Science, University at Albany*
