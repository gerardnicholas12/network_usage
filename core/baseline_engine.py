from __future__ import annotations

from dataclasses import dataclass
import numpy as np
import pandas as pd


@dataclass
class BaselineDeviationEngine:
    """Compare the latest zone observation with its weekday/hour baseline."""

    metrics: tuple[str, ...] = (
        "download_mbps", "active_devices", "bandwidth_utilisation_pct",
        "latency_ms", "usability_score",
    )

    def analyse(self, frame: pd.DataFrame, minimum_samples: int = 3) -> pd.DataFrame:
        if frame.empty:
            return pd.DataFrame()
        data = frame.copy()
        data["timestamp"] = pd.to_datetime(data["timestamp"])
        latest_time = data["timestamp"].max()
        history = data[data["timestamp"] < latest_time].copy()
        current = data[data["timestamp"] == latest_time].copy()
        if history.empty or current.empty:
            return pd.DataFrame()
        for part in (history, current):
            part["weekday"] = part["timestamp"].dt.day_of_week
            part["hour"] = part["timestamp"].dt.hour

        grouped = history.groupby(["zone_id", "weekday", "hour"])[list(self.metrics)].agg(["mean", "std", "count"])
        rows = []
        day_name = latest_time.day_name()
        bad_when_high = {"download_mbps", "active_devices", "bandwidth_utilisation_pct", "latency_ms"}
        for observation in current.itertuples():
            key = (observation.zone_id, observation.weekday, observation.hour)
            if key not in grouped.index:
                continue
            baseline = grouped.loc[key]
            for metric in self.metrics:
                count = int(baseline[(metric, "count")])
                mean = float(baseline[(metric, "mean")])
                std = float(baseline[(metric, "std")]) if pd.notna(baseline[(metric, "std")]) else 0.0
                value = float(getattr(observation, metric))
                if count < minimum_samples or abs(mean) < 1e-9:
                    continue
                deviation = (value - mean) / abs(mean) * 100
                z_score = (value - mean) / max(std, abs(mean) * 0.05, 1e-6)
                if abs(deviation) < 20 and abs(z_score) < 2:
                    continue
                adverse = (metric in bad_when_high and deviation > 0) or (metric == "usability_score" and deviation < 0)
                magnitude = max(abs(z_score), abs(deviation) / 25)
                severity = "High" if adverse and magnitude >= 4 else "Medium" if adverse and magnitude >= 2 else "Low"
                direction = "higher" if deviation > 0 else "lower"
                label = metric.replace("_", " ")
                rows.append({
                    "timestamp": latest_time, "zone_id": observation.zone_id, "metric": metric,
                    "current_value": round(value, 2), "baseline_value": round(mean, 2),
                    "deviation_pct": round(deviation, 1), "z_score": round(z_score, 2),
                    "severity": severity, "adverse": adverse,
                    "statement": f"{observation.zone_id} {label} is {abs(deviation):.0f}% {direction} than its normal {day_name} {latest_time:%H}:00 baseline.",
                })
        if not rows:
            return pd.DataFrame()
        order = {"High": 3, "Medium": 2, "Low": 1}
        result = pd.DataFrame(rows)
        result["severity_rank"] = result["severity"].map(order)
        return result.sort_values(["severity_rank", "adverse", "deviation_pct"], ascending=[False, False, False]).drop(columns="severity_rank").reset_index(drop=True)

