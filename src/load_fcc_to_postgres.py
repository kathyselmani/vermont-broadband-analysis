"""Load the combined FCC Parquet file into PostgreSQL (optional SQL layer).

Create the table first with sql/schema/001_create_fcc_fixed_broadband.sql.
Connection string comes from the DATABASE_URL environment variable
(default: "dbname=vermont_broadband").
"""

import os
from io import StringIO

import pandas as pd
import psycopg

from vermont_broadband_analysis.config import FCC_COMBINED_PARQUET as PARQUET_PATH

DATABASE_URL = os.environ.get("DATABASE_URL", "dbname=vermont_broadband")

TABLE_NAME = "fcc_fixed_broadband"


def main():
    print("Reading Parquet...")
    df = pd.read_parquet(PARQUET_PATH)

    print(f"Rows to load: {len(df):,}")

    # PostgreSQL expects dates cleanly formatted
    df["data_vintage"] = pd.to_datetime(df["data_vintage"]).dt.date

    columns = [
        "frn",
        "provider_id",
        "brand_name",
        "location_id",
        "technology",
        "technology_name",
        "max_advertised_download_speed",
        "max_advertised_upload_speed",
        "low_latency",
        "business_residential_code",
        "state_usps",
        "block_geoid",
        "h3_res8_id",
        "source_file",
        "data_vintage",
    ]

    df = df[columns]

    print("Connecting to PostgreSQL...")

    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            # Prevent accidental double-loading
            cur.execute(f"SELECT COUNT(*) FROM {TABLE_NAME}")

            existing_rows = cur.fetchone()[0]

            if existing_rows != 0:
                raise RuntimeError(
                    f"{TABLE_NAME} already contains "
                    f"{existing_rows:,} rows. Load aborted."
                )

            print("Loading data...")

            with cur.copy(
                f"""
                COPY {TABLE_NAME} (
                    {", ".join(columns)}
                )
                FROM STDIN
                WITH (FORMAT CSV, HEADER TRUE)
                """
            ) as copy:
                buffer = StringIO()

                df.to_csv(
                    buffer,
                    index=False,
                )

                buffer.seek(0)

                while data := buffer.read(1024 * 1024):
                    copy.write(data)

        conn.commit()

    print("Load completed successfully.")


if __name__ == "__main__":
    main()
