"""Profile, validate and combine the FCC BDC fixed broadband files for Vermont."""

import hashlib
from pathlib import Path

import pandas as pd

from . import config


def read_fcc_csv(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path, dtype=config.FCC_DTYPES)
    if df.columns.tolist() != config.EXPECTED_COLUMNS:
        raise ValueError(f"Schema mismatch in {path.name}")
    return df


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def list_csv_files() -> list[Path]:
    files = sorted(config.RAW_FCC_DIR.glob("*.csv"))
    if not files:
        raise FileNotFoundError(f"No FCC CSV files found in {config.RAW_FCC_DIR}")
    return files


def profile_csv(path: Path) -> dict:
    df = read_fcc_csv(path)
    geoid = df["block_geoid"]
    zip_path = path.with_suffix(".zip")
    return {
        "file_name": path.name,
        "zip_sha256": sha256(zip_path) if zip_path.exists() else None,
        "rows": len(df),
        "technology_codes": sorted(df["technology"].unique().tolist()),
        "states": sorted(df["state_usps"].dropna().unique().tolist()),
        "providers": df["provider_id"].nunique(),
        "brands": df["brand_name"].nunique(),
        "unique_locations": df["location_id"].nunique(),
        "full_duplicates": int(df.duplicated().sum()),
        "missing_values": int(df.isna().sum().sum()),
        "candidate_key_duplicates": int(
            df.duplicated(subset=config.CANDIDATE_KEY).sum()
        ),
        # Same location/provider/technology listed under more than one
        # business_residential_code (seen in GSO satellite and licensed FW).
        "location_provider_tech_repeats": int(
            df.duplicated(subset=["location_id", "provider_id", "technology"]).sum()
        ),
        "low_latency_values": sorted(df["low_latency"].unique().tolist()),
        "business_residential_codes": sorted(
            df["business_residential_code"].dropna().unique().tolist()
        ),
        "invalid_block_geoid_length": int((geoid.str.len() != 15).sum()),
        "non_vermont_block_geoids": int(
            (~geoid.str.startswith(config.VERMONT_STATE_FIPS)).sum()
        ),
        "max_download_mbps": int(df["max_advertised_download_speed"].max()),
        "min_download_mbps": int(df["max_advertised_download_speed"].min()),
    }


def profile() -> pd.DataFrame:
    results = []
    for path in list_csv_files():
        print(f"Profiling: {path.name}")
        results.append(profile_csv(path))
    inventory = pd.DataFrame(results)
    config.PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    out = config.PROCESSED_DIR / "fcc_file_inventory.csv"
    inventory.to_csv(out, index=False)
    print(inventory.drop(columns=["zip_sha256"]).to_string(index=False))
    print(f"\nInventory saved to: {out}")
    return inventory


def validate(df: pd.DataFrame, name: str) -> None:
    if set(df["state_usps"].dropna().unique()) != {"VT"}:
        raise ValueError(f"Unexpected state values in {name}")
    if df.isna().any().any():
        raise ValueError(f"Missing values in {name}")
    dupes = int(df.duplicated(subset=config.CANDIDATE_KEY).sum())
    if dupes:
        raise ValueError(f"{name} contains {dupes} candidate-key duplicates")
    if not df["block_geoid"].str.fullmatch(r"50\d{13}").all():
        raise ValueError(f"{name} contains invalid Vermont block GEOIDs")
    if not set(df["business_residential_code"].unique()) <= {"R", "B", "X"}:
        raise ValueError(f"{name} contains unknown business_residential_code values")


def build() -> pd.DataFrame:
    frames = []
    for path in list_csv_files():
        print(f"Loading: {path.name}")
        df = read_fcc_csv(path)
        validate(df, path.name)
        df["technology_name"] = df["technology"].map(config.TECHNOLOGY_NAMES)
        if df["technology_name"].isna().any():
            raise ValueError(f"Unknown technology code in {path.name}")
        df["source_file"] = path.name
        df["data_vintage"] = config.FCC_DATA_VINTAGE
        frames.append(df)

    broadband = pd.concat(frames, ignore_index=True)
    validate(broadband, "combined dataset")

    print(f"\nCombined rows: {len(broadband):,}")
    print(f"Unique locations: {broadband['location_id'].nunique():,}")
    print("\nRows by technology:")
    print(broadband["technology_name"].value_counts().sort_index().to_string())

    config.PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    broadband.to_parquet(config.FCC_COMBINED_PARQUET, index=False)
    print(f"\nSaved to: {config.FCC_COMBINED_PARQUET}")
    return broadband
