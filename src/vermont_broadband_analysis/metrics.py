"""Location-level access table and geographic / provider aggregates.

Analysis universe
-----------------
A location is included when at least one provider reports residential
("R") or residential-and-business ("X") availability there. Only those
R/X records are used to describe residential access.

Service tiers (FCC / NTIA BEAD convention)
------------------------------------------
* served:      a reliable technology offers >= 100/20 Mbps with low latency
* underserved: best reliable, low-latency offer is >= 25/3 but < 100/20
* unserved:    no reliable, low-latency offer of at least 25/3 Mbps

Reliable technologies = fiber, cable, copper/DSL, licensed and LBR fixed
wireless. Satellite and unlicensed fixed wireless are excluded, as in BEAD.
"""

import pandas as pd

from . import config

PROVIDER_ROLLUP_SUFFIX = "_providers"


def load_residential(path=config.FCC_COMBINED_PARQUET) -> pd.DataFrame:
    df = pd.read_parquet(path)
    df["block_geoid"] = df["block_geoid"].astype("string")
    return df[df["business_residential_code"].isin(config.RESIDENTIAL_CODES)].copy()


def build_location_table(res: pd.DataFrame) -> pd.DataFrame:
    down = res["max_advertised_download_speed"]
    up = res["max_advertised_upload_speed"]
    reliable = res["technology"].isin(config.RELIABLE_TECH) & (res["low_latency"] == 1)
    wired = res["technology"].isin(config.WIRED_TECH)

    flags = pd.DataFrame(
        {
            "location_id": res["location_id"],
            "has_fiber": res["technology"].eq(50),
            "has_cable": res["technology"].eq(40),
            "has_copper": res["technology"].eq(10),
            "has_licensed_fw": res["technology"].isin([71, 72]),
            "has_unlicensed_fw": res["technology"].eq(70),
            "has_fixed_wireless": res["technology"].isin(config.FIXED_WIRELESS_TECH),
            "has_satellite": res["technology"].isin(config.SATELLITE_TECH),
            "has_terrestrial": res["technology"].isin(config.TERRESTRIAL_TECH),
            "is_100_20_reliable": reliable
            & (down >= config.SERVED_DOWN)
            & (up >= config.SERVED_UP),
            "is_25_3_reliable": reliable
            & (down >= config.MIN_DOWN)
            & (up >= config.MIN_UP),
            "has_gigabit_wired": wired & (down >= config.GIGABIT_DOWN),
        }
    )
    loc = flags.groupby("location_id").max()

    loc["best_reliable_download"] = (
        res[reliable].groupby("location_id")["max_advertised_download_speed"].max()
    )
    loc["best_any_download"] = res.groupby("location_id")[
        "max_advertised_download_speed"
    ].max()

    def provider_count(mask: pd.Series) -> pd.Series:
        return res[mask].groupby("location_id")["provider_id"].nunique()

    wired_100 = wired & (down >= config.SERVED_DOWN) & (up >= config.SERVED_UP)
    loc["wired_100_20_providers"] = provider_count(wired_100)
    loc["reliable_100_20_providers"] = provider_count(
        reliable & (down >= config.SERVED_DOWN) & (up >= config.SERVED_UP)
    )
    loc["fiber_providers"] = provider_count(res["technology"].eq(50))
    loc["all_providers"] = provider_count(pd.Series(True, index=res.index))

    count_cols = [c for c in loc.columns if c.endswith(PROVIDER_ROLLUP_SUFFIX)]
    loc[count_cols] = loc[count_cols].fillna(0).astype("int16")
    loc["best_reliable_download"] = (
        loc["best_reliable_download"].fillna(0).astype("int32")
    )

    loc["service_tier"] = "unserved"
    loc.loc[loc["is_25_3_reliable"], "service_tier"] = "underserved"
    loc.loc[loc["is_100_20_reliable"], "service_tier"] = "served"
    loc["satellite_only"] = loc["has_satellite"] & ~loc["has_terrestrial"]

    # Geography: one block per location (asserted below).
    geo = res.groupby("location_id").agg(
        block_geoid=("block_geoid", "first"),
        h3_res8_id=("h3_res8_id", "first"),
        n_blocks=("block_geoid", "nunique"),
    )
    if (geo["n_blocks"] > 1).any():
        raise ValueError("Some locations map to more than one census block")
    loc = loc.join(geo.drop(columns="n_blocks"))
    loc["tract_geoid"] = loc["block_geoid"].str[:11]
    loc["county_fips"] = loc["block_geoid"].str[:5]
    loc["county_name"] = loc["county_fips"].map(config.VERMONT_COUNTIES)
    return loc.reset_index()


def summarize(loc: pd.DataFrame, by: list[str] | None) -> pd.DataFrame:
    """Aggregate the location table to any geography (or statewide if by=None)."""
    work = loc.assign(
        served=loc["service_tier"].eq("served"),
        underserved=loc["service_tier"].eq("underserved"),
        unserved=loc["service_tier"].eq("unserved"),
        no_wired_100_20=loc["wired_100_20_providers"].eq(0),
        one_wired_100_20=loc["wired_100_20_providers"].eq(1),
        two_plus_wired_100_20=loc["wired_100_20_providers"].ge(2),
    )
    sums = {
        "served": "sum",
        "underserved": "sum",
        "unserved": "sum",
        "has_fiber": "sum",
        "has_cable": "sum",
        "has_copper": "sum",
        "has_fixed_wireless": "sum",
        "has_gigabit_wired": "sum",
        "satellite_only": "sum",
        "no_wired_100_20": "sum",
        "one_wired_100_20": "sum",
        "two_plus_wired_100_20": "sum",
    }
    if by:
        grouped = work.groupby(by)
        out = grouped.agg(sums)
        out.insert(0, "locations", grouped.size())
        out["median_best_reliable_download"] = grouped[
            "best_reliable_download"
        ].median()
    else:
        out = work[list(sums)].sum().to_frame().T
        out.insert(0, "locations", len(work))
        out["median_best_reliable_download"] = work["best_reliable_download"].median()

    for col in sums:
        out[f"pct_{col}"] = (out[col] / out["locations"] * 100).round(2)
    return out.reset_index() if by else out


MIN_CELL_LOCATIONS = 5  # small-cell rule for published hexagon tables


def hexagon_summary(loc: pd.DataFrame) -> pd.DataFrame:
    """H3 res-8 summary safe to publish.

    Hexagons with fewer than MIN_CELL_LOCATIONS locations do not show their
    own values: their location count is withheld and their shares are replaced
    by those of the surrounding res-7 parent cell (about 7 res-8 cells).
    Each hexagon also gets the county where most of its locations are.
    """
    import h3

    work = loc.assign(
        h3_res7_id=loc["h3_res8_id"].map(lambda c: h3.cell_to_parent(c, 7))
    )
    res8 = summarize(work, ["h3_res8_id"])
    res7 = summarize(work, ["h3_res7_id"]).set_index("h3_res7_id")
    res8["h3_res7_id"] = res8["h3_res8_id"].map(lambda c: h3.cell_to_parent(c, 7))

    county = (
        work.groupby(["h3_res8_id", "county_fips"])
        .size()
        .rename("n")
        .reset_index()
        .sort_values("n", ascending=False)
        .drop_duplicates("h3_res8_id")
        .set_index("h3_res8_id")["county_fips"]
    )
    res8["county_fips"] = res8["h3_res8_id"].map(county)

    small = res8["locations"] < MIN_CELL_LOCATIONS
    value_cols = [c for c in res8.columns if c.startswith("pct_")] + [
        "median_best_reliable_download"
    ]
    parent_vals = res7.loc[res8.loc[small, "h3_res7_id"], value_cols].to_numpy()
    res8.loc[small, value_cols] = parent_vals
    count_cols = [
        c
        for c in res8.columns
        if c not in value_cols + ["h3_res8_id", "h3_res7_id", "county_fips"]
    ]
    res8[count_cols] = res8[count_cols].astype("Int64")
    res8.loc[small, count_cols] = pd.NA
    res8["small_cell"] = small
    return res8.drop(columns="h3_res7_id")


def technology_summary(res: pd.DataFrame, total_locations: int) -> pd.DataFrame:
    g = res.groupby(["technology", "technology_name"])
    out = g.agg(
        records=("location_id", "size"),
        locations=("location_id", "nunique"),
        providers=("provider_id", "nunique"),
        median_download=("max_advertised_download_speed", "median"),
        median_upload=("max_advertised_upload_speed", "median"),
    ).reset_index()
    out["pct_of_locations"] = (out["locations"] / total_locations * 100).round(2)
    out["reliable_under_bead"] = out["technology"].isin(config.RELIABLE_TECH)
    return out.sort_values("locations", ascending=False)


def provider_summary(res: pd.DataFrame, loc: pd.DataFrame) -> pd.DataFrame:
    """Brand-level footprint, plus how often the provider is the *only*
    wired 100/20 option at a location (a monopoly-exposure indicator)."""
    wired_100 = res[
        res["technology"].isin(config.WIRED_TECH)
        & (res["max_advertised_download_speed"] >= config.SERVED_DOWN)
        & (res["max_advertised_upload_speed"] >= config.SERVED_UP)
    ]
    sole = wired_100[
        wired_100["location_id"].isin(
            loc.loc[loc["wired_100_20_providers"] == 1, "location_id"]
        )
    ]
    out = (
        res.groupby(["provider_id", "brand_name"])
        .agg(
            locations=("location_id", "nunique"),
            technologies=("technology_name", lambda s: ", ".join(sorted(s.unique()))),
            median_download=("max_advertised_download_speed", "median"),
        )
        .join(
            sole.groupby(["provider_id", "brand_name"])["location_id"]
            .nunique()
            .rename("sole_wired_100_20_locations")
        )
        .fillna({"sole_wired_100_20_locations": 0})
        .reset_index()
        .sort_values("locations", ascending=False)
    )
    out["sole_wired_100_20_locations"] = out["sole_wired_100_20_locations"].astype(int)
    return out


def run() -> dict[str, pd.DataFrame]:
    res = load_residential()
    loc = build_location_table(res)

    tables = {
        "statewide_summary": summarize(loc, None),
        "county_summary": summarize(loc, ["county_fips", "county_name"]),
        "tract_summary": summarize(loc, ["tract_geoid", "county_name"]),
        "h3_res8_summary": hexagon_summary(loc),
        "technology_summary": technology_summary(res, len(loc)),
        "provider_summary": provider_summary(res, loc),
        "competition_distribution": (
            loc["wired_100_20_providers"]
            .value_counts()
            .sort_index()
            .rename_axis("wired_100_20_providers")
            .reset_index(name="locations")
        ),
        "service_tier_distribution": (
            loc["service_tier"]
            .value_counts()
            .rename_axis("service_tier")
            .reset_index(name="locations")
        ),
    }

    out_dir = config.PROCESSED_DIR / "analysis"
    out_dir.mkdir(parents=True, exist_ok=True)
    loc.to_parquet(config.PROCESSED_DIR / "location_access.parquet", index=False)
    for name, table in tables.items():
        table.to_csv(out_dir / f"{name}.csv", index=False)
    print(f"Location table: {len(loc):,} residential locations")
    print(tables["statewide_summary"].T.to_string())
    print(f"Saved tables to {out_dir}")
    tables["location_access"] = loc
    return tables
