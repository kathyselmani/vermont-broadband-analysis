"""Join FCC availability (tract level) with ACS indicators and describe
associations. Results are descriptive: correlation is not causation, and
ACS estimates carry sampling error (MOEs are kept in the joined table)."""

import pandas as pd

from . import config

FCC_METRICS = {
    "pct_served": "% locations served (100/20 reliable)",
    "pct_unserved": "% locations unserved (<25/3 reliable)",
    "pct_no_wired_100_20": "% locations with no wired 100/20 option",
    "pct_two_plus_wired_100_20": "% locations with 2+ wired 100/20 providers",
    "pct_has_fiber": "% locations with fiber",
}
ACS_METRICS = {
    "median_household_income": "Median household income",
    "pop_per_sqmi": "Population density (per sq mi)",
    "pct_below_poverty": "% below poverty",
    "median_age": "Median age",
    "pct_hh_broadband": "% households with broadband subscription (adoption)",
    "pct_hh_no_internet": "% households with no internet access",
}


def density_class(pop_per_sqmi: pd.Series) -> pd.Series:
    return pd.cut(
        pop_per_sqmi,
        bins=[-1, 50, 200, 1000, float("inf")],
        labels=[
            "Very rural (<50/sq mi)",
            "Rural (50-200)",
            "Small town (200-1,000)",
            "Urban (>1,000)",
        ],
    )


def income_quartile(income: pd.Series) -> pd.Series:
    return pd.qcut(income, 4, labels=["Q1 (lowest)", "Q2", "Q3", "Q4 (highest)"])


def run() -> dict[str, pd.DataFrame]:
    acs_path = config.PROCESSED_DIR / "acs_tract.csv"
    if not acs_path.exists():
        raise FileNotFoundError(
            "Run the 'census' step first (data/processed/acs_tract.csv missing)"
        )

    fcc = pd.read_csv(
        config.PROCESSED_DIR / "analysis" / "tract_summary.csv",
        dtype={"tract_geoid": "string"},
    )
    acs = pd.read_csv(
        acs_path, dtype={"tract_geoid": "string", "county_fips": "string"}
    )
    tract = fcc.merge(acs, on="tract_geoid", how="outer", indicator=True)

    unmatched = tract[tract["_merge"] != "both"]
    if len(unmatched):
        print(f"Warning: {len(unmatched)} tracts not matched between FCC and ACS:")
        print(
            unmatched[["tract_geoid", "_merge", "locations", "population"]].to_string(
                index=False
            )
        )
    tract = tract[tract["_merge"] == "both"].drop(columns="_merge")

    tract["density_class"] = density_class(tract["pop_per_sqmi"])
    tract["income_quartile"] = income_quartile(tract["median_household_income"])

    corr = (
        tract[list(FCC_METRICS) + list(ACS_METRICS)]
        .corr(method="spearman")
        .loc[list(FCC_METRICS), list(ACS_METRICS)]
        .round(3)
    )

    # Adoption (ACS household subscriptions) vs. demographics and availability
    adoption_cols = [
        "pct_hh_broadband",
        "pct_hh_wired_broadband",
        "pct_hh_no_internet",
        "pct_hh_no_computer",
    ]
    adoption_corr = (
        tract[
            adoption_cols
            + [
                "median_household_income",
                "pop_per_sqmi",
                "pct_below_poverty",
                "median_age",
                "pct_served",
            ]
        ]
        .corr(method="spearman")
        .loc[
            adoption_cols,
            [
                "median_household_income",
                "pop_per_sqmi",
                "pct_below_poverty",
                "median_age",
                "pct_served",
            ],
        ]
        .round(3)
    )

    def by_group(col: str) -> pd.DataFrame:
        g = tract.groupby(col, observed=True)
        out = g[
            [
                "locations",
                "served",
                "unserved",
                "no_wired_100_20",
                "has_fiber",
                "two_plus_wired_100_20",
            ]
        ].sum()
        for c in [
            "served",
            "unserved",
            "no_wired_100_20",
            "has_fiber",
            "two_plus_wired_100_20",
        ]:
            out[f"pct_{c}"] = (out[c] / out["locations"] * 100).round(2)
        out["tracts"] = g.size()
        out["median_income"] = g["median_household_income"].median()
        out["pct_hh_broadband_median"] = g["pct_hh_broadband"].median()
        # household-weighted adoption for the group
        out["pct_hh_broadband"] = (
            g["hh_broadband_any_type"].sum() / g["households"].sum() * 100
        ).round(2)
        out["pct_hh_wired_broadband"] = (
            g["hh_broadband_cable_fiber_dsl"].sum() / g["households"].sum() * 100
        ).round(2)
        out["population"] = g["population"].sum()
        return out.reset_index()

    tables = {
        "tract_fcc_acs": tract,
        "spearman_fcc_vs_acs": corr.reset_index(names="fcc_metric"),
        "spearman_adoption": adoption_corr.reset_index(names="adoption_metric"),
        "access_by_density_class": by_group("density_class"),
        "access_by_income_quartile": by_group("income_quartile"),
    }
    out_dir = config.PROCESSED_DIR / "analysis"
    for name, table in tables.items():
        table.to_csv(out_dir / f"{name}.csv", index=False)
    print(corr.to_string())
    print(adoption_corr.to_string())
    print(tables["access_by_density_class"].to_string())
    print(tables["access_by_income_quartile"].to_string())
    return tables
