import json
from pathlib import Path
import numpy as np
import pandas as pd
from config.settings import ROOT, RANDOM_SEED, HISTORY_DAYS, INTERVAL_MINUTES
from core.usability_engine import UsabilityCalculator


class CampusDataGenerator:
    """Reproducible, correlated simulation; locations and capacities are illustrative."""
    def __init__(self, seed=RANDOM_SEED, days=HISTORY_DAYS):
        self.seed, self.days = seed, days
        self.rng = np.random.default_rng(seed)
        self.zones_config = json.loads((ROOT / "config" / "zones.json").read_text())

    def zones(self):
        return pd.DataFrame(self.zones_config).drop(columns=["pattern"])

    def _occupancy(self, ts, pattern):
        h, weekday = ts.hour + ts.minute / 60, ts.weekday() < 5
        academic = np.exp(-((h - 12.5) / 4.2) ** 2) * (1 if weekday else .28)
        profiles = {
            "academic": .04 + .82 * academic,
            "library": .08 + .58 * np.exp(-((h - 14) / 5) ** 2) * (1 if weekday else .55),
            "laboratory": .04 + .88 * np.exp(-((h - 13.5) / 3.8) ** 2) * (1 if weekday else .18),
            "cafeteria": .04 + .78 * np.exp(-((h - 13) / 1.7) ** 2),
            "hostel": .12 + .70 * np.exp(-((h - 21) / 4) ** 2),
            "events": .03 + .25 * academic,
            "outdoor": .02 + .30 * np.exp(-((h - 17) / 3) ** 2),
        }
        return profiles.get(pattern, .1)

    def generate_metrics(self, end=None):
        end = pd.Timestamp(end or pd.Timestamp.now()).floor("15min")
        times = pd.date_range(end=end, periods=self.days * 24 * 60 // INTERVAL_MINUTES, freq=f"{INTERVAL_MINUTES}min")
        rows = []
        for zone in self.zones_config:
            for ts in times:
                occ = np.clip(self._occupancy(ts, zone["pattern"]) + self.rng.normal(0, .035), .01, 1.08)
                devices = int(np.clip(zone["device_capacity"] * occ, 1, zone["device_capacity"] * 1.08))
                users = int(devices * self.rng.uniform(.72, .91))
                capacity = zone["bandwidth_capacity_mbps"]
                throughput = np.clip(devices * self.rng.uniform(.45, 1.25), 1, capacity * 1.12)
                util = throughput / capacity * 100
                outage = self.rng.random() < .0015
                aps = max(0, zone["access_point_count"] - (1 if outage else 0))
                availability = aps / zone["access_point_count"] * 100
                latency = np.clip(12 + .007 * devices + max(0, util - 65) * .85 + self.rng.normal(0, 3), 4, 180)
                jitter = np.clip(2 + latency * .09 + self.rng.normal(0, 1.3), .2, 40)
                loss = np.clip(max(0, util - 72) * .055 + (100 - availability) * .08 + self.rng.normal(.08, .12), 0, 12)
                signal = np.clip(-48 - occ * 18 + self.rng.normal(0, 4), -92, -35)
                down = throughput * self.rng.uniform(.72, .88)
                up = throughput - down
                rows.append({"timestamp": ts.isoformat(), "zone_id": zone["zone_id"], "connected_users": users,
                    "active_devices": devices, "download_mbps": round(down,2), "upload_mbps": round(up,2),
                    "download_data_mb": round(down * 900 / 8,2), "upload_data_mb": round(up * 900 / 8,2),
                    "bandwidth_utilisation_pct": round(util,2), "latency_ms": round(latency,2),
                    "jitter_ms": round(jitter,2), "packet_loss_pct": round(loss,3), "signal_strength_dbm": round(signal,2),
                    "active_access_points": aps, "total_access_points": zone["access_point_count"],
                    "availability_pct": round(availability,2), "congestion_level": "High" if util>=80 else "Medium" if util>=60 else "Low"})
        df = pd.DataFrame(rows)
        df["usability_score"] = UsabilityCalculator().calculate(df)
        df["network_health_score"] = (df["usability_score"] * .75 + df["availability_pct"] * .25).clip(0,100).round(2)
        return df

    def generate_devices(self, metrics, per_timestamp=5):
        types = ["Smartphone","Laptop","Tablet","Desktop","IoT","Other"]
        os_map = {"Smartphone":["Android","iOS"],"Laptop":["Windows","macOS","Linux"],"Tablet":["Android","iOS"],
                  "Desktop":["Windows","Linux"],"IoT":["Other","Linux"],"Other":["Other"]}
        # A sampled longitudinal device dataset keeps the demo responsive while preserving trends.
        sample = metrics.iloc[::4].copy()
        rows=[]; counter=0
        for r in sample.itertuples():
            for _ in range(per_timestamp):
                counter += 1; dtype=self.rng.choice(types,p=[.38,.34,.10,.08,.07,.03]); did=f"DEV-{r.zone_id}-{(counter % 150)+1:03d}"
                rows.append({"timestamp":r.timestamp,"synthetic_device_id":did,"zone_id":r.zone_id,"device_type":dtype,
                    "operating_system":self.rng.choice(os_map[dtype]),"connection_status":self.rng.choice(["Active","Inactive"],p=[.88,.12]),
                    "session_duration_minutes":round(float(self.rng.gamma(2.2,35)),2),"download_mb":round(float(self.rng.lognormal(4,1)),2),
                    "upload_mb":round(float(self.rng.lognormal(2.7,.9)),2),"connection_count":int(self.rng.poisson(8)+1),
                    "risk_score":round(float(np.clip(self.rng.beta(1.5,7)*100,0,100)),2)})
        return pd.DataFrame(rows)

    def generate_flows(self, metrics, count=12000):
        pick = metrics.sample(n=min(count,len(metrics)), replace=count>len(metrics), random_state=self.seed)
        rows=[]
        for i, r in enumerate(pick.itertuples()):
            attack = self.rng.random() < .055
            label = self.rng.choice(["Port Scan","DoS","DNS Tunnelling","Data Exfiltration","Failed Connections"]) if attack else "Normal"
            conn=int(self.rng.poisson(15)); ports=int(self.rng.poisson(3)); dns=int(self.rng.poisson(5)); qlen=float(self.rng.normal(22,5)); failed=int(self.rng.poisson(2))
            sent=int(self.rng.lognormal(12,1)); received=int(self.rng.lognormal(13,1)); packets=max(2,int((sent+received)/self.rng.uniform(650,1300)))
            if label=="Port Scan": ports,conn,failed=int(self.rng.integers(30,100)),int(self.rng.integers(80,220)),int(self.rng.integers(15,50))
            elif label=="DoS": conn,packets=int(self.rng.integers(300,800)),int(self.rng.integers(10000,30000))
            elif label=="DNS Tunnelling": dns,qlen=int(self.rng.integers(100,280)),float(self.rng.integers(60,120))
            elif label=="Data Exfiltration": sent=int(self.rng.integers(55_000_000,180_000_000))
            elif label=="Failed Connections": failed=int(self.rng.integers(40,100))
            rows.append({"flow_id":f"FLOW-{i+1:07d}","timestamp":r.timestamp,"zone_id":r.zone_id,"synthetic_device_id":f"DEV-{self.rng.integers(1,1801):05d}",
                "source_ip":f"192.0.2.{self.rng.integers(1,255)}","destination_ip":f"198.51.100.{self.rng.integers(1,255)}",
                "source_port":int(self.rng.integers(1024,65535)),"destination_port":int(self.rng.choice([53,80,443,123,8080])),
                "protocol":str(self.rng.choice(["TCP","UDP","DNS"],p=[.65,.23,.12])),"flow_duration_ms":round(float(self.rng.lognormal(7.5,1)),2),
                "bytes_sent":sent,"bytes_received":received,"packets_sent":packets,"packets_received":max(1,int(packets*self.rng.uniform(.7,1.3))),
                "connection_attempts":conn,"unique_destination_ports":ports,"dns_query_count":dns,"average_dns_query_length":round(qlen,2),
                "failed_connection_count":failed,"traffic_label":label})
        return pd.DataFrame(rows)

    def generate_all(self):
        metrics=self.generate_metrics(); return self.zones(), metrics, self.generate_devices(metrics), self.generate_flows(metrics)

