# ============================================================
# Excel prep - a SAFE COPY of the CDSCO data with a clean importer name and counting IDs
# Folder : <project folder>\  (project root)
# Run    : python make_excel_copy.py
# Input  : Output/cdsco_final.csv   (read only, never changed)
# Output : Excel_Work/cdsco_for_excel.csv   (24,563 rows = the 15 original columns + 5 new ones)
# New columns:
#   importer_clean  = one tidy importer name per licence (Pvt Ltd / Private Limited merged)
#   risk_label      = High risk (Class D), Medium-high (Class C), Standard (Class A or B)
#   pair_id         = licence + category            -> Distinct Count = 6,714 pairs
#   pair_country_id = licence + category + country  -> Distinct Count for the country pivot
#   pair_class_id   = licence + category + class    -> Distinct Count for the class pivot
# ============================================================
import re  # tool for cleaning company names
import sys  # tool to read the optional folder argument
from pathlib import Path  # tool to work with folder paths
import pandas as pd  # tool to work with tables

BASE = Path(__file__).resolve().parent  # project folder = the folder this script sits in
if len(sys.argv) > 1:  # if a folder was typed after the script name
    BASE = Path(sys.argv[1])  # use that folder instead (only for testing)
OUT_DIR = BASE / "Excel_Work"  # new folder for everything we open in Excel
OUT_DIR.mkdir(exist_ok=True)  # make the folder if it is missing

df = pd.read_csv(BASE / "Output" / "cdsco_final.csv", low_memory=False)  # load the cleaned CDSCO file
print(f"Rows                    : {len(df):,}")  # should be 24,563
print(f"Unique licences         : {df['license_no'].nunique():,}")  # should be 5,163

# ---------------- clean importer name (same clean-up as Objective 06) ----------------
def clean_name(n):  # makes company names comparable
    if pd.isna(n):  # empty name
        return "unknown"  # call it unknown
    s = str(n).lower().replace("&", " and ")  # lower case, & -> and
    s = re.sub(r"[^a-z0-9 ]", " ", s)  # drop dots, commas and other symbols
    s = re.sub(r"\s+", " ", s).strip()  # squeeze spaces
    s = re.sub(r"\b(private limited|private ltd|pvt limited)\b", "pvt ltd", s)  # unify Pvt Ltd spellings
    return re.sub(r"\blimited\b", "ltd", s)  # limited -> ltd

df["importer_key"] = df["importer_name"].apply(clean_name)  # tidy key used only for grouping
print(f"Importer names before   : {df['importer_name'].nunique():,}")  # raw spellings
print(f"Rows with a blank importer name: {int(df['importer_name'].isna().sum()):,}")  # these become 'unknown'

# one importer per licence: the most common key among the licence's rows, ties -> alphabetical first
cnt = df.groupby(["license_no", "importer_key"]).size().rename("n").reset_index()  # rows per licence + key
cnt = cnt.sort_values(["license_no", "n", "importer_key"], ascending=[True, False, True])  # best key first
licence_key = cnt.drop_duplicates("license_no").set_index("license_no")["importer_key"]  # chosen key per licence
n_multi = int((cnt.groupby("license_no").size() > 1).sum())  # licences that had more than one key
df["importer_key"] = df["license_no"].map(licence_key)  # apply the chosen key to every row

# readable name = the most common original spelling of each key (ties -> alphabetical first)
def pick_name(x):  # chooses the display name for one key
    m = x.dropna().mode()  # most common real spelling (blank names are ignored)
    return m.sort_values().iloc[0] if len(m) else "unknown"  # if every name was blank, call it unknown
display = df.groupby("importer_key")["importer_name"].agg(pick_name)  # key -> name
df["importer_clean"] = df["importer_key"].map(display)  # add the readable clean name

# ---------------- risk label and counting IDs ----------------
df["risk_label"] = df["device_class"].map({"D": "High risk", "C": "Medium-high", "B": "Standard", "A": "Standard"})  # class -> label
df["pair_id"] = df["license_no"].astype(str) + "|" + df["category"].astype(str)  # licence + category
df["pair_country_id"] = df["pair_id"] + "|" + df["mfr_country"].astype(str)  # + country
df["pair_class_id"] = df["pair_id"] + "|" + df["device_class"].astype(str)  # + class

df = df.drop(columns=["importer_key"])  # internal helper, not needed in Excel
df.to_csv(OUT_DIR / "cdsco_for_excel.csv", index=False, encoding="utf-8-sig")  # save the Excel copy

# ---------------- checks printed on screen ----------------
print(f"Importer names after    : {df['importer_clean'].nunique():,}")  # fewer than before
print(f"Licences that had 2+ importer spellings (now one): {n_multi}")  # information
per_imp = df.drop_duplicates("license_no").groupby("importer_clean").size()  # unique licences per importer
print(f"Sum of licences per importer: {per_imp.sum():,}  (should be 5,163)")  # consistency check
print(f"pair_id distinct        : {df['pair_id'].nunique():,}  (should be 6,714)")  # licence-category pairs
print(f"pair_class_id distinct  : {df['pair_class_id'].nunique():,}  (should be 7,634)")  # matches Objective 08
print(f"pair_country_id distinct: {df['pair_country_id'].nunique():,}  (should be 6,714 or a little more)")  # matches Objective 07 totals
print("risk_label counts (rows):", df["risk_label"].value_counts(dropna=False).to_dict())  # no blanks expected
print(f"Columns                 : {df.shape[1]}  (15 original + 5 new = 20)")  # column check
print("\nSaved Excel_Work/cdsco_for_excel.csv")  # done message