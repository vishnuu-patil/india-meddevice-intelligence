# ============================================================
# Script 03a (v2) - CDSCO category mapping, after manual validation
# Folder : <project folder>\
# Run    : python categories.py
# Input  : Output/cdsco_clean.csv
# Output : Output/cdsco_categorized.csv        (same columns as before)
#          Output/category_review_other.csv    (same as before)
#          Output/cdsco_category_changes.csv   (NEW: every row whose category changed)
#          Output/cdsco_categorized_backup.csv (NEW: copy of the OLD file, made once)
#
# WHAT CHANGED FROM v1 (all come from the manual validation of 380 rows)
#   1. New name rules at the top: airway/respiratory items, central venous catheters,
#      peripheral artery stents, skin grafting, navigation systems.
#   2. NEW STEP "intended-use override": when the NAME points to one category but the
#      INTENDED USE clearly says another (hyaluronic acid for eyes/joints/IVF, dental
#      lasers, endoscope valves, microkeratome blades ...), the intended use wins.
#   3. Intended-use rules reordered and extended (PTA balloon catheters were landing in
#      Dialysis, microcatheters/pulse generators in Neuro, etc.).
#
# ROW FREEZE (so no "unnecessary" rows come back)
#   Rows that were "Other" in the OLD file stay "Other". A row that was categorised
#   before never becomes "Other". So cdsco_final.csv will keep exactly the same rows
#   (24,563) - only categories move between the 18 real categories.
# ============================================================
import re
import shutil
import sys
from pathlib import Path
import pandas as pd

BASE = Path(__file__).resolve().parent
if len(sys.argv) > 1:               # optional override for testing
    BASE = Path(sys.argv[1])

RAW = BASE / "Output" / "cdsco_clean.csv"
OUT = BASE / "Output" / "cdsco_categorized.csv"
BACKUP = BASE / "Output" / "cdsco_categorized_backup.csv"
REVIEW = BASE / "Output" / "category_review_other.csv"
CHANGES = BASE / "Output" / "cdsco_category_changes.csv"

# ---- keep a copy of the OLD file (only the first time; never overwritten) ----
if not BACKUP.exists():
    if not OUT.exists():
        sys.exit("No existing cdsco_categorized.csv to back up. Cannot freeze rows safely.")
    shutil.copy(OUT, BACKUP)
    print("Backup of the old file saved ->", BACKUP)
old = pd.read_csv(BACKUP, low_memory=False)

df = pd.read_csv(RAW)
assert len(df) == len(old), "cdsco_clean.csv and the backup have different row counts"
name = df["device_name"].fillna("").str.lower()
use = df["intended_use"].fillna("").str.lower()

# ---------------------------------------------------------------
# LAYER 1: rules on DEVICE NAME. Checked top to bottom, FIRST MATCH WINS.
# ---------------------------------------------------------------
NAME_RULES = [
    ("Other", r"radiotherap|accelerator|brachytherap|compression stocking|disinfect|steriliz|sterilant|biological indicator|autoclave|patient positioning"),
    # --- NEW (validation fixes) ---
    ("Neuro", r"navigation accessory"),
    ("Surgical & Endoscopy", r"skin graft|dermatome"),
    ("Cardiac & Vascular", r"(iliac|peripheral|carotid|femoral|renal|coronary)\s+(artery\s+)?stent|artery stent|arterial stent|(?<!neuro)vascular stent"),
    ("Critical Care & Respiratory", r"bronchial stent|tracheal stent|tracheobronchial|airway stent|catheter mount|breathing circuit|breathing system|tracheostom|speaking valve|exhalation valve|central venous|\bcvc\b"),
    # --- unchanged from v1 ---
    ("ENT & Hearing", r"hearing|cochlear|auditory|bionic ear|sound processor|tympan|sinus|\bent\b|tonsil|adenoid|tinnitus|otoscope|audiometer|\bear (tube|canal|wick|syring)|grommet|myringo|nasal packing|nasal splint|septoplast|turbinate"),
    ("Blood & Transfusion", r"blood component|transfusion|apheresis|leukocyte|leucocyte|platelet|blood bag|cell separator|autotransfusion|cell saver|cell processor|blood filter|blood warmer|autologous plasma|plasma (bag|separator|collection|freezing)|plasmapheresis"),
    ("IVF & Women's Health", r"in vitro fertili|\bivf\b|embryo|oocyte|sperm|intrauterine|\biud\b|uterine|vaginal|pessary|obstetric|contracepti|condom|gynae|gyne|colposcop|hysteroscop|fertili|follicle|culture medi|fetal|foetal|amnio|breast pump"),
    ("Ophthalmic", r"intraocular|\biol\b|contact lens|ophthalm|retina|retinal|cornea|vitrect|phaco|glaucoma|\beye|ocular|viscoelastic|slit-lamp|slit lamp|fundus|biometer|intracorneal"),
    ("Dental", r"dental|abutment|orthodont|endodont|tooth|teeth|periodont|bracket|denture|root canal|\bcrown\b|gingiv|prosthodon|porcelain|veneer|impression material|restorative|gutta percha|aligner|apex locator|ceramic ingot|glass ceramic|healing cap"),
    ("Aesthetics & Dermatology", r"dermal filler|lip filler|facial filler|soft tissue filler|\baesthetic|cosmetic|derma|botulinum|hyaluron|breast implant|facial implant|tissue expander|wrinkle|liposuction|hair removal|skin rejuvenation|cellulite"),
    ("Critical Care & Respiratory", r"epidural|nerve block|plexus|spinal anaesthesia|spinal anesthesia|pain relief|on-q"),
    ("Neuro", r"(?<!non-)neuro|brain|cerebr|\beeg\b|\bdura\b|\bdural\b|stereotactic|epilep|stimulator|\bdbs\b|deep brain|spinal cord|nerve|hydrocephalus|\bcsf\b|ventriculoperitoneal|lumboperitoneal|programmable shunt|shunt valve|shunt sensor"),
    ("Gastro / GI", r"gastr|colon|biliary|\bbile\b|esophag|oesophag|\bercp\b|sphincterotom|\bpolyps?\b|polypectomy|duoden|\bgi\b|bowel|rectal|hemorrhoid|haemorrhoid|enteral|feeding tube|freka|stomach|pancrea|\bstoma\b|colostomy|ileostomy|\bostomy|endoscopic stent|bariatric|gastric"),
    ("Urology", r"urolog|ureter|urethr|bladder|prostat|(?<!intravascular )lithotrip|stone basket|kidney stone|stone extractor|foley|urinary|urine (bag|collection|drainage|meter)|nephroscop|nephrostomy|cystoscop|resectoscop|incontinence|penile|erectile|urodynamic"),
    ("Dialysis & Renal", r"dialy|haemodial|hemodial|bloodline|hemoperfusion|haemoperfusion|renal|kidney|fistula|haemofilter|hemofilter"),
    ("Cardiac & Vascular", r"stent|coronary|cardiac|cardio|heart|pacemaker|pacing|mapping|defibrillat|electrophysiolog|angioplast|valve|aort|vascular|ablation|\bptca\b|\bpta\b|\bptv\b|\bcrt\b|atrial|ventric|embol|thrombect|occlu|endovascular|aneurysm|oxygenator|ecmo|graft|vena cava|arterial|artery|guiding catheter|guidewire|guide wire|intra-aortic|\becg\b|electrocardio|holter|\bcv catheter|pericard|septal|thromb|pledget|annuloplasty|detachable coil|inflation device"),
    ("Surgical & Endoscopy", r"mesh|hernia"),
    ("Orthopedic & Spine", r"knee|\bhip\b|femoral|tibial|\bbone|screw|spinal|spine|pedicle|orthop|arthro|joint|acetabul|humeral|shoulder|fixation|trauma|anchor|intramedullary|\bnail\b|plates?\b|plating|fracture|vertebr|cement|cartilage|meniscus|meniscal|ligament|tendon|\bcage\b|spacer|prosthesis|ankle|wrist|patella|hallux|osteo|craniomaxillofacial|mandible|midface|lumbar|k-wire|kirschner|\bdrills?\b|tibia|artificial disc|disc replacement|intervertebral|\btrials?\b"),
    ("Wound Care", r"dressing|wound|bandage|plaster|gauze|hydrocolloid|hydrogel|burn|negative pressure|ulcer|\bscar\b|sealant|tape\b|skin closure|tissue adhesive"),
    ("Critical Care & Respiratory", r"ventilat|infusion pump|syringe pump|oxygen|respirat|anaesth|anesth|airway|tracheo|endotracheal|nebuli|cpap|bipap|humidif|incubator|resuscit|suction|oximeter|laryngo|intubat|warmer|apnoea|patient monitor|bedside monitor|multipara|vital sign|\bpump"),
    ("Diagnostics: IVD & Lab", r"reagent|assay|test kit|diagnostic kit|rapid test|analy[sz]er|elisa|\bpcr\b|immuno|quality control|chemistry|control level|calibrator|diluent|glucose|lancet|hba1c|haemoglobin|hemoglobin|coagulation|blood gas|antigen|antibody|serolog|specimen|microplate"),
    ("Diagnostics: Imaging", r"ultrasound|x-ray|xray|radiograph|\bmri\b|\bct\b|tomograph|imaging|monitor|diagnos|sensor|thermometer|sphygmo|blood pressure|stethoscope|spirometer|spectromet|microscop|doppler|mammograph|fluorosc|densitomet|software|detector|scanner|syngo|camera|magnetic resonance|\bmr\b"),
    ("Surgical & Endoscopy", r"surgical|suture|laparoscop|endoscop|scope\b|biopsy|laser|forceps|scalpel|blade|trocar|stapler|staple|retractor|electrosurg|cautery|scissors|clip\b|clips\b|instrument|cutter|clamp|ligat|diathermy|harmonic|knife|dissector|speculum|grasper|hemostat|vessel sealing|tissue sealing|glue|loading unit|shears|handpiece|procedure tray|procedure kit"),
]

# ---------------------------------------------------------------
# NEW STEP - INTENDED-USE OVERRIDE
# The name gave a category, but the first 300 characters of the intended use clearly
# point somewhere else. Each rule: (new category, categories it may replace, use pattern)
# ---------------------------------------------------------------
OVERRIDES = [
    ("Ophthalmic",
     {"Aesthetics & Dermatology", "Surgical & Endoscopy", "Critical Care & Respiratory", "Cardiac & Vascular"},
     r"intraocular|cataract|cornea|lasik|microkeratome|vitrect|eye surgery|ophthalm|anterior segment"),
    ("IVF & Women's Health",
     {"Aesthetics & Dermatology"},
     r"oocyte|\bicsi\b|embryo|cumulus|assisted reproduct"),
    ("Orthopedic & Spine",
     {"Aesthetics & Dermatology", "Surgical & Endoscopy"},
     r"synovial|osteoarthritis|orthopedic|orthopaedic|vertebral|bone cement|spinal fusion|\bspine\b|\bspinal\b"),
    ("Dental",
     {"Surgical & Endoscopy", "Critical Care & Respiratory"},
     r"dental|dentist|dentition|\bteeth\b|\btooth\b|caries"),
    ("Surgical & Endoscopy",
     {"Cardiac & Vascular"},
     r"endoscop|dermatome|skin graft"),
]

# ---------------------------------------------------------------
# LAYER 2: name matched nothing -> check INTENDED USE (narrow, safe rules)
# Order matters: first match wins.
# ---------------------------------------------------------------
USE_RULES = [
    # NEW: strong heart / vessel signals first, so a PTA balloon that only MENTIONS
    # dialysis fistulae, or a pacemaker pulse generator, is not pulled into Dialysis or Neuro
    ("Cardiac & Vascular", r"angioplast|percutaneous transluminal|\bpta\b|\bptca\b|pacemaker|pulse generator|arrhythmia|bradycardia|coronary|peripheral vascul"),
    ("Dialysis & Renal", r"dialysis|haemodialysis|hemodialysis"),
    ("Gastro / GI", r"gastro|biliary|colon|esophag|oesophag|bowel"),
    ("Urology", r"urinary|ureter|urethra|bladder|prostat"),
    # NEW: radiofrequency nerve lesioning (pain management) is Neuro
    ("Neuro", r"lesions? in nervous tissue|neurological lesion|radiofrequency.{0,40}(nerve|neural|lesion)"),
    ("Critical Care & Respiratory", r"epidural|nerve block|plexus|spinal anaesthesia|spinal anesthesia|pain relief|on-q"),
    ("Neuro", r"neurovascular|intracranial|cerebral|stroke|epilep|parkinson|neurostim"),
    ("Cardiac & Vascular", r"coronary|cardiac|heart|vascular|angioplast|ablation|pacing|cardio|stent|valve|aneurysm"),
    ("Ophthalmic", r"ophthalm|cataract|retina|eye surg|intraocular"),
    ("Dental", r"dental|tooth|teeth|oral implant"),
    # NEW
    ("Aesthetics & Dermatology", r"skin lifting|skin tightening|hair (transplant|loss|restor|removal)|wrinkle|cellulite|body contour"),
    ("Surgical & Endoscopy", r"trocar|port of entry|endoscopic (surgery|procedure)|da vinci|laparoscop"),
    ("Diagnostics: Imaging", r"computed radiography|digital radiography|imaging plate|x-ray (system|unit|equipment|detector|sensor)"),
]

# Neuro-vascular devices (coils, neuro stents, neuro microcatheters) must stay Neuro
NEURO_USE_GUARD = r"neurovascul|neuro vascul|intracranial|neuro-vascul"

# ---------------------------------------------------------------
# LAYER 3: generic bucket (only reached if nothing specific matched)
# ---------------------------------------------------------------
CLEAR_GENERIC = r"needle|syringe|cannula|iv set|infusion set|administration set|scalp vein|blood collection|connector|stopcock|vial|pen injector|injector|atomizer|tubing"
GENERIC = r"introducer|access sheath|infuser|perfusion set|infusion system|needle|syringe|catheter|cannula|infusion set|iv set|administration set|scalp vein|blood collection|tube|tubing|connector|stopcock|vial|drain|pen injector|injector|atomizer|applicator|port\b"

# ---------------------------------------------------------------
# LAYER 4: last resort -> run the name rules on the first 200 characters
# of intended use. Less reliable, so it is labelled in category_source.
# ---------------------------------------------------------------
LAST_RESORT = [r for r in NAME_RULES if r[0] not in ("Other", "Neuro", "Gastro / GI", "Urology")]


def first_match(rules, text):
    for cat, rx in rules:
        if re.search(rx, text):
            return cat
    return None


# Specialty words used to stop an override when the intended use lists SEVERAL specialties
# (e.g. a suture "for cardiovascular, ophthalmic and neurological procedures").
SPEC = {
    "ophth": r"intraocular|cataract|cornea|lasik|microkeratome|vitrect|eye surgery|ophthalm|anterior segment|\beye\b",
    "ortho": r"orthopedic|orthopaedic|vertebral|spinal|\bspine\b|osteoarthritis|synovial|arthroplast",
    "dental": r"dental|dentist|dentition|\bteeth\b|\btooth\b|caries|dentistry",
    "cardio": r"cardiovascular|cardiac|coronary|\bheart\b|vascular|vasculature",
    "neuro": r"neurolog|neurosurg|cranial|\bbrain\b",
    "ivf": r"oocyte|\bicsi\b|embryo|cumulus|assisted reproduct|gynecolog",
    "gi": r"gastro|biliary|bowel|\bcolon",
    "uro": r"urolog|urinary|bladder",
    "derm": r"dermatolog|aesthetic",
}
SPEC_KEY = {"Ophthalmic": "ophth", "Orthopedic & Spine": "ortho", "Dental": "dental", "IVF & Women's Health": "ivf"}


DENTAL_BLOCK = r"medical (or|and|/) dental|dental (or|and|/) medical|da vinci|glove"


def use_override(cat, u):
    text = u[:300]
    for new_cat, replaces, rx in OVERRIDES:
        if cat in replaces and cat != new_cat and re.search(rx, text):
            if new_cat == "Dental" and re.search(DENTAL_BLOCK, text):
                continue
            if new_cat in SPEC_KEY:      # only if NO other specialty is mentioned
                if any(re.search(r, text) for k, r in SPEC.items() if k != SPEC_KEY[new_cat]):
                    continue
            elif re.search(SPEC["cardio"], text):   # Surgical override: must not be a heart/vessel use
                continue
            return new_cat
    return None


cats, sources = [], []
for n, u in zip(name, use):
    cat, src = first_match(NAME_RULES, n), "1_name"
    if cat is not None and cat != "Other":                       # NEW: intended-use override
        ov = use_override(cat, u)
        if ov:
            cat, src = ov, "2_use_narrow"
    if cat is None and re.search(CLEAR_GENERIC, n):
        # NEW: a vague generic name (Cannula, Tubing Pack) with a clear use goes by the use
        cat, src = "Needles, Syringes & Catheters (general)", "3_name_generic"
        ov = use_override("Surgical & Endoscopy", u)          # Ophthalmic / Dental / Ortho use wins
        if ov in ("Ophthalmic", "Dental"):
            cat, src = ov, "2_use_narrow"
    if cat is None:
        rules = USE_RULES[1:] if re.search(NEURO_USE_GUARD, u) else USE_RULES   # skip the strong-heart rule for neuro devices
        cat, src = first_match(rules, u), "2_use_narrow"
    if cat is None and re.search(GENERIC, n):
        cat, src = "Needles, Syringes & Catheters (general)", "3_name_generic"
    if cat is None:
        cat, src = first_match(LAST_RESORT, u[:200]), "4_use_broad"
    if cat is None:
        cat, src = "Other", "5_none"
    cats.append(cat)
    sources.append(src)

df["category"] = cats
df["category_source"] = sources

# ---------------------------------------------------------------
# ROW FREEZE: the set of kept rows must not change
# ---------------------------------------------------------------
was_other = (old["category"] == "Other").to_numpy()
new_other = (df["category"] == "Other").to_numpy()
back_to_other = ((~was_other) & new_other)        # rows that would be lost -> keep old answer
came_back = (was_other & (~new_other))            # old junk rows that would return -> keep Other
df.loc[came_back, ["category", "category_source"]] = ["Other", "5_none"]
df.loc[back_to_other, ["category", "category_source"]] = old.loc[back_to_other, ["category", "category_source"]].to_numpy()

# ---------------- checks ----------------
print("Rows:", len(df))
print(df["category"].value_counts())
print("Other %:", round((df["category"] == "Other").mean() * 100, 1))
print(df["category_source"].value_counts().sort_index())
print("\nRow freeze: old junk rows kept as Other :", int(came_back.sum()), "(would have returned)")
print("Row freeze: real rows protected from Other:", int(back_to_other.sum()))
print("Other rows now / before                  :", int((df['category'] == 'Other').sum()), "/", int(was_other.sum()))

changed = (df["category"] != old["category"]).to_numpy()
print("\n=== ROWS WHOSE CATEGORY CHANGED ===")
print("Changed rows:", int(changed.sum()), "of", len(df), f"({changed.mean():.1%})")
moves = (pd.DataFrame({"from": old.loc[changed, "category"], "to": df.loc[changed, "category"]})
         .value_counts().head(15))
print("Biggest moves (from, to):")
print(moves.to_string())
(pd.DataFrame({
    "device_name": df.loc[changed, "device_name"],
    "old_category": old.loc[changed, "category"],
    "new_category": df.loc[changed, "category"],
    "new_source": df.loc[changed, "category_source"],
    "license_no": df.loc[changed, "license_no"],
    "intended_use_start": df.loc[changed, "intended_use"].fillna("").str.slice(0, 150),
}).to_csv(CHANGES, index=False))

# list of unmapped names so you can improve the rules
(df.loc[df["category"] == "Other", "device_name"].str.lower()
   .value_counts().head(300).rename_axis("device_name").reset_index(name="rows")
   .to_csv(REVIEW, index=False))

df.to_csv(OUT, index=False)
print("\nSaved ->", OUT)
print("Review list ->", REVIEW)
print("Change list ->", CHANGES)
