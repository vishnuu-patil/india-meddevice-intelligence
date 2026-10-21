# ============================================================
# Objective 05 - Disease burden by district (NFHS-5) and link to device categories
# Folder : <project folder>\  (project root)
# Run    : python obj05_disease_burden.py
# Input  : Output/nfhs5_clean.csv      (from clean_nfhs5.py)
#          Output/cdsco_final.csv      (only used for the licence counts)
# Output : Output/obj05_district_scores.csv    (3 scores + 3 ranks for every district)
#          Output/obj05_top20_districts.csv    (20 highest-burden districts per disease)
#          Output/obj05_state_summary.csv      (state averages - UNWEIGHTED, see note)
#          Output/obj05_disease_to_device.csv  (disease -> device category + CDSCO licences)
#
# SCORES (simple averages, not real prevalence - no population data to weight with):
#   hypertension_score = (men elevated BP % + women elevated BP %) / 2
#   sugar_score        = (men high/very high sugar % + women high/very high sugar %) / 2
#   anaemia_score      = (women 15-49 anaemic % + children 6-59 months anaemic %) / 2
# If either input is blank, the score is blank (no averaging of one column).
# ============================================================
import sys  # tool to read the optional folder argument
from pathlib import Path  # tool to work with folder paths
import pandas as pd  # tool to work with tables

BASE = Path(__file__).resolve().parent  # project folder = the folder this script sits in
if len(sys.argv) > 1:  # if a folder was typed after the script name
    BASE = Path(sys.argv[1])  # use that folder instead (only for testing)

NFHS = BASE / "Output" / "nfhs5_clean.csv"  # the cleaned NFHS-5 file
CDSCO = BASE / "Output" / "cdsco_final.csv"  # the cleaned CDSCO file
OUT = BASE / "Output"  # folder where results are saved
Y0, Y1 = 2018, 2026  # same year window as the other objectives

nfhs = pd.read_csv(NFHS)  # load the cleaned NFHS-5 table
cdsco = pd.read_csv(CDSCO, low_memory=False)  # load the cleaned CDSCO table

# ---------------- the three scores ----------------
nfhs["hypertension_score"] = ((nfhs["bp_elevated_men_pct"] + nfhs["bp_elevated_women_pct"]) / 2).round(2)  # men and women blood pressure
nfhs["sugar_score"] = ((nfhs["sugar_high_men_pct"] + nfhs["sugar_high_women_pct"]) / 2).round(2)  # men and women blood sugar
nfhs["anaemia_score"] = ((nfhs["anaemia_women_15_49_pct"] + nfhs["anaemia_children_6_59m_pct"]) / 2).round(2)  # women and children anaemia
SCORES = {"hypertension_score": "Hypertension", "sugar_score": "Blood sugar", "anaemia_score": "Anaemia"}  # score column -> label

# ---------------- ranks (1 = highest burden) ----------------
for sc in SCORES:  # go through each score
    nfhs[sc.replace("_score", "_rank")] = nfhs[sc].rank(ascending=False, method="min").astype("Int64")  # rank districts, blanks stay blank

keys = ["state", "district", "state_lgd_code", "district_lgd_code"]  # identifying columns
score_cols = list(SCORES)  # the three score columns
rank_cols = [s.replace("_score", "_rank") for s in SCORES]  # the three rank columns
dist = nfhs[keys + score_cols + rank_cols].sort_values(["state", "district"])  # district table sorted by state then district
dist.to_csv(OUT / "obj05_district_scores.csv", index=False, encoding="utf-8-sig")  # save to file

# ---------------- top 20 districts per disease ----------------
top_parts = []  # list that will hold one small table per disease
for sc, label in SCORES.items():  # go through each score
    t = nfhs.dropna(subset=[sc]).sort_values([sc, "district_lgd_code"], ascending=[False, True]).head(20).copy()  # 20 highest scores
    t.insert(0, "rank", range(1, len(t) + 1))  # add rank number 1 to 20
    t.insert(0, "disease", label)  # add the disease name
    t = t[["disease", "rank", "state", "district", sc]].rename(columns={sc: "score"})  # keep the useful columns
    top_parts.append(t)  # remember this table
top20 = pd.concat(top_parts, ignore_index=True)  # stack the three tables into one
top20.to_csv(OUT / "obj05_top20_districts.csv", index=False, encoding="utf-8-sig")  # save to file

# ---------------- state summary (UNWEIGHTED average of districts) ----------------
state = nfhs.groupby("state").agg(districts=("district", "size"),
                                  hypertension_avg=("hypertension_score", "mean"),
                                  sugar_avg=("sugar_score", "mean"),
                                  anaemia_avg=("anaemia_score", "mean")).round(1).reset_index()  # one row per state
for col in ["hypertension_avg", "sugar_avg", "anaemia_avg"]:  # go through each state average
    state[col.replace("_avg", "_rank")] = state[col].rank(ascending=False, method="min").astype(int)  # rank states, 1 = highest
state = state.sort_values("state")  # sort by state name
state.to_csv(OUT / "obj05_state_summary.csv", index=False, encoding="utf-8-sig")  # save to file

# ---------------- disease -> device category (my judgement, you can change it) ----------------
MAPPING = [("hypertension_score", "Hypertension", "Cardiac & Vascular"),  # high blood pressure -> heart devices
           ("sugar_score", "Blood sugar", "Diagnostics: IVD & Lab"),  # high sugar -> glucose tests and lab kits
           ("sugar_score", "Blood sugar", "Dialysis & Renal"),  # high sugar -> kidney damage -> dialysis
           ("anaemia_score", "Anaemia", "Diagnostics: IVD & Lab")]  # anaemia -> blood tests

c = cdsco[cdsco["license_year"].between(Y0, Y1)]  # keep 2018 to 2026 only
pairs = c.drop_duplicates(["license_no", "category"])  # one row per unique (licence, category) pair
cat_n = pairs.groupby("category").size()  # licences per category
total = len(pairs)  # all pairs (should be 6,714)

rows = []  # list that will hold the mapping table lines
for sc, label, cat in MAPPING:  # go through each mapping line
    rows.append({"disease": label, "device_category": cat,
                 "cdsco_licences": int(cat_n.get(cat, 0)),  # licences in that category
                 "cdsco_share_pct": round(cat_n.get(cat, 0) / total * 100, 1),  # category's % of all licences
                 "district_avg_score": round(nfhs[sc].mean(), 1),  # unweighted average over districts
                 "district_min_score": round(nfhs[sc].min(), 1),  # lowest district
                 "district_max_score": round(nfhs[sc].max(), 1),  # highest district
                 "note": "mapping is analyst judgement"})  # reminder
d2d = pd.DataFrame(rows)  # mapping table
d2d.to_csv(OUT / "obj05_disease_to_device.csv", index=False, encoding="utf-8-sig")  # save to file

# ---------------- checks printed on screen ----------------
pd.set_option("display.width", 250)  # wider print so tables do not wrap
print(f"Districts                : {len(nfhs)}")  # should be 704
print(f"CDSCO licence-cat. pairs : {total:,}")  # should be 6,714
print("Blank scores             :", {k: int(nfhs[k].isna().sum()) for k in score_cols})  # only hypertension should have 2
print("\n=== SCORE SUMMARY (districts) ===")  # heading
print(nfhs[score_cols].describe().loc[["mean", "min", "max"]].round(1).to_string())  # average, lowest, highest
print("\n=== TOP 10 DISTRICTS PER DISEASE ===")  # heading
for label in SCORES.values():  # go through each disease
    print(f"\n-- {label} --")  # sub-heading
    print(top20[top20["disease"] == label].head(10)[["rank", "state", "district", "score"]].to_string(index=False))  # first 10 rows
print("\n=== HOW MANY OF THE TOP 20 DISTRICTS EACH STATE HAS ===")  # heading
for label in SCORES.values():  # go through each disease
    vc = top20[top20["disease"] == label]["state"].value_counts()  # count districts per state
    print(f"{label:13}:", ", ".join(f"{k} {v}" for k, v in vc.items()))  # print as one line
print("\n=== TOP 5 STATES (unweighted average of districts) ===")  # heading
for col, label in [("hypertension_avg", "Hypertension"), ("sugar_avg", "Blood sugar"), ("anaemia_avg", "Anaemia")]:  # each disease
    t5 = state.sort_values(col, ascending=False).head(5)  # five highest states
    print(f"{label:13}:", ", ".join(f"{r.state} {getattr(r, col)}" for r in t5.itertuples()))  # one line
print("\n=== DO THE SAME DISTRICTS RANK HIGH ON ALL THREE? (rank correlation, 1 = identical order) ===")  # heading
print(nfhs[score_cols].corr(method="spearman").round(2).to_string())  # rank correlation table
print("\n=== DISEASE -> DEVICE CATEGORY ===")  # heading
print(d2d.drop(columns="note").to_string(index=False))  # mapping table
print("\nSaved 4 files in Output/")  # done message