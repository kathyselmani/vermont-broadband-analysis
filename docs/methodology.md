# Methodology

## 1. Data provenance

| Dataset | Publisher | Vintage | Files |
|---------|-----------|---------|-------|
| Broadband Data Collection, fixed availability, Vermont | Federal Communications Commission | Data as of 2025-12-31 (files dated 18 Aug and 3 Sep 2026) | 8 CSVs in `data/raw/fcc/2025-12-31/`, one per technology |
| American Community Survey 5-year estimates | U.S. Census Bureau | 2020-2024 | Tract and county rows from the table-based Summary File |
| Gazetteer | U.S. Census Bureau | 2024 (2020 census geography) | Tract land area; town names and internal points |
| TIGERweb | U.S. Census Bureau | current | Generalized county outlines for the dashboard |

Source page for FCC files: <https://broadbandmap.fcc.gov/data-download/nationwide-data?version=dec2025>.
SHA-256 checksums of the FCC ZIP files are recorded in `data/processed/fcc_file_inventory.csv`;
Census downloads are recorded in `data/reference/census_download_manifest.json`.

**File naming.** The `50` in `bdc_50_<Technology>_fixed_broadband_...` is Vermont's
**state FIPS code**, not a technology code. Fiber to the Premises also has technology
code 50, which is a coincidence.

**Dates.** Dataset publication date and reference date are different concepts. The
analysis uses the reference date of the observations (December 31, 2025).

## 2. Pipeline

All transformations are code. Raw files are never edited by hand.

```
uv run vermont-broadband-analysis all          # every step
uv run vermont-broadband-analysis all --skip-census
```

| Step | Module | Output |
|------|--------|--------|
| `profile` | `fcc.py` | `data/processed/fcc_file_inventory.csv` (schema, keys, checksums, anomalies) |
| `build` | `fcc.py` | validated, combined `fcc_fixed_broadband_vermont_2025_12_31.parquet` (2,135,225 rows) |
| `metrics` | `metrics.py` | `location_access.parquet` + aggregate tables in `data/processed/analysis/` |
| `census` | `census.py` | `acs_tract.csv`, `acs_county.csv` |
| `socioeconomic` | `socioeconomic.py` | tract FCC + ACS join, correlations, group comparisons |
| `dashboard` | `dashboard_data.py` | `dashboard/web/data.json` and self-contained `dashboard/web/index.html` |

Validation in `build` stops the pipeline if a file has a schema mismatch, a non-VT
state, missing values, an invalid block GEOID, an unknown business/residential code,
or a duplicate on the candidate key.

## 3. Grain and keys

One FCC record = one `location_id` × `provider_id` × `technology` × `business_residential_code`.
This candidate key is unique in all eight files. `location_id + provider_id + technology`
alone is **not** unique: GSO satellite (Viasat) and licensed fixed wireless (AT&T, Verizon)
list some locations twice, once as business (B) and once as residential (R).

`provider_id` and `brand_name` are not one-to-one (e.g. provider 130335 reports both
*Consolidated Communications* and *Fidium Fiber*; *GREEN MOUNTAIN ACCESS* appears under two
provider IDs). Provider tables are therefore grouped by both.

Every location maps to exactly one 2020 census block (asserted in `metrics.py`).
County = first 5 digits of `block_geoid`, tract = first 11.

## 4. Analysis universe

`business_residential_code`: **R** residential only, **B** business only, **X** both.

The residential universe is every location with at least one R or X offer, and only those
offers are used. Because Starlink reports X almost everywhere, this universe contains all
282,377 FCC locations in the files. It cannot exclude business-only sites; that would
require the licensed FCC Broadband Serviceable Location Fabric.

## 5. Definitions

**Reliable technology** (NTIA BEAD): copper/DSL (10), cable (40), fiber (50), licensed
fixed wireless (71) and licensed-by-rule fixed wireless (72). Satellite (60, 61) and
unlicensed fixed wireless (70) are excluded.

| Tier | Rule (reliable technology **and** `low_latency = 1`) |
|------|------|
| Served | an offer of ≥ 100 Mbps down **and** ≥ 20 Mbps up |
| Underserved | best offer ≥ 25/3 but below 100/20 |
| Unserved | no offer of at least 25/3 |

Both speeds are taken from the **same record**. A location with 100 Mbps down from one
provider and 20 Mbps up from another is not served.

**Wired 100/20 competition** = number of distinct `provider_id`s offering ≥ 100/20 over
fiber, cable or copper at a location. **Sole wired provider** = the provider at locations
where that count is exactly one.

**Gigabit wired** = a fiber, cable or copper offer of ≥ 1,000 Mbps down.

**Satellite only** = satellite offers and no terrestrial (wired or fixed-wireless) offer.

## 6. Socioeconomic join

Tract-level FCC aggregates are joined to ACS tract estimates on the 11-digit GEOID (2020
tract definitions on both sides). Population density uses Gazetteer land area.
Associations are summarized with Spearman rank correlations (robust to skew and outliers)
and by grouping tracts into density classes and income quartiles. Tract groupings
re-aggregate location counts, so they are weighted by locations, not by tracts.

Every ACS figure is a survey estimate with a margin of error. MOEs for income and broadband
subscription are kept in `acs_tract.csv`. Small tracts are noisy, so the dashboard scatter
shows only tracts with at least 50 FCC locations.

## 7. Limitations

- **Availability ≠ adoption, price or quality.** FCC data is what providers report they
  could deliver within 10 business days. It is not measured speed, and it is challengeable.
- **Zero-speed records.** 192,595 records (mostly licensed fixed wireless and copper)
  report 0/0 Mbps. They appear to be offers below 1 Mbps (the public file stores whole
  Mbps). They are kept but never meet a threshold.
- **Universe.** Includes possible business-only sites (see §4).
- **Ecological inference.** Tract-level correlations do not describe individual households.
- **Snapshot.** One reporting period (Dec 2025). Network build-out continues, especially
  community fiber built by Vermont's Communications Union Districts.
- **Licensing.** See §8.

## 8. Privacy, licensing and attribution

**Public data only.** Every input is published openly by a U.S. federal agency:
the FCC Broadband Data Collection availability files and U.S. Census Bureau products
(ACS Summary File, Gazetteer, TIGERweb). The FCC states that BDC availability data
and the Census data shown on its map "are offered free and not subject to copyright
restriction" (17 U.S.C. §105, U.S. Government Works), and asks for attribution:
*Source data: FCC Broadband Data Collection*. That attribution appears in the
dashboard, README and these docs.

**The FCC Fabric is not redistributed.** CostQuest Associates owns the rights to the
Broadband Serviceable Location Fabric, including each **Location ID**, latitude,
longitude and address. The project uses Location IDs only internally, to count
locations. They never appear in any published output:
- raw FCC files and the location-level parquet files are git-ignored;
- dashboard data, aggregate tables and notebook outputs contain no Location IDs
  (notebooks 01 and 02b drop the column before displaying rows);
- no addresses or coordinates are used at all.

**Small-cell rule.** The finest published geography is the H3 resolution-8 hexagon
(about 0.7 km²), which the FCC itself publishes in the public files. Hexagons with
fewer than 5 locations (8,382 of 21,033) show no counts, and their percentages are
replaced by those of the surrounding resolution-7 cell (about 5 km²). Tract, town and
county figures are aggregates of hundreds or thousands of locations. Census figures
are published estimates for whole areas; no household-level data is used.

**Third-party names and software.** Provider brand names identify reported offers;
no logos or trademarks are reproduced. The dashboard uses deck.gl (MIT), h3-js
(Apache 2.0) and Google Fonts (SIL Open Font License). No photographs or third-party
images are used; the hero graphic is drawn from the data. The page sets no cookies
and loads no analytics.
