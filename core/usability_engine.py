from dataclasses import dataclass
import numpy as np
import pandas as pd
from config.settings import USABILITY_WEIGHTS


@dataclass
class UsabilityCalculator:
    weights: dict = None

    def __post_init__(self):
        self.weights = self.weights or USABILITY_WEIGHTS

    @staticmethod
    def _clip(value):
        return np.clip(value, 0, 100)

    def components(self, df: pd.DataFrame) -> pd.DataFrame:
        out = pd.DataFrame(index=df.index)
        out["latency"] = self._clip(100 - (df["latency_ms"] - 10) * 1.25)
        out["packet_loss"] = self._clip(100 - df["packet_loss_pct"] * 20)
        out["signal"] = self._clip((df["signal_strength_dbm"] + 90) * 2.5)
        out["congestion"] = self._clip(100 - df["bandwidth_utilisation_pct"])
        out["availability"] = self._clip(df["availability_pct"])
        out["jitter"] = self._clip(100 - df["jitter_ms"] * 4)
        return out

    def calculate(self, df: pd.DataFrame) -> pd.Series:
        if df.empty:
            return pd.Series(dtype=float)
        c = self.components(df)
        result = sum(c[name] * weight for name, weight in self.weights.items())
        return result.clip(0, 100).round(2)

    @staticmethod
    def classify(score: float) -> str:
        if score >= 85: return "Excellent"
        if score >= 70: return "Good"
        if score >= 50: return "Moderate"
        if score >= 30: return "Poor"
        return "Critical"

