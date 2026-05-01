-- Ocean Observation Stations Database Schema
-- Stores KHOA (Korea Hydrographic and Oceanographic Agency) observation station data

CREATE TABLE IF NOT EXISTS ocean_stations (
    station_id TEXT PRIMARY KEY,        -- Station ID (e.g., DT_0001, TW_0069, IE_0062)
    station_name TEXT NOT NULL,         -- Station name in Korean
    station_type TEXT NOT NULL,         -- Station type: 'tide', 'wave', 'buoy'
    lat REAL NOT NULL,                  -- Latitude
    lon REAL NOT NULL,                  -- Longitude
    provides_tide INTEGER DEFAULT 0,    -- Provides tide data (0 or 1)
    provides_wave INTEGER DEFAULT 0,    -- Provides wave data (0 or 1)
    provides_temp INTEGER DEFAULT 0,    -- Provides water temperature data (0 or 1)
    region_code TEXT,                   -- Linked region code (읍면동)
    marine_zone_code TEXT,              -- Linked marine zone code
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (marine_zone_code) REFERENCES marine_zones(zone_code)
);

-- Indexes for faster lookups
CREATE INDEX IF NOT EXISTS idx_ocean_stations_type ON ocean_stations(station_type);
CREATE INDEX IF NOT EXISTS idx_ocean_stations_zone ON ocean_stations(marine_zone_code);
CREATE INDEX IF NOT EXISTS idx_ocean_stations_tide ON ocean_stations(provides_tide);
CREATE INDEX IF NOT EXISTS idx_ocean_stations_wave ON ocean_stations(provides_wave);
