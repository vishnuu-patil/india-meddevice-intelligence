-- ===== SETUP (run once): view with cleaned importer names, same clean-up as the Python Objective 06 =====
CREATE OR REPLACE VIEW cdsco_importers AS
WITH step1 AS (
  SELECT license_no, category,
         TRIM(REGEXP_REPLACE(REGEXP_REPLACE(REPLACE(LOWER(importer_name), '&', ' and '), '[^a-z0-9 ]', ' '), ' +', ' ')) AS nm
  FROM cdsco
)
SELECT DISTINCT license_no, category,
       REGEXP_REPLACE(REGEXP_REPLACE(nm, '\\b(private limited|private ltd|pvt limited)\\b', 'pvt ltd'), '\\blimited\\b', 'ltd') AS importer_key
FROM step1;

-- ===== Q4. Price-capped vs free market (keyword flag - approximate until Objective 09 prices are in) =====
SELECT CASE WHEN device_name LIKE '%knee%' THEN 'Knee implant (price-capped)'
            WHEN device_name LIKE '%coronary%' AND device_name LIKE '%stent%' THEN 'Coronary stent (price-capped)'
            WHEN device_name LIKE '%stent%' THEN 'Other stent (cap may not apply)'
            ELSE 'Free market' END AS price_status,
       COUNT(*) AS device_rows,
       COUNT(DISTINCT license_no) AS licences
FROM cdsco
GROUP BY price_status
ORDER BY device_rows DESC;

-- ===== Q4b. Check what the keywords actually caught =====
SELECT device_name, COUNT(*) AS n
FROM cdsco
WHERE device_name LIKE '%knee%' OR device_name LIKE '%stent%'
GROUP BY device_name
ORDER BY n DESC
LIMIT 20;

-- ===== Q5. Categories with more than 500 new registrations in 2022-2026 =====
SELECT category, COUNT(*) AS new_pairs_2022_2026
FROM (SELECT DISTINCT license_no, category, license_year
      FROM cdsco WHERE license_year BETWEEN 2022 AND 2026) AS p
GROUP BY category
HAVING COUNT(*) > 500
ORDER BY new_pairs_2022_2026 DESC;

-- ===== Q6. Top 10 importers overall (names cleaned by the view) =====
SELECT importer_key,
       COUNT(*) AS licence_category_pairs,
       COUNT(DISTINCT license_no) AS unique_licences,
       COUNT(DISTINCT category) AS categories_covered
FROM cdsco_importers
GROUP BY importer_key
ORDER BY licence_category_pairs DESC, importer_key
LIMIT 10;

-- ===== Q7a. Top 10 countries of manufacture =====
SELECT mfr_country,
       COUNT(*) AS licence_category_pairs,
       ROUND(COUNT(*) * 100 / SUM(COUNT(*)) OVER (), 1) AS share_pct
FROM (SELECT DISTINCT license_no, category, mfr_country FROM cdsco) AS p
GROUP BY mfr_country
ORDER BY licence_category_pairs DESC
LIMIT 10;

-- ===== Q7b. Top country per category =====
WITH counts AS (
  SELECT category, mfr_country, COUNT(*) AS pairs
  FROM (SELECT DISTINCT license_no, category, mfr_country FROM cdsco) AS p
  GROUP BY category, mfr_country
),
ranked AS (
  SELECT category, mfr_country, pairs,
         ROW_NUMBER() OVER (PARTITION BY category ORDER BY pairs DESC, mfr_country) AS rn,
         SUM(pairs) OVER (PARTITION BY category) AS category_total
  FROM counts
)
SELECT category, mfr_country AS top_country,
       ROUND(pairs * 100 / category_total, 1) AS top_country_share_pct
FROM ranked
WHERE rn = 1
ORDER BY top_country_share_pct DESC, category;

-- ===== Q8. Pipeline gap, Version B (all rows): FDA share vs CDSCO share, 2018-2026 =====
WITH fda_n AS (
  SELECT category, COUNT(*) AS fda_rows
  FROM fda WHERE YEAR(approved_date) BETWEEN 2018 AND 2026
  GROUP BY category
),
cd_n AS (
  SELECT category, COUNT(*) AS cdsco_licences
  FROM (SELECT DISTINCT license_no, category FROM cdsco
        WHERE license_year BETWEEN 2018 AND 2026) AS p
  GROUP BY category
),
shares AS (
  SELECT f.category, f.fda_rows, COALESCE(c.cdsco_licences, 0) AS cdsco_licences,
         ROUND(f.fda_rows * 100 / SUM(f.fda_rows) OVER (), 1) AS fda_share_pct,
         ROUND(COALESCE(c.cdsco_licences, 0) * 100 / SUM(COALESCE(c.cdsco_licences, 0)) OVER (), 1) AS cdsco_share_pct
  FROM fda_n f
  LEFT JOIN cd_n c ON c.category = f.category
)
SELECT RANK() OVER (ORDER BY fda_share_pct - cdsco_share_pct DESC) AS gap_rank,
       category, fda_rows, cdsco_licences, fda_share_pct, cdsco_share_pct,
       ROUND(fda_share_pct - cdsco_share_pct, 1) AS share_gap_pp
FROM shares
ORDER BY share_gap_pp DESC;

-- ===== Q9. Disease burden (NFHS-5) joined to the device categories it links to =====
WITH burden AS (
  SELECT 'Hypertension' AS disease, ROUND(AVG((bp_elevated_men_pct + bp_elevated_women_pct) / 2), 1) AS avg_score FROM nfhs
  UNION ALL
  SELECT 'Blood sugar', ROUND(AVG((sugar_high_men_pct + sugar_high_women_pct) / 2), 1) FROM nfhs
  UNION ALL
  SELECT 'Anaemia', ROUND(AVG((anaemia_women_15_49_pct + anaemia_children_6_59m_pct) / 2), 1) FROM nfhs
),
disease_device AS (
  SELECT 'Hypertension' AS disease, 'Cardiac & Vascular' AS category
  UNION ALL SELECT 'Blood sugar', 'Diagnostics: IVD & Lab'
  UNION ALL SELECT 'Blood sugar', 'Dialysis & Renal'
  UNION ALL SELECT 'Anaemia', 'Diagnostics: IVD & Lab'
),
licences AS (
  SELECT category, COUNT(*) AS cdsco_licences
  FROM (SELECT DISTINCT license_no, category FROM cdsco) AS p
  GROUP BY category
)
SELECT b.disease, b.avg_score, d.category, l.cdsco_licences,
       ROUND(l.cdsco_licences * 100 / (SELECT SUM(cdsco_licences) FROM licences), 1) AS licence_share_pct
FROM burden b
INNER JOIN disease_device d ON d.disease = b.disease
INNER JOIN licences l ON l.category = d.category
ORDER BY b.disease, l.cdsco_licences DESC;

-- ===== Q9b. Top 5 states by hypertension (unweighted average of district scores) =====
SELECT state,
       ROUND(AVG((bp_elevated_men_pct + bp_elevated_women_pct) / 2), 1) AS hypertension_avg
FROM nfhs
GROUP BY state
ORDER BY hypertension_avg DESC
LIMIT 5;

-- ===== Q10. Top 3 importers inside each category (RANK within a partition) =====
WITH counts AS (
  SELECT category, importer_key, COUNT(*) AS licences
  FROM cdsco_importers
  GROUP BY category, importer_key
),
ranked AS (
  SELECT category, importer_key, licences,
         ROW_NUMBER() OVER (PARTITION BY category ORDER BY licences DESC, importer_key) AS rank_in_category,
         SUM(licences) OVER (PARTITION BY category) AS category_total
  FROM counts
)
SELECT category, rank_in_category, importer_key, licences, category_total,
       ROUND(licences * 100 / category_total, 1) AS share_pct
FROM ranked
WHERE rank_in_category <= 3
ORDER BY category, rank_in_category;

-- ===== Q11. Year-on-year growth per category (LAG compares with the previous year) =====
WITH yearly AS (
  SELECT category, license_year, COUNT(*) AS new_pairs
  FROM (SELECT DISTINCT license_no, category, license_year FROM cdsco) AS p
  GROUP BY category, license_year
)
SELECT category, license_year, new_pairs,
       LAG(new_pairs) OVER (PARTITION BY category ORDER BY license_year) AS prev_year_pairs,
       ROUND((new_pairs - LAG(new_pairs) OVER (PARTITION BY category ORDER BY license_year)) * 100
             / LAG(new_pairs) OVER (PARTITION BY category ORDER BY license_year), 1) AS yoy_pct,
       CASE WHEN license_year = 2026 THEN 'partial year' ELSE '' END AS note
FROM yearly
ORDER BY category, license_year;