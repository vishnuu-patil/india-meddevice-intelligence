# ============================================================
# Script 05b - FDA final clean file
# Folder : <project folder>\
# Run    : python clean_fda_final.py
# Input  : Output/fda_510k_with_days.csv
# Output : Output/fda_final.csv
#
# HOW A DEVICE GETS ITS CATEGORY (category_method)
#   1 = PANEL      FDA panel has ONE clear meaning (e.g. Orthopedic, Dental,
#                  Radiology) -> category taken straight from the panel.
#   2 = NAME RULE  Panel label COMBINES specialties (Gastroenterology + Urology,
#                  General + Plastic Surgery) -> keywords in the device name,
#                  using a list made for that panel.
#   3 = NAME RULE  Panel is unclear for another reason (General Hospital,
#                  Physical Medicine, Hematology, Unknown) -> device-name
#                  keywords for that panel; also the wide list (all categories)
#                  when a combined panel's own list found nothing.
#   4 = PANEL GUESS  Nothing matched in the name, so we use the panel's most
#                  likely category (only General+Plastic -> Surgical, and
#                  Hematology -> IVD). Weakest layer.
#   5 = NONE       No rule matched -> category "Other" (dropped from final file).
# ============================================================
import re
import sys
from pathlib import Path
import pandas as pd

BASE = Path(__file__).resolve().parent
if len(sys.argv) > 1:               # optional override for testing
    BASE = Path(sys.argv[1])

IN_FILE = BASE / "Output" / "fda_510k_with_days.csv"
OUT_FILE = BASE / "Output" / "fda_final.csv"

# same category names as the CDSCO file
CARD = "Cardiac & Vascular"
ORTH = "Orthopedic & Spine"
IMG = "Diagnostics: Imaging"
SURG = "Surgical & Endoscopy"
IVD = "Diagnostics: IVD & Lab"
DENT = "Dental"
CRIT = "Critical Care & Respiratory"
NEED = "Needles, Syringes & Catheters (general)"
IVF = "IVF & Women's Health"
OPH = "Ophthalmic"
NEURO = "Neuro"
GI = "Gastro / GI"
URO = "Urology"
WOUND = "Wound Care"
ENT = "ENT & Hearing"
DIAL = "Dialysis & Renal"
BLOOD = "Blood & Transfusion"
AES = "Aesthetics & Dermatology"
OTHER = "Other"

# ------------------------------------------------------------
# METHOD 1: panels that mean ONE category
# ------------------------------------------------------------
PANEL_DIRECT = {
    "Orthopedic": ORTH,
    "Radiology": IMG,
    "Cardiovascular": CARD,
    "Dental": DENT,
    "Neurology": NEURO,
    "Anesthesiology": CRIT,
    "Obstetrics/Gynecology": IVF,
    "Ophthalmic": OPH,
    "Ear, Nose, Throat": ENT,
    "Clinical Chemistry": IVD,
    "Microbiology": IVD,
    "Immunology": IVD,
    "Clinical Toxicology": IVD,
    "Pathology": IVD,
    "Medical Genetics": IVD,
}


def R(pattern):
    return re.compile(pattern, re.I)


# ------------------------------------------------------------
# METHOD 2 / 3: keyword rules (checked in order, first match wins)
# ------------------------------------------------------------
STERILE_OTHER = (OTHER, R(r"steriliz|sterilis|bowie|biological indicator|chemical indicator|indicator tape|"
                          r"sterile barrier|\bpouch|autoclave|instrument case|containment|challenge pack"))
R_DIAL = (DIAL, R(r"dialy|hemofilt|hemodiafil|bloodline|fistula|\bpd set|cycler|"
                  r"water purification|reverse osmosis"))
R_BLOOD = (BLOOD, R(r"blood bag|apheresis|transfus|plasmapheresis|cell salvage|autotransfus|cell separator"))
R_IVD_STRICT = (IVD, R(r"assay|reagent|test kit|analy[sz]er|calibrator|immunoassay|drug screen|"
                       r"coagulation|cytometer|test strip|glucose meter|glucose monitor"))
R_IVD = (IVD, R(r"assay|reagent|test kit|analy[sz]er|calibrator|immunoassay|drug screen|glucose|lateral flow|"
                r"\bpcr\b|diagnostic test|coagulation|hemoglobin|cytometer|test system"))
R_IVD_HEMA = (IVD, R(r"assay|reagent|test kit|analy[sz]er|calibrator|control plasma|\bcontrols?\b|coagulation|hemoglobin|cytometer|test system|\btest\b|glucose"))
R_WOUND = (WOUND, R(r"dressing|wound|bandage|negative pressure wound|npwt|hydrocolloid|hemostatic|gauze|\bburn|"
                    r"skin substitute|collagen|dermal template|cream|ointment|biocellulose|\bfilm\b|chito"))
R_AES = (AES, R(r"hair removal|hair growth|\bhair\b|wrinkle|aesthetic|dermal filler|breast implant|tattoo|cellulite|"
                r"rejuvenat|acne|cosmetic|body contour|fat reduction|cryolipolysis|non-ablative|light therapy|"
                r"led mask|skin tight|skin care|pigment|vascular lesion|botulinum|microneedl|epil|lumea|silk.?n|"
                r"\bipl\b|pulsed light|celluma|tricoglam|lightstim|pelleve|picocare|picosecond|dermal cooling"))
R_MASK = (CRIT, R(r"mask|respirator|n95|ventilat|oxygen|nebuliz|cpap|airway|tracheo|anesthesia|anaesthesia|"
                  r"pulse oximet|patient monitor"))
R_INFUSE = (CRIT, R(r"infusion (?:system|pump)|syringe pump|\biv pump|insulin pump|elastomeric"))
R_THERM = (IMG, R(r"thermomet|themomet|theromet|tympanic|blood pressure|sphygmo|ultrasound|x-ray|radiograph|"
                  r"\bmri\b|tomograph|fluorosc|mammograph|densitomet"))
R_GLOVE = (SURG, R(r"glove|gown|drape"))
R_NEED = (NEED, R(r"syringe|needle(?! driver| holder)|catheter|cannula|iv set|infusion set|administration set|"
                  r"lancet|\biv\b|stopcock|manifold|securacath|vial adapter|needleless|insulin delivery|"
                  r"leaderflex|infusion port|connector|solution set"))
R_SURG = (SURG, R(r"camera|imaging|video system|light source|visera|fascial|closure|surgical|endoscop|laparoscop|"
                  r"arthroscop|suture|stapl|trocar|biopsy|forceps|scalpel|electrosurg|\bmesh\b|retractor|cautery|"
                  r"harmonic|shears|\bclips?\b|ablation|sealer|needle driver|needle holder|vinci|robotic|bipolar|"
                  r"monopolar|ultrasonic|aspirator|laser|cusa|hernia"))
R_GI = (GI, R(r"gastr|colon|esoph|enteral|feeding|biliary|bariatric|duoden|ercp|enfit|rectal|\banal\b|"
              r"hemorrhoid|stomach|bowel|pancrea|sphincter|polyp|\bostomy\b|\bstoma\b|gallbladder|\bbile\b|hepat"))
R_URO = (URO, R(r"\buret|\burin(?:ary|e)? (?:catheter|bag|drain|collect|incont)|\burinary|\burolog|bladder|prostat|"
                r"cystoscop|kidney|lithotrip|incontinen|foley|nephro|\bpenile|erectile|vasectomy|"
                r"\bintermittent catheter|\brenal\b|ureteroscop"))
R_ORTH = (ORTH, R(r"orthop|\bspinal\b|\bspine\b|\bbone\b|\bknee\b|\bhip\b|pedicle|facet (?:screw|fixation|joint)|interbody|"
                  r"bone fixation|spinal fixation|arthro|fracture|\blimb\b|orthosis|brace\b"))
R_NEURO = (NEURO, R(r"neuro|brain|\beeg\b|cranial|shunt|\bnerve|\btens\b|stimulat|migraine"))
R_DENT = (DENT, R(r"dental|orthodont|endodont|\btooth\b|teeth|periodont|\boral\b|\bmouth|aligner|"
                  r"implant abutment|night guard|apex locator|orapeutic"))
R_CARD = (CARD, R(r"cardio|cardiac|coronary|\baort|embol|atherectomy|pacemaker|defibrill|\becg\b|"
                  r"electrocardio|thrombectomy|stent graft|vascular"))
R_OPH = (OPH, R(r"ophthalm|intraocular|contact lens|cataract|glaucoma|retina|vitrect|cornea|canalicular|"
                r"punctal|\beye\b"))
R_IVF = (IVF, R(r"\biui\b|\bivf\b|embryo|uterine|vagin|obstet|gynec|colposcop|contracept|\biud\b|breast pump|"
                r"fetal|menstrual|pelvic"))
R_ENT = (ENT, R(r"hearing|cochlear|tympan|tinnitus|\bsinus|\bear\b|\bears\b|auricular"))

PANEL_RULES = {                                        # METHOD 2
    "Gastroenterology, Urology": [R_DIAL, R_GI, R_URO, R_SURG, R_NEED],
    "General, Plastic Surgery":  [R_AES, R_WOUND, R_MASK, R_GLOVE, R_SURG],
    "General Hospital":          [STERILE_OTHER, R_GLOVE, R_THERM, R_MASK, R_NEED, R_INFUSE, R_WOUND, R_SURG],
    "Physical Medicine":         [R_NEURO, R_AES, R_ORTH],
    "Hematology":                [R_BLOOD, R_IVD_HEMA],
    "Unknown":                   [STERILE_OTHER, R_IVD_STRICT, R_WOUND, R_DENT, R_ORTH, R_AES, R_DIAL, R_BLOOD,
                                  R_URO, R_GI, R_CARD, R_NEURO, R_OPH, R_IVF, R_ENT, R_MASK, R_THERM,
                                  R_GLOVE, R_NEED, R_SURG, R_IVD],
}
WIDE_RULES = [STERILE_OTHER, R_INFUSE, R_IVD_STRICT, R_WOUND, R_AES, R_DIAL, R_BLOOD, R_DENT, R_ORTH,   # METHOD 3
              R_CARD, R_NEURO, R_OPH, R_IVF, R_ENT, R_URO, R_GI, R_MASK, R_THERM, R_GLOVE, R_NEED,
              R_SURG, R_IVD]
COMBINED_PANELS = {"Gastroenterology, Urology", "General, Plastic Surgery"}   # these get METHOD 2
PANEL_GUESS = {                                        # METHOD 4
    "General, Plastic Surgery": SURG,
    "Hematology": IVD,
}


def classify(panel, name):
    if panel in PANEL_DIRECT:
        return PANEL_DIRECT[panel], 1
    text = str(name)
    own_method = 2 if panel in COMBINED_PANELS else 3
    for cat, rx in PANEL_RULES.get(panel, []):
        if rx.search(text):
            return (cat, own_method) if cat != OTHER else (OTHER, 5)
    for cat, rx in WIDE_RULES:
        if rx.search(text):
            return (cat, 3) if cat != OTHER else (OTHER, 5)
    if panel in PANEL_GUESS:
        return PANEL_GUESS[panel], 4
    return OTHER, 5


# ------------------------------------------------------------
# LOAD + CLASSIFY
# ------------------------------------------------------------
df = pd.read_csv(IN_FILE, low_memory=False)
rows_before = len(df)

result = [classify(p, n) for p, n in zip(df["advisory_committee_description"], df["device_name"])]
df["category"] = [r[0] for r in result]
df["category_method"] = [r[1] for r in result]
# category_confidence from category_method (1,2 = HIGH | 3 = MED | 4 = LOW)
CONF = {1: "HIGH", 2: "HIGH", 3: "MED", 4: "LOW", 5: "LOW"}
df["category_confidence"] = df["category_method"].map(CONF)

# ------------------------------------------------------------
# RENAME + KEEP ONLY THE COLUMNS YOU ASKED FOR
# ------------------------------------------------------------
df = df.rename(columns={
    "k_number": "device_id",
    "applicant": "company_name",
    "country_code": "country",
    "decision_date": "approved_date",
    "date_received": "date_submission",
    "advisory_committee_description": "category_raw",
})
KEEP = [
    "device_id", "company_name", "device_name", "country",
    "approved_date", "date_submission",
    "category_raw", "category",
    "approval_days", "long_review_flag", "category_method", "category_confidence",
]
full = df[KEEP]
final = full[full["category"] != OTHER].reset_index(drop=True)   # drop leftover junk
final.to_csv(OUT_FILE, index=False, encoding="utf-8-sig")

# ---------------- checks ----------------
print(f"Rows before          : {rows_before:,}")
print(f"Rows dropped (Other) : {rows_before - len(final):,}  ({(rows_before - len(final)) / rows_before:.1%})")
print(f"Rows in final file   : {len(final):,}")
print(f"Unique device_id     : {final['device_id'].nunique():,}  (should equal rows)")
print(f"Approved date range  : {final['approved_date'].min()} to {final['approved_date'].max()}")
print(f"Median approval days : {final['approval_days'].median():.0f}")
print(f"Long review flags    : {int(final['long_review_flag'].sum())}")
print("\nCategory method counts (final file):")
print(final["category_method"].value_counts().sort_index().to_string())
print("\nMethod share of Other + final, by panel (before dropping Other):")
print(pd.crosstab(full["category_raw"], full["category_method"]).to_string())
print("\nCategory counts (final file):")
print(final["category"].value_counts().to_string())
print("\nCategory confidence counts (final file):")
print(final["category_confidence"].value_counts().to_string())
print("\nMissing values per column:")
print(final.isna().sum().to_string())
print(f"\nSaved: {OUT_FILE}")
