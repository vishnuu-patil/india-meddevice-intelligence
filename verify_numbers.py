# verify_numbers.py - recomputes the headline numbers from the repo files and prints PASS or FAIL
import sys  # lets the script return an exit code at the end
from pathlib import Path  # builds file paths that work on any computer
import pandas as pd  # reads the CSV files

BASE = Path(__file__).resolve().parent  # the folder this script sits in (repo root)
results = []  # one True/False per check

def check(name, actual, expected):  # compares one value with the expected value
    ok = actual == expected  # True when they match exactly
    results.append(ok)  # remember the result for the final summary
    print(("PASS  " if ok else "FAIL  ") + name + " | got: " + str(actual) + " | expected: " + str(expected))  # print one line per check

def lookup(df, col, val, out):  # finds the first row where col == val and returns column out (None if missing)
    hit = df.loc[df[col] == val, out]  # rows that match
    return float(hit.iloc[0]) if len(hit) else None  # first match or None

# ---------- raw FDA download converted to CSV ----------
raw = BASE / "Data" / "fda_510k.csv"  # converted openFDA file
if raw.exists():  # only check if the file is in the repo
    check("fda_510k.csv rows", len(pd.read_csv(raw, usecols=[0])), 51759)  # handover figure, verified by this run

# ---------- FDA final ----------
fda = pd.read_csv(BASE / "Output" / "fda_final.csv")  # cleaned FDA data
check("fda_final rows", len(fda), 47375)  # total rows
check("fda_final categories", fda["category"].nunique(), 18)  # number of categories
check("fda_final has no 'Other'", "Other" not in set(fda["category"]), True)  # Other rows were dropped
conf = fda["category_confidence"].value_counts()  # rows per confidence level
check("fda HIGH / MED / LOW", [int(conf.get(k, 0)) for k in ["HIGH", "MED", "LOW"]], [41100, 3751, 2524])  # confidence counts
check("fda method 1-4 counts", fda["category_method"].value_counts().sort_index().tolist(), [36487, 4613, 3751, 2524])  # rows per method
dates = pd.to_datetime(fda["approved_date"])  # approval dates as real dates
check("fda first approved_date", dates.min().strftime("%Y-%m-%d"), "2010-01-04")  # earliest date
check("fda last approved_date", dates.max().strftime("%Y-%m-%d"), "2026-09-19")  # latest date

# ---------- CDSCO final ----------
cd = pd.read_csv(BASE / "Output" / "cdsco_final.csv")  # cleaned CDSCO data
check("cdsco_final rows", len(cd), 24563)  # total rows
check("cdsco unique licences", cd["license_no"].nunique(), 5163)  # distinct licence numbers
check("cdsco licence-category pairs", len(cd[["license_no", "category"]].drop_duplicates()), 6714)  # counting rule
check("cdsco categories", cd["category"].nunique(), 18)  # number of categories

# ---------- Excel copy ----------
ce = pd.read_csv(BASE / "Excel_Work" / "cdsco_for_excel.csv")  # Excel version of the CDSCO data
check("excel rows, columns", ce.shape, (24563, 20))  # size of the file
check("excel distinct pair_id", ce["pair_id"].nunique(), 6714)  # licence-category pairs
check("excel distinct pair_class_id", ce["pair_class_id"].nunique(), 7634)  # licence-category-class pairs
check("excel distinct pair_country_id", ce["pair_country_id"].nunique(), 6719)  # licence-category-country pairs
pcl = ce.drop_duplicates("pair_class_id")["device_class"].value_counts()  # pairs per device class
check("class pairs A / B / C / D", [int(pcl.get(k, 0)) for k in ["A", "B", "C", "D"]], [268, 3613, 2821, 932])  # class split
pco = ce.drop_duplicates("pair_country_id")["mfr_country"].value_counts().head(3)  # top 3 countries by pairs
check("top 3 country pairs " + str(pco.index.tolist()), pco.tolist(), [1458, 1248, 714])  # US, China, Germany expected

# ---------- Objective 1 ----------
r1 = pd.read_csv(BASE / "Output" / "obj01_category_ranking.csv").sort_values("rank")  # category ranking
check("obj01 top 4 licences", r1["licences"].head(4).tolist(), [1005, 856, 759, 697])  # Cardiac, Imaging, Surgical, Ortho
check("obj01 top 4 share %", round(r1["licences"].head(4).sum() / r1["licences"].sum() * 100, 1), 49.4)  # share of top 4
check("obj01 total licences", int(r1["licences"].sum()), 6714)  # equals the pair count
for v in [645, 537, 514, 381, 79]:  # the other quoted category counts
    check("obj01 has a category with " + str(v), v in set(r1["licences"]), True)  # value present

# ---------- Objective 11 ----------
by = pd.read_csv(BASE / "Output" / "obj11_indian_by_year.csv")  # Indian clearances per year
check("obj11 Indian clearances total", int(by["indian_clearances"].sum()), 202)  # total
check("obj11 peak value", int(by["indian_clearances"].max()), 32)  # peak count
check("obj11 peak year", int(by.loc[by["indian_clearances"].idxmax(), "year"]), 2022)  # peak year
check("obj11 2026 (partial year)", lookup(by, "year", 2026, "indian_clearances"), 7.0)  # partial year
ad = pd.read_csv(BASE / "Output" / "obj11_approval_days.csv")  # approval days by group
check("median days, 202 Indian rows", lookup(ad, "rows", 202, "median_days"), 182.0)  # Indian applicants
check("median days, 47,375 all rows", lookup(ad, "rows", 47375, "median_days"), 124.0)  # all applicants
check("median days, 47,173 non-Indian rows", lookup(ad, "rows", 47173, "median_days"), 124.0)  # non-Indian applicants

# ---------- Pipeline gap A vs B ----------
pg = pd.read_csv(BASE / "Output" / "pipeline_gap_compare.csv")  # gap in version A and B
for a, b in [(9.0, 7.0), (5.9, 5.7), (3.5, 3.4), (4.2, 2.8), (-2.6, 2.0), (-5.9, -5.3), (-3.7, -3.5)]:  # expected (A, B) pairs
    hit = pg[((pg["share_gap_pp_A"] - a).abs() < 0.051) & ((pg["share_gap_pp_B"] - b).abs() < 0.051)]  # matching rows
    check("gap A/B " + str((a, b)) + " " + str(hit["category"].tolist()), len(hit) >= 1, True)  # at least one category matches

# ---------- summary ----------
print("\n" + str(sum(results)) + " passed, " + str(len(results) - sum(results)) + " failed")  # final tally
sys.exit(0 if all(results) else 1)  # non-zero exit code if anything failed
