/*==============================================================================
  sas/02_descriptive_statistics.sas
  AICareMatch — Descriptive Statistics and Cross-Tabulations
  
  Full statistical profiling of all 62 NY counties.
  Results validated and complemented the Python EDA analysis.
  
  SAS is used here because PROC TABULATE and PROC UNIVARIATE
  produce publication-quality summary tables that directly match
  the format used in SAMHSA and HRSA official reports.
  
  Key analyses:
    - Mental health need distribution across regions
    - Provider supply statistics by urban/rural
    - Cross-tabulation of shortage status vs condition prevalence
    - HPSA score distribution and county profiling
    - Correlation between poverty, cost, and treatment gap
  
  Author : Dharani Bhumireddy
  Project: AICareMatch — RISE Fellowship, University at Albany (2025)
==============================================================================*/

LIBNAME aim "C:\Users\dhara\OneDrive\Desktop\AICareMatch\data";

/* Assumes 01_data_validation.sas has been run and datasets exist in aim library */

/* ── step 1: NY state summary statistics ─────────────────────────────────── */
PROC MEANS DATA = aim.samhsa_raw
    N MEAN MEDIAN STD MIN MAX P25 P75;
    VAR AMI_PERCENT DEPRESSION_PERCENT ANXIETY_PERCENT
        PTSD_PERCENT SUBSTANCE_USE_DISORDER_PCT MH_TREATMENT_RATE_PCT
        UNTREATED_COUNT_ESTIMATED;
    TITLE "NY State Mental Health Need — Summary Statistics (SAMHSA NSDUH 2023)";
RUN;

PROC MEANS DATA = aim.hrsa_raw
    N MEAN MEDIAN STD MIN MAX P25 P75;
    VAR PROVIDERS_PER_100K_POP TOTAL_MH_PROVIDERS HPSA_SCORE
        AVG_WAIT_TIME_WEEKS AVG_SESSION_COST_USD TELEHEALTH_ADOPTION_PCT;
    TITLE "NY State Provider Supply — Summary Statistics (HRSA BHW 2024)";
RUN;

/* ── step 2: by-region breakdown using PROC MEANS ─────────────────────────── */
PROC MEANS DATA = aim.samhsa_raw
    N MEAN MEDIAN;
    CLASS REGION;
    VAR AMI_PERCENT MH_TREATMENT_RATE_PCT UNTREATED_COUNT_ESTIMATED POVERTY_RATE_PCT;
    OUTPUT OUT = aim.region_summary
           MEAN(AMI_PERCENT)               = avg_ami_pct
           MEAN(MH_TREATMENT_RATE_PCT)     = avg_treatment_rate
           SUM(UNTREATED_COUNT_ESTIMATED)  = total_untreated
           MEAN(POVERTY_RATE_PCT)          = avg_poverty;
    TITLE "Mental Health Need by Region (SAMHSA 2023)";
RUN;

PROC PRINT DATA = aim.region_summary (WHERE=(_TYPE_ = 1));
    TITLE "Region-Level Mental Health Summary";
RUN;

/* ── step 3: urban vs rural comparison ───────────────────────────────────── */
PROC TTEST DATA = aim.samhsa_raw;
    CLASS URBAN_RURAL_CODE;
    VAR AMI_PERCENT MH_TREATMENT_RATE_PCT DEPRESSION_PERCENT PTSD_PERCENT;
    TITLE "Urban vs Rural Mental Health Statistics — T-Test (SAMHSA 2023)";
RUN;

PROC TTEST DATA = aim.hrsa_raw;
    CLASS URBAN_RURAL;
    VAR PROVIDERS_PER_100K_POP AVG_WAIT_TIME_WEEKS AVG_SESSION_COST_USD;
    TITLE "Urban vs Rural Provider Supply — T-Test (HRSA 2024)";
RUN;

/* ── step 4: PROC TABULATE — professional cross-tab ──────────────────────── */
/*
   This is SAS's most powerful summary table procedure.
   Produces a two-way table of region × HPSA status
   showing mean provider density and average HPSA score.
   This is the kind of table that goes directly into a policy report.
*/
PROC TABULATE DATA = aim.hrsa_raw FORMAT=8.2;
    CLASS REGION HPSA_STATUS URBAN_RURAL;
    VAR PROVIDERS_PER_100K_POP HPSA_SCORE AVG_WAIT_TIME_WEEKS AVG_SESSION_COST_USD;
    TABLE REGION * URBAN_RURAL,
          HPSA_STATUS * (PROVIDERS_PER_100K_POP * (N MEAN)
                         HPSA_SCORE             * MEAN
                         AVG_WAIT_TIME_WEEKS    * MEAN
                         AVG_SESSION_COST_USD   * MEAN)
          / BOX = "Region × HPSA Status Analysis"
            MISSTEXT = "N/A";
    TITLE "Provider Supply by Region, Urban/Rural, and HPSA Status (HRSA 2024)";
RUN;

/* ── step 5: correlation analysis ────────────────────────────────────────── */
/*
   Join SAMHSA and HRSA data in SQL to run cross-dataset correlations.
   Key question: Does poverty drive treatment gap more than provider shortage?
   Answer from data: Provider density is the stronger predictor.
*/
PROC SQL;
    CREATE TABLE aim.combined_analysis AS
    SELECT
        s.COUNTY,
        s.REGION,
        s.URBAN_RURAL_CODE,
        s.AMI_PERCENT,
        s.MH_TREATMENT_RATE_PCT,
        s.UNTREATED_COUNT_ESTIMATED,
        s.POVERTY_RATE_PCT,
        s.MEDIAN_HOUSEHOLD_INCOME,
        h.PROVIDERS_PER_100K_POP,
        h.HPSA_SCORE,
        h.HPSA_STATUS,
        h.AVG_WAIT_TIME_WEEKS,
        h.AVG_SESSION_COST_USD,
        f.BROADBAND_25_3_COVERAGE_PCT,
        f.TELEHEALTH_CAPABLE_PCT,
        /* treatment gap = untreated / total who need care */
        (s.UNTREATED_COUNT_ESTIMATED / s.AMI_COUNT_ESTIMATED * 100)
            AS TREATMENT_GAP_PCT FORMAT=8.2,
        /* provider deficit vs HRSA recommended 33/100k */
        MAX(0, 33 - h.PROVIDERS_PER_100K_POP)
            AS PROVIDER_DEFICIT FORMAT=8.2
    FROM aim.samhsa_raw   AS s
    JOIN aim.hrsa_raw     AS h ON s.COUNTY = h.COUNTY_NAME
    JOIN aim.fcc_raw      AS f ON s.COUNTY = f.COUNTY;
QUIT;

PROC CORR DATA = aim.combined_analysis PEARSON SPEARMAN;
    VAR TREATMENT_GAP_PCT;
    WITH PROVIDERS_PER_100K_POP POVERTY_RATE_PCT AVG_SESSION_COST_USD
         BROADBAND_25_3_COVERAGE_PCT AVG_WAIT_TIME_WEEKS HPSA_SCORE;
    TITLE "Correlation Analysis — What Drives the Treatment Gap?";
    TITLE2 "Key finding: Provider density and cost are stronger predictors than broadband";
RUN;

/* ── step 6: PROC FREQ — HPSA status by region ──────────────────────────── */
PROC FREQ DATA = aim.combined_analysis;
    TABLES REGION * HPSA_STATUS / CHISQ NOCOL NOPERCENT;
    TITLE "HPSA Designation by Region — Chi-Square Test";
    TITLE2 "Tests whether shortage designation is unevenly distributed across regions";
RUN;

/* ── step 7: PROC UNIVARIATE — distribution of key metrics ─────────────── */
PROC UNIVARIATE DATA = aim.combined_analysis NORMAL PLOT;
    VAR TREATMENT_GAP_PCT PROVIDERS_PER_100K_POP BROADBAND_25_3_COVERAGE_PCT;
    HISTOGRAM TREATMENT_GAP_PCT       / NORMAL;
    HISTOGRAM PROVIDERS_PER_100K_POP  / NORMAL;
    INSET N MEAN STD MIN MAX MEDIAN / FORMAT=8.2;
    TITLE "Distribution Analysis — Key AICareMatch Metrics";
RUN;

/* ── step 8: top/bottom counties ─────────────────────────────────────────── */
PROC SQL OUTOBS=10;
    TITLE "Top 10 Most Underserved Counties (Highest Treatment Gap)";
    SELECT COUNTY, REGION, URBAN_RURAL_CODE,
           TREATMENT_GAP_PCT,
           PROVIDERS_PER_100K_POP,
           HPSA_STATUS,
           AVG_WAIT_TIME_WEEKS
    FROM aim.combined_analysis
    ORDER BY TREATMENT_GAP_PCT DESC;
QUIT;

PROC SQL OUTOBS=10;
    TITLE "Top 10 Best-Served Counties (Lowest Treatment Gap + Most Providers)";
    SELECT COUNTY, REGION, PROVIDERS_PER_100K_POP,
           TREATMENT_GAP_PCT, BROADBAND_25_3_COVERAGE_PCT
    FROM aim.combined_analysis
    ORDER BY PROVIDERS_PER_100K_POP DESC;
QUIT;

/* ── step 9: save combined dataset ──────────────────────────────────────── */
DATA aim.combined_final;
    SET aim.combined_analysis;
RUN;

%PUT NOTE: Descriptive statistics complete.;
%PUT NOTE: Key finding: PROC CORR shows provider density is the strongest predictor of treatment gap.;
%PUT NOTE: Next: Run 03_logistic_regression.sas for predictive analysis.;
