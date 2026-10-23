"""Reference geography for the dashboard: towns (county subdivisions) and
county outlines, plus a transparent county "need" index.

Inputs (public domain, U.S. Census Bureau):
* data/raw/census/vt_towns_2024.psv - 2024 Gazetteer county subdivisions
  (GEOID, name, internal point) with ACS 2020-2024 population (B01003).
* data/reference/vt_counties_tigerweb.txt - county outlines from TIGERweb
  (State_County layer 1), generalized (maxAllowableOffset 0.004 deg).
"""

import numpy as np
import pandas as pd

from . import config

TOWNS_FILE = config.RAW_CENSUS_DIR / "vt_towns_2024.psv"
COUNTY_SHAPES_FILE = config.REFERENCE_DIR / "vt_counties_tigerweb.txt"


def load_towns() -> pd.DataFrame:
    t = pd.read_csv(TOWNS_FILE, sep="|", dtype={"GEOID": "string"})
    t["county_fips"] = t["GEOID"].str[:5]
    t["county_name"] = t["county_fips"].map(config.VERMONT_COUNTIES)
    kind = t["NAME"].str.extract(r"\s(town|city|gore|grant)$", expand=False)
    t["kind"] = kind.fillna("town")
    t["name"] = t["NAME"].str.replace(r"\s(town|city|gore|grant)$", "", regex=True)
    # Gores and grants keep the word in their name (e.g. "Buels Gore")
    is_unorg = t["kind"].isin(["gore", "grant"])
    t.loc[is_unorg, "name"] = (
        t.loc[is_unorg, "NAME"]
        .str.replace(" gore", " Gore")
        .str.replace(" grant", " Grant")
    )
    return t.rename(
        columns={"INTPTLAT": "lat", "INTPTLONG": "lon", "POPULATION": "population"}
    )[
        [
            "GEOID",
            "name",
            "kind",
            "county_fips",
            "county_name",
            "population",
            "lat",
            "lon",
        ]
    ]


def load_county_geojson() -> dict:
    features = []
    for line in COUNTY_SHAPES_FILE.read_text().strip().splitlines():
        fips, name, geom = line.split("|")
        polygons = []
        for poly in geom.split("#"):
            rings = [
                [[float(x) for x in pt.split(",")] for pt in ring.split(" ")]
                for ring in poly.split(";")
            ]
            polygons.append(rings)
        features.append(
            {
                "type": "Feature",
                "properties": {"county_fips": fips, "county_name": name},
                "geometry": {"type": "MultiPolygon", "coordinates": polygons},
            }
        )
    return {"type": "FeatureCollection", "features": features}


def county_need_index(
    county: pd.DataFrame, acs_county: pd.DataFrame, acs_tract: pd.DataFrame
) -> pd.DataFrame:
    """Equal-weight index of four indicators, each min-max scaled across the
    14 counties (0 = best county, 1 = worst county):

    * gap        - % of locations below 100/20 (underserved + unserved)
    * choice     - % of locations with no wired 100/20 provider
    * adoption   - % of households without a broadband subscription (ACS)
    * rurality   - inverse population density (people per sq mi of land)

    Priority: High >= 0.60, Medium >= 0.35, otherwise Low. Each indicator is
    also labelled Low / Moderate / High by its scaled value (< 1/3, < 2/3, else).
    """
    land = acs_tract.groupby("county_fips")["land_sqmi"].sum()
    df = county.merge(
        acs_county[
            ["county_fips", "population", "pct_hh_broadband", "median_household_income"]
        ],
        on="county_fips",
    )
    df["land_sqmi"] = df["county_fips"].map(land)
    df["pop_per_sqmi"] = (df["population"] / df["land_sqmi"]).round(1)
    df["pct_below_100_20"] = (df["pct_underserved"] + df["pct_unserved"]).round(2)
    df["pct_hh_no_broadband"] = (100 - df["pct_hh_broadband"]).round(2)

    raw = {
        "gap": df["pct_below_100_20"],
        "choice": df["pct_no_wired_100_20"],
        "adoption": df["pct_hh_no_broadband"],
        "rurality": -np.log10(df["pop_per_sqmi"]),
    }
    for k, v in raw.items():
        df[f"need_{k}"] = ((v - v.min()) / (v.max() - v.min())).round(3)
        df[f"level_{k}"] = pd.cut(
            df[f"need_{k}"],
            [-0.01, 1 / 3, 2 / 3, 1.01],
            labels=["Low", "Moderate", "High"],
        ).astype(str)
    df["need_index"] = df[[f"need_{k}" for k in raw]].mean(axis=1).round(3)
    df["priority"] = pd.cut(
        df["need_index"], [-0.01, 0.35, 0.60, 1.01], labels=["Low", "Medium", "High"]
    ).astype(str)
    df["need_rank"] = df["need_index"].rank(ascending=False, method="first").astype(int)
    return df.sort_values("need_rank")
