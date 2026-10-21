# ============================================================
# Objective 10 - Import value (USD) vs licence count, by device segment
# Folder : <project folder>\  (project root)
# Run    : python obj10_import_value_vs_licences.py
# Input  : Data/India_Medical_Device_Imports.xlsx   (5 segments x 6 financial years)
#          Output/cdsco_final.csv                   (licences)
# Output : Output/obj10_imports_clean.csv       (clean long table, shares recomputed)
#          Output/obj10_import_growth.csv       (segment x year, growth, CAGR)
#          Output/obj10_segment_vs_licences.csv (the comparison)
#          Output/obj10_category_to_segment.csv (the mapping used - my judgement)
#
# IDEA: high import spend + few licences = low competition (possible opportunity).
# The import data has only 5 broad segments, our taxonomy has 18 categories, so every
# category is mapped to ONE segment (table below). Mapping is judgement, so we run two versions:
#   Version B = all 18 categories mapped.  Version A = only categories with a clear fit.
# WINDOWS: imports = financial years 2019-20 to 2024-25 (Apr 2019 - Mar 2025);
#          licences = license_year 2019 to 2024 (closest calendar match, approximate).
# ============================================================
import sys  # tool to read the optional folder argument and stop the script
from pathlib import Path  # tool to work with folder paths
import pandas as pd  # tool to work with tables

BASE = Path(__file__).resolve().parent  # project folder = the folder this script sits in
if len(sys.argv) > 1:  # if a folder was typed after the script name
    BASE = Path(sys.argv[1])  # use that folder instead (only for testing)
OUT = BASE / "Output"  # folder where results are saved

# ---------------- category -> segment mapping (edit here if you disagree) ----------------
# each line: category : (segment, fit)   fit = "clear" or "mixed"
MAP = {
    "Diagnostics: IVD & Lab": ("IVD", "clear"),  # test kits and reagents
    "Orthopedic & Spine": ("Implants", "clear"),  # knee, hip, spine implants
    "Diagnostics: Imaging": ("Electronic equipment", "clear"),  # MRI, CT, ultrasound, X-ray
    "Needles, Syringes & Catheters (general)": ("Consumables & disposables", "clear"),  # needles, IV sets
    "Wound Care": ("Consumables & disposables", "clear"),  # dressings
    "Blood & Transfusion": ("Consumables & disposables", "clear"),  # blood bags and sets
    "Cardiac & Vascular": ("Implants", "mixed"),  # stents and valves, but also catheters and monitors
    "Surgical & Endoscopy": ("Surgical instruments", "mixed"),  # instruments, but also gloves and endoscopes
    "Critical Care & Respiratory": ("Electronic equipment", "mixed"),  # ventilators, but also masks
    "Dental": ("Implants", "mixed"),  # implants, but also consumables
    "Ophthalmic": ("Implants", "mixed"),  # lenses, but also surgical consumables
    "ENT & Hearing": ("Implants", "mixed"),  # cochlear implants, but also hearing aids
    "Neuro": ("Implants", "mixed"),  # stimulators, but also instruments
    "Dialysis & Renal": ("Consumables & disposables", "mixed"),  # bloodlines, but also machines
    "Gastro / GI": ("Consumables & disposables", "mixed"),  # endoscopic accessories
    "Urology": ("Consumables & disposables", "mixed"),  # catheters, stone baskets
    "IVF & Women's Health": ("Consumables & disposables", "mixed"),  # culture media
    "Aesthetics & Dermatology": ("Consumables & disposables", "mixed"),  # fillers, but also lasers
}
# the import file uses different names for the same segment in different years
SEGMENT_FIX = {"Consumables and Disposables": "Consumables & disposables",  # tidy name
               "Surgical Instruments": "Surgical instruments",  # tidy name
               "Electronics Equipment": "Electronic equipment",  # 2019-20 to 2021-22 name
               "Electro-Medical Equip.": "Electronic equipment",  # 2023-24 onward name
               "Implants": "Implants",  # same
               "IVD Reagents": "IVD",  # 2019-20 to 2021-22 name
               "In-Vitro Diagnostics": "IVD"}  # 2022-23 onward name

# ---------------- load and clean the import table ----------------
raw = pd.read_excel(BASE / "Data" / "India_Medical_Device_Imports.xlsx", skiprows=3)  # skip the 3 title rows
raw = raw[raw["Country"] == "India"].copy()  # keep only data rows (drops the note at the bottom)
imp = pd.DataFrame({"fy": raw["Financial Year"].astype(str).str.strip(),  # financial year like 2019-20
                    "segment_raw": raw["Device Segment"].astype(str).str.strip(),  # name as in the file
                    "import_usd_mn": pd.to_numeric(raw["Import Value (USD Million)"], errors="coerce"),  # value in USD million
                    "share_in_file_pct": pd.to_numeric(raw["Percentage Share (%)"], errors="coerce")})  # share given in the file
imp["segment"] = imp["segment_raw"].map(SEGMENT_FIX)  # one name per segment
if imp["segment"].isna().any():  # if a segment name was not recognised
    print("STOP - unknown segment names:", imp[imp["segment"].isna()]["segment_raw"].unique())  # tell the user
    sys.exit(1)  # stop here
imp["share_pct"] = (imp["import_usd_mn"] / imp.groupby("fy")["import_usd_mn"].transform("sum") * 100).round(1)  # recomputed share per year
imp["share_diff_vs_file"] = (imp["share_pct"] - imp["share_in_file_pct"]).abs()  # how far the file's share is from ours
imp[["fy", "segment", "segment_raw", "import_usd_mn", "share_pct"]].to_csv(OUT / "obj10_imports_clean.csv", index=False, encoding="utf-8-sig")  # save clean table

# ---------------- growth ----------------
piv = imp.pivot_table(index="segment", columns="fy", values="import_usd_mn", aggfunc="sum")  # segment x year
fys = list(piv.columns)  # financial years in order
growth = piv.copy()  # start from the values
growth["total_6yrs"] = piv.sum(axis=1)  # six-year total
growth["cagr_pct_19_20_to_24_25"] = (((piv[fys[-1]] / piv[fys[0]]) ** (1 / (len(fys) - 1)) - 1) * 100).round(1)  # compound yearly growth
growth["last_year_growth_pct"] = ((piv[fys[-1]] / piv[fys[-2]] - 1) * 100).round(1)  # growth in the latest year
growth = growth.sort_values("total_6yrs", ascending=False)  # biggest first
growth.to_csv(OUT / "obj10_import_growth.csv", encoding="utf-8-sig")  # save to file

# ---------------- licence side ----------------
cd = pd.read_csv(OUT / "cdsco_final.csv", low_memory=False)  # load the CDSCO file
cd = cd[cd["license_year"].between(2019, 2024)]  # calendar years closest to the import window
pairs = cd.drop_duplicates(["license_no", "category"]).copy()  # unique (licence, category) pairs
pairs["segment"] = pairs["category"].map(lambda c: MAP[c][0])  # category -> segment
pairs["fit"] = pairs["category"].map(lambda c: MAP[c][1])  # clear or mixed
mapping = pd.DataFrame([(c, s, f) for c, (s, f) in MAP.items()], columns=["category", "segment", "fit"])  # mapping as a table
mapping["licences_2019_2024"] = mapping["category"].map(pairs.groupby("category").size()).fillna(0).astype(int)  # licences per category
mapping.to_csv(OUT / "obj10_category_to_segment.csv", index=False, encoding="utf-8-sig")  # save mapping

# ---------------- comparison ----------------
imp_tot = imp.groupby("segment")["import_usd_mn"].sum()  # six-year import value per segment
comp = pd.DataFrame({"import_usd_mn_6yrs": imp_tot})  # start the comparison table
comp["import_share_pct"] = (comp["import_usd_mn_6yrs"] / comp["import_usd_mn_6yrs"].sum() * 100).round(1)  # share of all imports
comp["licences_B"] = pairs.groupby("segment").size()  # Version B: all mapped categories
comp["licences_A"] = pairs[pairs["fit"] == "clear"].groupby("segment").size()  # Version A: clear-fit categories only
comp = comp.fillna(0)  # a segment with no clear-fit category gets 0
for v in ("A", "B"):  # do the same steps for both versions
    comp[f"licence_share_{v}_pct"] = (comp[f"licences_{v}"] / comp[f"licences_{v}"].sum() * 100).round(1)  # share of licences
    comp[f"spend_vs_licence_ratio_{v}"] = (comp["import_share_pct"] / comp[f"licence_share_{v}_pct"]).replace(float("inf"), float("nan")).round(2)  # >1 = spend high for its licence count
comp = comp.sort_values("import_usd_mn_6yrs", ascending=False).reset_index()  # biggest spend first
comp[["licences_A", "licences_B"]] = comp[["licences_A", "licences_B"]].astype(int)  # whole numbers
comp.to_csv(OUT / "obj10_segment_vs_licences.csv", index=False, encoding="utf-8-sig")  # save to file

# ---------------- checks printed on screen ----------------
pd.set_option("display.width", 250)  # wider print so tables do not wrap
print(f"Import rows            : {len(imp)}  ({imp['fy'].nunique()} years x {imp['segment'].nunique()} segments)")  # should be 30, 6 x 5
print("Total imports per year (USD Mn):")  # heading
print(imp.groupby("fy")["import_usd_mn"].sum().round(1).to_string())  # yearly totals
print(f"\nLargest gap between the file's share and our recomputed share: {imp['share_diff_vs_file'].max():.2f} points "
      f"(file has shares only for 2019-20 to 2021-22; 2020-21 and 2021-22 are rounded whole numbers)")  # data quality note
print("\n=== IMPORT GROWTH BY SEGMENT (USD Mn) ===")  # heading
print(growth.round(1).to_string())  # growth table
print(f"\nLicence pairs 2019-2024 : {len(pairs):,}")  # licence count used
print("\n=== SEGMENT: IMPORT SPEND vs LICENCES ===")  # heading
print(comp.to_string(index=False))  # comparison table
print("\nRatio > 1 = imports are a bigger share than licences (high spend, relatively few licences).")  # how to read
print("\nSaved 4 files in Output/")  # done message