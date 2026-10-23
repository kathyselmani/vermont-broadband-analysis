CREATE TABLE IF NOT EXISTS fcc_fixed_broadband (
    frn CHAR(10) NOT NULL,
    provider_id BIGINT NOT NULL,
    brand_name TEXT NOT NULL,
    location_id BIGINT NOT NULL,
    technology SMALLINT NOT NULL,
    technology_name TEXT NOT NULL,

    max_advertised_download_speed INTEGER NOT NULL,
    max_advertised_upload_speed INTEGER NOT NULL,

    low_latency SMALLINT NOT NULL,

    business_residential_code CHAR(1) NOT NULL,

    state_usps CHAR(2) NOT NULL,

    block_geoid CHAR(15) NOT NULL,
    h3_res8_id TEXT NOT NULL,

    source_file TEXT NOT NULL,
    data_vintage DATE NOT NULL,

    CONSTRAINT chk_business_residential
        CHECK (business_residential_code IN ('B', 'R', 'X')),

    CONSTRAINT chk_state
        CHECK (state_usps = 'VT'),

    CONSTRAINT uq_fcc_availability_record
        UNIQUE (
            location_id,
            provider_id,
            technology,
            business_residential_code
        )
);
CREATE INDEX IF NOT EXISTS idx_fcc_location
ON fcc_fixed_broadband (location_id);

CREATE INDEX IF NOT EXISTS idx_fcc_provider
ON fcc_fixed_broadband (provider_id);

CREATE INDEX IF NOT EXISTS idx_fcc_technology
ON fcc_fixed_broadband (technology);

CREATE INDEX IF NOT EXISTS idx_fcc_block_geoid
ON fcc_fixed_broadband (block_geoid);

CREATE INDEX IF NOT EXISTS idx_fcc_residential
ON fcc_fixed_broadband (business_residential_code);