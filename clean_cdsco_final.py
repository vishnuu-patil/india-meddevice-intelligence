# ============================================================
# Script 05a - CDSCO final clean file  (v2)
# Folder : <project folder>\
# Run    : python clean_cdsco_final.py
# Input  : Output/cdsco_categorized.csv
# Output : Output/cdsco_final.csv         (main clean file)
#          Output/cdsco_model_lookup.csv  (list of every model_id and what it means)
# ============================================================
import re
import sys
from pathlib import Path
import pandas as pd

BASE = Path(__file__).resolve().parent
if len(sys.argv) > 1:               # optional override for testing
    BASE = Path(sys.argv[1])

IN_FILE = BASE / "Output" / "cdsco_categorized.csv"
OUT_FILE = BASE / "Output" / "cdsco_final.csv"
LOOKUP_FILE = BASE / "Output" / "cdsco_model_lookup.csv"


# ------------------------------------------------------------
# FIX A: remove address leftovers from the END of importer_name
# e.g. "Spark Peripheral Technologies Shop No" -> "Spark Peripheral Technologies"
# The loop keeps cutting until nothing more matches.
# ------------------------------------------------------------
TAIL_PATTERNS = [
    # "Shop No", "Plot No.", "Office No", "Unit No.", "No.3", "Nos" ...
    re.compile(
        r"[\s,\-/(:]*\b(?:(?:shop|plot|office|unit|flat|door|gala|room|suite|"
        r"property|survey|house|godown|building|bldg|block|ward|old|new|h|d|c)\.?\s*)?"
        r"(?:no|nos)\b\.?\s*\d*$", re.I),
    # "Ground Floor", "First Floor", "Basement", "Floor"
    re.compile(
        r"[\s,\-/(:]*\b(?:(?:ground|first|second|third|fourth|fifth|lower|upper|"
        r"top|mezzanine|1st|2nd|3rd|4th)\s+)?(?:floor|basement)$", re.I),
    # short forms: GF / FF / SF / TF
    re.compile(r"[\s,\-/(:]*\b(?:gf|ff|sf|tf)$", re.I),
    # lonely "Shop", "Plot", "Flat", "Gala", "Door" at the end
    re.compile(r"[\s,\-/(:]*\b(?:shop|plot|flat|gala|door)$", re.I),
    # trailing junk punctuation
    re.compile(r"[\s,\-/(:&]+$"),
]


def fix_importer_name(name):
    if pd.isna(name):
        return name
    original = str(name).strip()
    current = original
    changed = True
    while changed:                      # loop until no pattern matches
        changed = False
        for pat in TAIL_PATTERNS:
            new = pat.sub("", current).strip()
            if new != current and len(new) >= 3:
                current = new
                changed = True
    return current


# ------------------------------------------------------------
# FIX B: clean model_numbers text, then give our own model_id
# ------------------------------------------------------------
NO_INFO = {"", "nil", "na", "n/a", "none", "-", "not applicable", "nil - nil",
           "nil - n/a", "na - na", "nil -", "na -", "n.a", "n.a."}


def clean_model_text(s):
    """Remove the scraped 'Show More ... Show Less' junk (text is pasted twice)."""
    if pd.isna(s):
        return ""
    s = str(s)
    if "Show More" in s:
        s = s.split("Show More", 1)[1]   # the full list sits after 'Show More'
    s = s.replace("Show Less", "")
    return re.sub(r"\s+", " ", s).strip()


def norm(s):
    return re.sub(r"\s+", " ", str(s)).strip().lower()


# ------------------------------------------------------------
# LOAD
# ------------------------------------------------------------
df = pd.read_csv(IN_FILE, low_memory=False)
rows_before = len(df)

# 1. Drop the leftover junk category
df = df[df["category"] != "Other"].copy().reset_index(drop=True)

# 2. category_source "1_name" -> 1, renamed to category_method
df["category_method"] = df["category_source"].str.extract(r"^(\d)", expand=False).astype(int)

# 2b. category_confidence from category_method (1,2 = HIGH | 3 = MED | 4 = LOW)
CONF = {1: "HIGH", 2: "HIGH", 3: "MED", 4: "LOW", 5: "LOW"}
df["category_confidence"] = df["category_method"].map(CONF)

# 2c. is_renewal: True when the row's issue_year is later than the year in the licence number
df["is_renewal"] = df["license_year"] != df["issue_year"]

# 3. device_class = letter only (A/B/C/D)
df["device_class"] = df["class_letter"].str.strip().str.upper()
assert df["device_class"].isin(["A", "B", "C", "D"]).all(), "Unexpected device class value"

# 4. importer_name tail fix
before_names = df["importer_name"].copy()
df["importer_name"] = df["importer_name"].map(fix_importer_name)
names_fixed = (before_names.fillna("") != df["importer_name"].fillna("")).sum()

# 5. model_id
df["model_text"] = df["model_numbers"].map(clean_model_text)
df["_no_info"] = df["model_text"].map(norm).isin(NO_INFO)
no_info = df["_no_info"]

# What identifies a model?
#   - normal rows : brand + the cleaned model list
#   - rows whose model list is empty/NIL : brand + device_name
brand_clean = df["brand_name"].fillna("").str.strip()
brand_key = brand_clean.str.lower()
df["_brand_label"] = brand_clean.where(brand_clean != "", "NoBrand").str.slice(0, 50).str.strip()
df["_id_text"] = df["model_text"].where(~no_info, "DEVICE: " + df["device_name"].fillna(""))
df["_key"] = brand_key + "||" + df["_id_text"].map(norm)

# Number models 1,2,3... inside each brand, in order of first appearance.
# Same brand + same model list -> same number.
first_seen = df.drop_duplicates("_key")[["_key", "_brand_label"]].copy()
first_seen["_brand_lower"] = first_seen["_brand_label"].str.lower()
first_seen["_n"] = first_seen.groupby("_brand_lower").cumcount() + 1
first_seen["model_id"] = first_seen["_brand_label"] + "-" + first_seen["_n"].astype(str)
df = df.merge(first_seen[["_key", "model_id"]], on="_key", how="left")

# ------------------------------------------------------------
# Lookup file: every model_id with the model list behind it
# (text cut at 1,000 characters so Excel can open it)
# ------------------------------------------------------------
lookup = (
    df.groupby("model_id", sort=False)
      .agg(brand=("_brand_label", "first"),
           device_name=("device_name", "first"),
           model_text=("model_text", "first"),
           used_device_name=("_no_info", "first"),
           rows_using_it=("model_id", "size"),
           licences_using_it=("license_no", "nunique"))
      .reset_index()
)
lookup["id_based_on"] = lookup["used_device_name"].map(
    {True: "device_name (model list was NIL/empty)", False: "model list"})
lookup = lookup.drop(columns="used_device_name")
lookup["model_text_length"] = lookup["model_text"].str.len()
lookup["model_text"] = lookup["model_text"].str.slice(0, 1000)
lookup.to_csv(LOOKUP_FILE, index=False, encoding="utf-8-sig")

# ------------------------------------------------------------
# FINAL FILE: model_id replaces the huge model_numbers column
# ------------------------------------------------------------
KEEP = [
    "importer_name", "license_no", "device_name", "device_class",
    "brand_name", "model_id", "mfr_country",
    "license_year", "issue_year", "is_renewal",
    "importer_state", "importer_pincode",
    "category", "category_method", "category_confidence",
]
final = df[KEEP]
final.to_csv(OUT_FILE, index=False, encoding="utf-8-sig")

# ---------------- checks ----------------
print(f"Rows before             : {rows_before:,}")
print(f"Rows dropped (Other)    : {rows_before - len(final):,}")
print(f"Rows in final file      : {len(final):,}")
print(f"Columns                 : {len(final.columns)}")
print(f"Unique licences         : {final['license_no'].nunique():,}")
print(f"Importer names shortened: {names_fixed:,} rows")
print(f"Unique importer names   : {final['importer_name'].nunique():,}")
print(f"Unique model_id         : {final['model_id'].nunique():,}")
print(f"Rows where model list was NIL -> used device_name: {int(df["_no_info"].sum()):,}")
print(f"Rows with no brand (prefix NoBrand): {int((df['_brand_label'] == 'NoBrand').sum()):,}")
print("\nDevice class counts:")
print(final["device_class"].value_counts().sort_index().to_string())
print("\nCategory method counts (1 = device name rule, 2 = intended use narrow,")
print("3 = generic name, 4 = intended use broad, 5 = no rule matched):")
print(final["category_method"].value_counts().sort_index().to_string())
print("\nis_renewal counts (True = later stamp on an older licence):")
print(final["is_renewal"].value_counts().to_string())
print("\nNew licences per license_year (unique licences):")
print(final.drop_duplicates("license_no")["license_year"].value_counts().sort_index().to_string())
print("\nCategory confidence counts:")
print(final["category_confidence"].value_counts().to_string())
print("\nMissing values per column:")
print(final.isna().sum().to_string())
print("\nSample of model_id:")
print(final[["brand_name", "model_id"]].drop_duplicates().head(8).to_string(index=False))
print(f"\nSaved: {OUT_FILE}")
print(f"Saved: {LOOKUP_FILE}")