# ============================================================
# FDA category validation + fix + re-validation (one script)
# Folder : <project folder>\
# Run    : python fda_validate_and_fix.py
# Reads  : Output/fda_final.csv
# Writes : Output/fda_final_v2.csv          (fixed file)
#          Output/fda_fix_report.csv        (which rows changed)
# ============================================================

import re
from pathlib import Path
import pandas as pd

# --- find project root (works from any location) ---
here = Path(__file__).resolve().parent
BASE = None
for candidate in [here, *here.parents]:
    if (candidate / "Output" / "fda_final.csv").exists():
        BASE = candidate
        break
if BASE is None:
    raise SystemExit("Cannot find project root. Looked for Output/fda_final.csv in parents.")

IN_FILE = BASE / "Output" / "fda_final.csv"
OUT_FILE = BASE / "Output" / "fda_final_v2.csv"
CHANGE_REPORT = BASE / "Output" / "fda_fix_report.csv"

# ============================================================
# STEP 1: VALIDATION summary
# ============================================================
print("=" * 60)
print("STEP 1: Validation summary (based on 372-row manual review)")
print("=" * 60)

VALIDATION_ERRORS = {
    37: "Critical Care & Respiratory",
    40: "Critical Care & Respiratory",
    44: "Critical Care & Respiratory",
    51: "Critical Care & Respiratory",
    135: "Gastro / GI",
    137: "Gastro / GI",
    222: "Urology",
    227: "Surgical & Endoscopy",
    231: "Surgical & Endoscopy",
    232: "Critical Care & Respiratory",
    244: "Orthopedic & Spine",
    250: "Orthopedic & Spine",
    255: "Orthopedic & Spine",
    256: "Orthopedic & Spine",
    302: "Diagnostics: Imaging",
    307: "Orthopedic & Spine",
    311: "Other",
    313: "Aesthetics & Dermatology",
    314: "Urology",
    319: "Aesthetics & Dermatology",
    321: "Aesthetics & Dermatology",
    325: "Aesthetics & Dermatology",
    328: "Aesthetics & Dermatology",
}

df = pd.read_csv(IN_FILE, low_memory=False)
print(f"Rows loaded: {len(df)}")
print(f"Columns: {list(df.columns)}")
print(f"Manual validation errors: {len(VALIDATION_ERRORS)}")
print(f"Sample accuracy (372 rows): {(372 - len(VALIDATION_ERRORS)) / 372 * 100:.1f}%")
print()

name = df["device_name"].fillna("").str.lower()
old_category = df["category"].copy()

# ============================================================
# STEP 2: APPLY FIXES
# ============================================================
print("=" * 60)
print("STEP 2: Applying rule fixes")
print("=" * 60)

# --- FIX 1: Panel override ---
PANEL_OVERRIDES = [
    ("Critical Care & Respiratory",
     {"Cardiac & Vascular"},
     r"patient monitor|hemodynamic|blood pressure|bp monitor|blood pressure monitor"),
    ("Orthopedic & Spine",
     {"Neuro"},
     r"\bspine\b|\bspinal\b|hip sextant|femoral|knee|orthop|implant|fixation|arthrex|nuvasive|zimmer biomet|stryker"),
]

for new_cat, replaces, pattern in PANEL_OVERRIDES:
    mask = (
        df["category"].isin(replaces) &
        name.str.contains(pattern, regex=True, na=False)
    )
    n = mask.sum()
    if n:
        df.loc[mask, "category"] = new_cat
        df.loc[mask, "category_method"] = 1
        df.loc[mask, "category_confidence"] = "HIGH"
        print(f"  Panel override -> {new_cat}: {n} rows")

# --- FIX 2: Aesthetic laser catch ---
AESTHETIC_PATTERN = (
    r"diode laser|led therapy|led light|low.level laser|photobiomodulation|"
    r"hair removal|fractional laser|aesthetic laser|\bipl\b|picosecond|"
    r"nd:yag laser|co2 laser|hairmax|erchonia|joule|spotlite|mula"
)
mask = (
    df["category"].isin(["Surgical & Endoscopy", "Diagnostics: IVD & Lab"]) &
    name.str.contains(AESTHETIC_PATTERN, regex=True, na=False)
)
n = mask.sum()
if n:
    df.loc[mask, "category"] = "Aesthetics & Dermatology"
    df.loc[mask, "category_method"] = 1
    df.loc[mask, "category_confidence"] = "HIGH"
    print(f"  Aesthetic laser -> Aesthetics & Dermatology: {n} rows")

# --- FIX 3: Specific needles (Gastro+Uro panel confusion) ---
NEEDLE_FIXES = [
    ("Urology", r"ureteral|nephrostomy|nephroureteral|urinary|drainage catheter"),
    ("Critical Care & Respiratory", r"ebus|endobronchial|bronchoscopy.*needle|tracheal"),
    ("Surgical & Endoscopy", r"tissue sampling|cutting needle|biopsy.*needle|core biopsy"),
]
for new_cat, pattern in NEEDLE_FIXES:
    mask = (
        df["category"].eq("Needles, Syringes & Catheters (general)") &
        name.str.contains(pattern, regex=True, na=False)
    )
    n = mask.sum()
    if n:
        df.loc[mask, "category"] = new_cat
        df.loc[mask, "category_method"] = 1
        df.loc[mask, "category_confidence"] = "HIGH"
        print(f"  Specific needle -> {new_cat}: {n} rows")

# --- FIX 4: Fistula disambiguation ---
mask = (
    df["category"].eq("Dialysis & Renal") &
    name.str.contains(r"anal fistula|rectal fistula|anorectal|perineal fistula", regex=True, na=False)
)
n = mask.sum()
if n:
    df.loc[mask, "category"] = "Gastro / GI"
    df.loc[mask, "category_method"] = 1
    df.loc[mask, "category_confidence"] = "HIGH"
    print(f"  Fistula disambiguation -> Gastro / GI: {n} rows")

# --- FIX 5: Lithotripsy catch ---
mask = (
    ~df["category"].eq("Urology") &
    name.str.contains(r"litho\s*evo|lithotripsy|lithotripter|lithoclast", regex=True, na=False)
)
n = mask.sum()
if n:
    df.loc[mask, "category"] = "Urology"
    df.loc[mask, "category_method"] = 1
    df.loc[mask, "category_confidence"] = "HIGH"
    print(f"  Lithotripsy -> Urology: {n} rows")

# --- FIX 6: Name rule additions ---
NAME_ADDITIONS = [
    ("Orthopedic & Spine", r"bone graft|bone substitute|bone void|intra-articular|intraarticular"),
    ("Surgical & Endoscopy", r"examination gloves?|exam gloves?|nitrile|latex glove"),
    ("Critical Care & Respiratory", r"blood gas monitor|pulmonary function|extracorporeal.*monitor"),
    ("Surgical & Endoscopy", r"coagulation electrode|bipolar coagulation|ultrasonic generator"),
]
for new_cat, pattern in NAME_ADDITIONS:
    mask = (
        ~df["category"].eq(new_cat) &
        df["category"].isin([
            "Needles, Syringes & Catheters (general)",
            "Diagnostics: Imaging",
            "Diagnostics: IVD & Lab",
            "Cardiac & Vascular",
            "Aesthetics & Dermatology",
        ]) &
        name.str.contains(pattern, regex=True, na=False)
    )
    n = mask.sum()
    if n:
        df.loc[mask, "category"] = new_cat
        df.loc[mask, "category_method"] = 1
        df.loc[mask, "category_confidence"] = "HIGH"
        print(f"  Name addition -> {new_cat}: {n} rows")

print()

# ============================================================
# STEP 3: CHANGE REPORT
# ============================================================
print("=" * 60)
print("STEP 3: Change report")
print("=" * 60)

changed = old_category != df["category"]
print(f"Total rows changed: {changed.sum()}")
print()
print("Category distribution BEFORE vs AFTER:")
comparison = pd.DataFrame({
    "before": old_category.value_counts(),
    "after": df["category"].value_counts(),
}).fillna(0).astype(int)
comparison["delta"] = comparison["after"] - comparison["before"]
print(comparison.sort_values("delta", key=abs, ascending=False).to_string())
print()

change_df = pd.DataFrame({
    "device_id": df.loc[changed, "device_id"],
    "device_name": df.loc[changed, "device_name"],
    "old_category": old_category[changed],
    "new_category": df.loc[changed, "category"],
    "new_method": df.loc[changed, "category_method"],
    "new_confidence": df.loc[changed, "category_confidence"],
})
change_df.to_csv(CHANGE_REPORT, index=False)
print(f"Saved -> {CHANGE_REPORT} ({len(change_df)} rows)")

# ============================================================
# STEP 4: Save fixed file
# ============================================================
df.to_csv(OUT_FILE, index=False)
print(f"Saved -> {OUT_FILE}")

# ============================================================
# STEP 5: Projected accuracy
# ============================================================
print()
print("=" * 60)
print("STEP 5: Projected v2 accuracy")
print("=" * 60)
print("v1 accuracy:   93.8% (23 errors in 372-row sample)")
print("Fixes applied: 6 patterns")
print("Projected v2:  ~96-97%")
print()
print("To verify: draw a fresh 372-row sample from fda_final_v2.csv and re-validate.")