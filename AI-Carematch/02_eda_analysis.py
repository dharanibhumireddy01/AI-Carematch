# 02_eda_analysis.py
# AICareMatch — Exploratory Data Analysis
#
# Generates 12 charts that tell the full story of the mental health
# supply-demand crisis across New York State's 62 counties.
# Each chart maps to a specific slide in the AICareMatch pitch deck.
#
# Run after 01_data_integration.py
#
# Author: Dharani Bhumireddy
# Project: AICareMatch — RISE Fellowship, University at Albany, SUNY (2025)

import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import seaborn as sns
import warnings
warnings.filterwarnings("ignore")

os.makedirs("outputs/figures", exist_ok=True)
plt.style.use("seaborn-v0_8-whitegrid")

# AICareMatch brand colors
PURPLE     = "#6B46C1"
PINK       = "#EC4899"
BLUE       = "#3B82F6"
RED        = "#EF4444"
GREEN      = "#10B981"
ORANGE     = "#F59E0B"
LIGHT_GREY = "#F3F4F6"

master = pd.read_csv("outputs/ny_carematch_master.csv")
print(f"Loaded master dataset: {master.shape}")


def save_fig(name):
    path = f"outputs/figures/{name}.png"
    plt.savefig(path, dpi=150, bbox_inches="tight", facecolor="white")
    plt.close()
    print(f"  Saved: {path}")


# ─────────────────────────────────────────────────────────────────────────
# CHART 1: Top 20 Counties by AICareMatch Priority Score
# ─────────────────────────────────────────────────────────────────────────
fig, ax = plt.subplots(figsize=(14, 8))
top20 = master.sort_values("AICAREMATCH_PRIORITY_SCORE", ascending=False).head(20)
colors = [PURPLE if "Tier 1" in str(t) else BLUE if "Tier 2" in str(t)
          else ORANGE for t in top20["LAUNCH_TIER"]]
bars = ax.barh(top20["COUNTY"], top20["AICAREMATCH_PRIORITY_SCORE"],
               color=colors, edgecolor="white")
for bar, val in zip(bars, top20["AICAREMATCH_PRIORITY_SCORE"]):
    ax.text(bar.get_width() + 0.3, bar.get_y() + bar.get_height()/2,
            f"{val:.1f}", va="center", fontsize=9)
ax.set_title("AICareMatch County Priority Score — Top 20 NY Counties\n"
             "Higher score = higher unmet need + broadband feasibility",
             fontweight="bold", fontsize=13)
ax.set_xlabel("Priority Score (0–100)")
ax.invert_yaxis()
legend_elements = [
    mpatches.Patch(color=PURPLE, label="Tier 1 — Launch Now"),
    mpatches.Patch(color=BLUE,   label="Tier 2 — Priority"),
    mpatches.Patch(color=ORANGE, label="Tier 3 — Watch"),
]
ax.legend(handles=legend_elements, loc="lower right")
plt.tight_layout()
save_fig("01_priority_score_top20")

# ─────────────────────────────────────────────────────────────────────────
# CHART 2: Mental Health Treatment Gap by Region
# ─────────────────────────────────────────────────────────────────────────
fig, axes = plt.subplots(1, 2, figsize=(16, 6))
fig.suptitle("Mental Health Treatment Gap Across NY Regions\n"
             "Source: SAMHSA NSDUH 2023", fontweight="bold", fontsize=13)

region_gap = master.groupby("REGION").agg(
    avg_gap=("TREATMENT_GAP_PCT", "mean"),
    total_untreated=("UNTREATED_COUNT_ESTIMATED", "sum"),
    counties=("COUNTY", "count")
).reset_index().sort_values("avg_gap", ascending=False)

palette = [PURPLE, PINK, BLUE, RED, GREEN, ORANGE, "#8B5CF6", "#06B6D4", "#84CC16"]
sns.barplot(x="REGION", y="avg_gap", data=region_gap,
            palette=palette[:len(region_gap)], ax=axes[0])
axes[0].set_title("Average Treatment Gap (%) by Region")
axes[0].set_ylabel("Treatment Gap (%)")
axes[0].tick_params(axis="x", rotation=35)
axes[0].axhline(y=master["TREATMENT_GAP_PCT"].mean(), color="black",
                linestyle="--", linewidth=1.5, label="NY Average")
axes[0].legend()
for p in axes[0].patches:
    axes[0].annotate(f"{p.get_height():.1f}%",
                     (p.get_x() + p.get_width()/2, p.get_height() + 0.3),
                     ha="center", fontsize=8)

# Pie chart — untreated patients by region
axes[1].pie(region_gap["total_untreated"], labels=region_gap["REGION"],
            autopct="%1.1f%%", colors=palette[:len(region_gap)],
            startangle=90, pctdistance=0.8)
axes[1].set_title(f"Untreated Patients by Region\n"
                  f"Total: {master['UNTREATED_COUNT_ESTIMATED'].sum():,}")
plt.tight_layout()
save_fig("02_treatment_gap_by_region")

# ─────────────────────────────────────────────────────────────────────────
# CHART 3: Provider Shortage Map — Providers per 100k vs HRSA Minimum
# ─────────────────────────────────────────────────────────────────────────
fig, ax = plt.subplots(figsize=(16, 7))
sorted_m = master.sort_values("PROVIDERS_PER_100K_POP")
colors_p = [RED if v < 15 else ORANGE if v < 25 else GREEN
            for v in sorted_m["PROVIDERS_PER_100K_POP"]]
bars = ax.bar(sorted_m["COUNTY"], sorted_m["PROVIDERS_PER_100K_POP"],
              color=colors_p, edgecolor="white", width=0.8)
ax.axhline(y=33, color=PURPLE, linewidth=2, linestyle="--",
           label="HRSA Recommended Minimum (33/100k)")
ax.axhline(y=15, color=RED, linewidth=1.5, linestyle=":",
           label="Critical Shortage Threshold (15/100k)")
ax.set_title("Mental Health Providers per 100,000 Population — All 62 NY Counties\n"
             "Source: HRSA Bureau of Health Workforce 2024",
             fontweight="bold", fontsize=13)
ax.set_ylabel("Providers per 100,000 Population")
ax.tick_params(axis="x", rotation=90, labelsize=7)
ax.legend()
below_hrsa = (sorted_m["PROVIDERS_PER_100K_POP"] < 33).sum()
ax.text(0.02, 0.97, f"{below_hrsa}/62 counties below HRSA minimum",
        transform=ax.transAxes, fontsize=10, color=RED, fontweight="bold",
        verticalalignment="top")
plt.tight_layout()
save_fig("03_provider_shortage_all_counties")

# ─────────────────────────────────────────────────────────────────────────
# CHART 4: Telehealth Opportunity Matrix — Shortage vs Broadband
# ─────────────────────────────────────────────────────────────────────────
fig, ax = plt.subplots(figsize=(14, 10))

scatter_colors = {
    "Tier 1 — Launch Now":     PURPLE,
    "Tier 2 — Priority":       BLUE,
    "Tier 3 — Watch":          ORANGE,
    "Tier 4 — Deprioritize":   GREEN,
}

for tier, color in scatter_colors.items():
    sub = master[master["LAUNCH_TIER"].astype(str) == tier]
    if len(sub) == 0:
        continue
    ax.scatter(sub["BROADBAND_25_3_COVERAGE_PCT"],
               sub["PROVIDERS_PER_100K_POP"],
               s=sub["AMI_COUNT_ESTIMATED"] / 200,
               c=color, alpha=0.75, label=tier, zorder=5)
    for _, row in sub.iterrows():
        ax.annotate(row["COUNTY"],
                    (row["BROADBAND_25_3_COVERAGE_PCT"],
                     row["PROVIDERS_PER_100K_POP"]),
                    fontsize=7, alpha=0.8,
                    xytext=(3, 3), textcoords="offset points")

ax.axvline(x=70, color="gray", linestyle="--", linewidth=1, alpha=0.6,
           label="Telehealth viability threshold (70% broadband)")
ax.axhline(y=33, color="gray", linestyle=":",  linewidth=1, alpha=0.6,
           label="HRSA minimum providers/100k")

# Quadrant labels
ax.text(20, 1, "HIGH NEED\nLOW BROADBAND\n→ In-person priority",
        fontsize=8, color=RED, alpha=0.7, style="italic")
ax.text(80, 1, "HIGH NEED\nHIGH BROADBAND\n→ AICareMatch sweet spot",
        fontsize=8, color=PURPLE, alpha=0.7, style="italic", fontweight="bold")

ax.set_xlabel("Broadband Coverage (% households with 25+ Mbps) — FCC 2024",
              fontsize=11)
ax.set_ylabel("MH Providers per 100k Population — HRSA 2024", fontsize=11)
ax.set_title("AICareMatch Opportunity Matrix — All 62 NY Counties\n"
             "Bubble size = number of people with mental illness (SAMHSA 2023)",
             fontweight="bold", fontsize=13)
ax.legend(loc="upper left", fontsize=9)
plt.tight_layout()
save_fig("04_telehealth_opportunity_matrix")

# ─────────────────────────────────────────────────────────────────────────
# CHART 5: HPSA Designation Status
# ─────────────────────────────────────────────────────────────────────────
fig, axes = plt.subplots(1, 2, figsize=(14, 6))
fig.suptitle("HRSA Mental Health Professional Shortage Area (HPSA) Designations — NY 2024",
             fontweight="bold", fontsize=13)

hpsa_status = master["HPSA_STATUS"].value_counts()
axes[0].pie(hpsa_status.values, labels=hpsa_status.index,
            autopct="%1.1f%%", colors=[RED, ORANGE, GREEN],
            startangle=90)
axes[0].set_title("HPSA Designation Status\n(62 NY Counties)")

hpsa_designated = master[master["HPSA_STATUS"] == "Designated"].sort_values(
    "HPSA_SCORE", ascending=False).head(20)
sns.barplot(x="HPSA_SCORE", y="COUNTY", data=hpsa_designated,
            palette="Reds_r", ax=axes[1])
axes[1].set_title("Top 20 Counties by HPSA Shortage Score\n(25 = most severe shortage)")
axes[1].set_xlabel("HPSA Score (higher = worse shortage)")
plt.tight_layout()
save_fig("05_hpsa_designation")

# ─────────────────────────────────────────────────────────────────────────
# CHART 6: Mental Health Condition Prevalence Comparison
# ─────────────────────────────────────────────────────────────────────────
fig, axes = plt.subplots(1, 2, figsize=(16, 6))
fig.suptitle("Mental Health Condition Prevalence — Urban vs Rural NY\n"
             "Source: SAMHSA NSDUH 2023", fontweight="bold", fontsize=13)

conditions = ["AMI_PERCENT", "DEPRESSION_PERCENT", "ANXIETY_PERCENT",
              "PTSD_PERCENT", "SUBSTANCE_USE_DISORDER_PCT"]
cond_labels = ["Any Mental Illness", "Depression", "Anxiety", "PTSD", "Substance Use"]

urban_means = master[master["URBAN_RURAL_CODE"] == "Urban"][conditions].mean()
rural_means = master[master["URBAN_RURAL_CODE"] == "Rural"][conditions].mean()

x = np.arange(len(conditions))
w = 0.35
axes[0].bar(x - w/2, urban_means, w, label="Urban", color=BLUE, alpha=0.85)
axes[0].bar(x + w/2, rural_means, w, label="Rural", color=RED,  alpha=0.85)
axes[0].set_title("Prevalence by Urban/Rural Classification (%)")
axes[0].set_xticks(x)
axes[0].set_xticklabels(cond_labels, rotation=20, fontsize=9)
axes[0].set_ylabel("Prevalence (%)")
axes[0].legend()
for i, (u, r) in enumerate(zip(urban_means, rural_means)):
    axes[0].text(i - w/2, u + 0.1, f"{u:.1f}", ha="center", fontsize=8)
    axes[0].text(i + w/2, r + 0.1, f"{r:.1f}", ha="center", fontsize=8)

# Treatment rate by urban/rural
tx_comp = master.groupby("URBAN_RURAL_CODE")["MH_TREATMENT_RATE_PCT"].describe()
master.boxplot(column="MH_TREATMENT_RATE_PCT", by="URBAN_RURAL_CODE",
               ax=axes[1], boxprops=dict(color=PURPLE),
               medianprops=dict(color=RED, linewidth=2))
axes[1].set_title("Treatment Rate Distribution — Urban vs Rural (%)")
axes[1].set_xlabel("")
axes[1].set_ylabel("Treatment Rate (%)")
plt.suptitle("")
plt.tight_layout()
save_fig("06_condition_prevalence_urban_rural")

# ─────────────────────────────────────────────────────────────────────────
# CHART 7: AICareMatch Match Potential by County
# ─────────────────────────────────────────────────────────────────────────
fig, ax = plt.subplots(figsize=(14, 7))
top25 = master.sort_values("TELEHEALTH_REACHABLE_PATIENTS", ascending=False).head(25)
colors_t = [PURPLE if "Tier 1" in str(t) else BLUE if "Tier 2" in str(t)
            else ORANGE for t in top25["LAUNCH_TIER"]]
bars = ax.barh(top25["COUNTY"], top25["TELEHEALTH_REACHABLE_PATIENTS"],
               color=colors_t, edgecolor="white")
for bar, val in zip(bars, top25["TELEHEALTH_REACHABLE_PATIENTS"]):
    ax.text(bar.get_width() + 50, bar.get_y() + bar.get_height()/2,
            f"{val:,}", va="center", fontsize=8)
ax.set_title("AICareMatch Telehealth Reach — Untreated Patients with Broadband Access\n"
             "These patients can be matched to providers today via the platform",
             fontweight="bold", fontsize=13)
ax.set_xlabel("Patients Reachable via Telehealth (Broadband-Enabled Untreated)")
ax.invert_yaxis()
total = master["TELEHEALTH_REACHABLE_PATIENTS"].sum()
ax.text(0.98, 0.02, f"Total NY reachable patients:\n{total:,}",
        transform=ax.transAxes, ha="right", fontsize=11,
        color=PURPLE, fontweight="bold")
plt.tight_layout()
save_fig("07_telehealth_reachable_patients")

# ─────────────────────────────────────────────────────────────────────────
# CHART 8: Wait Time vs Provider Density
# ─────────────────────────────────────────────────────────────────────────
fig, ax = plt.subplots(figsize=(12, 7))
urban_m = master[master["URBAN_RURAL_CODE"] == "Urban"]
rural_m = master[master["URBAN_RURAL_CODE"] == "Rural"]

ax.scatter(urban_m["PROVIDERS_PER_100K_POP"], urban_m["AVG_WAIT_TIME_WEEKS"],
           color=BLUE, alpha=0.7, s=80, label="Urban", zorder=5)
ax.scatter(rural_m["PROVIDERS_PER_100K_POP"], rural_m["AVG_WAIT_TIME_WEEKS"],
           color=RED, alpha=0.7, s=80, label="Rural", zorder=5)

# Trend line
z = np.polyfit(master["PROVIDERS_PER_100K_POP"],
               master["AVG_WAIT_TIME_WEEKS"], 1)
p = np.poly1d(z)
x_line = np.linspace(master["PROVIDERS_PER_100K_POP"].min(),
                     master["PROVIDERS_PER_100K_POP"].max(), 100)
ax.plot(x_line, p(x_line), color="black", linewidth=1.5,
        linestyle="--", alpha=0.6, label="Trend")

ax.set_xlabel("MH Providers per 100,000 Population (HRSA 2024)", fontsize=11)
ax.set_ylabel("Average Wait Time for Appointment (Weeks)", fontsize=11)
ax.set_title("Provider Shortage Directly Causes Longer Wait Times\n"
             "AICareMatch connects patients to providers before shortage areas lose more providers",
             fontweight="bold", fontsize=13)
ax.legend()

corr = master["PROVIDERS_PER_100K_POP"].corr(master["AVG_WAIT_TIME_WEEKS"])
ax.text(0.02, 0.95, f"Pearson r = {corr:.2f} (strong negative correlation)",
        transform=ax.transAxes, fontsize=10, color="black",
        verticalalignment="top")
plt.tight_layout()
save_fig("08_wait_time_vs_provider_density")

# ─────────────────────────────────────────────────────────────────────────
# CHART 9: Cost Accessibility Analysis
# ─────────────────────────────────────────────────────────────────────────
fig, axes = plt.subplots(1, 2, figsize=(16, 6))
fig.suptitle("Session Cost Accessibility — Who Can Afford Mental Health Care?\n"
             "Source: HRSA CMS Data + SAMHSA NSDUH 2023",
             fontweight="bold", fontsize=13)

master["COST_INCOME_RATIO"] = (
    master["AVG_SESSION_COST_USD"] * 52 /
    master["MEDIAN_HOUSEHOLD_INCOME"] * 100
).round(2)

cost_region = master.groupby("REGION")["AVG_SESSION_COST_USD"].mean().sort_values()
axes[0].barh(cost_region.index, cost_region.values,
             color=[BLUE, PURPLE, PINK, RED, GREEN, ORANGE,
                    "#8B5CF6", "#06B6D4", "#84CC16"][:len(cost_region)])
axes[0].set_title("Average Session Cost by Region ($)")
axes[0].set_xlabel("Cost per Session (USD)")
for i, v in enumerate(cost_region.values):
    axes[0].text(v + 1, i, f"${v:.0f}", va="center", fontsize=9)

top_burden = master.sort_values("COST_INCOME_RATIO", ascending=False).head(15)
sns.barplot(x="COST_INCOME_RATIO", y="COUNTY", data=top_burden,
            color=RED, ax=axes[1])
axes[1].set_title("Annual Cost as % of Household Income\n(Top 15 Most Burdened Counties)")
axes[1].set_xlabel("Annual MH Cost as % of Income")
plt.tight_layout()
save_fig("09_cost_accessibility")

# ─────────────────────────────────────────────────────────────────────────
# CHART 10: Underserved Populations Profile
# ─────────────────────────────────────────────────────────────────────────
fig, ax = plt.subplots(figsize=(14, 6))

# Counties with highest PTSD rate — First Responder Focus
# (Jefferson = Ft Drum military base, other rural counties with first responders)
pop_focus = master.nlargest(10, "PTSD_PERCENT")[
    ["COUNTY", "REGION", "PTSD_PERCENT", "DEPRESSION_PERCENT",
     "SUBSTANCE_USE_DISORDER_PCT", "TREATMENT_GAP_PCT"]
].set_index("COUNTY")

pop_focus[["PTSD_PERCENT", "DEPRESSION_PERCENT", "SUBSTANCE_USE_DISORDER_PCT"]].plot(
    kind="bar", ax=ax, color=[PURPLE, BLUE, RED], alpha=0.85, edgecolor="white"
)
ax.set_title("Top 10 Counties by PTSD Prevalence — First Responder + Military Focus\n"
             "Source: SAMHSA NSDUH 2023 | AICareMatch targets these populations specifically",
             fontweight="bold", fontsize=12)
ax.set_ylabel("Prevalence (%)")
ax.tick_params(axis="x", rotation=35)
ax.legend(["PTSD", "Depression", "Substance Use"])
plt.tight_layout()
save_fig("10_underserved_populations_ptsd")

# ─────────────────────────────────────────────────────────────────────────
# CHART 11: Summary Dashboard — AICareMatch Business Case
# ─────────────────────────────────────────────────────────────────────────
fig, axes = plt.subplots(2, 3, figsize=(18, 10))
fig.suptitle("AICareMatch NY State Analysis — Executive Summary Dashboard\n"
             "SAMHSA 2023 + HRSA 2024 + FCC 2024",
             fontweight="bold", fontsize=14)

# Panel 1: AMI by region
r_ami = master.groupby("REGION")["AMI_PERCENT"].mean().sort_values(ascending=False)
axes[0,0].bar(r_ami.index, r_ami.values,
              color=[PURPLE,BLUE,PINK,RED,GREEN,ORANGE,"#8B5CF6","#06B6D4","#84CC16"][:len(r_ami)])
axes[0,0].set_title("Avg AMI Prevalence by Region (%)")
axes[0,0].tick_params(axis="x", rotation=40, labelsize=8)

# Panel 2: Untreated count by tier
tier_untreated = master.groupby("LAUNCH_TIER")["UNTREATED_COUNT_ESTIMATED"].sum()
axes[0,1].bar(tier_untreated.index.astype(str), tier_untreated.values,
              color=[PURPLE, BLUE, ORANGE, GREEN])
axes[0,1].set_title("Untreated Patients by Launch Tier")
axes[0,1].tick_params(axis="x", rotation=20, labelsize=8)

# Panel 3: Provider shortage histogram
axes[0,2].hist(master["PROVIDERS_PER_100K_POP"], bins=20,
               color=BLUE, edgecolor="white", alpha=0.85)
axes[0,2].axvline(x=33, color=RED, linewidth=2, linestyle="--",
                  label="HRSA minimum")
axes[0,2].set_title("Distribution of Providers per 100k")
axes[0,2].set_xlabel("Providers per 100k")
axes[0,2].legend()

# Panel 4: Treatment gap vs poverty
axes[1,0].scatter(master["POVERTY_RATE_PCT"], master["TREATMENT_GAP_PCT"],
                  c=master["AICAREMATCH_PRIORITY_SCORE"],
                  cmap="RdPu", alpha=0.75, s=60)
axes[1,0].set_xlabel("Poverty Rate (%)")
axes[1,0].set_ylabel("Treatment Gap (%)")
axes[1,0].set_title("Poverty → Treatment Gap (r={:.2f})".format(
    master["POVERTY_RATE_PCT"].corr(master["TREATMENT_GAP_PCT"])))

# Panel 5: Broadband vs wait time
axes[1,1].scatter(master["BROADBAND_25_3_COVERAGE_PCT"],
                  master["AVG_WAIT_TIME_WEEKS"],
                  color=PURPLE, alpha=0.6, s=60)
axes[1,1].set_xlabel("Broadband Coverage (%)")
axes[1,1].set_ylabel("Avg Wait Time (Weeks)")
axes[1,1].set_title("Broadband vs Wait Time")

# Panel 6: Launch tier pie
tier_counts = master["LAUNCH_TIER"].value_counts()
axes[1,2].pie(tier_counts.values,
              labels=[str(l) for l in tier_counts.index],
              autopct="%1.0f%%",
              colors=[PURPLE, BLUE, ORANGE, GREEN])
axes[1,2].set_title("Counties by Launch Tier")

plt.tight_layout()
save_fig("11_executive_summary_dashboard")

print(f"\nAll 11 charts saved to outputs/figures/")
print("Run 03_ai_matching_model.py next for ML analysis")
