from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
MODEL_DIR = ROOT / "models"
REPORT_DIR = ROOT / "reports"
DB_PATH = DATA_DIR / "network_usage.db"
MODEL_PATH = MODEL_DIR / "isolation_forest.joblib"
CAMPUS_CONFIG_PATH = ROOT / "config" / "campus.json"
RANDOM_SEED = 2647122
INTERVAL_MINUTES = 15
HISTORY_DAYS = 30

USABILITY_WEIGHTS = {
    "latency": 0.20, "packet_loss": 0.20, "signal": 0.20,
    "congestion": 0.20, "availability": 0.15, "jitter": 0.05,
}

ANOMALY_FEATURES = [
    "bytes_sent", "bytes_received", "packets_sent", "packets_received",
    "connection_attempts", "unique_destination_ports", "dns_query_count",
    "average_dns_query_length", "failed_connection_count", "flow_duration_ms",
]

for directory in (DATA_DIR, MODEL_DIR, REPORT_DIR):
    directory.mkdir(parents=True, exist_ok=True)

