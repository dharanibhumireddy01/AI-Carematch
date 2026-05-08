/*==============================================================================
  sas/01_data_validation.sas
  AICareMatch — Data Validation and Quality Checks
  
  First step in any government health data analysis.
  Run this before any Python analysis to validate the raw data.
  SAS is the standard tool for SAMHSA/HRSA data validation because
  these agencies themselves publish and analyze data in SAS format.
  
  Validates all 3 datasets:
    SAMHSA NSDUH 2023  — demand side
    HRSA BHW 2024      — supply side
    FCC Broadband 2024 — infrastructure
  
  To run:
    1. Export each CSV to SAS dataset using PROC IMPORT below
    2. Submit in SAS Studio (free at https://welcome.oda.sas.com)
    3. Check log for ERROR / WARNING messages
  
  Author : Dharani Bhumireddy
  Project: AICareMatch — RISE Fellowship, University at Albany (2025)
==============================================================================*/

/* ── set library ─────────────────────────────────────────────────────────── */
LIBNAME aim "C:\Users\dhara\OneDrive\Desktop\AICareMatch\data";

/* ── import SAMHSA NSDUH 2023 ─────────────────────────────────────────────── */
PROC IMPORT
    DATAFILE = "C:\Users\dhara\OneDrive\Desktop\AICareMatch\data\samhsa_nsduh_ny_2023.csv"
    OUT      = aim.samhsa_raw
    DBMS     = CSV
    REPLACE;
    GETNAMES  = YES;
    GUESSINGROWS = 100;
RUN;

/* ── import HRSA Provider Data 2024 ──────────────────────────────────────── */
PROC IMPORT
    DATAFILE = "C:\Users\dhara\OneDrive\Desktop\AICareMatch\data\hrsa_provider_ny_2024.csv"
    OUT      = aim.hrsa_raw
    DBMS     = CSV
    REPLACE;
    GETNAMES  = YES;
    GUESSINGROWS = 100;
RUN;

/* ── import FCC Broadband 2024 ────────────────────────────────────────────── */
PROC IMPORT
    DATAFILE = "C:\Users\dhara\OneDrive\Desktop\AICareMatch\data\fcc_broadband_ny_2024.csv"
    OUT      = aim.fcc_raw
    DBMS     = CSV
    REPLACE;
    GETNAMES  = YES;
    GUESSINGROWS = 100;
RUN;

/* ── step 1: structure validation ────────────────────────────────────────── */
PROC CONTENTS DATA = aim.samhsa_raw;
    TITLE "SAMHSA NSDUH 2023 — Dataset Structure";
RUN;

PROC CONTENTS DATA = aim.hrsa_raw;
    TITLE "HRSA Provider Data 2024 — Dataset Structure";
RUN;

PROC CONTENTS DATA = aim.fcc_raw;
    TITLE "FCC Broadband 2024 — Dataset Structure";
RUN;

/* ── step 2: record count and first 10 rows ──────────────────────────────── */
PROC PRINT DATA = aim.samhsa_raw (OBS=10);
    TITLE "SAMHSA — First 10 Records";
RUN;

PROC PRINT DATA = aim.hrsa_raw (OBS=10);
    TITLE "HRSA — First 10 Records";
RUN;

/* ── step 3: missing value analysis ─────────────────────────────────────── */
/*
   Critical columns that must have no missing values before analysis begins.
   If PROC MEANS shows NMISS > 0 for any of these, stop and investigate.
*/
PROC MEANS DATA = aim.samhsa_raw
    N NMISS MIN MAX MEAN MEDIAN STDDEV;
    VAR AMI_PERCENT DEPRESSION_PERCENT ANXIETY_PERCENT PTSD_PERCENT
        MH_TREATMENT_RATE_PCT AMI_COUNT_ESTIMATED UNTREATED_COUNT_ESTIMATED
        POVERTY_RATE_PCT MEDIAN_HOUSEHOLD_INCOME;
    TITLE "SAMHSA — Missing Values and Descriptive Stats for Key Numeric Variables";
RUN;

PROC MEANS DATA = aim.hrsa_raw
    N NMISS MIN MAX MEAN MEDIAN STDDEV;
    VAR PROVIDERS_PER_100K_POP HPSA_SCORE TOTAL_MH_PROVIDERS
        AVG_WAIT_TIME_WEEKS AVG_SESSION_COST_USD TELEHEALTH_ADOPTION_PCT;
    TITLE "HRSA — Missing Values and Descriptive Stats";
RUN;

PROC MEANS DATA = aim.fcc_raw
    N NMISS MIN MAX MEAN MEDIAN;
    VAR BROADBAND_25_3_COVERAGE_PCT TELEHEALTH_CAPABLE_PCT
        UNSERVED_HOUSEHOLDS_PCT MOBILE_5G_NR_COVERAGE_PCT;
    TITLE "FCC — Missing Values and Broadband Coverage Statistics";
RUN;

/* ── step 4: categorical variable validation ─────────────────────────────── */
PROC FREQ DATA = aim.samhsa_raw;
    TABLES REGION URBAN_RURAL_CODE / NOCUM MISSING;
    TITLE "SAMHSA — Region and Urban/Rural Distribution (all 62 counties)";
RUN;

PROC FREQ DATA = aim.hrsa_raw;
    TABLES HPSA_STATUS HPSA_SHORTAGE_TYPE / NOCUM MISSING;
    TITLE "HRSA — HPSA Status Distribution";
RUN;

/* ── step 5: range validation ───────────────────────────────────────────── */
/*
   Check for values outside expected clinical ranges.
   AMI prevalence should be 15-35% for NY counties.
   Providers per 100k should be 1-150 for US counties.
   Broadband should be 0-100%.
*/
PROC SQL;
    TITLE "SAMHSA — Records with Unusual AMI Prevalence (outside 10-40%)";
    SELECT COUNTY, AMI_PERCENT, REGION, URBAN_RURAL_CODE
    FROM aim.samhsa_raw
    WHERE AMI_PERCENT < 10 OR AMI_PERCENT > 40
    ORDER BY AMI_PERCENT;
QUIT;

PROC SQL;
    TITLE "HRSA — Records with Extreme Provider Counts";
    SELECT COUNTY_NAME, PROVIDERS_PER_100K_POP, HPSA_STATUS, REGION
    FROM aim.hrsa_raw
    WHERE PROVIDERS_PER_100K_POP < 2 OR PROVIDERS_PER_100K_POP > 200
    ORDER BY PROVIDERS_PER_100K_POP;
QUIT;

PROC SQL;
    TITLE "FCC — Records with Broadband Coverage Outside 0-100%";
    SELECT COUNTY, BROADBAND_25_3_COVERAGE_PCT, REGION
    FROM aim.fcc_raw
    WHERE BROADBAND_25_3_COVERAGE_PCT < 0 OR BROADBAND_25_3_COVERAGE_PCT > 100
    ORDER BY BROADBAND_25_3_COVERAGE_PCT;
QUIT;

/* ── step 6: county count validation ────────────────────────────────────── */
/*
   All three datasets should have exactly 62 records (62 NY counties).
   Mismatch here means data was filtered or counties are named differently.
*/
PROC SQL;
    TITLE "County Count Validation — All Three Datasets";
    SELECT "SAMHSA" AS dataset, COUNT(*) AS county_count
    FROM aim.samhsa_raw
    UNION ALL
    SELECT "HRSA", COUNT(*) FROM aim.hrsa_raw
    UNION ALL
    SELECT "FCC", COUNT(*) FROM aim.fcc_raw;
QUIT;

/* ── step 7: save validation summary ─────────────────────────────────────── */
PROC SQL;
    CREATE TABLE aim.validation_summary AS
    SELECT
        "Total SAMHSA Records" AS check_name, COUNT(*) AS value
    FROM aim.samhsa_raw
    UNION ALL
    SELECT "SAMHSA Missing AMI_PERCENT",
           SUM(CASE WHEN AMI_PERCENT IS MISSING THEN 1 ELSE 0 END)
    FROM aim.samhsa_raw
    UNION ALL
    SELECT "Total HRSA Records", COUNT(*) FROM aim.hrsa_raw
    UNION ALL
    SELECT "HRSA HPSA Designated",
           SUM(CASE WHEN HPSA_STATUS = "Designated" THEN 1 ELSE 0 END)
    FROM aim.hrsa_raw
    UNION ALL
    SELECT "Total FCC Records", COUNT(*) FROM aim.fcc_raw
    UNION ALL
    SELECT "FCC Counties Below 70% Broadband",
           SUM(CASE WHEN BROADBAND_25_3_COVERAGE_PCT < 70 THEN 1 ELSE 0 END)
    FROM aim.fcc_raw;
QUIT;

PROC PRINT DATA = aim.validation_summary;
    TITLE "AICareMatch Data Validation Summary";
RUN;

%PUT NOTE: Data validation complete. Check log for any ERROR or WARNING messages.;
%PUT NOTE: If all record counts = 62 and no missing values flagged, proceed to 02_descriptive_statistics.sas;
