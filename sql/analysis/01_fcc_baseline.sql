-- 1. Total de locations únicas
SELECT COUNT(DISTINCT location_id) AS total_locations
FROM fcc_fixed_broadband;


-- 2. Total de locations con disponibilidad residencial o mixta
SELECT COUNT(DISTINCT location_id) AS residential_locations
FROM fcc_fixed_broadband
WHERE business_residential_code IN ('R', 'X');


-- 3. Locations únicas por tecnología
SELECT
    technology,
    technology_name,
    COUNT(DISTINCT location_id) AS locations
FROM fcc_fixed_broadband
GROUP BY technology, technology_name
ORDER BY locations DESC;


-- 4. Locations residenciales/mixed por tecnología
SELECT
    technology,
    technology_name,
    COUNT(DISTINCT location_id) AS residential_locations
FROM fcc_fixed_broadband
WHERE business_residential_code IN ('R', 'X')
GROUP BY technology, technology_name
ORDER BY residential_locations DESC;


-- 5. Locations residenciales/mixed con fibra
SELECT COUNT(DISTINCT location_id) AS residential_fiber_locations
FROM fcc_fixed_broadband
WHERE technology = 50
  AND business_residential_code IN ('R', 'X');


-- 6. Proveedores únicos por tecnología
SELECT
    technology,
    technology_name,
    COUNT(DISTINCT provider_id) AS providers
FROM fcc_fixed_broadband
GROUP BY technology, technology_name
ORDER BY providers DESC;