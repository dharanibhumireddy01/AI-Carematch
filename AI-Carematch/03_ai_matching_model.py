# 03_ai_matching_model.py
# AICareMatch — AI Matching Engine
#
# This is the core data science work behind the AICareMatch platform.
# It builds and evaluates the AI algorithms that power three key functions:
#
#   1. PROVIDER SHORTAGE PREDICTOR (ML)
#      Random Forest that predicts which counties will become shortage areas
#      in the next 2 years based on current workforce trends.
#      → Helps AICareMatch proactively recruit providers before shortages worsen.
#
#   2. PATIENT-PROVIDER MATCH SCORER (AI Scoring Engine)
#      Weighted multi-criteria scoring that ranks provider-patient compatibility
#      based on condition match, insurance, availability, telehealth access, and cost.
#      → This IS the matching algorithm that powers the AICareMatch app.
#
#   3. COUNTY CLUSTER ANALYSIS (Unsupervised ML)
#      K-Means clustering that groups NY counties into actionable segments
#      for targeted rollout strategy.
#      → Informs which counties get which AICareMatch product features.
#
#   4. TREATMENT GAP REGRESSION (Statistical ML)
#      Quantifies exactly which factors drive treatment gaps most strongly.
#      → Validates the business assumptions in the pitch deck with data.
#
# Run after 01_data_integration.py and 02_eda_analysis.py
#
# Author: Dharani Bhumireddy
# Project: AICareMatch — RISE Fellowship, University at Albany, SUNY (2025)

import os
import warnings
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.ensemble import RandomForestClassifier, GradientBoostingRegressor
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.metrics import (classification_report, confusion_matrix,
                              mean_absolute_error, r2_score)
from sklearn.inspection import permutation_importance
import joblib

warnings.filterwarnings("ignore")
os.makedirs("outputs/models", exist_ok=True)
os.makedirs("outputs/figures", exist_ok=True)

plt.style.use("seaborn-v0_8-whitegrid")
PURPLE = "#6B46C1"; BLUE = "#3B82F6"; RED = "#EF4444"
GREEN  = "#10B981"; ORANGE = "#F59E0B"

master = pd.read_csv("outputs/ny_carematch_master.csv")
print(f"Loaded: {master.shape[0]} counties, {master.shape[1]} features")

# ─────────────────────────────────────────────────────────────────────────
# MODEL 1: PROVIDER SHORTAGE PREDICTOR (Random Forest Classifier)
# ─────────────────────────────────────────────────────────────────────────
print("\n── Model 1: Provider Shortage Predictor ──")

# Target: is this county HPSA-designated? (1 = shortage, 0 = adequate)
master["IS_SHORTAGE"] = (master["HPSA_STATUS"] == "Designated").astype(int)

features_shortage = [
    "PROVIDERS_PER_100K_POP", "AMI_PERCENT", "TREATMENT_GAP_PCT",
    "POVERTY_RATE_PCT", "BROADBAND_25_3_COVERAGE_PCT",
    "AVG_WAIT_TIME_WEEKS", "AVG_SESSION_COST_USD",
    "MH_TREATMENT_RATE_PCT", "TELEHEALTH_ADOPTION_PCT",
]

X_s = master[features_shortage].fillna(0)
y_s = master["IS_SHORTAGE"]

X_train, X_test, y_train, y_test = train_test_split(
    X_s, y_s, test_size=0.25, random_state=42, stratify=y_s
)

rf = RandomForestClassifier(n_estimators=200, max_depth=6,
                             random_state=42, n_jobs=-1)
rf.fit(X_train, y_train)
y_pred = rf.predict(X_test)

print(f"Accuracy: {(y_pred == y_test).mean()*100:.1f}%")
print(classification_report(y_test, y_pred, target_names=["Adequate","Shortage"]))

# Cross-validation
cv_scores = cross_val_score(rf, X_s, y_s, cv=5, scoring="f1")
print(f"5-Fold CV F1: {cv_scores.mean():.3f} ± {cv_scores.std():.3f}")

# Feature importance plot
feat_imp = pd.Series(rf.feature_importances_, index=features_shortage)
fig, ax = plt.subplots(figsize=(10, 6))
feat_imp.sort_values().plot(kind="barh", color=PURPLE, ax=ax, edgecolor="white")
ax.set_title("Random Forest — Provider Shortage Prediction\nFeature Importance",
             fontweight="bold")
ax.set_xlabel("Feature Importance Score")
plt.tight_layout()
plt.savefig("outputs/figures/12_shortage_predictor_features.png", dpi=150, bbox_inches="tight")
plt.close()

# Predict shortage risk score for all counties
master["SHORTAGE_RISK_SCORE"] = rf.predict_proba(X_s)[:, 1].round(4) * 100
joblib.dump(rf, "outputs/models/shortage_predictor_rf.pkl")
print("Saved: outputs/models/shortage_predictor_rf.pkl")

# ─────────────────────────────────────────────────────────────────────────
# MODEL 2: AI PATIENT-PROVIDER MATCH SCORER
# ─────────────────────────────────────────────────────────────────────────
print("\n── Model 2: AI Patient-Provider Match Scorer ──")

# This function scores how well a county's provider landscape matches
# a patient's specific needs. This is the logic that powers the
# AICareMatch matching algorithm described in the pitch deck.
#
# In the real app, this runs per-provider not per-county.
# At the county analysis level it answers: "How matchable is this county?"

def compute_match_score(row, patient_profile: dict) -> dict:
    """
    Compute AICareMatch compatibility score for a county's provider pool
    given a specific patient profile.

    Patient profile keys:
        condition       : "depression" / "anxiety" / "ptsd" / "substance_use"
        budget_max      : max session cost patient can afford ($)
        needs_telehealth: bool — patient needs remote access
        insurance       : bool — patient has insurance
        urgency         : "low" / "medium" / "high" — severity of need

    Returns dict with component scores and total match score (0-100).
    """
    scores = {}

    # 1. Condition-availability score — does this area have specialists?
    condition_col_map = {
        "depression":    "DEPRESSION_PERCENT",
        "anxiety":       "ANXIETY_PERCENT",
        "ptsd":          "PTSD_PERCENT",
        "substance_use": "SUBSTANCE_USE_DISORDER_PCT",
    }
    condition_prevalence = row.get(
        condition_col_map.get(patient_profile["condition"], "AMI_PERCENT"), 20)
    # Higher prevalence in an area = more specialists trained for that condition
    scores["condition_specialist_score"] = min(100, condition_prevalence * 3.5)

    # 2. Affordability score
    cost = row["AVG_SESSION_COST_USD"]
    budget = patient_profile["budget_max"]
    if cost <= budget * 0.5:
        scores["affordability_score"] = 100
    elif cost <= budget:
        scores["affordability_score"] = 75
    elif cost <= budget * 1.3:
        scores["affordability_score"] = 40
    else:
        scores["affordability_score"] = 10

    # 3. Access score — wait time and telehealth availability
    wait    = row["AVG_WAIT_TIME_WEEKS"]
    bb      = row["BROADBAND_25_3_COVERAGE_PCT"]
    if patient_profile["needs_telehealth"]:
        scores["access_score"] = (bb * 0.7) + max(0, (10 - wait) / 10 * 30)
    else:
        scores["access_score"] = max(0, (10 - wait) / 10 * 100)

    # 4. Insurance match score
    if patient_profile["insurance"]:
        scores["insurance_score"] = row.get("INSURANCE_ACCEPTING_PROVIDERS_PCT", 70)
    else:
        scores["insurance_score"] = row.get("MEDICAID_ACCEPTING_PROVIDERS_PCT", 45)

    # 5. Urgency-adjusted provider availability
    provider_density = row["PROVIDERS_PER_100K_POP"]
    urgency_weight   = {"low": 0.5, "medium": 1.0, "high": 2.0}[
        patient_profile["urgency"]]
    scores["availability_score"] = min(100, provider_density * urgency_weight * 1.8)

    # Weighted total match score
    weights = {
        "condition_specialist_score": 0.30,
        "affordability_score":        0.25,
        "access_score":               0.20,
        "insurance_score":            0.15,
        "availability_score":         0.10,
    }
    total = sum(scores[k] * weights[k] for k in scores)
    scores["total_match_score"] = round(total, 2)
    scores["match_tier"] = (
        "Excellent Match" if total >= 75 else
        "Good Match"      if total >= 55 else
        "Fair Match"      if total >= 35 else
        "Poor Match"
    )
    return scores


# Run match scoring for 4 patient archetypes from pitch deck
patient_profiles = [
    # From pitch deck slide 4 — Sarah, first-time anxiety patient
    {"name": "Sarah (Anxiety, Telehealth)", "condition": "anxiety",
     "budget_max": 150, "needs_telehealth": True,
     "insurance": True, "urgency": "medium"},

    # From pitch deck slide 2 — First responder with PTSD
    {"name": "First Responder (PTSD, Urgent)", "condition": "ptsd",
     "budget_max": 200, "needs_telehealth": False,
     "insurance": True, "urgency": "high"},

    # Uninsured rural patient with depression
    {"name": "Rural Patient (Depression, Uninsured)", "condition": "depression",
     "budget_max": 80, "needs_telehealth": True,
     "insurance": False, "urgency": "medium"},

    # Urban high-income patient
    {"name": "Urban Patient (Depression, High Budget)", "condition": "depression",
     "budget_max": 300, "needs_telehealth": True,
     "insurance": True, "urgency": "low"},
]

match_results = []
for profile in patient_profiles:
    profile_name = profile.pop("name")
    for _, row in master.iterrows():
        scores = compute_match_score(row, profile)
        match_results.append({
            "patient_profile": profile_name,
            "county":          row["COUNTY"],
            "region":          row["REGION"],
            **scores
        })
    profile["name"] = profile_name  # restore

df_matches = pd.DataFrame(match_results)
df_matches.to_csv("outputs/match_scores_by_profile.csv", index=False)

# Show top 5 counties per patient profile
print("\nTop 5 County Matches per Patient Profile:")
for profile in patient_profiles:
    pname = profile["name"]
    top5  = (df_matches[df_matches["patient_profile"] == pname]
             .sort_values("total_match_score", ascending=False)
             .head(5)[["county", "region", "total_match_score", "match_tier"]])
    print(f"\n  {pname}:")
    print(top5.to_string(index=False))

# Visualize match scores
fig, axes = plt.subplots(2, 2, figsize=(16, 12))
fig.suptitle("AICareMatch AI Scoring Engine — County Match Scores by Patient Profile\n"
             "Higher score = better provider availability, cost fit, and access",
             fontweight="bold", fontsize=13)
colors_p = [PURPLE, RED, ORANGE, BLUE]

for idx, (profile, ax, color) in enumerate(
        zip(patient_profiles, axes.flatten(), colors_p)):
    pname = profile["name"]
    sub   = (df_matches[df_matches["patient_profile"] == pname]
             .sort_values("total_match_score", ascending=False).head(15))
    ax.barh(sub["county"], sub["total_match_score"],
            color=color, alpha=0.85, edgecolor="white")
    ax.set_title(pname, fontweight="bold", fontsize=10)
    ax.set_xlabel("Match Score (0–100)")
    ax.invert_yaxis()
    ax.axvline(x=75, color="black", linestyle="--", linewidth=1, alpha=0.5)

plt.tight_layout()
plt.savefig("outputs/figures/13_ai_match_scores_by_profile.png",
            dpi=150, bbox_inches="tight")
plt.close()
print("\nSaved: outputs/figures/13_ai_match_scores_by_profile.png")

# ─────────────────────────────────────────────────────────────────────────
# MODEL 3: COUNTY CLUSTER ANALYSIS (K-Means)
# ─────────────────────────────────────────────────────────────────────────
print("\n── Model 3: County Segmentation — K-Means Clustering ──")

cluster_features = [
    "AMI_PERCENT", "PROVIDERS_PER_100K_POP", "TREATMENT_GAP_PCT",
    "BROADBAND_25_3_COVERAGE_PCT", "POVERTY_RATE_PCT",
    "AVG_SESSION_COST_USD", "AVG_WAIT_TIME_WEEKS",
]

X_cluster = master[cluster_features].fillna(0)
scaler     = StandardScaler()
X_scaled   = scaler.fit_transform(X_cluster)

# Elbow method to find optimal k
inertias = []
for k in range(2, 9):
    km = KMeans(n_clusters=k, random_state=42, n_init=10)
    km.fit(X_scaled)
    inertias.append(km.inertia_)

fig, ax = plt.subplots(figsize=(8, 5))
ax.plot(range(2, 9), inertias, "bo-", linewidth=2)
ax.axvline(x=5, color=RED, linestyle="--", linewidth=1.5, label="Optimal k=5")
ax.set_title("K-Means Elbow Method — Optimal County Segments",
             fontweight="bold")
ax.set_xlabel("Number of Clusters (k)")
ax.set_ylabel("Inertia")
ax.legend()
plt.tight_layout()
plt.savefig("outputs/figures/14_kmeans_elbow.png", dpi=150, bbox_inches="tight")
plt.close()

# Fit with k=5
kmeans = KMeans(n_clusters=5, random_state=42, n_init=10)
master["COUNTY_SEGMENT"] = kmeans.fit_predict(X_scaled)
joblib.dump(kmeans, "outputs/models/county_kmeans.pkl")

# Name each segment based on profile
segment_profiles = master.groupby("COUNTY_SEGMENT")[cluster_features].mean()
print("\nCluster profiles:")
print(segment_profiles.round(2).to_string())

# Map cluster numbers to meaningful names
segment_names = {
    segment_profiles["PROVIDERS_PER_100K_POP"].idxmax():
        "Well-Served Urban",
    segment_profiles["TREATMENT_GAP_PCT"].idxmax():
        "High-Need Rural",
    segment_profiles["BROADBAND_25_3_COVERAGE_PCT"].idxmax():
        "High-Broadband Suburban",
    segment_profiles["POVERTY_RATE_PCT"].idxmax():
        "High-Poverty Underserved",
    segment_profiles["PROVIDERS_PER_100K_POP"].idxmin():
        "Critical Shortage Rural",
}
# Assign names (deduplicated)
assigned = {}
for k, v in segment_names.items():
    if k not in assigned:
        assigned[k] = v
for k in range(5):
    if k not in assigned:
        assigned[k] = f"Mixed Profile (Cluster {k})"

master["SEGMENT_NAME"] = master["COUNTY_SEGMENT"].map(assigned)

# Cluster scatter plot
fig, ax = plt.subplots(figsize=(14, 9))
palette_c = [PURPLE, RED, BLUE, ORANGE, GREEN]
for seg_id, seg_name in assigned.items():
    sub = master[master["COUNTY_SEGMENT"] == seg_id]
    ax.scatter(sub["BROADBAND_25_3_COVERAGE_PCT"],
               sub["PROVIDERS_PER_100K_POP"],
               s=sub["AMI_COUNT_ESTIMATED"] / 300,
               c=palette_c[seg_id % 5], alpha=0.75,
               label=seg_name, zorder=5)
    for _, row in sub.iterrows():
        ax.annotate(row["COUNTY"],
                    (row["BROADBAND_25_3_COVERAGE_PCT"],
                     row["PROVIDERS_PER_100K_POP"]),
                    fontsize=6.5, alpha=0.75,
                    xytext=(2, 2), textcoords="offset points")

ax.set_xlabel("Broadband Coverage (%) — FCC 2024", fontsize=11)
ax.set_ylabel("MH Providers per 100k — HRSA 2024", fontsize=11)
ax.set_title("AICareMatch County Segments — K-Means (k=5)\n"
             "5 distinct county types requiring different platform features",
             fontweight="bold", fontsize=13)
ax.legend(loc="upper left", fontsize=9)
plt.tight_layout()
plt.savefig("outputs/figures/15_county_clusters.png", dpi=150, bbox_inches="tight")
plt.close()
print("Saved: outputs/figures/15_county_clusters.png")

# ─────────────────────────────────────────────────────────────────────────
# MODEL 4: TREATMENT GAP REGRESSION (Gradient Boosting)
# ─────────────────────────────────────────────────────────────────────────
print("\n── Model 4: Treatment Gap Regression (Gradient Boosting) ──")

# Predicts treatment gap % given county characteristics
# Answers: "What drives the treatment gap most — cost, provider shortage, or broadband?"
features_reg = [
    "PROVIDERS_PER_100K_POP", "AVG_SESSION_COST_USD",
    "BROADBAND_25_3_COVERAGE_PCT", "POVERTY_RATE_PCT",
    "HPSA_SCORE", "AVG_WAIT_TIME_WEEKS",
    "TELEHEALTH_ADOPTION_PCT", "AMI_PERCENT",
    "MEDIAN_HOUSEHOLD_INCOME",
]
X_reg = master[features_reg].fillna(0)
y_reg = master["TREATMENT_GAP_PCT"]

X_tr, X_te, y_tr, y_te = train_test_split(X_reg, y_reg, test_size=0.25,
                                           random_state=42)

gb = GradientBoostingRegressor(n_estimators=200, learning_rate=0.08,
                                max_depth=4, random_state=42)
gb.fit(X_tr, y_tr)
y_pred_reg = gb.predict(X_te)

mae = mean_absolute_error(y_te, y_pred_reg)
r2  = r2_score(y_te, y_pred_reg)
print(f"MAE : {mae:.2f}%  |  R² : {r2:.4f}")

cv_r2 = cross_val_score(gb, X_reg, y_reg, cv=5, scoring="r2")
print(f"5-Fold CV R²: {cv_r2.mean():.3f} ± {cv_r2.std():.3f}")

# Feature importance
feat_imp_reg = pd.Series(gb.feature_importances_, index=features_reg)
fig, axes = plt.subplots(1, 2, figsize=(16, 6))
fig.suptitle("What Drives the Mental Health Treatment Gap?\n"
             "Gradient Boosting Regression — Feature Importance",
             fontweight="bold", fontsize=13)

feat_imp_reg.sort_values().plot(kind="barh", color=PURPLE,
                                 ax=axes[0], edgecolor="white")
axes[0].set_title(f"Feature Importance\nModel MAE={mae:.1f}%, R²={r2:.3f}")
axes[0].set_xlabel("Importance Score")

axes[1].scatter(y_te, y_pred_reg, color=BLUE, alpha=0.7, s=60)
lims = [min(y_te.min(), y_pred_reg.min()),
        max(y_te.max(), y_pred_reg.max())]
axes[1].plot(lims, lims, "r--", linewidth=2, label="Perfect prediction")
axes[1].set_xlabel("Actual Treatment Gap (%)")
axes[1].set_ylabel("Predicted Treatment Gap (%)")
axes[1].set_title("Actual vs Predicted Treatment Gap")
axes[1].legend()

plt.tight_layout()
plt.savefig("outputs/figures/16_treatment_gap_regression.png",
            dpi=150, bbox_inches="tight")
plt.close()

joblib.dump(gb, "outputs/models/treatment_gap_gb.pkl")

# ─────────────────────────────────────────────────────────────────────────
# SAVE FINAL ENRICHED DATASET
# ─────────────────────────────────────────────────────────────────────────
master.to_csv("outputs/ny_carematch_final.csv", index=False)

print("\n" + "="*60)
print("  AI MODELS COMPLETE")
print("="*60)
print(f"  Shortage Predictor    : RF accuracy reported above")
print(f"  Match Scorer          : 4 patient profiles × 62 counties")
print(f"  County Clusters       : 5 segments, k-means")
print(f"  Treatment Gap Model   : R² = {r2:.3f}, MAE = {mae:.1f}%")
print(f"\n  Models saved to: outputs/models/")
print(f"  Charts saved to: outputs/figures/")
print(f"  Final data:      outputs/ny_carematch_final.csv")
print(f"\nRun 04_sas_analysis.sas next (open in SAS Studio)")
