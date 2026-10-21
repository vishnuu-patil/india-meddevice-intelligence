from pathlib import Path
import pandas as pd

BASE = Path(__file__).resolve().parent
RAW = BASE / "Data" / "fda_510k.csv"
OUT = BASE / "Output" / "fda_510k_with_days.csv"
OUT.parent.mkdir(parents=True, exist_ok=True)

df = pd.read_csv(RAW)
print("Rows loaded:", len(df))

# 1. dates -> real datetime
df["decision_date"] = pd.to_datetime(df["decision_date"], errors="coerce")
df["date_received"] = pd.to_datetime(df["date_received"], errors="coerce")

# 2. approval days
df["approval_days"] = (df["decision_date"] - df["date_received"]).dt.days

# 3. year columns for later grouping
df["decision_year"] = df["decision_date"].dt.year
df["received_year"] = df["date_received"].dt.year

# 4. flag (not delete) extreme reviews
df["long_review_flag"] = df["approval_days"] > 1000

# checks
print("Bad dates:", df[["decision_date", "date_received"]].isna().sum().to_dict())
print("Negative days:", (df["approval_days"] < 0).sum())
print(df["approval_days"].describe().round(1))
print("Flagged >1000 days:", df["long_review_flag"].sum())

df.to_csv(OUT, index=False)
print("Saved ->", OUT)