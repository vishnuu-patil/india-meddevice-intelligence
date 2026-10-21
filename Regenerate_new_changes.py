# ============================================================
# Regenerate cdsco_category_changes.csv from two files that exist
# Folder : <project folder>\
# Run    : python regenerate_changes.py
# Reads  : Output/_audit/cdsco_categorized_backup.csv
#          Output/cdsco_final.csv
# Writes : Output/_audit/cdsco_category_changes_recovered.csv
# ============================================================

from pathlib import Path
import pandas as pd

BASE = Path(__file__).resolve().parent
AUDIT = BASE / "Output" / "_audit"
OUT_FILE = BASE / "Output" / "cdsco_final.csv"
BACKUP_FILE = AUDIT / "cdsco_categorized_backup.csv"
RECOVERED = AUDIT / "cdsco_category_changes_recovered.csv"

print("Looking for:")
print("  backup:", BACKUP_FILE)
print("  final :", OUT_FILE)
print()

if not BACKUP_FILE.exists():
    raise SystemExit(f"Missing backup: {BACKUP_FILE}")
if not OUT_FILE.exists():
    raise SystemExit(f"Missing final:  {OUT_FILE}")

backup = pd.read_csv(BACKUP_FILE, low_memory=False)
final = pd.read_csv(OUT_FILE, low_memory=False)

print(f"Backup rows:  {len(backup)}")
print(f"Final rows:   {len(final)}")
print()

# Drop Other rows from backup so row counts align
backup_no_other = backup[backup['category'] != 'Other'].reset_index(drop=True)
final_reset = final.reset_index(drop=True)

print(f"Backup (no Other): {len(backup_no_other)}")
print(f"Final:             {len(final_reset)}")
print()

if len(backup_no_other) != len(final_reset):
    raise SystemExit(
        f"Row mismatch: backup_no_other={len(backup_no_other)}, final={len(final_reset)}\n"
        "Cannot align rows. Check that cdsco_final.csv was generated from this backup."
    )

changed = backup_no_other['category'] != final_reset['category']
print(f"Rows whose category changed: {changed.sum()}")

changes_df = pd.DataFrame({
    'device_name': final_reset.loc[changed, 'device_name'].values,
    'old_category': backup_no_other.loc[changed, 'category'].values,
    'new_category': final_reset.loc[changed, 'category'].values,
    'new_method': final_reset.loc[changed, 'category_method'].values,
    'new_confidence': final_reset.loc[changed, 'category_confidence'].values,
    'license_no': final_reset.loc[changed, 'license_no'].values,
})

changes_df.to_csv(RECOVERED, index=False)
print()
print(f"Saved: {RECOVERED}")
print(f"Rows written: {len(changes_df)}")