"""Load and tidy U.S. Census Bureau inputs for Vermont.

* ACS 2020-2024 5-year estimates (tract and county): population, income,
  poverty, household internet subscriptions, computers, age.
* Gazetteer tract land area, used for population density.
* Optional: 2024 cartographic boundary files (tracts, counties).

ACS source, in order of preference:
1. ``data/raw/census/acs5_2024_vt_extract.csv`` - Vermont rows extracted from
   the ACS table-based Summary File (www2.census.gov/programs-surveys/acs/
   summary_file/2024/table-based-SF/data/5YRData/acsdt5y2024-<table>.dat).
   Rebuild it with ``extract_summary_file(<folder with the .dat files>)``.
2. The Census Data API (may require a free API key: set CENSUS_API_KEY).

All raw downloads are cached under data/raw/census/ and a manifest with
URL, retrieval date and SHA-256 is written to data/reference/.
"""

import datetime as dt
import io
import json
import zipfile

import pandas as pd
import requests

from . import config

ACS_YEAR = 2024  # ACS 2020-2024 5-year estimates (released Dec 2025)
GEO_YEAR = 2024
STATE = config.VERMONT_STATE_FIPS

ACS_VARIABLES = {
    "B01003_001E": "population",
    "B01002_001E": "median_age",
    "B19013_001E": "median_household_income",
    "B19013_001M": "median_household_income_moe",
    "B17001_001E": "poverty_universe",
    "B17001_002E": "below_poverty",
    "B28002_001E": "households",
    "B28002_002E": "hh_with_internet_subscription",
    "B28002_004E": "hh_broadband_any_type",
    "B28002_004M": "hh_broadband_any_type_moe",
    "B28002_007E": "hh_broadband_cable_fiber_dsl",
    "B28002_013E": "hh_no_internet_access",
    "B28003_001E": "hh_computer_universe",
    "B28003_006E": "hh_no_computer",
}

URLS = {
    "tract_shapes": f"https://www2.census.gov/geo/tiger/GENZ{GEO_YEAR}/shp/cb_{GEO_YEAR}_{STATE}_tract_500k.zip",
    "county_shapes": f"https://www2.census.gov/geo/tiger/GENZ{GEO_YEAR}/shp/cb_{GEO_YEAR}_us_county_500k.zip",
    "tract_gazetteer": (
        f"https://www2.census.gov/geo/docs/maps-data/data/gazetteer/{GEO_YEAR}_Gazetteer/"
        f"{GEO_YEAR}_gaz_tracts_{STATE}.txt"
    ),
}

ACS_API = f"https://api.census.gov/data/{ACS_YEAR}/acs/acs5"

# Census uses large negative sentinels for suppressed / unavailable values.
SENTINELS = [-666666666, -999999999, -888888888, -222222222, -333333333, -555555555]


def _manifest_path():
    config.REFERENCE_DIR.mkdir(parents=True, exist_ok=True)
    return config.REFERENCE_DIR / "census_download_manifest.json"


def _record(name: str, url: str, content: bytes) -> None:
    import hashlib

    path = _manifest_path()
    manifest = json.loads(path.read_text()) if path.exists() else {}
    manifest[name] = {
        "url": url,
        "retrieved": dt.datetime.now(tz=dt.UTC).date().isoformat(),
        "sha256": hashlib.sha256(content).hexdigest(),
        "bytes": len(content),
    }
    path.write_text(json.dumps(manifest, indent=2))


def _download(name: str, url: str, filename: str, refresh: bool = False) -> bytes:
    config.RAW_CENSUS_DIR.mkdir(parents=True, exist_ok=True)
    target = config.RAW_CENSUS_DIR / filename
    if target.exists() and not refresh:
        return target.read_bytes()
    print(f"Downloading {url}")
    resp = requests.get(url, timeout=120)
    resp.raise_for_status()
    target.write_bytes(resp.content)
    _record(name, url, resp.content)
    return resp.content


SUMMARY_FILE_EXTRACT = config.RAW_CENSUS_DIR / f"acs5_{ACS_YEAR}_vt_extract.csv"
GAZ_EXTRACT = config.RAW_CENSUS_DIR / f"{GEO_YEAR}_gaz_tracts_{STATE}_landarea.csv"
SUMMARY_FILE_URL = f"https://www2.census.gov/programs-surveys/acs/summary_file/{ACS_YEAR}/table-based-SF/data/5YRData/"


def _sf_column(var: str) -> str:
    """API name B28002_004E -> summary-file name B28002_E004."""
    table, rest = var.split("_")
    return f"{table}_{rest[-1]}{rest[:-1]}"


def extract_summary_file(dat_dir) -> pd.DataFrame:
    """Build the Vermont extract from full ACS table-based summary files
    (acsdt5y2024-b01003.dat, ...). Keeps county and tract rows only."""
    from pathlib import Path

    tables = sorted({v.split("_")[0].lower() for v in ACS_VARIABLES})
    merged = None
    for t in tables:
        cols = [_sf_column(v) for v in ACS_VARIABLES if v.lower().startswith(t)]
        df = pd.read_csv(
            Path(dat_dir) / f"acsdt5y{ACS_YEAR}-{t}.dat",
            sep="|",
            usecols=["GEO_ID", *cols],
            dtype=str,
        )
        df = df[df["GEO_ID"].str.match(rf"^(0500000|1400000)US{STATE}")]
        df["GEO_ID"] = df["GEO_ID"].str.split("US").str[1]
        merged = df if merged is None else merged.merge(df, on="GEO_ID")
    config.RAW_CENSUS_DIR.mkdir(parents=True, exist_ok=True)
    merged.to_csv(SUMMARY_FILE_EXTRACT, index=False)
    return merged


def _from_summary_extract(level: str) -> pd.DataFrame:
    raw = pd.read_csv(SUMMARY_FILE_EXTRACT, dtype={"GEO_ID": "string"})
    raw = raw[raw["GEO_ID"].str.len() == (11 if level == "tract" else 5)]
    out = pd.DataFrame({"GEO_ID": raw["GEO_ID"]})
    for var in ACS_VARIABLES:
        out[var] = raw[_sf_column(var)]
    out["state"] = out["GEO_ID"].str[:2]
    out["county"] = out["GEO_ID"].str[2:5]
    if level == "tract":
        out["tract"] = out["GEO_ID"].str[5:]
    out["NAME"] = None
    return out.drop(columns="GEO_ID")


def _tidy(df: pd.DataFrame, level: str) -> pd.DataFrame:
    for var in ACS_VARIABLES:
        df[var] = pd.to_numeric(df[var], errors="coerce").astype("float64")
        df.loc[df[var].isin(SENTINELS), var] = float("nan")
    df = df.rename(columns=ACS_VARIABLES)
    if level == "tract":
        df["tract_geoid"] = df["state"] + df["county"] + df["tract"]
    df["county_fips"] = df["state"] + df["county"]

    hh = df["households"].where(df["households"] > 0)
    df["pct_hh_broadband"] = (df["hh_broadband_any_type"] / hh * 100).round(2)
    df["pct_hh_wired_broadband"] = (
        df["hh_broadband_cable_fiber_dsl"] / hh * 100
    ).round(2)
    df["pct_hh_no_internet"] = (df["hh_no_internet_access"] / hh * 100).round(2)
    df["pct_below_poverty"] = (
        df["below_poverty"]
        / df["poverty_universe"].where(df["poverty_universe"] > 0)
        * 100
    ).round(2)
    df["pct_hh_no_computer"] = (
        df["hh_no_computer"]
        / df["hh_computer_universe"].where(df["hh_computer_universe"] > 0)
        * 100
    ).round(2)
    return df.drop(
        columns=["state", "county", "NAME"] + (["tract"] if level == "tract" else [])
    )


def load_acs(level: str, refresh: bool = False) -> pd.DataFrame:
    if SUMMARY_FILE_EXTRACT.exists() and not refresh:
        return _tidy(_from_summary_extract(level), level)
    return fetch_acs(level, refresh)


def fetch_acs(level: str, refresh: bool = False) -> pd.DataFrame:
    if level == "tract":
        geo = f"for=tract:*&in=state:{STATE}"
    elif level == "county":
        geo = f"for=county:*&in=state:{STATE}"
    else:
        raise ValueError(level)
    import os

    key = os.environ.get("CENSUS_API_KEY")
    url = f"{ACS_API}?get=NAME,{','.join(ACS_VARIABLES)}&{geo}" + (
        f"&key={key}" if key else ""
    )
    raw = json.loads(
        _download(f"acs_{level}", url, f"acs5_{ACS_YEAR}_{level}.json", refresh)
    )
    df = pd.DataFrame(raw[1:], columns=raw[0])
    return _tidy(df, level)


def fetch_tract_land_area(refresh: bool = False) -> pd.DataFrame:
    if GAZ_EXTRACT.exists() and not refresh:
        gaz = pd.read_csv(GAZ_EXTRACT, dtype={"GEOID": "string"})
        return gaz.rename(columns={"GEOID": "tract_geoid", "ALAND_SQMI": "land_sqmi"})
    raw = _download(
        "tract_gazetteer",
        URLS["tract_gazetteer"],
        f"{GEO_YEAR}_gaz_tracts_{STATE}.txt",
        refresh,
    )
    gaz = pd.read_csv(io.BytesIO(raw), sep="\t", dtype={"GEOID": "string"})
    gaz.columns = gaz.columns.str.strip()
    return gaz[["GEOID", "ALAND_SQMI"]].rename(
        columns={"GEOID": "tract_geoid", "ALAND_SQMI": "land_sqmi"}
    )


def _shapes_to_geojson(raw_zip: bytes, keep, id_field: str, tolerance: float) -> dict:
    import shapefile
    from shapely.geometry import mapping, shape

    with zipfile.ZipFile(io.BytesIO(raw_zip)) as zf:
        stem = next(n for n in zf.namelist() if n.endswith(".shp"))[:-4]
        reader = shapefile.Reader(
            shp=io.BytesIO(zf.read(stem + ".shp")),
            dbf=io.BytesIO(zf.read(stem + ".dbf")),
            shx=io.BytesIO(zf.read(stem + ".shx")),
        )
        features = []
        for sr in reader.iterShapeRecords():
            rec = sr.record.as_dict()
            if not keep(rec):
                continue
            geom = shape(sr.shape.__geo_interface__).simplify(
                tolerance, preserve_topology=True
            )
            geojson_geom = json.loads(json.dumps(mapping(geom)))
            features.append(
                {
                    "type": "Feature",
                    "properties": {"id": rec[id_field], "name": rec.get("NAME")},
                    "geometry": _round_coords(geojson_geom),
                }
            )
    return {"type": "FeatureCollection", "features": features}


def _round_coords(geom: dict, ndigits: int = 4) -> dict:
    def rnd(c):
        if isinstance(c[0], (int, float)):
            return [round(c[0], ndigits), round(c[1], ndigits)]
        return [rnd(x) for x in c]

    geom["coordinates"] = rnd(geom["coordinates"])
    return geom


def fetch_boundaries(refresh: bool = False) -> dict[str, dict]:
    tract_zip = _download(
        "tract_shapes",
        URLS["tract_shapes"],
        f"cb_{GEO_YEAR}_{STATE}_tract_500k.zip",
        refresh,
    )
    county_zip = _download(
        "county_shapes",
        URLS["county_shapes"],
        f"cb_{GEO_YEAR}_us_county_500k.zip",
        refresh,
    )
    tracts = _shapes_to_geojson(tract_zip, lambda r: True, "GEOID", 0.0005)
    counties = _shapes_to_geojson(
        county_zip, lambda r: r["STATEFP"] == STATE, "GEOID", 0.001
    )
    config.REFERENCE_DIR.mkdir(parents=True, exist_ok=True)
    (config.REFERENCE_DIR / "vt_tracts.geojson").write_text(json.dumps(tracts))
    (config.REFERENCE_DIR / "vt_counties.geojson").write_text(json.dumps(counties))
    return {"tracts": tracts, "counties": counties}


def run(refresh: bool = False, boundaries: bool = False) -> dict[str, pd.DataFrame]:
    tract = load_acs("tract", refresh).merge(
        fetch_tract_land_area(refresh), on="tract_geoid", how="left"
    )
    tract["pop_per_sqmi"] = (
        tract["population"] / tract["land_sqmi"].where(tract["land_sqmi"] > 0)
    ).round(1)
    county = load_acs("county", refresh)
    if boundaries:
        fetch_boundaries(refresh)

    if tract["population"].sum() != county["population"].sum():
        raise ValueError("Tract and county population totals differ")

    config.PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    tract.to_csv(config.PROCESSED_DIR / "acs_tract.csv", index=False)
    county.to_csv(config.PROCESSED_DIR / "acs_county.csv", index=False)
    print(f"ACS tracts: {len(tract)}, counties: {len(county)}")
    return {"tract": tract, "county": county}
