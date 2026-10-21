# ============================================================
# Fix 4 - FRESH random sample for second-round CDSCO validation (v2)
# Folder : <project folder>\
# Run    : python fresh_sample_cdsco.py      (run AFTER the new categories.py)
# Input  : Output/cdsco_categorized.csv   (the NEW one, after the rule fixes)
#          Output/validation_cdsco.csv    (v1 sheet - only used to EXCLUDE the old 380 rows)
#          Output/cdsco_categorized_backup.csv (only used to check you are not on the old file)
# Output : Output/validation_cdsco_v2.csv
#
# SAMPLE : 20 random rows per category x 18 categories = 360 base rows
#          + 20 extra rows from each category listed in EXTRA_CATEGORIES (default 3 -> 60)
#          = 420 rows. "Other" rows are never sampled. Rows already checked in v1 are excluded.
# SEED   : 7 (v1 used 42), so the sample is reproducible but different.
#
# HOW TO FILL (in Excel):  correct = Y / N / unsure   |   should_be = right category if N
#                          notes = short reason (optional)
# Overall accuracy must be calculated on the 360 "base" rows only - the extra rows are
# deliberately over-weighted toward weak categories.
# ============================================================
import sys
from pathlib import Path
import pandas as pd

BASE = Path(__file__).resolve().parent
if len(sys.argv) > 1:               # optional override for testing
    BASE = Path(sys.argv[1])

SRC = BASE / "Output" / "cdsco_categorized.csv"
V1 = BASE / "Output" / "validation_cdsco.csv"
BACKUP = BASE / "Output" / "cdsco_categorized_backup.csv"
OUT = BASE / "Output" / "validation_cdsco_v2.csv"

SEED = 7
PER_CATEGORY = 20
EXTRA_PER_CATEGORY = 20
# extra weight where errors are likely. In your v1 sheet Surgical & Endoscopy actually had the
# most errors (4 of 22), so you may want to add it:  "Surgical & Endoscopy"
EXTRA_CATEGORIES = ["Cardiac & Vascular", "Aesthetics & Dermatology",
                    "Needles, Syringes & Catheters (general)"]

def clean_cols(frame):
    """Strip BOM/spaces and lower-case column names so small formatting differences don't break things."""
    frame.columns = [str(c).strip().lstrip("\ufeff").lower() for c in frame.columns]
    return frame


df = clean_cols(pd.read_csv(SRC, low_memory=False))
need = ["device_name", "intended_use", "category", "category_source", "license_no", "importer_name"]
missing = [c for c in need if c not in df.columns]
if missing:
    sys.exit(f"cdsco_categorized.csv is missing columns {missing}. Columns found: {list(df.columns)[:30]}")

# ---- safety check: make sure this is the NEW categorized file ----
old_cat = None
if BACKUP.exists():
    try:
        b = clean_cols(pd.read_csv(BACKUP, low_memory=False))
        if "category" in b.columns:
            old_cat = b["category"].to_numpy()
        else:
            print("Warning: the backup file has no 'category' column, so I cannot compare.")
            print("         Columns found in the backup:", list(b.columns)[:30])
    except Exception as e:
        print("Warning: could not read the backup file:", e)
else:
    print("Warning: no backup file found, cannot confirm the categories are the new ones.")
if old_cat is not None and len(old_cat) == len(df) and (old_cat == df["category"].to_numpy()).all():
    sys.exit("cdsco_categorized.csv is identical to the OLD file. Run the new categories.py first.")

# ---- position of every kept row inside cdsco_final.csv (same order, 'Other' removed) ----
kept = df[df["category"] != "Other"].copy()
kept["pos"] = range(len(kept))
kept["row_no"] = kept["pos"] + 2            # row number in cdsco_final.csv as seen in Excel

# ---- exclude the 380 rows already checked in v1 ----
if V1.exists():
    try:
        v1 = pd.read_csv(V1, encoding="utf-8-sig", low_memory=False)
    except UnicodeDecodeError:
        v1 = pd.read_csv(V1, encoding="latin-1", low_memory=False)
    v1 = clean_cols(v1)
    if "row_no" in v1.columns:
        v1_pos = set((v1["row_no"].astype(int) - 2).tolist())
        check = kept.set_index("pos").loc[sorted(v1_pos)]
        assert (check["device_name"].fillna("").to_numpy() ==
                v1.sort_values("row_no")["device_name"].fillna("").to_numpy()).all(), \
            "v1 rows do not line up with cdsco_categorized.csv"
        pool = kept[~kept["pos"].isin(v1_pos)]
        print(f"Excluded {len(v1_pos)} rows already checked in v1")
    else:
        v1_pos = set()
        pool = kept
        print("Warning: v1 sheet has no row_no column, nothing excluded. Columns:", list(v1.columns)[:20])
else:
    v1_pos = set()
    pool = kept
    print("Warning: v1 sheet not found, nothing excluded")

# ---- draw the sample ----
base_parts, extra_parts = [], []
for cat, g in pool.groupby("category"):
    take = g.sample(n=min(PER_CATEGORY, len(g)), random_state=SEED)
    base_parts.append(take.assign(sample_type="base"))
    if cat in EXTRA_CATEGORIES:
        rest = g.drop(take.index)
        extra_parts.append(rest.sample(n=min(EXTRA_PER_CATEGORY, len(rest)), random_state=SEED)
                           .assign(sample_type="extra"))
sample = pd.concat(base_parts + extra_parts)

sample["intended_use"] = (sample["intended_use"].fillna("").str.replace(r"\s+", " ", regex=True)
                          .str.slice(0, 300))
sample = sample.sort_values(["category", "sample_type"]).reset_index(drop=True)
sample.insert(0, "sample_id", range(1, len(sample) + 1))
sample["correct"] = ""
sample["should_be"] = ""
sample["notes"] = ""

cols = ["sample_id", "device_name", "intended_use", "category", "category_source",
        "license_no", "importer_name", "correct", "should_be", "notes", "sample_type", "row_no"]
out = sample[cols]
out.to_csv(OUT, index=False, encoding="utf-8-sig")

# ---------------- checks ----------------
print(f"\nRows to check : {len(out)}  ({(out['sample_type'] == 'base').sum()} base + "
      f"{(out['sample_type'] == 'extra').sum()} extra)")
print(f"Duplicates    : {out['row_no'].duplicated().sum()}")
print(f"Overlap with v1: {len(set(out['row_no'] - 2) & v1_pos)}")
print(f"'Other' rows  : {(out['category'] == 'Other').sum()}")
print("\nRows per category:")
print(out["category"].value_counts().sort_index().to_string())
print("\ncategory_source in the sample:")
print(out["category_source"].value_counts().sort_index().to_string())
print(f"\nSaved: {OUT}")

