import sqlite3
from contextlib import contextmanager
from pathlib import Path
import pandas as pd
from config.settings import DB_PATH


SCHEMAS = {
    "zones": """CREATE TABLE IF NOT EXISTS zones (
        zone_id TEXT PRIMARY KEY, zone_name TEXT NOT NULL, building_type TEXT,
        latitude REAL, longitude REAL, map_x REAL, map_y REAL,
        access_point_count INTEGER, device_capacity INTEGER, bandwidth_capacity_mbps REAL)""",
    "network_metrics": """CREATE TABLE IF NOT EXISTS network_metrics (
        timestamp TEXT NOT NULL, zone_id TEXT NOT NULL, connected_users INTEGER, active_devices INTEGER,
        download_mbps REAL, upload_mbps REAL, download_data_mb REAL, upload_data_mb REAL,
        bandwidth_utilisation_pct REAL, latency_ms REAL, jitter_ms REAL, packet_loss_pct REAL,
        signal_strength_dbm REAL, active_access_points INTEGER, total_access_points INTEGER,
        availability_pct REAL, congestion_level TEXT, usability_score REAL, network_health_score REAL,
        PRIMARY KEY(timestamp, zone_id), FOREIGN KEY(zone_id) REFERENCES zones(zone_id))""",
    "devices": """CREATE TABLE IF NOT EXISTS devices (
        timestamp TEXT, synthetic_device_id TEXT, zone_id TEXT, device_type TEXT, operating_system TEXT,
        connection_status TEXT, session_duration_minutes REAL, download_mb REAL, upload_mb REAL,
        connection_count INTEGER, risk_score REAL, PRIMARY KEY(timestamp, synthetic_device_id))""",
    "flows": """CREATE TABLE IF NOT EXISTS flows (
        flow_id TEXT PRIMARY KEY, timestamp TEXT, zone_id TEXT, synthetic_device_id TEXT, source_ip TEXT,
        destination_ip TEXT, source_port INTEGER, destination_port INTEGER, protocol TEXT, flow_duration_ms REAL,
        bytes_sent INTEGER, bytes_received INTEGER, packets_sent INTEGER, packets_received INTEGER,
        connection_attempts INTEGER, unique_destination_ports INTEGER, dns_query_count INTEGER,
        average_dns_query_length REAL, failed_connection_count INTEGER, traffic_label TEXT)""",
    "security_events": """CREATE TABLE IF NOT EXISTS security_events (
        event_id TEXT PRIMARY KEY, timestamp TEXT, zone_id TEXT, synthetic_device_id TEXT, threat_type TEXT,
        severity TEXT, detection_method TEXT, anomaly_score REAL, confidence_description TEXT,
        event_description TEXT, recommended_action TEXT, event_status TEXT)""",
    "anomaly_results": """CREATE TABLE IF NOT EXISTS anomaly_results (
        flow_id TEXT PRIMARY KEY, timestamp TEXT, zone_id TEXT, anomaly_score REAL, prediction INTEGER,
        explanation TEXT, model_trained_at TEXT)""",
    "live_measurements": """CREATE TABLE IF NOT EXISTS live_measurements (
        timestamp TEXT, interface_name TEXT, upload_mbps REAL, download_mbps REAL, latency_ms REAL,
        signal_strength_pct REAL, bytes_sent INTEGER, bytes_received INTEGER)""",
    "app_settings": "CREATE TABLE IF NOT EXISTS app_settings (key TEXT PRIMARY KEY, value TEXT)"
}


class DatabaseManager:
    def __init__(self, path: Path = DB_PATH):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    @contextmanager
    def connect(self):
        con = sqlite3.connect(self.path, timeout=30)
        con.execute("PRAGMA foreign_keys=ON")
        try:
            yield con
            con.commit()
        except Exception:
            con.rollback()
            raise
        finally:
            con.close()

    def initialise(self):
        with self.connect() as con:
            for sql in SCHEMAS.values(): con.execute(sql)
            for table in ("network_metrics", "devices", "flows", "security_events", "anomaly_results"):
                con.execute(f"CREATE INDEX IF NOT EXISTS idx_{table}_timestamp ON {table}(timestamp)")
                if table != "anomaly_results": con.execute(f"CREATE INDEX IF NOT EXISTS idx_{table}_zone ON {table}(zone_id)")

    def replace(self, table: str, df: pd.DataFrame):
        if table not in SCHEMAS: raise ValueError("Unsupported table")
        with self.connect() as con:
            con.execute(f"DELETE FROM {table}")
            df.to_sql(table, con, if_exists="append", index=False, method="multi", chunksize=500)

    def append(self, table: str, df: pd.DataFrame):
        if table not in SCHEMAS: raise ValueError("Unsupported table")
        with self.connect() as con:
            df.to_sql(table, con, if_exists="append", index=False, method="multi", chunksize=500)

    def replace_simulation(self, datasets: dict[str, pd.DataFrame]):
        """Atomically replace related simulation tables in foreign-key-safe order."""
        allowed={"zones","network_metrics","devices","flows","security_events","anomaly_results"}
        if set(datasets)-allowed: raise ValueError("Unsupported simulation table")
        with self.connect() as con:
            for table in ("anomaly_results","security_events","flows","devices","network_metrics","zones"):
                con.execute(f"DELETE FROM {table}")
            for table in ("zones","network_metrics","devices","flows","security_events","anomaly_results"):
                frame=datasets.get(table)
                if frame is not None and not frame.empty:
                    frame.to_sql(table,con,if_exists="append",index=False,method="multi",chunksize=500)

    def read(self, table: str) -> pd.DataFrame:
        if table not in SCHEMAS: raise ValueError("Unsupported table")
        with self.connect() as con:
            return pd.read_sql_query(f"SELECT * FROM {table}", con)

    def count(self, table: str) -> int:
        if table not in SCHEMAS: raise ValueError("Unsupported table")
        with self.connect() as con:
            return con.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]

    def sync_zones(self, zones: pd.DataFrame):
        """Keep descriptive zone configuration current without rebuilding history."""
        columns=["zone_id","zone_name","building_type","latitude","longitude","map_x","map_y",
                 "access_point_count","device_capacity","bandwidth_capacity_mbps"]
        sql="""INSERT INTO zones (zone_id,zone_name,building_type,latitude,longitude,map_x,map_y,
                 access_point_count,device_capacity,bandwidth_capacity_mbps) VALUES (?,?,?,?,?,?,?,?,?,?)
                 ON CONFLICT(zone_id) DO UPDATE SET zone_name=excluded.zone_name,
                 building_type=excluded.building_type,latitude=excluded.latitude,longitude=excluded.longitude,
                 map_x=excluded.map_x,map_y=excluded.map_y,access_point_count=excluded.access_point_count,
                 device_capacity=excluded.device_capacity,bandwidth_capacity_mbps=excluded.bandwidth_capacity_mbps"""
        with self.connect() as con:
            con.executemany(sql,list(zones[columns].itertuples(index=False,name=None)))

