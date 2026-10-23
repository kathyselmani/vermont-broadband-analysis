CREATE OR REPLACE VIEW vw_fcc_location_access AS

SELECT
    location_id,

    MAX(
        CASE
            WHEN technology = 50 THEN 1
            ELSE 0
        END
    ) AS has_fiber,

    MAX(
        CASE
            WHEN technology = 40 THEN 1
            ELSE 0
        END
    ) AS has_cable,

    MAX(
        CASE
            WHEN technology = 10 THEN 1
            ELSE 0
        END
    ) AS has_copper,

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

GROUP BY location_id;