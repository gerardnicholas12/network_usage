from __future__ import annotations

from dataclasses import dataclass
import numpy as np
import pandas as pd
from core.usability_engine import UsabilityCalculator


@dataclass
class NetworkScenarioEngine:
    """Deterministic, non-persistent what-if calculator for one simulated zone."""

    def simulate(self, current: pd.Series, zone: pd.Series, ap_failures=0, user_increase_pct=0,
                 capacity_increase_pct=0, signal_drop_db=0, security_spike_pct=0):
        base = current.copy()
        scenario = current.copy()
        total_aps = int(current["total_access_points"])
        active_aps = max(0, total_aps - int(ap_failures))
        device_factor = 1 + user_increase_pct / 100
        demand_factor = device_factor * (1 + security_spike_pct / 250)
        capacity = float(zone["bandwidth_capacity_mbps"]) * (1 + capacity_increase_pct / 100)
        base_throughput = float(current["download_mbps"] + current["upload_mbps"])
        throughput = base_throughput * demand_factor
        utilisation = np.clip(throughput / max(capacity, 1) * 100, 0, 140)
        extra_util = max(0, utilisation - float(current["bandwidth_utilisation_pct"]))

        scenario["connected_users"] = round(float(current["connected_users"]) * device_factor)
        scenario["active_devices"] = round(float(current["active_devices"]) * device_factor)
        scenario["download_mbps"] = throughput * .82
        scenario["upload_mbps"] = throughput * .18
        scenario["bandwidth_utilisation_pct"] = utilisation
        scenario["active_access_points"] = active_aps
        scenario["availability_pct"] = active_aps / max(total_aps, 1) * 100
        scenario["signal_strength_dbm"] = float(current["signal_strength_dbm"]) - signal_drop_db
        scenario["latency_ms"] = float(current["latency_ms"]) + extra_util * .75 + ap_failures * 2.5 + security_spike_pct * .025
        scenario["jitter_ms"] = float(current["jitter_ms"]) + extra_util * .12 + ap_failures * .5
        scenario["packet_loss_pct"] = np.clip(float(current["packet_loss_pct"]) + extra_util * .045 + ap_failures * .25, 0, 20)
        calculated = UsabilityCalculator().calculate(pd.DataFrame([scenario]))
        scenario["usability_score"] = float(calculated.iloc[0])
        scenario["network_health_score"] = float(np.clip(scenario["usability_score"] * .75 + scenario["availability_pct"] * .25, 0, 100))
        return base, scenario

