import re
from pathlib import Path
import pandas as pd

BASE = Path(__file__).resolve().parent
RAW = BASE / "Data" / "MD - Medical Devices.xlsx"
OUT = BASE / "Output" / "cdsco_clean.csv"
OUT.parent.mkdir(parents=True, exist_ok=True)

# 1. load (row 0 is a title, real headers are on row 1)
df = pd.read_excel(RAW, header=1)
print("Rows loaded:", len(df))

# 2. rename
df = df.rename(columns={
    "Importer Name and address": "importer_raw",
    "License Number": "license_raw",
    "Name of Device": "device_name",
    "Device Class": "device_class",
    "Intended Use": "intended_use",
    "Brand Name": "brand_name",
    "Model Numbers": "model_numbers",
    "Address": "mfr_address_raw",
})

# 3. drop useless columns
print("'Intended' same as 'Intended Use':", (df["Intended"] == df["intended_use"]).mean())
df = df.drop(columns=["S No.", "Issuing Authority", "Action", "Intended"])

# 4. trim whitespace on every text column
for c in df.select_dtypes(include=["object", "string"]).columns:
    df[c] = df[c].str.strip()

# 5. licence number, licence year, issue date, issue year
df["license_no"] = df["license_raw"].str.extract(r"(IMP/MD/\d{4}/\d+)")[0]
df["license_year"] = df["license_raw"].str.extract(r"IMP/MD/(\d{4})/")[0].astype("Int64")
df["issue_date"] = pd.to_datetime(
    df["license_raw"].str.extract(r"Issued on:\s*(\d{2}-[A-Za-z]{3}-\d{4})")[0],
    format="%d-%b-%Y", errors="coerce")
df["issue_year"] = df["issue_date"].dt.year.astype("Int64")

# 6. importer: pincode, state, name
df["importer_pincode"] = df["importer_raw"].str.extract(r"Pincode:\s*(\d{6})")[0]
df["importer_state"] = df["importer_raw"].str.extract(r",\s*([^,]+?)\s*Pincode:")[0].str.strip()
df["is_telangana"] = df["importer_state"].str.lower().eq("telangana")
df["is_hyderabad"] = df["importer_raw"].str.contains(r"hyderabad|secunderabad", case=False, na=False)

suffix = r"^(.*?\b(?:private limited|pvt\.? ?ltd\.?|limited|ltd\.?|llp|inc\.?|corporation|corp\.?))\b"
df["importer_name"] = df["importer_raw"].str.extract(suffix, flags=re.IGNORECASE)[0]
fallback = df["importer_raw"].str.split(r"\s\d|,", n=1, regex=True).str[0]
df["importer_name"] = df["importer_name"].fillna(fallback)
df["importer_name"] = (df["importer_name"]
    .str.replace(r"^m/s\.?\s*", "", regex=True, flags=re.IGNORECASE)
    .str.replace(r"\s+", " ", regex=True)
    .str.strip().str.title())

# 7. manufacturer country (Actual site first, Legal site as fallback)
act = df["mfr_address_raw"].str.extract(r"Actual Manufacturing Site.*?Country:\s*([^\n]+)", flags=re.DOTALL)[0]
leg = df["mfr_address_raw"].str.extract(r"Legal Manufacturing Site.*?Country:\s*([^\n]+)", flags=re.DOTALL)[0]
df["mfr_country"] = act.fillna(leg).str.strip()

# 8. device class standardise
df["device_class"] = df["device_class"].str.title().str.strip()
df["class_letter"] = df["device_class"].str[-1]

# 9. duplicates
before = len(df)
df = df.drop_duplicates(subset=["license_raw", "device_name", "device_class", "brand_name",
                                "model_numbers", "mfr_address_raw"])
print("Duplicates removed:", before - len(df))

# checks
print("Rows now:", len(df))
print(df[["license_no", "license_year", "issue_date", "importer_state", "importer_name", "mfr_country"]].isna().sum())
print("license_year != issue_year:", (df["license_year"] != df["issue_year"]).sum())
print(df["importer_state"].value_counts().head(8))
print(df["importer_name"].value_counts().head(10))

df.to_csv(OUT, index=False)
print("Saved ->", OUT)