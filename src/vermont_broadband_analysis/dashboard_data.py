"""Export the dashboard data bundle and render dashboard/web/index.html.

dashboard/web/app.html is the page source (no data). This step writes
data.json and a self-contained index.html with the data inlined, so the
dashboard opens straight from disk or any static host (e.g. GitHub Pages).
"""

import json

import pandas as pd

from . import config, places


def _records(df: pd.DataFrame, cols: list[str]) -> list[list]:
    return df[cols].astype(object).where(df[cols].notna(), None).values.tolist()


def run() -> dict:
    a = config.PROCESSED_DIR / "analysis"
    state = pd.read_csv(a / "statewide_summary.csv").iloc[0]
    county = pd.read_csv(a / "county_summary.csv", dtype={"county_fips": "string"})
    hexes = pd.read_csv(a / "h3_res8_summary.csv", dtype={"county_fips": "string"})
    tech = pd.read_csv(a / "technology_summary.csv")
    prov = pd.read_csv(a / "provider_summary.csv")
    comp = pd.read_csv(a / "competition_distribution.csv")

    hexes = hexes.copy()
    hexes["small_cell"] = hexes["small_cell"].astype(bool).astype(int)
    hexes["pct_below_100_20"] = (
        hexes["pct_underserved"] + hexes["pct_unserved"]
    ).round(2)
    hex_cols = [
        "h3_res8_id",
        "county_fips",
        "small_cell",
        "locations",
        "pct_below_100_20",
        "pct_served",
        "pct_unserved",
        "pct_has_fiber",
        "pct_no_wired_100_20",
        "pct_two_plus_wired_100_20",
        "median_best_reliable_download",
    ]

    county["pct_below_100_20"] = (
        county["pct_underserved"] + county["pct_unserved"]
    ).round(2)
    towns = places.load_towns()

    bundle = {
        "meta": {
            "fcc_vintage": config.FCC_DATA_VINTAGE,
            "fcc_source": "Source data: FCC Broadband Data Collection (fixed availability, Vermont, data as of Dec 31, 2025)",
            "census_source": "U.S. Census Bureau: ACS 2020-2024 5-year estimates, 2024 Gazetteer, TIGERweb",
            "min_cell_locations": 5,
        },
        "kpis": {k: (float(v) if pd.notna(v) else None) for k, v in state.items()},
        "hex_columns": hex_cols,
        "hexes": _records(hexes, hex_cols),
        "counties": county.to_dict(orient="records"),
        "counties_geojson": places.load_county_geojson(),
        "towns": towns[
            ["name", "kind", "county_fips", "population", "lat", "lon"]
        ].values.tolist(),
        "technology": tech.to_dict(orient="records"),
        "providers": prov.to_dict(orient="records"),
        "competition": comp.to_dict(orient="records"),
    }

    tract_path = a / "tract_fcc_acs.csv"
    if tract_path.exists():
        tract = pd.read_csv(tract_path, dtype={"tract_geoid": "string"})
        acs_county = pd.read_csv(
            config.PROCESSED_DIR / "acs_county.csv", dtype={"county_fips": "string"}
        )
        acs_tract = pd.read_csv(
            config.PROCESSED_DIR / "acs_tract.csv",
            dtype={"county_fips": "string", "tract_geoid": "string"},
        )
        need = places.county_need_index(county, acs_county, acs_tract)
        need.to_csv(a / "county_need_index.csv", index=False)
        bundle["need"] = need[
            [
                "county_fips",
                "county_name",
                "need_index",
                "need_rank",
                "priority",
                "pct_below_100_20",
                "pct_no_wired_100_20",
                "pct_hh_no_broadband",
                "pop_per_sqmi",
                "population",
                "median_household_income",
                "need_gap",
                "need_choice",
                "need_adoption",
                "need_rurality",
                "level_gap",
                "level_choice",
                "level_adoption",
                "level_rurality",
            ]
        ].to_dict(orient="records")
        tract_cols = [
            "tract_geoid",
            "county_name",
            "locations",
            "pct_served",
            "pct_unserved",
            "pct_no_wired_100_20",
            "pct_has_fiber",
            "population",
            "median_household_income",
            "pct_hh_broadband",
            "pct_hh_wired_broadband",
            "pct_hh_no_internet",
            "pct_below_poverty",
            "pop_per_sqmi",
            "density_class",
            "income_quartile",
        ]
        bundle["tract_columns"] = tract_cols
        bundle["tracts"] = _records(tract, tract_cols)
        bundle["county_acs"] = acs_county[
            [
                "county_fips",
                "population",
                "median_household_income",
                "pct_hh_broadband",
                "pct_hh_no_internet",
                "pct_below_poverty",
            ]
        ].to_dict(orient="records")
        bundle["spearman"] = pd.read_csv(a / "spearman_fcc_vs_acs.csv").to_dict(
            orient="records"
        )
        bundle["spearman_adoption"] = pd.read_csv(a / "spearman_adoption.csv").to_dict(
            orient="records"
        )
        bundle["by_density"] = pd.read_csv(a / "access_by_density_class.csv").to_dict(
            orient="records"
        )
        bundle["by_income"] = pd.read_csv(a / "access_by_income_quartile.csv").to_dict(
            orient="records"
        )

    out = config.DASHBOARD_DIR / "web" / "data.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(bundle, separators=(",", ":"), allow_nan=False, default=str)
    )
    print(f"Dashboard data written to {out} ({out.stat().st_size / 1e6:.2f} MB)")
    render(bundle)
    return bundle


def render(bundle: dict) -> None:
    web = config.DASHBOARD_DIR / "web"
    app = (web / "app.html").read_text()
    data = json.dumps(
        bundle, separators=(",", ":"), allow_nan=False, default=str
    ).replace("</", "<\\/")
    head, body = app.replace("/*__DATA__*/", data).split('<div class="wrap">', 1)
    page = (
        '<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
        + head
        + '</head>\n<body>\n<div class="wrap">'
        + body
        + "\n</body>\n</html>\n"
    )
    (web / "index.html").write_text(page)
    print(f"Dashboard page written to {web / 'index.html'}")
