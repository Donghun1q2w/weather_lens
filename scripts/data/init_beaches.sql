-- Beaches table schema
-- Stores beach (해수욕장) data from KMA Beach Weather Service

CREATE TABLE IF NOT EXISTS beaches (
    beach_num INTEGER PRIMARY KEY,       -- Beach number from KMA data
    name TEXT NOT NULL,                  -- Beach name (한글)
    nx INTEGER NOT NULL,                 -- KMA grid X coordinate
    ny INTEGER NOT NULL,                 -- KMA grid Y coordinate
    lon REAL NOT NULL,                   -- Longitude (WGS84)
    lat REAL NOT NULL,                   -- Latitude (WGS84)

    -- Region mapping (determined by proximity)
    region_code TEXT,                    -- Nearest 읍면동 region code

    -- Marine zone mapping (inherited from region)
    marine_zone_code TEXT,               -- Marine forecast zone

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (region_code) REFERENCES regions(code),
    FOREIGN KEY (marine_zone_code) REFERENCES marine_zones(zone_code)
);

-- Indexes for efficient lookups
CREATE INDEX IF NOT EXISTS idx_beaches_region ON beaches(region_code);
CREATE INDEX IF NOT EXISTS idx_beaches_marine_zone ON beaches(marine_zone_code);
CREATE INDEX IF NOT EXISTS idx_beaches_coords ON beaches(lat, lon);
