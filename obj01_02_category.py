# ============================================================
# Objectives 01 + 02 - Category ranking and growth trend
# Folder : <project folder>\  (project root)
# Run    : python obj01_02_category.py
# Input  : Output/cdsco_final.csv
# Output : Output/obj01_category_ranking.csv
#          Output/obj02_growth_by_year.csv
#          Output/obj02_growth_yoy_pct.csv
# ============================================================
from pathlib import Path  # tool to work with folder paths
import pandas as pd  # tool to work with tables

BASE = Path(__file__).resolve().parent  # project folder = the folder this script sits in
IN_FILE = BASE / "Output" / "cdsco_final.csv"  # the cleaned CDSCO file we read
Y0, Y1 = 2018, 2026  # first and last year we look at

df = pd.read_csv(IN_FILE, low_memory=False)  # load the CDSCO file into a table
df = df[df["license_year"].between(Y0, Y1)].copy()  # keep only 2018 to 2026 rows

# one row per unique (licence, category) pair - same counting as the pipeline gap
pairs = df.drop_duplicates(["license_no", "category"]).copy()  # remove repeat rows of the same licence+category

# ---------------- OBJECTIVE 01: category ranking ----------------
rank = pairs.groupby("category").size().rename("licences")  # count pairs in each category
rank = rank.sort_values(ascending=False).reset_index()  # biggest category first
rank["share_pct"] = (rank["licences"] / rank["licences"].sum() * 100).round(1)  # each category's % of the total
rank.insert(0, "rank", range(1, len(rank) + 1))  # add rank number 1, 2, 3...
rank.to_csv(BASE / "Output" / "obj01_category_ranking.csv", index=False, encoding="utf-8-sig")  # save to file

# ---------------- OBJECTIVE 02: growth trend ----------------
trend = pairs.pivot_table(index="category", columns="license_year",
                          values="license_no", aggfunc="count", fill_value=0)  # category rows x year columns, count of pairs
trend = trend.reindex(columns=range(Y0, Y1 + 1), fill_value=0)  # make sure every year 2018-2026 has a column
trend["total"] = trend.sum(axis=1)  # add a total column per category
trend = trend.sort_values("total", ascending=False)  # biggest category on top
trend.to_csv(BASE / "Output" / "obj02_growth_by_year.csv", encoding="utf-8-sig")  # save counts per year

yoy = trend.drop(columns="total").pct_change(axis=1) * 100  # % change of each year versus the year before
yoy = yoy.replace([float("inf"), float("-inf")], float("nan")).round(1)  # a jump from 0 has no % - blank it
yoy = yoy.rename(columns={Y1: f"{Y1}_partial"})  # label 2026 as partial year (data ends 1 Oct 2026)
yoy.to_csv(BASE / "Output" / "obj02_growth_yoy_pct.csv", encoding="utf-8-sig")  # save growth %

# ---------------- checks printed on screen ----------------
pd.set_option("display.width", 220)  # wider print so the table does not wrap
print(f"Unique licences        : {pairs['license_no'].nunique():,}")  # should match earlier check
print(f"Licence-category pairs : {len(pairs):,}")  # should match earlier check
print("\n=== OBJ 01: CATEGORY RANKING ===")  # heading
print(rank.to_string(index=False))  # show the ranking table
print("\n=== OBJ 02: NEW PAIRS PER YEAR (2026 is partial) ===")  # heading
print(trend.to_string())  # show counts per year
print("\nTotal pairs per year (all categories):")  # heading
print(trend.drop(columns="total").sum().to_string())  # show yearly totals
print("\nSaved 3 files in Output/")  # done message