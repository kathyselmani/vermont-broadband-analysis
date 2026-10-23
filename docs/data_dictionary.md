# Data Dictionary

Datasets and fields used in the Vermont Broadband Access & Digital Divide Analysis.

---

## 1. FCC Broadband Data Collection — fixed availability

| | |
|---|---|
| **Publisher** | Federal Communications Commission |
| **Coverage** | Vermont (state FIPS 50), all 8 fixed technologies |
| **Data vintage** | December 31, 2025 |
| **Files** | `bdc_50_<Technology>_fixed_broadband_D25_<release date>.csv` (released 18 Aug 2026 for fiber, 3 Sep 2026 for the rest) |
| **Retrieved** | August–September 2026 |
| **Checksums** | SHA-256 per ZIP in `data/processed/fcc_file_inventory.csv` |
| **Fiber ZIP SHA-256** | `3bb3850436ab0ccbf03324e9310520c0e410b8d81903ae703d58a40f827d1678` |

### Row definition

One row = one provider's reported fixed broadband offer at one broadband-serviceable
location, for one technology and one business/residential class. Unique key:
`location_id + provider_id + technology + business_residential_code`.

### Records by file

| Technology (code) | Rows | Locations | Providers |
|---|---:|---:|---:|
| Copper (10) | 108,650 | 108,552 | 9 |
| Cable (40) | 191,040 | 190,998 | 4 |
| Fiber to the Premises (50) | 203,946 | 187,037 | 22 |
| GSO Satellite (60) | 768,584 | 282,371 | 2 |
| NGSO Satellite (61) | 282,226 | 282,226 | 1 |
| Unlicensed Fixed Wireless (70) | 9,014 | 9,009 | 4 |
| Licensed Fixed Wireless (71) | 563,775 | 269,839 | 5 |
| LBR Fixed Wireless (72) | 7,990 | 7,982 | 5 |
| **Combined** | **2,135,225** | **282,377** | |

### Fields

| Field | Type | Description |
|---|---|---|
| `frn` | int | FCC Registration Number of the filing entity |
| `provider_id` | int | FCC provider identifier. Not one-to-one with `brand_name` |
| `brand_name` | text | Consumer-facing brand (e.g. *Fidium Fiber*, *Xfinity*) |
| `location_id` | int | FCC Broadband Serviceable Location identifier |
| `technology` | int | 10 Copper, 40 Cable, 50 Fiber, 60 GSO satellite, 61 NGSO satellite, 70 unlicensed FW, 71 licensed FW, 72 licensed-by-rule FW |
| `max_advertised_download_speed` | int (Mbps) | Maximum advertised download speed. `0` appears to mean below 1 Mbps |
| `max_advertised_upload_speed` | int (Mbps) | Maximum advertised upload speed |
| `low_latency` | 0/1 | 1 = round-trip latency ≤ 100 ms. Always 0 for GSO satellite |
| `business_residential_code` | R/B/X | R residential only, B business only, X both |
| `state_usps` | text | Always `VT` |
| `block_geoid` | text(15) | 2020 census block GEOID (read as text to keep leading digits) |
| `h3_res8_id` | text | Uber H3 resolution-8 cell (≈0.74 km²) containing the location |
| `technology_name` | text | *Derived.* Label for `technology` |
| `source_file` | text | *Derived.* Original CSV name |
| `data_vintage` | date | *Derived.* 2025-12-31 |

### Derived location table (`data/processed/location_access.parquet`)

One row per residential location (282,377 rows). Built from R/X records only.

| Field | Description |
|---|---|
| `has_fiber`, `has_cable`, `has_copper`, `has_licensed_fw`, `has_unlicensed_fw`, `has_fixed_wireless`, `has_satellite`, `has_terrestrial` | Technology reported at the location |
| `is_100_20_reliable` / `is_25_3_reliable` | A reliable, low-latency offer meets the threshold (same record) |
| `has_gigabit_wired` | Fiber, cable or copper offer ≥ 1,000 Mbps down |
| `service_tier` | `served` / `underserved` / `unserved` (see methodology) |
| `satellite_only` | Satellite offers and no terrestrial offer |
| `best_reliable_download`, `best_any_download` | Highest advertised download (Mbps) |
| `wired_100_20_providers` | Distinct providers offering ≥ 100/20 over fiber, cable or copper |
| `reliable_100_20_providers`, `fiber_providers`, `all_providers` | Other provider counts |
| `block_geoid`, `tract_geoid`, `county_fips`, `county_name`, `h3_res8_id` | Geography |

Aggregates (`statewide_summary`, `county_summary`, `tract_summary`, `h3_res8_summary`) carry
counts of the flags above plus `pct_*` shares of `locations` and
`median_best_reliable_download`.

---

## 2. U.S. Census Bureau — American Community Survey

| | |
|---|---|
| **Product** | ACS 5-year estimates, 2020–2024 |
| **Geography** | Census tracts (2020 definitions) and counties, Vermont |
| **Access** | ACS table-based Summary File (www2.census.gov), Vermont rows extracted to `data/raw/census/acs5_2024_vt_extract.csv`; provenance in `data/reference/census_download_manifest.json`. The Census Data API is supported as a fallback (`CENSUS_API_KEY`). |

### Row definition

One row per census tract (`acs_tract.csv`) or county (`acs_county.csv`).

### Fields

| Field | ACS variable | Description |
|---|---|---|
| `population` | B01003_001E | Total population |
| `median_age` | B01002_001E | Median age |
| `median_household_income` (+ `_moe`) | B19013_001E/M | Median household income, inflation-adjusted dollars |
| `poverty_universe`, `below_poverty` | B17001_001E, _002E | Poverty status in the past 12 months |
| `households` | B28002_001E | Households (internet subscription universe) |
| `hh_with_internet_subscription` | B28002_002E | With an internet subscription |
| `hh_broadband_any_type` (+ `_moe`) | B28002_004E/M | Broadband of any type (adoption) |
| `hh_broadband_cable_fiber_dsl` | B28002_007E | Cable, fiber or DSL subscription |
| `hh_no_internet_access` | B28002_013E | No internet access |
| `hh_computer_universe`, `hh_no_computer` | B28003_001E, _006E | Computer ownership |
| `pct_hh_broadband`, `pct_hh_wired_broadband`, `pct_hh_no_internet`, `pct_below_poverty`, `pct_hh_no_computer` | derived | Shares of the relevant universe |
| `land_sqmi` | Gazetteer `ALAND_SQMI` | Land area |
| `pop_per_sqmi` | derived | Population density |

Census suppression sentinels (e.g. −666666666) are converted to missing values.

---

## 3. Towns (county subdivisions)

`data/raw/census/vt_towns_2024.psv`: one row per Vermont county subdivision (256:
242 towns, 10 cities, 3 gores, 1 grant). Fields: `GEOID` (10 digits; digits 1–5 are the
county FIPS), `NAME`, `INTPTLAT`, `INTPTLONG` (Census internal point, used only to
place labels), `POPULATION` (ACS 2020–2024 B01003). Used for the town-to-county
finder and directory. Note that several towns share a name with a different county
(e.g. the town of Essex is in Chittenden County, not Essex County).

## 4. County need index (`data/processed/analysis/county_need_index.csv`)

Four indicators, each min-max scaled across the 14 counties (0 = best, 1 = worst):
`need_gap` (% below 100/20), `need_choice` (% no wired 100/20), `need_adoption`
(% households without a broadband subscription, ACS), `need_rurality` (−log10 people
per sq mi). `need_index` = their mean; `priority` High ≥ 0.60, Medium ≥ 0.35, else Low.
`level_*` labels split each scaled indicator into thirds.

## 5. Geography

The map uses the FCC-provided `h3_res8_id` hexagons (published with the small-cell rule in `methodology.md` §8) and generalized county outlines from TIGERweb (`data/reference/vt_counties_tigerweb.txt`).
`census.run(boundaries=True)` can optionally download 2024 cartographic boundary files
(1:500k) and write simplified `data/reference/vt_tracts.geojson` and `vt_counties.geojson`.
