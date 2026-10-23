"""Project-wide constants: paths, FCC code lists and analytical thresholds."""

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]

DATA_DIR = PROJECT_ROOT / "data"
RAW_FCC_DIR = DATA_DIR / "raw" / "fcc" / "2025-12-31"
RAW_CENSUS_DIR = DATA_DIR / "raw" / "census"
REFERENCE_DIR = DATA_DIR / "reference"
PROCESSED_DIR = DATA_DIR / "processed"
DASHBOARD_DIR = PROJECT_ROOT / "dashboard"

FCC_DATA_VINTAGE = "2025-12-31"
FCC_COMBINED_PARQUET = PROCESSED_DIR / "fcc_fixed_broadband_vermont_2025_12_31.parquet"

# The "50" in FCC file names (bdc_50_...) is the state FIPS code for Vermont.
# It is NOT the technology code.
VERMONT_STATE_FIPS = "50"

EXPECTED_COLUMNS = [
    "frn",
    "provider_id",
    "brand_name",
    "location_id",
    "technology",
    "max_advertised_download_speed",
    "max_advertised_upload_speed",
    "low_latency",
    "business_residential_code",
    "state_usps",
    "block_geoid",
    "h3_res8_id",
]

# Read identifiers as text so GEOIDs never lose leading zeros.
FCC_DTYPES = {
    "frn": "string",  # 10-digit FCC Registration Number; keep leading zeros
    "provider_id": "int64",
    "brand_name": "string",
    "location_id": "int64",
    "technology": "int16",
    "max_advertised_download_speed": "int32",
    "max_advertised_upload_speed": "int32",
    "low_latency": "int8",
    "business_residential_code": "string",
    "state_usps": "string",
    "block_geoid": "string",
    "h3_res8_id": "string",
}

# Grain of every FCC availability file (validated in notebooks 01 and 02).
CANDIDATE_KEY = [
    "location_id",
    "provider_id",
    "technology",
    "business_residential_code",
]

# FCC BDC technology codes.
TECHNOLOGY_NAMES = {
    10: "Copper",
    40: "Cable",
    50: "Fiber to the Premises",
    60: "GSO Satellite",
    61: "NGSO Satellite",
    70: "Unlicensed Fixed Wireless",
    71: "Licensed Fixed Wireless",
    72: "LBR Fixed Wireless",
}

WIRED_TECH = [10, 40, 50]
FIXED_WIRELESS_TECH = [70, 71, 72]
SATELLITE_TECH = [60, 61]
TERRESTRIAL_TECH = WIRED_TECH + FIXED_WIRELESS_TECH

# "Reliable" technologies follow the NTIA BEAD definition: fiber, cable,
# copper/DSL and licensed (incl. licensed-by-rule) fixed wireless.
# Satellite and unlicensed fixed wireless are excluded.
RELIABLE_TECH = [10, 40, 50, 71, 72]

# Business/residential codes: R = residential only, B = business only,
# X = both residential and business service offered.
RESIDENTIAL_CODES = ["R", "X"]

# Speed thresholds (Mbps), FCC/BEAD service tiers.
SERVED_DOWN, SERVED_UP = 100, 20
MIN_DOWN, MIN_UP = 25, 3
GIGABIT_DOWN = 1000

VERMONT_COUNTIES = {
    "50001": "Addison",
    "50003": "Bennington",
    "50005": "Caledonia",
    "50007": "Chittenden",
    "50009": "Essex",
    "50011": "Franklin",
    "50013": "Grand Isle",
    "50015": "Lamoille",
    "50017": "Orange",
    "50019": "Orleans",
    "50021": "Rutland",
    "50023": "Washington",
    "50025": "Windham",
    "50027": "Windsor",
}
