import json
from pathlib import Path
import pandas as pd
from config.settings import ROOT


class ThreatDetectionEngine:
    def __init__(self, rules_path: Path = ROOT / "config" / "detection_rules.json"):
        self.rules=json.loads(Path(rules_path).read_text())

    def detect(self, flows: pd.DataFrame) -> pd.DataFrame:
        events=[]
        for r in flows.itertuples():
            finding=None
            if r.packets_sent>self.rules["dos_pattern"]["packets_sent"] and r.connection_attempts>self.rules["dos_pattern"]["connection_attempts"]:
                finding=("Potential DoS pattern","Critical",f"{r.packets_sent:,} packets and {r.connection_attempts} attempts","Rate-limit the source in an authorised environment and inspect service logs.")
            elif r.unique_destination_ports>self.rules["port_scan"]["unique_destination_ports"]:
                finding=("Potential port scanning","High",f"{r.unique_destination_ports} unique destination ports","Review destination-port pattern and isolate the synthetic endpoint if validated.")
            elif r.dns_query_count>self.rules["dns_tunnelling"]["dns_query_count"] and r.average_dns_query_length>self.rules["dns_tunnelling"]["average_dns_query_length"]:
                finding=("Possible DNS tunnelling","High",f"{r.dns_query_count} queries; mean length {r.average_dns_query_length:.0f}","Inspect authorised DNS logs and validate queried domains.")
            elif r.bytes_sent>self.rules["outbound_transfer"]["bytes_sent"]:
                finding=("Unusual outbound transfer","High",f"{r.bytes_sent/1e6:.1f} MB sent","Verify the business purpose and review endpoint activity.")
            elif r.failed_connection_count>self.rules["failed_connections"]["failed_connection_count"]:
                finding=("Repeated failed connections","Medium",f"{r.failed_connection_count} failed connections","Check authentication and firewall logs for the synthetic endpoint.")
            elif r.connection_attempts>self.rules["connection_burst"]["connection_attempts"]:
                finding=("Unusual connection frequency","Medium",f"{r.connection_attempts} attempts","Review connection destinations and rate trends.")
            if finding:
                threat,severity,evidence,action=finding; events.append({"event_id":f"EVT-{len(events)+1:06d}","timestamp":r.timestamp,
                    "zone_id":r.zone_id,"synthetic_device_id":r.synthetic_device_id,"threat_type":threat,"severity":severity,
                    "detection_method":"Defensive rule-based analysis","anomaly_score":None,"confidence_description":"Threshold evidence observed; requires investigation",
                    "event_description":evidence,"recommended_action":action,"event_status":"Open"})
        return pd.DataFrame(events)

