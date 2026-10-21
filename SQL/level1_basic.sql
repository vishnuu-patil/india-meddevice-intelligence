-- Q1. Top 15 device categories by CDSCO unique licences
-- Counts unique (licence, category) pairs, the same way as the Python work.
SELECT category,
       COUNT(*) AS licences,
       ROUND(COUNT(*) * 100 / SUM(COUNT(*)) OVER (), 1) AS share_pct  -- % of ALL 6,714 pairs
FROM (SELECT DISTINCT license_no, category FROM cdsco) AS p
GROUP BY category
ORDER BY licences DESC
LIMIT 15;

-- Q2. New registrations per category per year, 2018-2026 (renewals excluded)
-- license_year is fixed per licence, so renewals never count as new.
SELECT category,
       SUM(license_year = 2018) AS y2018, SUM(license_year = 2019) AS y2019,
       SUM(license_year = 2020) AS y2020, SUM(license_year = 2021) AS y2021,
       SUM(license_year = 2022) AS y2022, SUM(license_year = 2023) AS y2023,
       SUM(license_year = 2024) AS y2024, SUM(license_year = 2025) AS y2025,
       SUM(license_year = 2026) AS y2026,  -- 2026 is a partial year (data ends 1 Oct)
       COUNT(*) AS total
FROM (SELECT DISTINCT license_no, category, license_year FROM cdsco) AS p
GROUP BY category
ORDER BY total DESC;

-- Q2b. Check totals per year (all categories)
SELECT license_year, COUNT(*) AS new_pairs
FROM (SELECT DISTINCT license_no, category, license_year FROM cdsco) AS p
GROUP BY license_year
ORDER BY license_year;

-- Q3. Device class mix: what % of registrations is each risk class?
SELECT device_class,
       COUNT(*) AS licence_category_pairs,
       ROUND(COUNT(*) * 100 / SUM(COUNT(*)) OVER (), 1) AS share_pct
FROM (SELECT DISTINCT license_no, category, device_class FROM cdsco) AS p
GROUP BY device_class
ORDER BY device_class;