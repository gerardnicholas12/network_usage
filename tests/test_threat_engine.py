import pandas as pd
from core.threat_engine import ThreatDetectionEngine

def test_port_scan_detection():
    row={"flow_id":"x","timestamp":"2026-01-01","zone_id":"Z01","synthetic_device_id":"DEV-1",
         "packets_sent":10,"connection_attempts":50,"unique_destination_ports":50,"dns_query_count":1,
         "average_dns_query_length":10,"bytes_sent":100,"failed_connection_count":1}
    events=ThreatDetectionEngine().detect(pd.DataFrame([row]))
    assert len(events)==1 and events.iloc[0].threat_type=="Potential port scanning"

def test_normal_flow_not_flagged():
    row={"flow_id":"x","timestamp":"2026-01-01","zone_id":"Z01","synthetic_device_id":"DEV-1",
         "packets_sent":10,"connection_attempts":10,"unique_destination_ports":2,"dns_query_count":3,
         "average_dns_query_length":20,"bytes_sent":1000,"failed_connection_count":0}
    assert ThreatDetectionEngine().detect(pd.DataFrame([row])).empty

