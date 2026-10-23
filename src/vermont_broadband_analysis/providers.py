"""Which providers offer service where: by county and by H3 resolution-7 zone.

For each area and each brand + technology, the share of the area's residential
locations where that brand reports an R/X offer, the median advertised speed, and
the share of its offers that reach 100/20 Mbps.

Privacy: zones are H3 resolution 7 (about 5 km2). A zone with fewer than
MIN_ZONE_LOCATIONS locations borrows the provider list of its resolution-6 parent
(about 36 km2) and is flagged; no location-level data is published.
"""

import h3
import pandas as pd

from . import config

MIN_ZONE_LOCATIONS = 5


def _area_providers(
    res: pd.DataFrame, area_col: str, totals: pd.Series
) -> pd.DataFrame:
    meets = (res["max_advertised_download_speed"] >= config.SERVED_DOWN) & (
        res["max_advertised_upload_speed"] >= config.SERVED_UP
    )
    g = res.assign(meets_100_20=meets).groupby([area_col, "brand_name", "technology"])
    out = g.agg(
        locations=("location_id", "nunique"),
        median_download=("max_advertised_download_speed", "median"),
        median_upload=("max_advertised_upload_speed", "median"),
        share_offers_100_20=("meets_100_20", "mean"),
    ).reset_index()
    out["area_locations"] = out[area_col].map(totals)
    out["pct_locations"] = (out["locations"] / out["area_locations"] * 100).round(1)
    out["share_offers_100_20"] = (out["share_offers_100_20"] * 100).round(0)
    out["technology_name"] = out["technology"].map(config.TECHNOLOGY_NAMES)
    return out.sort_values([area_col, "locations"], ascending=[True, False])


def run() -> dict[str, pd.DataFrame]:
    df = pd.read_parquet(config.FCC_COMBINED_PARQUET)
    res = df[df["business_residential_code"].isin(config.RESIDENTIAL_CODES)].copy()
    res["county_fips"] = res["block_geoid"].astype("string").str[:5]
    res["h3_res7_id"] = res["h3_res8_id"].map(lambda c: h3.cell_to_parent(c, 7))
    res["h3_res6_id"] = res["h3_res7_id"].map(lambda c: h3.cell_to_parent(c, 6))

    county_tot = res.groupby("county_fips")["location_id"].nunique()
    county = _area_providers(res, "county_fips", county_tot)
    county["county_name"] = county["county_fips"].map(config.VERMONT_COUNTIES)

    z7_tot = res.groupby("h3_res7_id")["location_id"].nunique()
    z6_tot = res.groupby("h3_res6_id")["location_id"].nunique()
    z7 = _area_providers(res, "h3_res7_id", z7_tot)
    z6 = _area_providers(res, "h3_res6_id", z6_tot)

    small = z7_tot[z7_tot < MIN_ZONE_LOCATIONS].index
    parents = {c: h3.cell_to_parent(c, 6) for c in small}
    borrowed = []
    for cell, parent in parents.items():
        rows = (
            z6[z6["h3_res6_id"] == parent]
            .drop(columns="h3_res6_id")
            .assign(h3_res7_id=cell)
        )
        borrowed.append(rows)
    zones = pd.concat([z7[~z7["h3_res7_id"].isin(small)]] + borrowed, ignore_index=True)
    zones["borrowed_from_res6"] = zones["h3_res7_id"].isin(small)
    # Counts are not published for zones: only shares, speeds and the zone size band
    zones = zones.drop(columns=["locations"])
    zones.loc[zones["borrowed_from_res6"], "area_locations"] = pd.NA

    out_dir = config.PROCESSED_DIR / "analysis"
    county.to_csv(out_dir / "providers_by_county.csv", index=False)
    zones.to_csv(out_dir / "providers_by_zone_h3r7.csv", index=False)
    print(
        f"Providers by county: {len(county)} rows; by zone: {zones['h3_res7_id'].nunique()} zones, "
        f"{len(zones)} rows ({len(small)} small zones use their res-6 parent)"
    )
    return {"county": county, "zones": zones}
