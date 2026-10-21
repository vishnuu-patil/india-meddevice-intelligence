# ============================================================
# Script 04 - Pipeline gap (rewrite: Fix 1 + Fix 2)
# Folder : <project folder>\
# Run    : python pipeline_gap.py
# Input  : Output/fda_final.csv , Output/cdsco_final.csv
# Output : Output/pipeline_gap_vA.csv       (Version A: HIGH + MED confidence rows only)
#          Output/pipeline_gap_vB.csv       (Version B: all rows)
#          Output/pipeline_gap_compare.csv  (rank in A vs rank in B, side by side)
#
# FIX 1 : CDSCO is counted as UNIQUE (licence, category) pairs, not rows.
# FIX 2 : two versions. A = no LOW-confidence rows. B = everything.
#
# Window  : 2018 to 2026 on both sides.
#           FDA   -> year of approved_date
#           CDSCO -> license_year (fixed per licence, so no renewal inflation)
# Gap     : share gap = FDA share % - CDSCO share %  (in percentage points)
#           Positive = big in FDA, small in India  -> possible import opportunity.
# ============================================================
import sys
from pathlib import Path
import pandas as pd

BASE = Path(__file__).resolve().parent
if len(sys.argv) > 1:               # optional override for testing
    BASE = Path(sys.argv[1])

FDA_FILE = BASE / "Output" / "fda_final.csv"
CDSCO_FILE = BASE / "Output" / "cdsco_final.csv"
Y0, Y1 = 2018, 2026

fda = pd.read_csv(FDA_FILE, low_memory=False)
cdsco = pd.read_csv(CDSCO_FILE, low_memory=False)

# ---- same time window on both sides ----
fda["year"] = pd.to_datetime(fda["approved_date"]).dt.year
fda = fda[fda["year"].between(Y0, Y1)].copy()
cdsco = cdsco[cdsco["license_year"].between(Y0, Y1)].copy()

print(f"FDA rows in {Y0}-{Y1}   : {len(fda):,}")
print(f"CDSCO rows in {Y0}-{Y1} : {len(cdsco):,}")
print(f"CDSCO unique licences  : {cdsco['license_no'].nunique():,}")


def build_gap(fda_df, cdsco_df):
    """Return one table: FDA vs CDSCO share per category, ranked by share gap."""
    fda_n = fda_df.groupby("category").size().rename("fda_rows")

    # FIX 1: unique (licence, category) pairs
    pairs = cdsco_df.drop_duplicates(["license_no", "category"])
    cdsco_n = pairs.groupby("category").size().rename("cdsco_licences")
    cdsco_rows = cdsco_df.groupby("category").size().rename("cdsco_rows")

    t = pd.concat([fda_n, cdsco_n, cdsco_rows], axis=1).fillna(0).astype(int)
    t["fda_share_pct"] = (t["fda_rows"] / t["fda_rows"].sum() * 100).round(1)
    t["cdsco_share_pct"] = (t["cdsco_licences"] / t["cdsco_licences"].sum() * 100).round(1)
    t["share_gap_pp"] = (t["fda_share_pct"] - t["cdsco_share_pct"]).round(1)
    # what the OLD row-counting method would have shown (for comparison only)
    t["cdsco_share_if_rows_pct"] = (t["cdsco_rows"] / t["cdsco_rows"].sum() * 100).round(1)
    t["old_row_gap_pp"] = (t["fda_share_pct"] - t["cdsco_share_if_rows_pct"]).round(1)
    t = t.sort_values("share_gap_pp", ascending=False)
    t.insert(0, "rank", range(1, len(t) + 1))
    return t.reset_index().rename(columns={"index": "category"})


# ---- Version B: everything ----
gap_b = build_gap(fda, cdsco)

# ---- Version A: drop LOW-confidence rows on BOTH sides ----
fda_a = fda[fda["category_confidence"].isin(["HIGH", "MED"])]
cdsco_a = cdsco[cdsco["category_confidence"].isin(["HIGH", "MED"])]
gap_a = build_gap(fda_a, cdsco_a)

gap_a.to_csv(BASE / "Output" / "pipeline_gap_vA.csv", index=False, encoding="utf-8-sig")
gap_b.to_csv(BASE / "Output" / "pipeline_gap_vB.csv", index=False, encoding="utf-8-sig")

# ---- compare A vs B ----
cmp_ = gap_a[["category", "rank", "share_gap_pp"]].merge(
    gap_b[["category", "rank", "share_gap_pp"]],
    on="category", suffixes=("_A", "_B"))
cmp_["rank_change"] = cmp_["rank_B"] - cmp_["rank_A"]
cmp_ = cmp_.sort_values("rank_B")
cmp_.to_csv(BASE / "Output" / "pipeline_gap_compare.csv", index=False, encoding="utf-8-sig")

# ---------------- checks ----------------
show = ["rank", "category", "fda_rows", "cdsco_licences", "fda_share_pct",
        "cdsco_share_pct", "share_gap_pp", "old_row_gap_pp"]
pd.set_option("display.width", 220)
print(f"\nFDA rows used  A: {len(fda_a):,}   B: {len(fda):,}")
print(f"CDSCO pairs    A: {cdsco_a.drop_duplicates(['license_no','category']).shape[0]:,}   "
      f"B: {cdsco.drop_duplicates(['license_no','category']).shape[0]:,}")
print("\n=== VERSION B (all rows) ===")
print(gap_b[show].to_string(index=False))
print("\n=== VERSION A (HIGH + MED only) ===")
print(gap_a[show].to_string(index=False))
print("\n=== RANK COMPARISON (positive change = category ranks lower in B than A) ===")
print(cmp_.to_string(index=False))
top_a = set(gap_a.head(5)["category"])
top_b = set(gap_b.head(5)["category"])
print(f"\nTop-5 gap categories in both versions: {len(top_a & top_b)} of 5")
print("\nSaved: pipeline_gap_vA.csv, pipeline_gap_vB.csv, pipeline_gap_compare.csv in Output/")