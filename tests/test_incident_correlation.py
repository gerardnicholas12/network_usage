import pandas as pd
from core.incident_correlation import IncidentCorrelator


def test_reconnaissance_alerts_and_anomaly_are_correlated():
    events=pd.DataFrame([
        {"event_id":"E1","timestamp":"2026-11-24 10:00","zone_id":"Z01","synthetic_device_id":"DEV-1","threat_type":"Potential port scanning","severity":"High","event_status":"Open"},
        {"event_id":"E2","timestamp":"2026-11-24 10:20","zone_id":"Z01","synthetic_device_id":"DEV-1","threat_type":"Repeated failed connections","severity":"Medium","event_status":"Open"},
    ])
    flows=pd.DataFrame([{"flow_id":"F1","synthetic_device_id":"DEV-1"}])
    anomalies=pd.DataFrame([{"flow_id":"F1","timestamp":"2026-11-24 10:15","zone_id":"Z01","prediction":1}])
    result=IncidentCorrelator().correlate(events,flows,anomalies)
    assert len(result)==1
    assert result.iloc[0].incident_title=="Suspicious reconnaissance pattern"
    assert result.iloc[0].ml_anomaly_count==1


def test_unrelated_single_alert_is_not_an_incident():
    events=pd.DataFrame([{"event_id":"E1","timestamp":"2026-11-24","zone_id":"Z01","synthetic_device_id":"DEV-1","threat_type":"Potential port scanning","severity":"High","event_status":"Open"}])
    assert IncidentCorrelator().correlate(events,pd.DataFrame(),pd.DataFrame()).empty

