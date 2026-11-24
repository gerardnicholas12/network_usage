from __future__ import annotations

from dataclasses import dataclass
import pandas as pd


INCIDENT_COLUMNS = [
    "incident_id", "start_time", "end_time", "zone_id", "synthetic_device_id",
    "incident_title", "severity", "alert_count", "ml_anomaly_count",
    "threat_types", "confidence_pct", "evidence_summary", "event_status",
]


@dataclass
class IncidentCorrelator:
    """Correlate defensive alerts and ML anomalies by device, zone, and time."""

    window_minutes: int = 60

    @staticmethod
    def _title(threats: set[str], anomaly_count: int) -> str:
        joined = " ".join(threats).lower()
        if "port scanning" in joined and "failed connections" in joined:
            return "Suspicious reconnaissance pattern"
        if "dns tunnelling" in joined and "outbound transfer" in joined:
            return "Possible covert data-transfer pattern"
        if "dos" in joined or "connection frequency" in joined:
            return "Potential service-disruption pattern"
        if anomaly_count and len(threats) > 1:
            return "Multi-signal anomalous activity"
        if anomaly_count:
            return "Rule alert supported by ML anomaly"
        return "Related defensive alerts"

    def correlate(
        self, events: pd.DataFrame, flows: pd.DataFrame, anomaly_results: pd.DataFrame
    ) -> pd.DataFrame:
        if events.empty:
            return pd.DataFrame(columns=INCIDENT_COLUMNS)

        alerts = events.copy()
        alerts["timestamp"] = pd.to_datetime(alerts["timestamp"])
        alerts = alerts.sort_values(["zone_id", "synthetic_device_id", "timestamp"])

        anomaly_devices = pd.DataFrame()
        if not anomaly_results.empty and not flows.empty:
            anomaly_devices = anomaly_results[anomaly_results["prediction"] == 1].merge(
                flows[["flow_id", "synthetic_device_id"]].drop_duplicates("flow_id"),
                on="flow_id", how="left",
            )
            anomaly_devices["timestamp"] = pd.to_datetime(anomaly_devices["timestamp"])

        clusters: list[pd.DataFrame] = []
        window = pd.Timedelta(minutes=self.window_minutes)
        for _, group in alerts.groupby(["zone_id", "synthetic_device_id"], dropna=False):
            start = 0
            times = group["timestamp"].tolist()
            for idx in range(1, len(group)):
                if times[idx] - times[idx - 1] > window:
                    clusters.append(group.iloc[start:idx])
                    start = idx
            clusters.append(group.iloc[start:])

        severity_rank = {"Informational": 0, "Low": 1, "Medium": 2, "High": 3, "Critical": 4}
        rows = []
        for cluster in clusters:
            first = cluster.iloc[0]
            start_time, end_time = cluster["timestamp"].min(), cluster["timestamp"].max()
            matching = anomaly_devices
            if not matching.empty:
                matching = matching[
                    (matching["zone_id"] == first["zone_id"])
                    & (matching["synthetic_device_id"] == first["synthetic_device_id"])
                    & (matching["timestamp"].between(start_time - window, end_time + window))
                ]
            anomaly_count = len(matching)
            if len(cluster) < 2 and anomaly_count == 0:
                continue
            threats = set(cluster["threat_type"].astype(str))
            severity = max(cluster["severity"], key=lambda item: severity_rank.get(item, 0))
            if anomaly_count >= 2 and severity_rank.get(severity, 0) < 3:
                severity = "High"
            confidence = min(96, 55 + max(0, len(cluster) - 1) * 10 + min(anomaly_count, 4) * 5)
            rows.append({
                "incident_id": f"INC-{len(rows) + 1:05d}",
                "start_time": start_time,
                "end_time": end_time,
                "zone_id": first["zone_id"],
                "synthetic_device_id": first["synthetic_device_id"],
                "incident_title": self._title(threats, anomaly_count),
                "severity": severity,
                "alert_count": len(cluster),
                "ml_anomaly_count": anomaly_count,
                "threat_types": ", ".join(sorted(threats)),
                "confidence_pct": confidence,
                "evidence_summary": f"{len(cluster)} related rule alert(s) and {anomaly_count} ML anomaly signal(s) within ±{self.window_minutes} minutes.",
                "event_status": "Open" if (cluster["event_status"] == "Open").any() else cluster.iloc[-1]["event_status"],
            })
        return pd.DataFrame(rows, columns=INCIDENT_COLUMNS).sort_values(
            ["start_time", "confidence_pct"], ascending=[False, False]
        ).reset_index(drop=True) if rows else pd.DataFrame(columns=INCIDENT_COLUMNS)

