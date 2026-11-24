from __future__ import annotations

from dataclasses import dataclass
import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression
from sklearn.metrics import r2_score


@dataclass
class CongestionForecastEngine:
    interval_minutes: int = 15

    metric_bounds = {
        "connected_devices": (0, None),
        "bandwidth_utilisation_pct": (0, 140),
        "latency_ms": (0, None),
        "usability_score": (0, 100),
    }

    def _aggregate(self, frame: pd.DataFrame) -> pd.DataFrame:
        data = frame.copy(); data["timestamp"] = pd.to_datetime(data["timestamp"])
        return data.groupby("timestamp", as_index=False).agg(
            connected_devices=("active_devices", "sum"),
            bandwidth_utilisation_pct=("bandwidth_utilisation_pct", "mean"),
            latency_ms=("latency_ms", "mean"),
            usability_score=("usability_score", "mean"),
        ).sort_values("timestamp")

    @staticmethod
    def _features(timestamps: pd.Series, origin: pd.Timestamp) -> np.ndarray:
        ts = pd.to_datetime(timestamps)
        trend = (ts - origin).dt.total_seconds().to_numpy() / 900
        minute = ts.dt.hour.to_numpy() * 60 + ts.dt.minute.to_numpy()
        weekday = ts.dt.day_of_week.to_numpy()
        return np.column_stack([
            trend,
            np.sin(2 * np.pi * minute / 1440), np.cos(2 * np.pi * minute / 1440),
            np.sin(2 * np.pi * weekday / 7), np.cos(2 * np.pi * weekday / 7),
        ])

    def forecast(self, frame: pd.DataFrame, horizon_minutes: int = 60):
        aggregate = self._aggregate(frame)
        if len(aggregate) < 96:
            raise ValueError("At least 24 hours of 15-minute observations are required for forecasting.")
        training = aggregate.tail(min(len(aggregate), 14 * 96)).copy()
        steps = max(2, int(horizon_minutes / self.interval_minutes))
        future_times = pd.Series(pd.date_range(
            training["timestamp"].max() + pd.Timedelta(minutes=self.interval_minutes),
            periods=steps, freq=f"{self.interval_minutes}min",
        ))
        origin = training["timestamp"].min()
        x_train = self._features(training["timestamp"], origin)
        x_future = self._features(future_times, origin)
        future = pd.DataFrame({"timestamp": future_times})
        diagnostics = []
        for metric, bounds in self.metric_bounds.items():
            model = LinearRegression().fit(x_train, training[metric])
            fitted = model.predict(x_train); predicted = model.predict(x_future)
            residual_std = float(np.std(training[metric].to_numpy() - fitted))
            lower, upper = bounds
            if lower is not None: predicted = np.maximum(predicted, lower)
            if upper is not None: predicted = np.minimum(predicted, upper)
            future[metric] = predicted
            future[f"{metric}_lower"] = np.maximum(predicted - 1.64 * residual_std, lower if lower is not None else -np.inf)
            future[f"{metric}_upper"] = np.minimum(predicted + 1.64 * residual_std, upper if upper is not None else np.inf)
            diagnostics.append({"metric": metric, "r2_score": round(float(r2_score(training[metric], fitted)), 3), "residual_std": round(residual_std, 3)})
        return training, future, pd.DataFrame(diagnostics)

