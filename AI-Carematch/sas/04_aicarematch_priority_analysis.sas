/*==============================================================================
  sas/04_aicarematch_priority_analysis.sas
  AICareMatch — Priority Score Validation and Launch Strategy Analysis
  
  This is the final SAS analysis — it takes the AICareMatch Priority Score
  computed in Python (01_data_integration.py) and validates, profiles,
  and reports on it using SAS's superior reporting capabilities.
  
  Key output: A formatted launch strategy report for the AICareMatch team.
  This is the type of report that would be presented to Albany Med,
  NY OMH, or potential investors to justify the launch county selection.
  
  Author : Dharani Bhumireddy
  Project: AICareMatch — RISE Fellowship, University at Albany (2025)
==============================================================================*/

LIBNAME aim "C:\Users\dhara\OneDrive\Desktop\AICareMatch\data";

/* ── load the Python-generated master dataset ────────────────────────────── */
PROC IMPORT
    DATAFILE = "C:\Users\dhara\OneDrive\Desktop\AICareMatch\outputs\ny_carematch_final.csv"
    OUT      = aim.master_final
    DBMS     = CSV
    REPLACE;
    GETNAMES  = YES;
    GUESSINGROWS = 100;
RUN;

/* ── step 1: validate the priority score distribution ────────────────────── */
PROC UNIVARIATE DATA = aim.master_final NORMAL;
    VAR AICAREMATCH_PRIORITY_SCORE SHORTAGE_RISK_SCORE TREATMENT_GAP_PCT;
    HISTOGRAM AICAREMATCH_PRIORITY_SCORE / NORMAL;
    INSET N MEAN MEDIAN STD MIN MAX / FORMAT=8.2;
    TITLE "AICareMatch Priority Score Distribution — All 62 NY Counties";
RUN;

/* ── step 2: tier breakdown with PROC FREQ ────────────────────────────────── */
PROC FREQ DATA = aim.master_final;
    TABLES LAUNCH_TIER / NOCUM PLOTS=FREQPLOT;
    TITLE "AICareMatch Launch Tier Distribution";
RUN;

PROC FREQ DATA = aim.master_final;
    TABLES LAUNCH_TIER * REGION / NOROW NOCOL NOPERCENT;
    TITLE "Launch Tier by Region — Where Are the Critical Priority Counties?";
RUN;

/* ── step 3: Tier 1 counties — full profile ──────────────────────────────── */
PROC PRINT DATA = aim.master_final NOOBS;
    WHERE LAUNCH_TIER CONTAINS "Tier 1";
    VAR COUNTY REGION AICAREMATCH_PRIORITY_SCORE TREATMENT_GAP_PCT
        PROVIDERS_PER_100K_POP HPSA_SCORE BROADBAND_25_3_COVERAGE_PCT
        AMI_COUNT_ESTIMATED TELEHEALTH_REACHABLE_PATIENTS
        AVG_WAIT_TIME_WEEKS AVG_SESSION_COST_USD;
    TITLE "AICareMatch Tier 1 Counties — LAUNCH NOW";
    TITLE2 "These counties have the highest unmet need AND telehealth feasibility";
RUN;

/* ── step 4: PROC TABULATE — executive summary table ─────────────────────── */
PROC TABULATE DATA = aim.master_final FORMAT=COMMA12.;
    CLASS LAUNCH_TIER REGION;
    VAR AICAREMATCH_PRIORITY_SCORE TREATMENT_GAP_PCT
        PROVIDERS_PER_100K_POP TELEHEALTH_REACHABLE_PATIENTS
        AMI_COUNT_ESTIMATED UNTREATED_COUNT_ESTIMATED;
    TABLE LAUNCH_TIER,
          (AICAREMATCH_PRIORITY_SCORE TREATMENT_GAP_PCT
           PROVIDERS_PER_100K_POP) * MEAN
          TELEHEALTH_REACHABLE_PATIENTS * SUM
          AMI_COUNT_ESTIMATED * SUM
          UNTREATED_COUNT_ESTIMATED * SUM
          / BOX = "Launch Tier Summary"
            MISSTEXT = "N/A"
            STYLE=[BACKGROUND=LIGHTBLUE];
    TITLE "AICareMatch Launch Strategy — Summary by Tier";
    TITLE2 "SUM columns show total patients in each tier | MEAN shows avg county characteristics";
RUN;

/* ── step 5: underserved populations analysis ─────────────────────────────── */
/*
   AICareMatch specifically targets: first responders, rural communities,
   postpartum women, elderly. Identify counties for each segment.
*/

/* First Responder + Military Focus (PTSD) */
PROC SQL OUTOBS=10;
    TITLE "First Responder / Military Focus — Top 10 Counties by PTSD Prevalence";
    TITLE2 "Jefferson County (Ft. Drum) and North Country are primary targets";
    SELECT COUNTY, REGION, PTSD_PERCENT FORMAT=8.1,
           PROVIDERS_PER_100K_POP FORMAT=8.1,
           TREATMENT_GAP_PCT FORMAT=8.1,
           AICAREMATCH_PRIORITY_SCORE FORMAT=8.1
    FROM aim.master_final
    ORDER BY PTSD_PERCENT DESC;
QUIT;

/* Substance Use / SUD Focus */
PROC SQL OUTOBS=10;
    TITLE "Substance Use Disorder Focus — Top 10 Counties";
    SELECT COUNTY, REGION, SUBSTANCE_USE_DISORDER_PCT FORMAT=8.1,
           PROVIDERS_PER_100K_POP, TREATMENT_GAP_PCT FORMAT=8.1
    FROM aim.master_final
    ORDER BY SUBSTANCE_USE_DISORDER_PCT DESC;
QUIT;

/* High-Poverty / Uninsured Focus */
PROC SQL OUTOBS=10;
    TITLE "High-Poverty Counties — Cost Barrier Focus";
    TITLE2 "These counties most need AICareMatch cost transparency feature";
    SELECT COUNTY, REGION, POVERTY_RATE_PCT FORMAT=8.1,
           AVG_SESSION_COST_USD FORMAT=8.0,
           MEDIAN_HOUSEHOLD_INCOME FORMAT=DOLLAR10.,
           TREATMENT_GAP_PCT FORMAT=8.1
    FROM aim.master_final
    ORDER BY POVERTY_RATE_PCT DESC;
QUIT;

/* ── step 6: Albany launch market — detailed profile ─────────────────────── */
PROC SQL;
    TITLE "Capital Region Counties — Albany Med Pilot Market Analysis";
    SELECT COUNTY, AICAREMATCH_PRIORITY_SCORE FORMAT=8.1,
           LAUNCH_TIER, TREATMENT_GAP_PCT FORMAT=8.1,
           PROVIDERS_PER_100K_POP FORMAT=8.1,
           TELEHEALTH_REACHABLE_PATIENTS FORMAT=COMMA12.,
           AVG_WAIT_TIME_WEEKS FORMAT=8.1,
           BROADBAND_25_3_COVERAGE_PCT FORMAT=8.1
    FROM aim.master_final
    WHERE REGION = "Capital"
    ORDER BY AICAREMATCH_PRIORITY_SCORE DESC;
QUIT;

/* ── step 7: telehealth viability vs in-person need ─────────────────────── */
/*
   Classifies counties into 4 quadrants:
   Q1: High need + High broadband = Pure telehealth market (AICareMatch ideal)
   Q2: High need + Low broadband  = Hybrid market (need in-person partners)
   Q3: Low need  + High broadband = Expansion market (future phase)
   Q4: Low need  + Low broadband  = Not priority
*/
DATA aim.quadrant_analysis;
    SET aim.master_final;
    HIGH_NEED      = (TREATMENT_GAP_PCT > 58);
    HIGH_BROADBAND = (BROADBAND_25_3_COVERAGE_PCT > 70);
    
    IF      HIGH_NEED AND     HIGH_BROADBAND THEN QUADRANT = "Q1: Telehealth Sweet Spot";
    ELSE IF HIGH_NEED AND NOT HIGH_BROADBAND THEN QUADRANT = "Q2: Hybrid Care Needed";
    ELSE IF NOT HIGH_NEED AND HIGH_BROADBAND THEN QUADRANT = "Q3: Future Expansion";
    ELSE                                          QUADRANT = "Q4: Lower Priority";
RUN;

PROC FREQ DATA = aim.quadrant_analysis;
    TABLES QUADRANT / NOCUM;
    TITLE "AICareMatch Market Quadrant Analysis — 62 NY Counties";
RUN;

PROC PRINT DATA = aim.quadrant_analysis NOOBS;
    WHERE QUADRANT = "Q1: Telehealth Sweet Spot";
    VAR COUNTY REGION TREATMENT_GAP_PCT BROADBAND_25_3_COVERAGE_PCT
        AICAREMATCH_PRIORITY_SCORE TELEHEALTH_REACHABLE_PATIENTS;
    TITLE "Q1 Counties — Ideal AICareMatch Telehealth Markets";
RUN;

/* ── step 8: generate launch report ─────────────────────────────────────── */
ODS PDF FILE = "C:\Users\dhara\OneDrive\Desktop\AICareMatch\outputs\reports\aicarematch_sas_launch_report.pdf"
    STYLE = JOURNAL;

PROC PRINT DATA = aim.master_final (OBS=20) NOOBS;
    VAR COUNTY REGION LAUNCH_TIER AICAREMATCH_PRIORITY_SCORE
        TREATMENT_GAP_PCT PROVIDERS_PER_100K_POP
        TELEHEALTH_REACHABLE_PATIENTS;
    TITLE "AICareMatch NY State Launch Priority Report";
    TITLE2 "Top 20 Counties by Priority Score";
RUN;

ODS PDF CLOSE;

%PUT NOTE: AICareMatch SAS analysis complete.;
%PUT NOTE: PDF report saved to outputs/reports/aicarematch_sas_launch_report.pdf;
%PUT NOTE: Share this report with the AICareMatch team for launch decisions.;
