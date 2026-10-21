from pathlib import Path
import pandas as pd

BASE = Path(__file__).resolve().parent
SRC = BASE / "Output" / "fda_final_v2.csv"
OUT = BASE / "Output" / "validation_fda_v2.csv"

df = pd.read_csv(SRC, low_memory=False)

# Same method as v1: 20 per category, weighted extra on the worst v1 categories
worst_v1 = ["Cardiac & Vascular", "Surgical & Endoscopy", "Neuro", "Diagnostics: IVD & Lab"]
parts = []
for cat in df['category'].dropna().unique():
    n = 20 + (10 if cat in worst_v1 else 0)  # 20 base, 30 for worst 4
    sub = df[df['category'] == cat]
    n = min(n, len(sub))
    parts.append(sub.sample(n=n, random_state=99))  # different seed from v1

out = pd.concat(parts, ignore_index=True)
out = out[['device_id', 'device_name', 'category_raw',
           'category', 'category_method', 'category_confidence']].copy()
out['correct'] = ''
out['should_be'] = ''

out.to_csv(OUT, index=False)
print(f"Sampled {len(out)} rows -> {OUT}")
print()
print(out['category'].value_counts().to_string())