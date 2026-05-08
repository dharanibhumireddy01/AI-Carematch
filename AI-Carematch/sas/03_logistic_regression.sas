/*==============================================================================
  sas/03_logistic_regression.sas
  AICareMatch — Predictive Analysis in SAS
  
  Three analyses:
    1. PROC LOGISTIC — Predicts which counties are at risk of becoming
       HPSA-designated shortage areas. Complements the Python Random Forest.
  
    2. PROC REG — Linear regression to quantify what drives treatment gap.
       Validates the Python Gradient Boosting findings.
  
    3. PROC CLUSTER — Hierarchical clustering of counties.
       Compares with Python K-Means to validate county segments.
  
  The SAS results are compared against Python model outputs in the README.
  Agreement between SAS (classical stats) and Python (ML) builds confidence
  in the findings.
  
  Author : Dharani Bhumireddy
  Project: AICareMatch — RISE Fellowship, University at Albany (2025)
==============================================================================*/

LIBNAME aim "C:\Users\dhara\OneDrive\Desktop\AICareMatch\data";

/* assumes aim.combined_final exists from 02_descriptive_statistics.sas */

/* ── step 1: prepare binary target variable ──────────────────────────────── */
DATA aim.model_data;
    SET aim.combined_final;

    /* Binary: 1 = HPSA designated shortage, 0 = adequate supply */
    IS_SHORTAGE = (HPSA_STATUS = "Designated");

    /* High treatment gap flag for secondary analysis */
    HIGH_GAP = (TREATMENT_GAP_PCT > 60);

    /* Normalize provider density for regression */
    LOG_PROVIDERS = LOG(PROVIDERS_PER_100K_POP + 1);

    /* Urban dummy */
    IS_URBAN = (URBAN_RURAL_CODE = "Urban");
RUN;

/* ── step 2: PROC LOGISTIC — shortage predictor ──────────────────────────── */
/*
   Logistic regression predicts P(HPSA_DESIGNATED = 1) for each county.
   
   Interpretation:
   - Negative coefficient on PROVIDERS_PER_100K_POP means more providers
     = lower probability of shortage designation (expected, validates model)
   - Positive coefficient on POVERTY_RATE_PCT means higher poverty
     = higher shortage risk
   - Odds ratios (EXP) tell us the multiplicative effect per unit change
*/
PROC LOGISTIC DATA = aim.model_data DESCENDING;
    MODEL IS_SHORTAGE (EVENT='1') =
        LOG_PROVIDERS
        POVERTY_RATE_PCT
        AMI_PERCENT
        BROADBAND_25_3_COVERAGE_PCT
        AVG_SESSION_COST_USD
        IS_URBAN
        / SELECTION = STEPWISE
          SLENTRY   = 0.05
          SLSTAY    = 0.05
          LACKFIT
          CTABLE
          PPROB     = 0.5
          EXPB;
    OUTPUT OUT = aim.logistic_predictions
           PREDICTED = pred_shortage_prob
           LOWER     = pred_lower
           UPPER     = pred_upper;
    TITLE "AICareMatch — HPSA Shortage Risk Logistic Regression";
    TITLE2 "Identifies counties at risk of worsening provider shortage";
RUN;

/* Print top counties most likely to become shortage areas */
PROC SQL OUTOBS=15;
    TITLE "Top 15 Counties by Predicted Shortage Risk (PROC LOGISTIC)";
    SELECT m.COUNTY, m.REGION, l.pred_shortage_prob FORMAT=8.4,
           m.PROVIDERS_PER_100K_POP, m.HPSA_STATUS,
           m.POVERTY_RATE_PCT
    FROM aim.logistic_predictions AS l
    JOIN aim.model_data           AS m ON l.COUNTY = m.COUNTY
    WHERE m.HPSA_STATUS NE "Designated"   /* counties NOT yet designated */
    ORDER BY l.pred_shortage_prob DESC;
QUIT;

/* ── step 3: PROC REG — treatment gap regression ─────────────────────────── */
/*
   Multiple linear regression to quantify which factors drive treatment gap.
   
   This validates the Python Gradient Boosting findings.
   If both models agree on which features matter most, we have high
   confidence in the business recommendations.
*/
PROC REG DATA = aim.model_data;
    MODEL TREATMENT_GAP_PCT =
        LOG_PROVIDERS
        POVERTY_RATE_PCT
        AVG_SESSION_COST_USD
        BROADBAND_25_3_COVERAGE_PCT
        AMI_PERCENT
        AVG_WAIT_TIME_WEEKS
        IS_URBAN
        / STB         /* standardized betas for comparison */
          VIF         /* variance inflation factor for multicollinearity */
          SELECTION = STEPWISE
          SLENTRY   = 0.05
          SLSTAY    = 0.05;
    OUTPUT OUT = aim.reg_predictions
           PREDICTED = pred_gap
           RESIDUAL  = resid_gap;
    TITLE "Treatment Gap Regression — What Drives Unmet Mental Health Need?";
    TITLE2 "STB = standardized coefficient — larger absolute value = stronger predictor";
RUN;

/* ── step 4: residual analysis ───────────────────────────────────────────── */
/*
   Counties with large positive residuals = treatment gap is WORSE than
   the model predicts — these are hidden crisis counties that standard
   indicators would miss. AICareMatch should investigate these first.
*/
PROC SQL OUTOBS=10;
    TITLE "Hidden Crisis Counties — Gap Much Worse Than Predicted (High Residual)";
    SELECT r.COUNTY, m.REGION, m.TREATMENT_GAP_PCT FORMAT=8.1,
           r.pred_gap FORMAT=8.1, r.resid_gap FORMAT=8.1,
           m.PROVIDERS_PER_100K_POP, m.POVERTY_RATE_PCT
    FROM aim.reg_predictions AS r
    JOIN aim.model_data      AS m ON r.COUNTY = m.COUNTY
    ORDER BY r.resid_gap DESC;
QUIT;

/* ── step 5: PROC CLUSTER — hierarchical clustering ─────────────────────── */
/*
   Hierarchical clustering using Ward's method.
   Complements Python K-Means clustering (Model 3 in 03_ai_matching_model.py).
   Both methods should identify similar county groupings.
*/
PROC STANDARD DATA = aim.model_data OUT = aim.model_standardized MEAN=0 STD=1;
    VAR AMI_PERCENT LOG_PROVIDERS TREATMENT_GAP_PCT
        BROADBAND_25_3_COVERAGE_PCT POVERTY_RATE_PCT
        AVG_SESSION_COST_USD AVG_WAIT_TIME_WEEKS;
RUN;

PROC CLUSTER DATA   = aim.model_standardized
             METHOD = WARD
             OUTTREE = aim.cluster_tree
             PRINT   = 10
             PLOTS   = ALL;
    VAR AMI_PERCENT LOG_PROVIDERS TREATMENT_GAP_PCT
        BROADBAND_25_3_COVERAGE_PCT POVERTY_RATE_PCT
        AVG_SESSION_COST_USD AVG_WAIT_TIME_WEEKS;
    ID COUNTY;
    TITLE "Hierarchical Clustering of NY Counties — Ward's Method";
    TITLE2 "Compares with Python K-Means segments in 03_ai_matching_model.py";
RUN;

/* Cut tree at 5 clusters (same as Python K-Means k=5) */
PROC TREE DATA = aim.cluster_tree NCLUSTERS = 5
          OUT  = aim.cluster_assignments;
    ID COUNTY;
    TITLE "5-Cluster Solution — County Segments";
RUN;

PROC SORT DATA = aim.cluster_assignments;
    BY CLUSTER;
RUN;

PROC PRINT DATA = aim.cluster_assignments;
    TITLE "County Cluster Assignments (5 Segments)";
    TITLE2 "Compare these groupings with Python K-Means output";
RUN;

/* Profile each cluster */
PROC MEANS DATA = aim.model_data NWAY NOPRINT;
    CLASS COUNTY;
    VAR AMI_PERCENT PROVIDERS_PER_100K_POP TREATMENT_GAP_PCT
        BROADBAND_25_3_COVERAGE_PCT POVERTY_RATE_PCT;
    OUTPUT OUT = aim.county_profiles MEAN=;
RUN;

/* ── step 6: save model summary ──────────────────────────────────────────── */
PROC SQL;
    CREATE TABLE aim.model_summary AS
    SELECT
        "PROC LOGISTIC" AS model_name,
        "HPSA Shortage Prediction" AS target,
        "See logistic_predictions dataset" AS results
    UNION ALL
    SELECT "PROC REG", "Treatment Gap %",
           "See reg_predictions dataset"
    UNION ALL
    SELECT "PROC CLUSTER (Ward)", "County Segments (k=5)",
           "See cluster_assignments dataset";
QUIT;

PROC PRINT DATA = aim.model_summary;
    TITLE "AICareMatch SAS Model Summary";
RUN;

%PUT NOTE: SAS predictive analysis complete.;
%PUT NOTE: Compare PROC LOGISTIC predictions with Python RF (outputs/models/shortage_predictor_rf.pkl);
%PUT NOTE: Compare PROC CLUSTER with Python K-Means (outputs/models/county_kmeans.pkl);
%PUT NOTE: Agreement between SAS and Python validates findings.;
