from datetime import datetime, timezone
import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import RobustScaler
from sklearn.metrics import precision_score, recall_score, f1_score, confusion_matrix
from config.settings import ANOMALY_FEATURES, MODEL_PATH, RANDOM_SEED


class AnomalyDetectionEngine:
    def __init__(self, contamination=.05, estimators=150, seed=RANDOM_SEED, model_path=MODEL_PATH):
        self.contamination, self.estimators, self.seed = contamination, estimators, seed
        self.model_path=model_path; self.pipeline=None; self.trained_at=None; self.baseline=None

    def _validate(self, df):
        missing=set(ANOMALY_FEATURES)-set(df.columns)
        if missing: raise ValueError(f"Missing ML features: {sorted(missing)}")
        return df[ANOMALY_FEATURES].apply(pd.to_numeric, errors="coerce")

    def train(self, flows):
        ordered=flows.sort_values("timestamp")
        normal=ordered[ordered.get("traffic_label", "Normal")=="Normal"]
        train=normal.iloc[:max(20,int(len(normal)*.75))]
        x=self._validate(train)
        self.pipeline=Pipeline([("imputer",SimpleImputer(strategy="median")),("scale",RobustScaler()),
            ("model",IsolationForest(n_estimators=self.estimators,contamination=self.contamination,random_state=self.seed,n_jobs=-1))])
        self.pipeline.fit(x); self.trained_at=datetime.now(timezone.utc).isoformat()
        self.baseline=x.median().to_dict(); self.model_path.parent.mkdir(parents=True,exist_ok=True); joblib.dump(self,self.model_path)
        return self

    def predict(self, flows):
        if self.pipeline is None: raise RuntimeError("Model is not trained")
        x=self._validate(flows); pred=self.pipeline.predict(x); score=-self.pipeline.decision_function(x)
        result=flows[["flow_id","timestamp","zone_id"]].copy(); result["anomaly_score"]=score.round(5); result["prediction"]=(pred==-1).astype(int)
        def explain(row):
            if not row["prediction"]: return "Within the learned baseline"
            ratios=[]
            original=flows.loc[row.name]
            for f in ANOMALY_FEATURES:
                base=max(abs(float(self.baseline.get(f,1))),1); ratios.append((abs(float(original[f]))/base,f,float(original[f])))
            return "; ".join(f"{f}={v:,.1f}" for _,f,v in sorted(ratios,reverse=True)[:3])+" differ most from baseline"
        result["explanation"]=result.apply(explain,axis=1); result["model_trained_at"]=self.trained_at
        return result

    @staticmethod
    def evaluate(flows, results):
        truth=(flows["traffic_label"]!="Normal").astype(int); pred=results["prediction"]
        return {"precision":precision_score(truth,pred,zero_division=0),"recall":recall_score(truth,pred,zero_division=0),
                "f1":f1_score(truth,pred,zero_division=0),"confusion_matrix":confusion_matrix(truth,pred).tolist()}

