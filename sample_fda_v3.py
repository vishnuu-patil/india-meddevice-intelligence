# ============================================================
# Draw a fresh random sample from fda_final_v3.csv for validation
# Folder : <project folder>\
# Run    : python sample_fda_v3.py
# Reads  : Output/fda_final_v3.csv
# Writes : Output/validation_fda_v3.csv
# ============================================================

from pathlib import Path
import pandas as pd

BASE = Path(__file__).resolve().parent
SRC = BASE / "Output" / "fda_final_v3.csv"
OUT = BASE / "Output" / "validation_fda_v3.csv"

df = pd.read_csv(SRC, low_memory=False)

# Weight toward categories that had errors in v2:
# Neuro, Needles, Urology, Aesthetics, Cardiac
weighted = ["Neuro", "Needles, Syringes & Catheters (general)",
            "Urology", "Aesthetics & Dermatology", "Cardiac & Vascular"]

parts = []
for cat in df['category'].dropna().unique():
    n = 20 + (15 if cat in weighted else 0)   # 20 base, 35 for weighted
    sub = df[df['category'] == cat]
    n = min(n, len(sub))
    parts.append(sub.sample(n=n, random_state=777))   # new seed

out = pd.concat(parts, ignore_index=True)
out = out[['device_id', 'device_name', 'category_raw',
           'category', 'category_method', 'category_confidence']].copy()
out['correct'] = ''
out['should_be'] = ''

out.to_csv(OUT, index=False)
print(f"Sampled {len(out)} rows -> {OUT}")
print()
print(out['category'].value_counts().to_string())