# Findings

**Scope:** residential fixed broadband availability in Vermont, FCC Broadband Data
Collection (data as of December 31, 2025), joined to ACS 2020–2024 5-year estimates.
All figures are reported availability, not measured speed, price or adoption, except
where ACS adoption is stated. Definitions are in [`methodology.md`](methodology.md).

## 1. Coverage is high

| Tier (reliable technology, low latency) | Locations | Share |
|---|---:|---:|
| Served (≥ 100/20 Mbps) | 253,307 | 89.7% |
| Underserved (25/3 to 100/20) | 15,158 | 5.4% |
| Unserved (< 25/3) | 13,912 | 4.9% |
| **Total residential locations** | **282,377** | |

- 88.5% of locations can buy **wired gigabit** service (fiber, cable or copper ≥ 1,000 Mbps).
- Median best reliable download offer: **2,000 Mbps**.
- 3,085 locations (1.1%) have satellite and nothing terrestrial.

## 2. Technology

| Technology | Locations reached | Median advertised (Mbps) | Counts as reliable |
|---|---:|---:|:-:|
| GSO satellite | 100.0% | 100 / 3 | no (high latency) |
| NGSO satellite (Starlink) | 99.9% | 280 / 30 | no |
| Licensed fixed wireless | 91.7% | 25 / 3 | yes |
| Cable | 67.3% | 1,200 / 35 | yes |
| Fiber to the Premises | 64.9% | 2,000 / 2,000 | yes |
| Copper (DSL) | 37.1% | 10 / 1 | yes |
| Unlicensed fixed wireless | 3.2% | 75 / 25 | no |
| LBR fixed wireless | 2.8% | 50 / 10 | yes |

Fixed wireless and satellite reach almost every location, but the high-speed tiers
come from fiber and cable.

## 3. Choice is thin

| Wired providers offering 100/20 | Locations | Share |
|---|---:|---:|
| 0 | 30,814 | 10.9% |
| 1 | 119,777 | 42.4% |
| 2 | 126,775 | 44.9% |
| 3 or more | 5,011 | 1.8% |

**53.3%** of locations have one wired 100/20 provider or none. The largest sole wired
providers are Xfinity (61,314 locations), Fidium Fiber (14,246), ECFiber (12,734),
GREEN MOUNTAIN ACCESS (7,775 across its two provider IDs), Spectrum (6,642) and
NEK Broadband (4,924).

*Correction to the first exploration:* the early figure "~91% of locations have a single
provider" came from the **fiber file only**. It is a fiber statistic: 91.6% of
residential fiber locations have one fiber provider, but 69% of those also have a
second wired 100/20 provider, usually cable.

## 4. Geography: the Northeast Kingdom and Grand Isle

| County | Locations | Served | Unserved | No wired 100/20 |
|---|---:|---:|---:|---:|
| Essex | 4,676 | 55.3% | 18.1% | 47.9% |
| Grand Isle | 5,590 | 60.7% | 9.9% | 40.9% |
| Orleans | 15,412 | 67.8% | 15.9% | 33.1% |
| Caledonia | 14,875 | 74.5% | 12.2% | 26.6% |
| … | | | | |
| Bennington | 18,669 | 96.9% | 2.4% | 3.3% |
| Windsor | 30,240 | 97.4% | 1.5% | 2.7% |
| Chittenden | 49,255 | 97.5% | 1.0% | 2.7% |
| Rutland | 29,257 | 98.2% | 1.3% | 2.0% |

- The Northeast Kingdom (Essex, Orleans, Caledonia) has 12.4% of locations but **36.7%
  of unserved locations** (5,107 of 13,912).
- Grand Isle has almost no fiber (0.02%) and depends on cable; 41% of its locations
  have no wired 100/20 option.
- Least-served tracts (≥ 1,000 locations): 50009950100 Essex (23% served),
  50013020100 Grand Isle (33%), 50019951700 Orleans (36%), 50017959101 Orange (44%),
  50005957000 Caledonia (46%).

Full table: `data/processed/analysis/county_summary.csv`; tract and H3 hexagon tables
in the same folder.

## 5. Rurality limits access; income limits adoption

Spearman correlations across 193 census tracts:

| | Population density | Median income |
|---|---:|---:|
| % locations served (FCC) | **0.73** | −0.06 |
| % locations unserved (FCC) | −0.77 | 0.01 |
| % no wired 100/20 option (FCC) | −0.72 | 0.07 |
| % households with broadband subscription (ACS) | 0.20 | **0.35** |
| % households with no internet (ACS) | −0.26 | −0.36 |

| Tract density | Served | Unserved | Wired subscription (ACS) |
|---|---:|---:|---:|
| Very rural (< 50/sq mi) | 80.6% | 10.1% | 71.0% |
| Rural (50–200) | 92.1% | 3.0% | 76.6% |
| Small town (200–1,000) | 98.5% | 0.8% | 81.7% |
| Urban (> 1,000) | 99.5% | 0.2% | 78.7% |

| Tract income quartile | Median income | Served | Wired subscription (ACS) |
|---|---:|---:|---:|
| Q1 (lowest) | $61,161 | 89.8% | 73.8% |
| Q2 | $75,156 | 85.4% | 73.4% |
| Q3 | $86,110 | 88.7% | 75.7% |
| Q4 (highest) | $107,370 | 94.4% | 82.1% |

**Interpretation.** Where infrastructure is missing, the reason is geography: low-density
tracts are far more likely to be unserved, regardless of income. Where infrastructure
exists, income shapes whether households subscribe. Remaining gaps call for two
different responses: rural build-out (the Northeast Kingdom, Grand Isle, very rural
tracts) and affordability support in lower-income areas.

Availability counts locations; adoption counts households. The two columns compare
levels across groups, not the same population. These are ecological associations with
ACS sampling error, not causal effects.

## 6. Limitations

See [`methodology.md` §7](methodology.md#7-limitations): provider-reported availability,
0-Mbps records, a residential universe that may include some business-only sites, a
single reporting period, and tract-level (not household-level) socioeconomic data.
