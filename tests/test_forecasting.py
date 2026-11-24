import numpy as np
import pandas as pd
from core.forecasting import CongestionForecastEngine


def test_forecast_horizons_and_bounds():
    times=pd.date_range("2026-11-01",periods=8*96,freq="15min")
    hour=times.hour.to_numpy()+times.minute.to_numpy()/60
    frame=pd.DataFrame({"timestamp":times,"zone_id":"Z01","active_devices":200+60*np.sin(2*np.pi*hour/24),"bandwidth_utilisation_pct":45+20*np.sin(2*np.pi*hour/24),"latency_ms":20+5*np.sin(2*np.pi*hour/24),"usability_score":80-5*np.sin(2*np.pi*hour/24)})
    history,future,diagnostics=CongestionForecastEngine().forecast(frame,240)
    assert len(future)==16
    assert future.usability_score.between(0,100).all()
    assert set(diagnostics.metric)=={"connected_devices","bandwidth_utilisation_pct","latency_ms","usability_score"}

