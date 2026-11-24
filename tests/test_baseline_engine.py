import pandas as pd
from core.baseline_engine import BaselineDeviationEngine


def test_detects_large_hourly_baseline_deviation():
    times=pd.date_range("2026-10-27 10:00",periods=5,freq="7D")
    rows=[]
    for ts in times:
        rows.append({"timestamp":ts,"zone_id":"Z01","download_mbps":100,"active_devices":100,"bandwidth_utilisation_pct":30,"latency_ms":15,"usability_score":88})
    rows.append({"timestamp":pd.Timestamp("2026-12-01 10:00"),"zone_id":"Z01","download_mbps":180,"active_devices":100,"bandwidth_utilisation_pct":30,"latency_ms":15,"usability_score":88})
    result=BaselineDeviationEngine().analyse(pd.DataFrame(rows))
    assert not result.empty
    detected=result[result.metric=="download_mbps"].iloc[0]
    assert detected.deviation_pct==80
    assert detected.adverse

