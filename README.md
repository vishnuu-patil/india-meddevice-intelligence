# India Medical Device Market Intelligence

Public-data analysis of which medical device categories are licensed for import into India (CDSCO) and how that compares with US FDA 510(k) clearances.

**Author:** S Vishnu Patil | [LinkedIn](https://www.linkedin.com/in/vishnuupatil)

All data is public. No data from any employer is used.

## Project summary (Problem, Approach, Result)

**Problem.** India imports a large share of its medical devices, but there is no single view of which device categories hold the most import licences, which countries and risk classes dominate, and how the Indian licence mix differs from what the US FDA clears.

**Approach.**
- Cleaned the CDSCO import licence list (24,563 rows) and the openFDA 510(k) download (51,759 raw rows, 47,375 after cleaning).
- Assigned every device to one of 18 categories with rule-based keyword and panel logic, and stored a confidence flag (HIGH / MED / LOW) per row.
- Counted licences as **licence-category pairs**, never raw rows (see [data_dictionary.md](data_dictionary.md)).
- Compared the category share of CDSCO licences with the share of FDA clearances in two versions: A (HIGH + MED confidence only) and B (all rows), to test whether the ranking holds.
- Built MySQL queries, an Excel pivot workbook and a 2-page Power BI dashboard on the same cleaned files.

**Result.**
- 5,163 unique import licences give 6,714 licence-category pairs across 18 categories.
- The top 4 categories hold 49.4% of all pairs: Cardiac & Vascular 1,005 (15.0%), Diagnostics: Imaging 856, Surgical & Endoscopy 759, Orthopedic & Spine 697.
- By manufacturing country (as listed in CDSCO), the top 3 by licence-category-country pairs are United States 1,458, China 1,248 and Germany 714.
- By device class, the 7,634 licence-category-class pairs split A 268, B 3,613, C 2,821, D 932.
- Only 202 of 47,375 FDA clearances (0.43%) are from Indian applicants. They peaked at 32 in 2022; 2026 shows 7 (partial year, data to 2026-09-19).
- Median FDA review time is 182 days for Indian applicants against 124 days for all applicants and for non-Indian applicants.
- The pipeline-gap ranking is mostly stable across versions: Orthopedic & Spine has the largest gap in both (9.0 pp in A, 7.0 pp in B). Surgical & Endoscopy moves from -2.6 pp (A) to +2.0 pp (B), so that category depends on the confidence filter.

## Verify the numbers yourself

    pip install -r requirements.txt
    python verify_numbers.py

The script recomputes the figures above from the files in this repo and prints PASS or FAIL per line. Last run: 40 passed, 0 failed.

## Folder map

| Folder / file | Contents |
|---|---|
| root `*.py` | Cleaning and analysis scripts (run order below) |
| `Data/` | Source files used by the scripts (some must be downloaded, see Data sources) |
| `Output/` | Cleaned datasets and all result files (`cdsco_final.csv`, `fda_final.csv`, `obj01` to `obj11`, `pipeline_gap_*`) |
| `Excel_Work/` | `cdsco_for_excel.csv`, the file behind the Excel pivots |
| `Output/India_MedDevice_Pivots.xlsx` | Excel pivot workbook |
| `PowerBI/` | `India_MedDevice.pbix`, the 2-page dashboard |
| `data_dictionary.md` | Column definitions, counting rule, confidence mapping |
| `verify_numbers.py` | Recomputes the headline numbers |

## Data sources

| Data | Source | In this repo? |
|---|---|---|
| FDA 510(k) clearances | openFDA device 510(k) download (`device-510k-0001-of-0001.json`, about 1.58 GB) | Not included. Download from the openFDA downloads page. The converted `Data/fda_510k.csv` is included. |
| CDSCO import licences | CDSCO medical device list (`MD - Medical Devices.xlsx`) | Included |
| NFHS-5 district indicators | NDAP report 6822 (`NDAP_REPORT_6822.csv`, `6822_METADATA.csv`) | Not included. Download from NDAP and place in `Data/`. |
| India medical device imports | `India_Medical_Device_Imports.xlsx`, compiled from public import statistics | Not included. Used only by `obj10_import_value_vs_licences.py`. |

Data files keep the licences of their original sources. The code is MIT-licensed.

## Run order

Paths are relative to the repo root; scripts must sit next to `Data/` and `Output/`.

| Stage | Script | Reads | Writes |
|---|---|---|---|
| FDA 1 | `01_convert_json_to_csv.py` | `Data/device-510k-0001-of-0001.json` | `Data/fda_510k.csv` |
| FDA 2 | `fda_510k_cleaned.py` | `Data/fda_510k.csv` | `Output/fda_510k_with_days.csv` |
| FDA 3 | `clean_fda_final.py` | `Output/fda_510k_with_days.csv` | `Output/fda_final.csv` |
| CDSCO 1 | `clean_cdsco.py` | `Data/MD - Medical Devices.xlsx` | `Output/cdsco_clean.csv` |
| CDSCO 2-3 | `archive_cdsco.py`, `cdsco_categories_new.py` | `cdsco_clean.csv` and a categorisation backup | `cdsco_categorized.csv` and change reports |
| CDSCO 4 | `clean_cdsco_final.py` | `Output/cdsco_categorized.csv` | `Output/cdsco_final.csv`, `cdsco_model_lookup.csv` |
| Audit | `Regenerate_new_changes.py` | `cdsco_final.csv` and a backup | `Output/_audit/cdsco_category_changes_recovered.csv` |
| NFHS | `clean_nfhs5.py` | NDAP files, `cdsco_final.csv` | `nfhs5_*`, `state_name_map` |
| Obj 01-02 | `obj01_02_category.py` | `cdsco_final.csv` | `obj01_*`, `obj02_*` |
| Obj 05 | `obj05_disease_burden.py` | `nfhs5_clean.csv`, `cdsco_final.csv` | `obj05_*` |
| Obj 06-08 | `obj06_07_08_competitors_country_class.py` | `cdsco_final.csv` | `obj06_*`, `obj07_*`, `obj08_*` |
| Obj 10 | `obj10_import_value_vs_licences.py` | imports file, `cdsco_final.csv` | `obj10_*` |
| Obj 11 | `obj11_indian_fda.py` | `fda_final.csv` | `obj11_*` |
| Obj 03 | `pipelinegap_final.py` | `fda_final.csv`, `cdsco_final.csv` | `pipeline_gap_vA`, `vB`, `compare` |
| Excel | `make_excel_copy.py` | `cdsco_final.csv` | `Excel_Work/cdsco_for_excel.csv` |
| MySQL | `load_db.py` | the Output CSVs | database `device_analysis` (password typed at run time) |

Also included: `Data_validation_files.py`, `fresh_cdsco_validation.py`, `fda_validate_and_fix.py`, `fda_validate_and_fix_v3.py`, `sample_fda_v2.py`, `sample_fda_v3.py` (sampling and checking helpers).

## SQL and dashboard

- `SQL/level1_basic.sql`: Q1 to Q3 (category ranking, new registrations per year, device-class mix).
- `SQL/level2_4_queries.sql`: Q4 to Q11 (price-cap keyword flag, importers, manufacturing countries, pipeline gap Version B, NFHS-5 disease burden, window functions).
- The queries run on the MySQL tables loaded by `load_db.py` and count licence-category pairs.
- Q4 is an approximate keyword flag, not price data (Objective 09 is not done).
- The SQL queries have not all been cross-checked against the Python outputs. `verify_numbers.py` covers the Python output files only.
- Dashboard: 2-page Power BI report, [PDF export](Screenshots/India_MedDevice_Dashboard.pdf). The source file is `PowerBI/India_MedDevice.pbix`.
## Method notes

- **Confidence flag:** `category_method` 1 and 2 = HIGH, 3 = MED, 4 and 5 = LOW. Version A of the gap uses HIGH + MED only; Version B uses all rows.
- **Counting rule:** one licence is counted once per category (licence-category pair).
- **Both gap versions are published** so the ranking can be checked, not just the favourable one.

## Limitations

- **Registration counts are not demand.** A licence count shows what is licensed, not what is bought or used.
- **The pipeline gap is a pipeline asymmetry.** It compares FDA clearance share with CDSCO licence share (gap = FDA share minus CDSCO share, in percentage points, 2018-2026). It does not measure unmet demand.
- **Applicant country is not place of manufacture.** The FDA `country` column is the applicant's country.
- **Categories are rule-based.** Keyword and panel rules assign the 18 categories, with a confidence flag per row. Category accuracy has not been independently measured and no marked validation sheet is published. `validation_fda.csv` and `validation_cdsco_v2.csv` are unmarked sample files.
- **2026 is a partial year.** FDA data ends 2026-09-19.
- **Not every script was re-run end to end in this repo.** `verify_numbers.py` checks the published output files. The CDSCO stages marked "backup" need a 52 MB categorisation backup that is not included, so those stages are history and audit steps; the final CSVs are included.
- **Dashboard has 2 pages.** The Power BI file does not include a disease-burden map page.

## Not done

- Objectives 09, 12 and 13.
- Objective 04 was dropped.
