# ============================================================
# rebuild_backup.py - recreates Output/cdsco_categorized_backup.csv (the OLD categories)
# Folder : <project folder>\
# Run    : python rebuild_backup.py
# It uses the ORIGINAL (pre-validation) rules from the old categories.py on
# Output/cdsco_clean.csv. It writes ONLY the backup file - cdsco_categorized.csv and
# category_review_other.csv are not touched.
# ============================================================
import re
from pathlib import Path
import pandas as pd

import sys
BASE = Path(__file__).resolve().parent
if len(sys.argv) > 1:               # optional override for testing
    BASE = Path(sys.argv[1])
RAW = BASE / "Output" / "cdsco_clean.csv"
OUT = BASE / "Output" / "cdsco_categorized_backup.csv"     # only the backup is written
CURRENT = BASE / "Output" / "cdsco_categorized.csv"          # read-only, used for the check

df = pd.read_csv(RAW)
name = df["device_name"].fillna("").str.lower()
use = df["intended_use"].fillna("").str.lower()

# ---------------------------------------------------------------
# LAYER 1: rules on DEVICE NAME. Checked top to bottom, FIRST MATCH WINS.
# Specific categories sit above generic ones, so a coronary catheter is
# caught by Cardiac before it can reach the generic catheter bucket.
# ---------------------------------------------------------------
NAME_RULES = [
    ("Other", r"radiotherap|accelerator|brachytherap|compression stocking|disinfect|steriliz|sterilant|biological indicator|autoclave|patient positioning"),
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
# LAYER 2: name matched nothing -> check INTENDED USE (narrow, safe rules)
# ---------------------------------------------------------------
USE_RULES = [
    ("Dialysis & Renal", r"dialysis|haemodialysis|hemodialysis"),
    ("Gastro / GI", r"gastro|biliary|colon|esophag|oesophag|bowel"),
    ("Urology", r"urinary|ureter|urethra|bladder|prostat"),
    ("Critical Care & Respiratory", r"epidural|nerve block|plexus|spinal anaesthesia|spinal anesthesia|pain relief|on-q"),
    ("Neuro", r"neurovascular|intracranial|cerebral|stroke|epilep|parkinson|neurostim"),
    ("Cardiac & Vascular", r"coronary|cardiac|heart|vascular|angioplast|ablation|pacing|cardio|stent|valve|aneurysm"),
    ("Ophthalmic", r"ophthalm|cataract|retina|eye surg|intraocular"),
    ("Dental", r"dental|tooth|teeth|oral implant"),
]

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


cats, sources = [], []
for n, u in zip(name, use):
    cat, src = first_match(NAME_RULES, n), "1_name"
    if cat is None and re.search(CLEAR_GENERIC, n):
        cat, src = "Needles, Syringes & Catheters (general)", "3_name_generic"
    if cat is None:
        cat, src = first_match(USE_RULES, u), "2_use_narrow"
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

# ---------------- save + check ----------------
df.to_csv(OUT, index=False)
print("Rebuilt the OLD categorisation (original rules) ->", OUT)
print("Rows:", len(df), "| Other:", int((df["category"] == "Other").sum()))
if CURRENT.exists():
    cur = pd.read_csv(CURRENT, low_memory=False)
    if len(cur) == len(df):
        print("Rows differing from the current cdsco_categorized.csv:", int((cur["category"] != df["category"]).sum()), "(expected 715)")
        print("Other rows identical in both files:", bool(((cur["category"] == "Other") == (df["category"] == "Other")).all()))