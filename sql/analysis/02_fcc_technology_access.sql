-- Build one analytical row per residential/mixed FCC location

WITH location_access AS (
    SELECT
        location_id,

        MAX(CASE WHEN technology = 50 THEN 1 ELSE 0 END) AS has_fiber,

        MAX(CASE WHEN technology = 40 THEN 1 ELSE 0 END) AS has_cable,

        MAX(
            CASE
                WHEN technology IN (70, 71, 72) THEN 1
                ELSE 0
            END
        ) AS has_fixed_wireless,

        MAX(
            CASE
                WHEN technology IN (10, 40, 50, 70, 71, 72) THEN 1
                ELSE 0
            END
        ) AS has_terrestrial,

        MAX(
            CASE
                WHEN technology IN (60, 61) THEN 1
                ELSE 0
            END
        ) AS has_satellite

    FROM fcc_fixed_broadband

    WHERE business_residential_code IN ('R', 'X')

    GROUP BY location_id
)

SELECT *
FROM location_access
LIMIT 20;

-- Residential/mixed locations with terrestrial fixed availability

WITH location_access AS (
    SELECT
        location_id,

        MAX(
            CASE
                WHEN technology IN (10, 40, 50, 70, 71, 72) THEN 1
                ELSE 0
            END
        ) AS has_terrestrial

    FROM fcc_fixed_broadband

    WHERE business_residential_code IN ('R', 'X')

    GROUP BY location_id
)

SELECT
    COUNT(*) AS total_locations,
    SUM(has_terrestrial) AS terrestrial_locations
FROM location_access;


-- Locations with satellite availability but no terrestrial fixed availability

WITH location_access AS (
    SELECT
        location_id,

        MAX(
            CASE
                WHEN technology IN (10, 40, 50, 70, 71, 72) THEN 1
                ELSE 0
            END
        ) AS has_terrestrial,

        MAX(
            CASE
                WHEN technology IN (60, 61) THEN 1
                ELSE 0
            END
        ) AS has_satellite

    FROM fcc_fixed_broadband

    WHERE business_residential_code IN ('R', 'X')

    GROUP BY location_id
)

SELECT
    COUNT(*) AS satellite_only_locations
FROM location_access
WHERE has_satellite = 1
  AND has_terrestrial = 0;

  -- Residential/mixed locations with and without fiber

WITH location_access AS (
    SELECT
        location_id,

        MAX(
            CASE
                WHEN technology = 50 THEN 1
                ELSE 0
            END
        ) AS has_fiber

    FROM fcc_fixed_broadband

    WHERE business_residential_code IN ('R', 'X')

    GROUP BY location_id
)

SELECT
    has_fiber,
    COUNT(*) AS locations
FROM location_access
GROUP BY has_fiber
ORDER BY has_fiber DESC;

-- Fiber and cable availability combinations

WITH location_access AS (
    SELECT
        location_id,

        MAX(CASE WHEN technology = 50 THEN 1 ELSE 0 END) AS has_fiber,
        MAX(CASE WHEN technology = 40 THEN 1 ELSE 0 END) AS has_cable

    FROM fcc_fixed_broadband

    WHERE business_residential_code IN ('R', 'X')

    GROUP BY location_id
)

SELECT
    has_fiber,
    has_cable,
    COUNT(*) AS locations
FROM location_access
GROUP BY has_fiber, has_cable
ORDER BY has_fiber DESC, has_cable DESC;