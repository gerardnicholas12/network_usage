import pandas as pd
from core.scenario_engine import NetworkScenarioEngine


def test_failures_and_demand_reduce_health():
    current=pd.Series({"connected_users":100,"active_devices":120,"download_mbps":200,"upload_mbps":50,"bandwidth_utilisation_pct":50,"active_access_points":5,"total_access_points":5,"availability_pct":100,"signal_strength_dbm":-55,"latency_ms":15,"jitter_ms":3,"packet_loss_pct":.2,"usability_score":88,"network_health_score":91})
    zone=pd.Series({"bandwidth_capacity_mbps":500})
    base,scenario=NetworkScenarioEngine().simulate(current,zone,ap_failures=2,user_increase_pct=100,signal_drop_db=10,security_spike_pct=50)
    assert scenario.active_access_points==3
    assert scenario.latency_ms>base.latency_ms
    assert scenario.usability_score<base.usability_score

