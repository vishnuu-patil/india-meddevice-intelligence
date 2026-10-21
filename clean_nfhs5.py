# ============================================================
# NFHS-5 district file - cleaning (keeps 20 columns)
# Folder : <project folder>\  (project root)
# Run    : python clean_nfhs5.py
# Input  : Data/NDAP_REPORT_6822.csv   (raw file - never edited)
#          Data/6822_METADATA.csv      (optional - adds the NDAP variable codes)
#          Output/cdsco_final.csv      (optional - only used to check state names)
# Output : Output/nfhs5_clean.csv            (704 districts x 20 columns)
#          Output/nfhs5_column_map.csv       (new name <-> original name <-> NDAP code)
#          Output/nfhs5_cleaning_audit.csv   (every zero that was blanked or flagged)
#          Output/state_name_map.csv         (CDSCO state spelling <-> NFHS spelling)
# ============================================================
import sys  # tool to read the optional folder argument and stop the script
from pathlib import Path  # tool to work with folder paths
import pandas as pd  # tool to work with tables

BASE = Path(__file__).resolve().parent  # project folder = the folder this script sits in
if len(sys.argv) > 1:  # if a folder was typed after the script name
    BASE = Path(sys.argv[1])  # use that folder instead (only for testing)

RAW = BASE / "Data" / "NDAP_REPORT_6822.csv"  # the raw NFHS-5 file
META = BASE / "Data" / "6822_METADATA.csv"  # the NDAP metadata file (optional)
CDSCO = BASE / "Output" / "cdsco_final.csv"  # the CDSCO file (optional, for state names)
OUT = BASE / "Output"  # folder where results are saved

# ---------------- the 20 columns we keep ----------------
# each line: (name in the raw file without the unit text, new short name, group)
PLAN = [
    ("State lgd code", "state_lgd_code", "Key"),  # official state ID
    ("State", "state", "Key"),  # state name
    ("District lgd code", "district_lgd_code", "Key"),  # official district ID
    ("District", "district", "Key"),  # district name
    ("Elevated blood pressure or taking medicine to control blood pressure (%)", "bp_elevated_men_pct", "Hypertension"),  # men (inferred from column order)
    ("Women suffering from elevated blood pressure (%)", "bp_elevated_women_pct", "Hypertension"),  # women
    ("Men-mildly elevated blood pressure (%)", "bp_mild_men_pct", "Hypertension"),  # men, mild
    ("Women-mildly elevated blood pressure (%)", "bp_mild_women_pct", "Hypertension"),  # women, mild
    ("Moderately or severely elevated blood pressure (%)", "bp_severe_men_pct", "Hypertension"),  # men, moderate or severe (inferred)
    ("Women-moderately or severely elevated blood pressure (%)", "bp_severe_women_pct", "Hypertension"),  # women, moderate or severe
    ("Men suffering from high or very high blood sugar level (%)", "sugar_high_men_pct", "Blood sugar"),  # men, high or very high
    ("Women suffering from high or very high blood sugar level (%)", "sugar_high_women_pct", "Blood sugar"),  # women, high or very high
    ("Men suffering from very high blood sugar level (%)", "sugar_veryhigh_men_pct", "Blood sugar"),  # men, very high
    ("Women suffering from very high blood sugar level (%)", "sugar_veryhigh_women_pct", "Blood sugar"),  # women, very high
    ("Women age group 15 to 49 years who are anaemic (%)", "anaemia_women_15_49_pct", "Anaemia"),  # women 15-49
    ("Women age group 15 to 19 years who are anaemic (%)", "anaemia_women_15_19_pct", "Anaemia"),  # women 15-19 (reference only)
    ("Children age group 6 to 59 months who are anaemic (%)", "anaemia_children_6_59m_pct", "Anaemia"),  # children 6-59 months
    ("Women who are overweight or obese (%)", "women_overweight_obese_pct", "Overweight"),  # women 15-49
    ("Men age group 15 years and above who use any kind of tobacco (%)", "men_tobacco_pct", "Tobacco"),  # men 15+
    ("Women age 15 years and above who use any kind of tobacco (%)", "women_tobacco_pct", "Tobacco"),  # women 15+
]
BLANK_GROUPS = {"Hypertension", "Blood sugar", "Anaemia", "Overweight"}  # a zero here is a placeholder -> blank it
FLAG_GROUPS = {"Tobacco"}  # a zero here might be real -> only flag it, keep it

# ---------------- load the raw file ----------------
raw = pd.read_csv(RAW)  # read the raw NFHS-5 file
print(f"Raw file: {raw.shape[0]} rows x {raw.shape[1]} columns")  # should be 704 x 110

# map "short column name" -> "full column name" (the full name carries the long unit text)
lookup = {c.split("(UOM")[0].strip(): c for c in raw.columns}  # cut the unit text off every column name
if len(lookup) != len(raw.columns):  # if two columns ended up with the same short name
    print("WARNING: some column names are not unique after cutting the unit text")  # tell the user

missing = [s for s, _, _ in PLAN if s not in lookup]  # any wanted column that is not in the file
if missing:  # if something is missing
    print("STOP - these columns were not found in the raw file:")  # tell the user
    for m in missing:  # list each one
        print("  -", m)  # print its name
    sys.exit(1)  # stop the script here

# ---------------- build the slim table with short names ----------------
slim = pd.DataFrame({new: raw[lookup[short]] for short, new, _ in PLAN})  # keep only the 20 wanted columns, renamed
group_of = {new: grp for _, new, grp in PLAN}  # quick lookup: column -> group
data_cols = [new for _, new, grp in PLAN if grp != "Key"]  # the 16 data columns (not keys)

slim["state"] = slim["state"].astype(str).str.strip()  # remove stray spaces around state names
slim["district"] = slim["district"].astype(str).str.strip()  # remove stray spaces around district names

for col in data_cols:  # go through every data column
    before = slim[col].isna().sum()  # blanks before the number conversion
    slim[col] = pd.to_numeric(slim[col], errors="coerce")  # make sure it is a number (text like * becomes blank)
    after = slim[col].isna().sum()  # blanks after the conversion
    if after > before:  # if the conversion created new blanks
        print(f"NOTE: {col} had {after - before} non-number cells turned into blanks")  # tell the user

# ---------------- zeros: blank or flag ----------------
audit = []  # list that will hold one line per zero found
for col in data_cols:  # go through every data column
    zero_rows = slim.index[slim[col] == 0]  # rows where the value is exactly 0
    for i in zero_rows:  # go through each of those rows
        action = "blanked (0.0 is a placeholder)" if group_of[col] in BLANK_GROUPS else "flagged, kept"  # decide what to do
        audit.append({"state": slim.at[i, "state"], "district": slim.at[i, "district"],
                      "district_lgd_code": slim.at[i, "district_lgd_code"],
                      "column": col, "old_value": 0.0, "action": action})  # remember it in the audit list
        if group_of[col] in BLANK_GROUPS:  # if this group's zeros are placeholders
            slim.at[i, col] = float("nan")  # blank the cell
audit_df = pd.DataFrame(audit, columns=["state", "district", "district_lgd_code", "column", "old_value", "action"])  # audit as a table

# ---------------- column map (new name <-> original name <-> NDAP code) ----------------
codes = {}  # will hold NDAP variable codes
if META.exists():  # if the metadata file is there
    meta = pd.read_csv(META)  # read it
    codes = {str(n).strip(): c for n, c in zip(meta["VariableName"], meta["VariableCode"])}  # variable name -> code
else:  # if it is not there
    print("NOTE: Data/6822_METADATA.csv not found - the code column will be empty")  # tell the user
col_map = pd.DataFrame({
    "new_name": [new for _, new, _ in PLAN],  # short name we use
    "original_name": [lookup[short] for short, _, _ in PLAN],  # full name in the raw file
    "ndap_code": [codes.get(short, "") for short, _, _ in PLAN],  # NDAP variable code
    "group": [grp for _, _, grp in PLAN],  # which disease group it belongs to
})

# ---------------- state name map: CDSCO spelling <-> NFHS spelling ----------------
FALLBACK = ["Andhra Pradesh", "Bihar", "Chandigarh", "Chhattishgarh", "Dadra And Nagar Haveli", "Daman And Diu",
            "Delhi", "Goa", "Gujarat", "Haryana", "Himachal Pradesh", "Jammu And Kashmir", "Karnataka", "Kerala",
            "Madhya Pradesh", "Maharashtra", "Orissa", "Puducherry", "Punjab", "Rajasthan", "Tamil Nadu",
            "Telangana", "Uttar Pradesh", "Uttarakhand", "West Bengal"]  # CDSCO states used if cdsco_final.csv is missing
if CDSCO.exists():  # if the CDSCO file is there
    cd_states = sorted(pd.read_csv(CDSCO, usecols=["importer_state"])["importer_state"].dropna().unique())  # read its states
else:  # if not
    cd_states = FALLBACK  # use the saved list
OVERRIDES = {"Chhattishgarh": "Chhattisgarh",  # CDSCO typo
             "Orissa": "Odisha",  # old state name
             "Dadra And Nagar Haveli": "The Dadra And Nagar Haveli And Daman And Diu",  # merged UT
             "Daman And Diu": "The Dadra And Nagar Haveli And Daman And Diu"}  # merged UT
nfhs_states = set(slim["state"])  # all state names in the cleaned NFHS table
rows = []  # list that will hold the state map lines
for s in cd_states:  # go through each CDSCO state
    n = OVERRIDES.get(s, s)  # NFHS spelling (same name unless it is in the override list)
    ok = n in nfhs_states  # is that name found in NFHS?
    rows.append({"cdsco_state": s, "nfhs_state": n if ok else "", "matched": ok,
                 "note": ("renamed" if s in OVERRIDES else "same name") if ok else "not in NFHS file"})  # one map line
state_map = pd.DataFrame(rows)  # state map as a table

# ---------------- save ----------------
slim.to_csv(OUT / "nfhs5_clean.csv", index=False, encoding="utf-8-sig")  # cleaned table
col_map.to_csv(OUT / "nfhs5_column_map.csv", index=False, encoding="utf-8-sig")  # column map
audit_df.to_csv(OUT / "nfhs5_cleaning_audit.csv", index=False, encoding="utf-8-sig")  # audit of zeros
state_map.to_csv(OUT / "state_name_map.csv", index=False, encoding="utf-8-sig")  # state name map

# ---------------- checks printed on screen ----------------
pd.set_option("display.width", 250)  # wider print so tables do not wrap
pd.set_option("display.max_colwidth", 60)  # keep long text readable
print(f"\nClean table            : {slim.shape[0]} rows x {slim.shape[1]} columns")  # should be 704 x 20
print(f"Unique district codes  : {slim['district_lgd_code'].nunique()}")  # should be 704
print(f"Repeated State+District: {slim.duplicated(['state', 'district']).sum()}")  # should be 0
print(f"States / UTs           : {slim['state'].nunique()}")  # should be 34
dup_names = slim[slim.duplicated('district', keep=False)].sort_values('district')  # districts whose name appears twice
print(f"Distinct district names: {slim['district'].nunique()}  (name repeats in more than one state: "
      f"{', '.join(sorted(dup_names['district'].unique()))})")  # name-only join is unsafe
vals = slim[data_cols]  # just the data columns
print(f"Cells below 0 or above 100: {int(((vals < 0) | (vals > 100)).sum().sum())}")  # should be 0
nulls = vals.isna().sum()  # blanks per column
print("Columns with blanks    :", {k: int(v) for k, v in nulls[nulls > 0].items()} or "none")  # only the 2 blanked BP cells
for sx in ("men", "women"):  # check men and women separately
    bad = slim[f"bp_elevated_{sx}_pct"] + 0.5 < slim[f"bp_mild_{sx}_pct"] + slim[f"bp_severe_{sx}_pct"]  # elevated should be >= mild + severe
    print(f"BP check ({sx}): districts where elevated < mild + severe = {int(bad.sum())}")  # should be 0
print("\n=== AUDIT (zeros found) ===")  # heading
print(audit_df.to_string(index=False) if len(audit_df) else "none")  # show the audit table
print("\n=== STATE NAME MAP (CDSCO -> NFHS) ===")  # heading
print(state_map.to_string(index=False))  # show the state map
print(f"\nCDSCO states matched: {int(state_map['matched'].sum())} of {len(state_map)}")  # how many matched
print("\nSaved 4 files in Output/")  # done message