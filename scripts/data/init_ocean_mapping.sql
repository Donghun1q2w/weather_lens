-- Ocean-Region Mapping Database Schema
-- Maps coastal regions to ocean observation stations

CREATE TABLE IF NOT EXISTS ocean_region_mapping (
    region_code TEXT PRIMARY KEY,           -- 읍면동 코드
    region_name TEXT NOT NULL,              -- 읍면동 이름
    ocean_station_id TEXT,                  -- 해양 관측소 ID (e.g., DT_0001)
    ocean_station_name TEXT,                -- 해양 관측소명
    distance_km REAL,                       -- 관측소까지 거리 (km)
    is_coastal BOOLEAN DEFAULT FALSE,       -- 해안선 30km 이내 여부
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Index for faster lookups
CREATE INDEX IF NOT EXISTS idx_coastal ON ocean_region_mapping(is_coastal);
CREATE INDEX IF NOT EXISTS idx_station ON ocean_region_mapping(ocean_station_id);

-- Sample data for reference (to be populated with actual data)
-- INSERT INTO ocean_region_mapping (region_code, region_name, ocean_station_id, ocean_station_name, distance_km, is_coastal)
-- VALUES
--   ('4671025000', '강원특별자치도 강릉시 주문진읍', 'DT_0001', '주문진항', 0.5, TRUE),
--   ('4671031000', '강원특별자치도 강릉시 강동면', 'DT_0001', '주문진항', 8.2, TRUE);
