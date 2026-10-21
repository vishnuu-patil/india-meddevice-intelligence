# ============================================================
# Fix 4 - Manual validation sample
# Folder : <project folder>\
# Run    : python fix4_sample.py
# Input  : Output/cdsco_final.csv  (+ Output/cdsco_categorized.csv for intended_use text)
#          Output/fda_final.csv
# Output : Output/validation_cdsco.csv
#          Output/validation_fda.csv
#
# WHAT IT DOES
#   - Picks 20 random rows per category (fewer if the category has fewer rows).
#   - Adds 20 EXTRA rows per file from the weaker groups (MED + LOW confidence),
#     because a pure random sample is mostly HIGH rows.
#   - Same random seed every time, so a rerun gives the SAME rows.
#
# HOW TO FILL THE SHEET (in Excel)
#   correct    : Y  = the assigned category fits the device
#                N  = it does not fit
#                unsure = cannot tell from the text (left out of the accuracy maths)
#   should_be  : if correct = N, write the category it should have been
#   Please do not re-sort or delete rows. Save the file as CSV when done.
# ============================================================
import sys
from pathlib import Path
import pandas as pd

BASE = Path(__file__).resolve().parent
if len(sys.argv) > 1:               # optional override for testing
    BASE = Path(sys.argv[1])

OUT = BASE / "Output"
SEED = 42
PER_CATEGORY = 20
EXTRA_WEAK = 20


def pick_sample(df):
    """Return df with a sample_type column: 'random' (per category) + 'extra_weak'."""
    parts = []
    for cat, g in df.groupby("category"):
        n = min(PER_CATEGORY, len(g))
        parts.append(g.sample(n=n, random_state=SEED).assign(sample_type="random"))
    rand = pd.concat(parts)

    weak_pool = df[df["category_confidence"].isin(["MED", "LOW"]) & ~df.index.isin(rand.index)]
    extra = weak_pool.sample(n=min(EXTRA_WEAK, len(weak_pool)), random_state=SEED).assign(sample_type="extra_weak")
    return pd.concat([rand, extra])


def finish(sample, cols, out_file):
    sample = sample.sort_values(["category", "sample_type"]).reset_index()
    sample = sample.rename(columns={"index": "_idx"})
    sample["row_no"] = sample["_idx"] + 2          # row number in the final CSV as seen in Excel
    sample.insert(0, "sample_id", range(1, len(sample) + 1))
    sample["correct"] = ""
    sample["should_be"] = ""
    sample = sample[["sample_id", "sample_type", "row_no"] + cols + ["correct", "should_be"]]
    sample.to_csv(out_file, index=False, encoding="utf-8-sig")
    return sample


# ------------------------- CDSCO -------------------------
cd = pd.read_csv(OUT / "cdsco_final.csv", low_memory=False)

# attach intended_use (it decided categories for methods 2 and 4). Rows are in the same
# order as cdsco_final once "Other" is removed - checked below so nothing can drift.
raw = pd.read_csv(OUT / "cdsco_categorized.csv", low_memory=False)
raw = raw[raw["category"] != "Other"].reset_index(drop=True)
assert len(raw) == len(cd), "cdsco_categorized and cdsco_final have different row counts"
assert (raw["license_no"] == cd["license_no"]).all() and (raw["category"] == cd["category"]).all(), \
    "Row order mismatch between cdsco_categorized and cdsco_final"
cd["intended_use"] = raw["intended_use"].fillna("").str.replace(r"\s+", " ", regex=True).str.slice(0, 250)

cd_sample = finish(
    pick_sample(cd),
    ["category", "category_method", "category_confidence", "device_name",
     "intended_use", "brand_name", "importer_name", "license_no"],
    OUT / "validation_cdsco.csv")

# --------------------------- FDA ---------------------------
fd = pd.read_csv(OUT / "fda_final.csv", low_memory=False)
fd_sample = finish(
    pick_sample(fd),
    ["category", "category_method", "category_confidence", "device_name",
     "category_raw", "company_name", "device_id"],
    OUT / "validation_fda.csv")

# ---------------- checks ----------------
for name, s, total in [("CDSCO", cd_sample, len(cd)), ("FDA", fd_sample, len(fd))]:
    print(f"\n===== {name} =====")
    print(f"Rows in final file : {total:,}")
    print(f"Rows to check      : {len(s):,}  ({(s['sample_type'] == 'random').sum()} random + "
          f"{(s['sample_type'] == 'extra_weak').sum()} extra weak)")
    print(f"Duplicates         : {s['row_no'].duplicated().sum()}")
    print("Confidence in sample:")
    print(s["category_confidence"].value_counts().to_string())
    print("Rows per category (random part):")
    print(s[s["sample_type"] == "random"]["category"].value_counts().sort_index().to_string())

print(f"\nSaved: {OUT / 'validation_cdsco.csv'}")
print(f"Saved: {OUT / 'validation_fda.csv'}")