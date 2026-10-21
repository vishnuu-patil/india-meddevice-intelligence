# ============================================================
# Objective 11 - Indian applicants in the US FDA 510(k) data
# Folder : <project folder>\  (project root)
# Run    : python obj11_indian_fda.py
# Input  : Output/fda_final.csv  (47,375 rows, 2010 to 19 Sep 2026)
# Output : Output/obj11_indian_by_year.csv          (Indian clearances + share of all, per year)
#          Output/obj11_indian_by_category.csv      (Indian clearances per category)
#          Output/obj11_indian_category_by_year.csv (category x year counts)
#          Output/obj11_top_indian_companies.csv    (top 15 Indian applicants)
#          Output/obj11_approval_days.csv           (approval days: Indian vs all)
# NOTE: the FDA "country" field is most likely the APPLICANT's country, so we call them
#       "Indian applicants", not "devices made in India".
# ============================================================
import re  # tool for cleaning company names
import sys  # tool to read the optional folder argument
from pathlib import Path  # tool to work with folder paths
import pandas as pd  # tool to work with tables

BASE = Path(__file__).resolve().parent  # project folder = the folder this script sits in
if len(sys.argv) > 1:  # if a folder was typed after the script name
    BASE = Path(sys.argv[1])  # use that folder instead (only for testing)
OUT = BASE / "Output"  # folder where results are saved

df = pd.read_csv(OUT / "fda_final.csv", low_memory=False)  # load the cleaned FDA file
df["year"] = pd.to_datetime(df["approved_date"], errors="coerce").dt.year  # year of approval
df["country"] = df["country"].astype(str).str.strip().str.upper()  # tidy the 2-letter country code

pd.set_option("display.width", 250)  # wider print so tables do not wrap
print(f"FDA rows                : {len(df):,}")  # should be 47,375
print(f"Years covered           : {int(df['year'].min())} to {int(df['year'].max())}")  # should be 2010 to 2026
print(f"Repeated device_id      : {df['device_id'].duplicated().sum():,}")  # information only
print("Top 8 country codes     :", df["country"].value_counts().head(8).to_dict())  # confirm how India is spelled

ind = df[df["country"] == "IN"].copy()  # keep only Indian applicants
if ind.empty:  # if no row has the code IN
    print("STOP - no rows with country = IN. Check the country codes printed above.")  # tell the user
    sys.exit(1)  # stop here
print(f"Indian rows (country=IN): {len(ind):,}  ({len(ind) / len(df) * 100:.1f}% of all FDA rows)")  # size of the Indian group

# ---------------- by year ----------------
all_y = df.groupby("year").size().rename("all_clearances")  # all clearances per year
in_y = ind.groupby("year").size().rename("indian_clearances")  # Indian clearances per year
by_year = pd.concat([in_y, all_y], axis=1).fillna(0).astype(int).reset_index()  # one table, missing years = 0
by_year["indian_share_pct"] = (by_year["indian_clearances"] / by_year["all_clearances"] * 100).round(2)  # Indian % of all
by_year["partial_year"] = by_year["year"] == by_year["year"].max()  # last year is partial (data ends 19 Sep 2026)
by_year["year"] = by_year["year"].astype(int)  # make the year a whole number
by_year.to_csv(OUT / "obj11_indian_by_year.csv", index=False, encoding="utf-8-sig")  # save to file

# ---------------- by category ----------------
cat_in = ind.groupby("category").size().rename("indian_clearances")  # Indian clearances per category
cat_all = df.groupby("category").size().rename("all_clearances")  # all clearances per category
by_cat = pd.concat([cat_in, cat_all], axis=1).fillna(0).astype(int)  # one table
by_cat["share_of_indian_pct"] = (by_cat["indian_clearances"] / by_cat["indian_clearances"].sum() * 100).round(1)  # category's % of Indian total
by_cat["indian_share_in_category_pct"] = (by_cat["indian_clearances"] / by_cat["all_clearances"] * 100).round(2)  # Indian % inside the category
by_cat = by_cat.sort_values("indian_clearances", ascending=False).reset_index()  # biggest first
by_cat.to_csv(OUT / "obj11_indian_by_category.csv", index=False, encoding="utf-8-sig")  # save to file

cat_year = ind.pivot_table(index="category", columns="year", values="device_id", aggfunc="count", fill_value=0)  # category x year
cat_year.columns = [int(c) for c in cat_year.columns]  # whole-number year headers
cat_year["total"] = cat_year.sum(axis=1)  # total per category
cat_year = cat_year.sort_values("total", ascending=False)  # biggest first
cat_year.to_csv(OUT / "obj11_indian_category_by_year.csv", encoding="utf-8-sig")  # save to file

# ---------------- top Indian companies ----------------
def clean_name(n):  # makes company names comparable
    s = re.sub(r"[^a-z0-9 ]", " ", str(n).lower().replace("&", " and "))  # lower case, drop symbols
    s = re.sub(r"\s+", " ", s).strip()  # squeeze spaces
    s = re.sub(r"\b(private limited|private ltd|pvt limited)\b", "pvt ltd", s)  # unify Pvt Ltd spellings
    return re.sub(r"\blimited\b", "ltd", s)  # limited -> ltd

ind["company_key"] = ind["company_name"].apply(clean_name)  # tidy key used only for grouping
show = ind.groupby("company_key")["company_name"].agg(lambda x: x.mode().iloc[0])  # most common spelling
comp = ind.groupby("company_key").agg(clearances=("device_id", "size"), categories_covered=("category", "nunique"),
                                      first_year=("year", "min"), last_year=("year", "max")).reset_index()  # per company
comp["company"] = comp["company_key"].map(show)  # readable name
comp = comp.sort_values("clearances", ascending=False).head(15)[["company", "clearances", "categories_covered", "first_year", "last_year"]]  # top 15
comp.to_csv(OUT / "obj11_top_indian_companies.csv", index=False, encoding="utf-8-sig")  # save to file

# ---------------- approval days ----------------
def days_row(name, g):  # summary line for one group
    d = pd.to_numeric(g["approval_days"], errors="coerce").dropna()  # keep real numbers only
    return {"group": name, "rows": len(d), "median_days": d.median(), "mean_days": round(d.mean(), 1)}  # summary
days = pd.DataFrame([days_row("Indian applicants", ind), days_row("All applicants", df),
                     days_row("Non-Indian applicants", df[df["country"] != "IN"])])  # three groups
days.to_csv(OUT / "obj11_approval_days.csv", index=False, encoding="utf-8-sig")  # save to file

# ---------------- checks printed on screen ----------------
print("\n=== INDIAN CLEARANCES BY YEAR (last year is partial) ===")  # heading
print(by_year.to_string(index=False))  # yearly table
print(f"\nSum of yearly Indian clearances: {by_year['indian_clearances'].sum():,}  (should equal Indian rows)")  # consistency check
print("\n=== BY CATEGORY ===")  # heading
print(by_cat.to_string(index=False))  # category table
print(f"\nSum of category Indian clearances: {by_cat['indian_clearances'].sum():,}  (should equal Indian rows)")  # consistency check
print("\n=== TOP 15 INDIAN APPLICANTS ===")  # heading
print(comp.to_string(index=False))  # company table
print("\n=== APPROVAL DAYS ===")  # heading
print(days.to_string(index=False))  # days table
print("\nSaved 5 files in Output/")  # done message