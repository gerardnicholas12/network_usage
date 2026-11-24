import logging
from datetime import datetime
import pandas as pd
import streamlit as st
from components.styles import apply_styles, sidebar_brand, sidebar_status, scroll_to_top
from config.settings import DB_PATH, MODEL_PATH
from core.database import DatabaseManager
from core.data_generator import CampusDataGenerator
from core.threat_engine import ThreatDetectionEngine
from core.anomaly_detector import AnomalyDetectionEngine
from views import pages

logging.basicConfig(level=logging.INFO,format="%(asctime)s %(levelname)s %(message)s")
st.set_page_config(page_title="Network Usage",page_icon="📶",layout="wide",initial_sidebar_state="expanded")
apply_styles(); db=DatabaseManager(); db.initialise()

def build_data(force=False):
    if force or db.count("network_metrics")==0:
        with st.spinner("Generating reproducible 30-day campus simulation…"):
            zones,metrics,devices,flows=CampusDataGenerator().generate_all()
            events=ThreatDetectionEngine().detect(flows)
            engine=AnomalyDetectionEngine().train(flows); results=engine.predict(flows)
            db.replace_simulation({"zones":zones,"network_metrics":metrics,"devices":devices,"flows":flows,"security_events":events,"anomaly_results":results})
            st.cache_data.clear()

@st.cache_data(show_spinner=False)
def load_all(db_mtime):
    return {n:db.read(n) for n in ["zones","network_metrics","devices","flows","security_events","anomaly_results","live_measurements"]}

build_data(); db.sync_zones(CampusDataGenerator().zones()); data=load_all(DB_PATH.stat().st_mtime_ns)
for table in ["network_metrics","devices","flows","security_events","anomaly_results"]:
    if "timestamp" in data[table]: data[table]["timestamp"]=pd.to_datetime(data[table]["timestamp"])

sidebar_brand()
navigation=["Campus Overview","Geographical Heatmap","Wi-Fi Usage Analytics","Network Performance","Device Intelligence","Threat Detection Centre","AI Anomaly Intelligence","Live Local Monitoring","Reports and Data Explorer","System Information"]
nav_icons={"Campus Overview":"◉", "Geographical Heatmap":"⌖", "Wi-Fi Usage Analytics":"≋", "Network Performance":"⌁", "Device Intelligence":"▦", "Threat Detection Centre":"⚠", "AI Anomaly Intelligence":"✦", "Live Local Monitoring":"●", "Reports and Data Explorer":"▤", "System Information":"ⓘ"}
page=st.sidebar.radio("Navigation",navigation,format_func=lambda item:f"{nav_icons[item]}   {item}",label_visibility="collapsed")
if st.session_state.get("_active_page") != page:
    st.session_state["_active_page"] = page
    scroll_to_top()
st.sidebar.markdown('<div class="sidebar-section-label">Scope & controls</div>',unsafe_allow_html=True)
metrics=data["network_metrics"]; zones=data["zones"]
devices=data["devices"]; flows=data["flows"]; events=data["security_events"]; anomalies=data["anomaly_results"]
if page not in ["Live Local Monitoring","System Information"]:
    if st.sidebar.button("Reset filters",width="stretch"):
        for key in ("zone_filter","building_filter","date_filter","replay_index"): st.session_state.pop(key,None)
        st.rerun()
    buildings=st.sidebar.multiselect("Building category",sorted(zones.building_type.unique()),default=[],key="building_filter")
    available_zones=zones[zones.building_type.isin(buildings)] if buildings else zones
    selected=st.sidebar.multiselect("Campus zones",available_zones.zone_name.tolist(),default=[],key="zone_filter")
    scope_ids=available_zones.zone_id
    if selected:
        scope_ids=zones[zones.zone_name.isin(selected)].zone_id
    metrics=metrics[metrics.zone_id.isin(scope_ids)]; devices=devices[devices.zone_id.isin(scope_ids)]
    flows=flows[flows.zone_id.isin(scope_ids)]; events=events[events.zone_id.isin(scope_ids)]; anomalies=anomalies[anomalies.zone_id.isin(scope_ids)]
    min_d,max_d=metrics.timestamp.min().date(),metrics.timestamp.max().date(); dates=st.sidebar.date_input("Date range",(min_d,max_d),min_value=min_d,max_value=max_d,key="date_filter")
    if len(dates)==2:
        start,end=dates; metrics=metrics[(metrics.timestamp.dt.date>=start)&(metrics.timestamp.dt.date<=end)]
        devices=devices[(devices.timestamp.dt.date>=start)&(devices.timestamp.dt.date<=end)]; flows=flows[(flows.timestamp.dt.date>=start)&(flows.timestamp.dt.date<=end)]
        events=events[(events.timestamp.dt.date>=start)&(events.timestamp.dt.date<=end)]; anomalies=anomalies[(anomalies.timestamp.dt.date>=start)&(anomalies.timestamp.dt.date<=end)]
    if st.sidebar.toggle("Simulation replay",value=False):
        replay_times=sorted(metrics.timestamp.unique())
        if replay_times:
            maximum=len(replay_times)-1; current=min(st.session_state.get("replay_index",0),maximum)
            current=st.sidebar.slider("Replay position",0,maximum,current,key="replay_index")
            if st.sidebar.button("Advance one interval"):
                st.session_state.replay_index=min(current+1,maximum); st.rerun()
            cutoff=pd.Timestamp(replay_times[current]); metrics=metrics[metrics.timestamp<=cutoff]
            devices=devices[devices.timestamp<=cutoff]; flows=flows[flows.timestamp<=cutoff]; events=events[events.timestamp<=cutoff]; anomalies=anomalies[anomalies.timestamp<=cutoff]
            st.sidebar.caption(f"SIMULATION replay: {cutoff:%d %b %Y, %H:%M}")
if st.sidebar.button("Regenerate simulation",width="stretch"): build_data(True); st.rerun()
sidebar_status(data["network_metrics"].timestamp.max())
if page=="Campus Overview": pages.overview(metrics,zones,devices,events)
elif page=="Geographical Heatmap": pages.heatmap(metrics,zones,events)
elif page=="Wi-Fi Usage Analytics": pages.usage(metrics,zones,devices,flows)
elif page=="Network Performance": pages.performance(metrics,zones)
elif page=="Device Intelligence": pages.device_intelligence(devices,metrics)
elif page=="Threat Detection Centre": pages.threats(events,flows,zones,anomalies)
elif page=="AI Anomaly Intelligence":
    import joblib
    model=joblib.load(MODEL_PATH); model_metrics=model.evaluate(flows,anomalies); pages.anomaly(flows,anomalies,model_metrics)
    with st.expander("Retrain model"):
        contamination=st.slider("Contamination",.01,.20,float(model.contamination),.01); estimators=st.slider("Estimators",50,400,int(model.estimators),25)
        seed=st.number_input("Random seed",value=int(model.seed),step=1)
        if st.button("Retrain Isolation Forest",type="primary"):
            with st.spinner("Training on the chronological normal baseline…"):
                fresh=AnomalyDetectionEngine(contamination,estimators,int(seed)).train(data["flows"]); result=fresh.predict(data["flows"]); db.replace("anomaly_results",result); st.cache_data.clear()
            st.success("Model retrained and persisted."); st.rerun()
elif page=="Live Local Monitoring": pages.live_monitoring(db)
elif page=="Reports and Data Explorer": pages.reports({"Network metrics":metrics,"Campus zones":zones[zones.zone_id.isin(scope_ids)],"Devices":devices,"Network flows":flows,"Security events":events,"Anomaly results":anomalies,"Live history":data["live_measurements"]},zones)
else: pages.system_info()


