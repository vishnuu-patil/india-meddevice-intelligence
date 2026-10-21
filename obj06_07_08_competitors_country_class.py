# ============================================================
# Objectives 06 + 07 + 08 - Competitors, country of manufacture, device class
# Folder : <project folder>\  (project root)
# Run    : python obj06_07_08_competitors_country_class.py
# Input  : Output/cdsco_final.csv
# Output : Output/obj06_top_importers_by_category.csv
#          Output/obj06_category_concentration.csv
#          Output/obj06_top_importers_overall.csv
#          Output/obj07_country_totals.csv
#          Output/obj07_country_by_category.csv
#          Output/obj07_top_country_per_category.csv
#          Output/obj08_class_overall.csv
#          Output/obj08_class_by_category.csv
#          Output/obj08_class_by_year.csv
# ============================================================
import re  # tool for finding and replacing text patterns
from pathlib import Path  # tool to work with folder paths
import pandas as pd  # tool to work with tables

BASE = Path(__file__).resolve().parent  # project folder = the folder this script sits in
IN_FILE = BASE / "Output" / "cdsco_final.csv"  # the cleaned CDSCO file we read
OUT = BASE / "Output"  # folder where we save results
Y0, Y1 = 2018, 2026  # first and last year we look at

df = pd.read_csv(IN_FILE, low_memory=False)  # load the CDSCO file into a table
df = df[df["license_year"].between(Y0, Y1)].copy()  # keep only 2018 to 2026 rows

pd.set_option("display.width", 250)  # wider print so tables do not wrap
pd.set_option("display.max_columns", 30)  # allow many columns on screen


# ---------------- helper: make company names comparable ----------------
def clean_name(name):  # takes one importer name and returns a tidy version
    if pd.isna(name):  # if the name is empty
        return "unknown"  # call it unknown
    s = str(name).lower()  # make everything small letters
    s = s.replace("&", " and ")  # change & into the word and
    s = re.sub(r"[^a-z0-9 ]", " ", s)  # remove dots, commas and other symbols
    s = re.sub(r"\s+", " ", s).strip()  # squeeze many spaces into one and trim the ends
    s = re.sub(r"\bprivate limited\b", "pvt ltd", s)  # private limited -> pvt ltd
    s = re.sub(r"\bprivate ltd\b", "pvt ltd", s)  # private ltd -> pvt ltd
    s = re.sub(r"\bpvt limited\b", "pvt ltd", s)  # pvt limited -> pvt ltd
    s = re.sub(r"\blimited\b", "ltd", s)  # limited -> ltd
    return s  # give back the tidy name


# ---------------- OBJECTIVE 06: competitor landscape ----------------
pairs = df.drop_duplicates(["license_no", "category"]).copy()  # one row per unique (licence, category) pair
pairs["importer_key"] = pairs["importer_name"].apply(clean_name)  # tidy name used only for grouping

# the most common original spelling of each tidy name, used for display
show_name = pairs.groupby("importer_key")["importer_name"].agg(
    lambda x: x.mode().iloc[0] if not x.mode().empty else "")  # pick the spelling that appears most

by_cat = (pairs.groupby(["category", "importer_key"]).size()
          .rename("licences").reset_index())  # licences per importer inside each category
cat_total = pairs.groupby("category").size().rename("category_total")  # total licences in each category
by_cat = by_cat.merge(cat_total, on="category")  # attach the category total to every row
by_cat["share_pct"] = (by_cat["licences"] / by_cat["category_total"] * 100).round(1)  # importer's % of its category
by_cat["importer_name"] = by_cat["importer_key"].map(show_name)  # add the readable company name
by_cat = by_cat.sort_values(["category", "licences", "importer_key"],
                            ascending=[True, False, True])  # biggest importer first inside each category
by_cat["rank_in_category"] = by_cat.groupby("category").cumcount() + 1  # rank 1, 2, 3 inside each category

top3 = by_cat[by_cat["rank_in_category"] <= 3][
    ["category", "rank_in_category", "importer_name", "licences", "category_total", "share_pct"]]  # keep top 3 per category
top3.to_csv(OUT / "obj06_top_importers_by_category.csv", index=False, encoding="utf-8-sig")  # save to file

conc = (top3.groupby("category")
        .agg(top3_licences=("licences", "sum"), category_total=("category_total", "first"))
        .reset_index())  # add up the top 3 in each category
conc["top3_share_pct"] = (conc["top3_licences"] / conc["category_total"] * 100).round(1)  # how much the top 3 hold together
conc = conc.sort_values("top3_share_pct", ascending=False)  # most concentrated category first
conc.to_csv(OUT / "obj06_category_concentration.csv", index=False, encoding="utf-8-sig")  # save to file

overall = (pairs.groupby("importer_key")
           .agg(licence_category_pairs=("license_no", "size"),
                unique_licences=("license_no", "nunique"),
                categories_covered=("category", "nunique"))
           .reset_index())  # per importer: pairs, unique licences, number of categories
overall["importer_name"] = overall["importer_key"].map(show_name)  # add the readable company name
overall = overall.sort_values("licence_category_pairs", ascending=False).head(15)  # keep the top 15
overall = overall[["importer_name", "licence_category_pairs", "unique_licences", "categories_covered"]]  # tidy column order
overall.to_csv(OUT / "obj06_top_importers_overall.csv", index=False, encoding="utf-8-sig")  # save to file

# ---------------- OBJECTIVE 07: country of manufacture ----------------
c = df.copy()  # work on a copy so the original table stays untouched
c["mfr_country"] = c["mfr_country"].fillna("Unknown").astype(str).str.strip()  # empty country -> Unknown
cp = c.drop_duplicates(["license_no", "category", "mfr_country"])  # one row per unique (licence, category, country)

country_total = (cp.groupby("mfr_country").size().rename("licence_category_pairs")
                 .sort_values(ascending=False).reset_index())  # pairs per country, biggest first
country_total["share_pct"] = (country_total["licence_category_pairs"]
                              / country_total["licence_category_pairs"].sum() * 100).round(1)  # country's % of all
country_total.to_csv(OUT / "obj07_country_totals.csv", index=False, encoding="utf-8-sig")  # save to file

cmat = cp.pivot_table(index="category", columns="mfr_country", values="license_no",
                      aggfunc="count", fill_value=0)  # category rows x country columns
cmat = cmat[country_total["mfr_country"]]  # order the columns biggest country first
cmat.to_csv(OUT / "obj07_country_by_category.csv", encoding="utf-8-sig")  # save to file

cshare = cmat.div(cmat.sum(axis=1), axis=0) * 100  # each country's % inside its category
top_country = pd.DataFrame({
    "top_country": cmat.idxmax(axis=1),  # country with the most pairs in the category
    "top_country_share_pct": cshare.max(axis=1).round(1),  # its % share
    "china_share_pct": (cshare["China"].round(1) if "China" in cshare.columns else float("nan")),  # China's % if China exists
})  # small summary table per category
top_country = top_country.sort_values("top_country_share_pct", ascending=False)  # most dependent category first
top_country.to_csv(OUT / "obj07_top_country_per_category.csv", encoding="utf-8-sig")  # save to file

# ---------------- OBJECTIVE 08: device class ----------------
dp = df.drop_duplicates(["license_no", "category", "device_class"])  # one row per unique (licence, category, class)

cls_overall = dp.groupby("device_class").size().rename("licence_category_pairs").reset_index()  # pairs per class
cls_overall["share_pct"] = (cls_overall["licence_category_pairs"]
                            / cls_overall["licence_category_pairs"].sum() * 100).round(1)  # class's % of all
cls_overall.to_csv(OUT / "obj08_class_overall.csv", index=False, encoding="utf-8-sig")  # save to file

cls_cat = dp.pivot_table(index="category", columns="device_class", values="license_no",
                         aggfunc="count", fill_value=0)  # category rows x class columns
high_cols = [x for x in cls_cat.columns if x in ("C", "D")]  # the high-risk class columns that exist
cls_cat["high_risk_pct"] = (cls_cat[high_cols].sum(axis=1) / cls_cat.sum(axis=1) * 100).round(1)  # % that is class C or D
cls_cat = cls_cat.sort_values("high_risk_pct", ascending=False)  # riskiest category first
cls_cat.to_csv(OUT / "obj08_class_by_category.csv", encoding="utf-8-sig")  # save to file

cls_year = dp.pivot_table(index="license_year", columns="device_class", values="license_no",
                          aggfunc="count", fill_value=0)  # year rows x class columns
cls_year["high_risk_pct"] = (cls_year[high_cols].sum(axis=1) / cls_year.sum(axis=1) * 100).round(1)  # % C or D per year
cls_year.to_csv(OUT / "obj08_class_by_year.csv", encoding="utf-8-sig")  # save to file

# ---------------- checks printed on screen ----------------
print(f"Unique licences        : {pairs['license_no'].nunique():,}")  # should be 5,163
print(f"Licence-category pairs : {len(pairs):,}")  # should be 6,714
print(f"Importer names before clean-up: {pairs['importer_name'].nunique():,}")  # raw spellings
print(f"Importer names after clean-up : {pairs['importer_key'].nunique():,}")  # after merging spelling variants

print("\n=== OBJ 06: TOP 3 IMPORTERS PER CATEGORY ===")  # heading
print(top3.to_string(index=False))  # show the top 3 table
print("\n=== OBJ 06: HOW CONCENTRATED IS EACH CATEGORY (top 3 share) ===")  # heading
print(conc[["category", "top3_licences", "category_total", "top3_share_pct"]].to_string(index=False))  # show concentration
print("\n=== OBJ 06: TOP 15 IMPORTERS OVERALL ===")  # heading
print(overall.to_string(index=False))  # show overall leaders

print("\n=== OBJ 07: TOP 10 COUNTRIES OF MANUFACTURE ===")  # heading
print(country_total.head(10).to_string(index=False))  # show the biggest countries
print(f"Unknown country pairs: {int((country_total.set_index('mfr_country')['licence_category_pairs']).get('Unknown', 0)):,}")  # how many have no country
print("\n=== OBJ 07: TOP COUNTRY PER CATEGORY ===")  # heading
print(top_country.to_string())  # show top country per category

print("\n=== OBJ 08: DEVICE CLASS OVERALL ===")  # heading
print(cls_overall.to_string(index=False))  # show A/B/C/D split
print("\n=== OBJ 08: CLASS BY CATEGORY (riskiest first) ===")  # heading
print(cls_cat.to_string())  # show class mix per category
print("\n=== OBJ 08: CLASS BY YEAR (2026 is partial) ===")  # heading
print(cls_year.to_string())  # show class mix per year

print("\nSaved 9 files in Output/")  # done message