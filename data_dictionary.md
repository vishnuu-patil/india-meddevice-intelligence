# Data dictionary

## Counting rule
Licences are counted as **licence-category pairs** (one licence counted once per category), never as raw rows. One licence can have many device rows. Registration counts are not demand.

## Confidence flag (both cleaned datasets)
`category_method` 1 and 2 = HIGH, 3 = MED, 4 and 5 = LOW. Version A of the pipeline gap uses HIGH + MED rows only. Version B uses all rows.

FDA method meanings (see `clean_fda_final.py`): 1 = FDA panel has one clear meaning; 2 = name keywords on combined panels; 3 = name keywords where the panel is unclear; 4 = panel guess (weakest layer); 5 = no match, category "Other", dropped.

## Output/cdsco_final.csv (24,563 rows, 15 columns)
| Column | Meaning |
|---|---|
| importer_name | Importer as listed in the CDSCO file |
| license_no | CDSCO import licence number |
| device_name | Device name as listed |
| device_class | Risk class A, B, C or D |
| brand_name | Brand name |
| model_id | Brand plus a running number, links to cdsco_model_lookup.csv |
| mfr_country | Manufacturing country as listed in the CDSCO file |
| license_year | Licence year from the licence record |
| issue_year | Year the licence was issued |
| is_renewal | True if the record is a renewal |
| importer_state | State of the importer |
| importer_pincode | Pincode of the importer |
| category | One of 18 device categories assigned by the cleaning scripts |
| category_method | Which rule assigned the category (1 to 5) |
| category_confidence | HIGH, MED or LOW (mapping above) |

## Output/cdsco_model_lookup.csv
model_id, brand, device_name, model_text (original model text), rows_using_it, licences_using_it, id_based_on, model_text_length.

## Excel_Work/cdsco_for_excel.csv (24,563 rows, 20 columns)
All cdsco_final columns plus:
| Column | Meaning |
|---|---|
| importer_clean | Importer name after cleaning |
| risk_label | Label derived from device class (made in make_excel_copy.py) |
| pair_id | license_no + category; distinct values = licence-category pairs (6,714) |
| pair_country_id | pair_id + manufacturing country (6,719 distinct) |
| pair_class_id | pair_id + device class (7,634 distinct) |

## Output/fda_final.csv (47,375 rows, 12 columns)
| Column | Meaning |
|---|---|
| device_id | FDA 510(k) record id |
| company_name | Applicant company |
| device_name | Device name |
| country | Applicant country (not place of manufacture) |
| approved_date | FDA decision date (2010-01-04 to 2026-09-19) |
| date_submission | Date the application was received |
| category_raw | Original FDA panel/category text |
| category | One of 18 categories ("Other" rows dropped) |
| approval_days | Days from submission to approval |
| long_review_flag | Flag for unusually long reviews (rule in fda_510k_cleaned.py) |
| category_method | Which rule assigned the category (1 to 4 remain) |
| category_confidence | HIGH, MED or LOW |

## Other result files
- `obj01_*`, `obj02_*`: category ranking and growth. `licences` = licence-category pairs, `share_pct` = share of all pairs.
- `obj05_*`: disease burden (NFHS-5) against device categories by district and state.
- `obj06_*`, `obj07_*`, `obj08_*`: importers, manufacturing countries, device classes.
- `obj10_*`: import value against licence counts.
- `obj11_*`: Indian applicants in FDA clearances. 2026 is a partial year (`partial_year` = True).
- `pipeline_gap_vA/vB/compare`: share gap in percentage points between FDA clearances and CDSCO licences. This is a pipeline asymmetry, not a measure of unmet demand.