from core.data_generator import CampusDataGenerator
from core.anomaly_detector import AnomalyDetectionEngine

def test_train_predict_and_evaluate(tmp_path):
    gen=CampusDataGenerator(seed=4,days=1); metrics=gen.generate_metrics(); flows=gen.generate_flows(metrics,count=500)
    engine=AnomalyDetectionEngine(estimators=20,model_path=tmp_path/"model.joblib").train(flows)
    result=engine.predict(flows); evaluation=engine.evaluate(flows,result)
    assert len(result)==len(flows) and set(result.prediction.unique())<={0,1}
    assert (tmp_path/"model.joblib").exists() and 0<=evaluation["f1"]<=1

