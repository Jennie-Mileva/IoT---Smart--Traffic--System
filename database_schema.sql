-- ============================================================
-- IoT Smart Traffic Management System
-- Database Schema
-- Team 3
-- ============================================================

-- Create and use the database
CREATE DATABASE IF NOT EXISTS smart_traffic;
USE smart_traffic;

-- ─────────────────────────────────────────────
-- TABLE 1: intersections
-- Stores the 4 fixed intersection nodes
-- ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS intersections (
    id          VARCHAR(5)  PRIMARY KEY,        -- e.g. 'I-A'
    label       VARCHAR(20) NOT NULL,           -- e.g. 'North'
    pos_x       FLOAT       NOT NULL,           -- grid x coordinate
    pos_y       FLOAT       NOT NULL,           -- grid y coordinate
    created_at  TIMESTAMP   DEFAULT CURRENT_TIMESTAMP
);

-- Insert the 4 intersections
INSERT IGNORE INTO intersections (id, label, pos_x, pos_y) VALUES
    ('I-A', 'North', 0.0, 1.0),
    ('I-B', 'East',  1.0, 2.0),
    ('I-C', 'West',  0.0, 0.0),
    ('I-D', 'South', 1.0, 1.0);

-- ─────────────────────────────────────────────
-- TABLE 2: traffic_readings
-- Every tick, one row per intersection is saved
-- ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS traffic_readings (
    id              INT         AUTO_INCREMENT PRIMARY KEY,
    intersection_id VARCHAR(5)  NOT NULL,
    tick            INT         NOT NULL,           -- simulation tick number
    volume          FLOAT       NOT NULL,           -- vehicles per minute
    congestion_level VARCHAR(10) NOT NULL,          -- LOW / MEDIUM / HIGH
    signal_timing   INT         NOT NULL,           -- green phase in seconds
    recorded_at     TIMESTAMP   DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (intersection_id) REFERENCES intersections(id)
);

-- Index for fast queries by intersection and time
CREATE INDEX idx_intersection_tick ON traffic_readings(intersection_id, tick);
CREATE INDEX idx_recorded_at       ON traffic_readings(recorded_at);

-- ─────────────────────────────────────────────
-- TABLE 3: reroute_events
-- Logged whenever congestion triggers rerouting
-- ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS reroute_events (
    id                  INT         AUTO_INCREMENT PRIMARY KEY,
    tick                INT         NOT NULL,
    congested_node      VARCHAR(5)  NOT NULL,
    volume_at_trigger   FLOAT       NOT NULL,
    alternate_routes    TEXT        NOT NULL,   -- comma-separated route names
    astar_path          VARCHAR(100),           -- e.g. 'I-A -> I-C -> I-D'
    astar_cost          FLOAT,
    triggered_at        TIMESTAMP   DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (congested_node) REFERENCES intersections(id)
);

-- ─────────────────────────────────────────────
-- TABLE 4: emergency_events
-- Logged whenever an emergency vehicle is triggered
-- ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS emergency_events (
    id              INT         AUTO_INCREMENT PRIMARY KEY,
    tick            INT         NOT NULL,
    intersection_id VARCHAR(5)  NOT NULL,
    diverted_routes TEXT        NOT NULL,   -- which routes were cleared
    triggered_at    TIMESTAMP   DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (intersection_id) REFERENCES intersections(id)
);

-- ─────────────────────────────────────────────
-- TABLE 5: system_events
-- General event log (INFO / ALERT / SUCCESS)
-- ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS system_events (
    id          INT         AUTO_INCREMENT PRIMARY KEY,
    tick        INT         NOT NULL,
    level       VARCHAR(10) NOT NULL,       -- INFO / ALERT / SUCCESS
    message     TEXT        NOT NULL,
    logged_at   TIMESTAMP   DEFAULT CURRENT_TIMESTAMP
);

-- ─────────────────────────────────────────────
-- USEFUL VIEWS
-- ─────────────────────────────────────────────

-- View: Latest reading per intersection
CREATE OR REPLACE VIEW latest_readings AS
    SELECT t.*
    FROM traffic_readings t
    INNER JOIN (
        SELECT intersection_id, MAX(tick) AS max_tick
        FROM traffic_readings
        GROUP BY intersection_id
    ) latest ON t.intersection_id = latest.intersection_id
           AND t.tick = latest.max_tick;

-- View: Congestion summary
CREATE OR REPLACE VIEW congestion_summary AS
    SELECT
        intersection_id,
        COUNT(*) AS total_readings,
        SUM(CASE WHEN congestion_level = 'HIGH'   THEN 1 ELSE 0 END) AS high_count,
        SUM(CASE WHEN congestion_level = 'MEDIUM' THEN 1 ELSE 0 END) AS medium_count,
        SUM(CASE WHEN congestion_level = 'LOW'    THEN 1 ELSE 0 END) AS low_count,
        ROUND(AVG(volume), 2) AS avg_volume,
        ROUND(MAX(volume), 2) AS peak_volume
    FROM traffic_readings
    GROUP BY intersection_id;
