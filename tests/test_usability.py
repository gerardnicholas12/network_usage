import pandas as pd
from core.usability_engine import UsabilityCalculator

def test_usability_bounds_and_direction():
    df=pd.DataFrame({"latency_ms":[10,200],"packet_loss_pct":[0,20],"signal_strength_dbm":[-45,-95],
        "bandwidth_utilisation_pct":[10,120],"availability_pct":[100,0],"jitter_ms":[1,50]})
    scores=UsabilityCalculator().calculate(df)
    assert scores.between(0,100).all()
    assert scores.iloc[0]>scores.iloc[1]

def test_classifications():
    assert UsabilityCalculator.classify(85)=="Excellent"
    assert UsabilityCalculator.classify(29)=="Critical"

