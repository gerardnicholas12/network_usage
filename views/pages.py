from datetime import datetime
import json
import io, time
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from components.charts import style, COLORS
from components.styles import header
from core.usability_engine import UsabilityCalculator
from core.network_monitor import NetworkMonitor, calculate_throughput
from core.incident_correlation import IncidentCorrelator
from core.baseline_engine import BaselineDeviationEngine
from core.forecasting import CongestionForecastEngine
from core.scenario_engine import NetworkScenarioEngine
from config.settings import CAMPUS_CONFIG_PATH


CAMPUS_LOCATION=json.loads(CAMPUS_CONFIG_PATH.read_text(encoding="utf-8"))


def empty(df):
    if df.empty: st.warning("No records match the current filters. Reset or widen the filters."); return True
    return False

def _latest(metrics):
    t=metrics["timestamp"].max(); return metrics[metrics["timestamp"]==t]

def overview(metrics,zones,devices,events):
    header("Campus Overview","Executive view of simulated campus-wide network conditions.")
    if empty(metrics): return
    latest=_latest(metrics); prev=metrics[metrics["timestamp"]==metrics.loc[metrics.timestamp<metrics.timestamp.max(),"timestamp"].max()]
    vals=[("Connected users",latest.connected_users.sum(),latest.connected_users.sum()-prev.connected_users.sum()),("Active devices",latest.active_devices.sum(),None),
          ("Active APs",latest.active_access_points.sum(),None),("Download Mbps",latest.download_mbps.sum(),None),("Upload Mbps",latest.upload_mbps.sum(),None),
          ("Usability",latest.usability_score.mean(),None),("Network health",latest.network_health_score.mean(),None),("Open alerts",len(events),None)]
    cols=st.columns(4)
    for i,(label,value,delta) in enumerate(vals): cols[i%4].metric(label,f"{value:,.1f}",f"{delta:+,.0f}" if delta is not None else None)
    daily=(metrics.assign(timestamp=pd.to_datetime(metrics.timestamp)).set_index("timestamp")
           .resample("2h")[["download_mbps","upload_mbps"]].sum().reset_index())
    c1,c2=st.columns([1.65,1])
    c1.plotly_chart(style(px.area(daily,x="timestamp",y=["download_mbps","upload_mbps"],title="Campus traffic over time")),width="stretch")
    zone=latest.merge(zones,on="zone_id").sort_values("bandwidth_utilisation_pct")
    c2.plotly_chart(style(px.bar(zone,x="bandwidth_utilisation_pct",y="zone_name",orientation="h",title="Current zone utilisation",color="bandwidth_utilisation_pct",color_continuous_scale="Bluered")),width="stretch")
    c3,c4,c5=st.columns(3)
    dev=devices.groupby("device_type",as_index=False).size(); c3.plotly_chart(style(px.pie(dev,names="device_type",values="size",hole=.62,title="Device distribution"),330),width="stretch")
    sev=events.groupby("severity",as_index=False).size() if not events.empty else pd.DataFrame({"severity":["None"],"size":[1]})
    c4.plotly_chart(style(px.pie(sev,names="severity",values="size",hole=.62,title="Alert severity",color="severity",color_discrete_map={"Critical":"#EF4444","High":"#F97316","Medium":"#F59E0B"}),330),width="stretch")
    gauge=go.Figure(go.Indicator(mode="gauge+number",value=latest.network_health_score.mean(),title={"text":"Campus network health"},gauge={"axis":{"range":[0,100]},"bar":{"color":"#38BDF8"},"steps":[{"range":[0,50],"color":"#451a1a"},{"range":[50,70],"color":"#422006"},{"range":[70,100],"color":"#052e16"}]}))
    c5.plotly_chart(style(gauge,330),width="stretch")
    left,right=st.columns(2); left.subheader("Most congested zones"); left.dataframe(zone.nlargest(5,"bandwidth_utilisation_pct")[["zone_name","bandwidth_utilisation_pct","latency_ms"]],hide_index=True,width="stretch")
    right.subheader("Recent security events"); right.dataframe(events.sort_values("timestamp",ascending=False).head(5)[["timestamp","threat_type","severity","event_status"]] if not events.empty else pd.DataFrame(),hide_index=True,width="stretch")

def heatmap(metrics,zones,events):
    header("Geographical Heatmap","Illustrative zone-level conditions — not a measured RF coverage survey.")
    if empty(metrics): return
    latest=_latest(metrics).merge(zones,on="zone_id"); counts=events.groupby("zone_id").size().rename("security_events") if not events.empty else pd.Series(dtype=int)
    latest=latest.join(counts,on="zone_id").fillna({"security_events":0})
    options={"Wi-Fi traffic intensity":"download_mbps","Connected device density":"active_devices","Network usability":"usability_score","Signal strength":"signal_strength_dbm","Latency":"latency_ms","Bandwidth congestion":"bandwidth_utilisation_pct","Security threat hotspots":"security_events","Access point availability":"availability_pct"}
    controls=st.columns([1.25,1]); label=controls[0].selectbox("Map metric",options); metric=options[label]
    mode=controls[1].selectbox("Visualisation",["Central Campus geolocation","Offline heatmap","Zone markers (offline)","3D comparison"])
    hover=["zone_name","connected_users","active_devices","download_mbps","upload_mbps","signal_strength_dbm","latency_ms","packet_loss_pct","bandwidth_utilisation_pct","usability_score","security_events"]
    good_high=metric in ["usability_score","availability_pct","signal_strength_dbm"]
    risk_high=metric in ["latency_ms","bandwidth_utilisation_pct","security_events"]
    scale="RdYlGn" if good_high else "RdYlGn_r" if risk_high else "Turbo"
    if mode=="Central Campus geolocation":
        campus=CAMPUS_LOCATION
        info_left,info_right=st.columns([1.7,1])
        with info_left.container(border=True):
            st.markdown(f"**{campus['campus_name']}**")
            st.caption(campus["address"])
        with info_right.container(border=True):
            st.markdown(f"**Campus reference:** `{campus['latitude']:.6f}, {campus['longitude']:.6f}`")
            st.link_button("Open official campus page",campus["official_page"],width="stretch")
        fig=px.scatter_map(latest,lat="latitude",lon="longitude",size="active_devices",color=metric,
            hover_name="zone_name",hover_data=hover,zoom=campus["default_zoom"],height=620,
            map_style="open-street-map",center={"lat":campus["latitude"],"lon":campus["longitude"]},
            color_continuous_scale=scale)
        fig.add_trace(go.Scattermap(lat=[campus["latitude"]],lon=[campus["longitude"]],mode="markers+text",
            text=["CHRIST Central Campus"],textposition="top right",name="Campus reference",
            marker={"size":20,"color":"#F8FAFC"},hovertemplate=f"<b>{campus['short_name']}</b><br>{campus['address']}<br>{campus['latitude']:.6f}, {campus['longitude']:.6f}<extra></extra>"))
        fig.update_layout(map={"style":"open-street-map","center":{"lat":campus["latitude"],"lon":campus["longitude"]},"zoom":campus["default_zoom"]},legend={"orientation":"h","y":.02,"x":.02})
    elif mode=="Offline heatmap":
        # Inverse-distance interpolation is a visual aid between zone points, not measured RF coverage.
        gx=np.linspace(18,84,90); gy=np.linspace(14,82,90); xx,yy=np.meshgrid(gx,gy)
        dx=xx[...,None]-latest.map_x.to_numpy(); dy=yy[...,None]-latest.map_y.to_numpy()
        weights=1/(dx*dx+dy*dy+18); zz=(weights*latest[metric].to_numpy()).sum(axis=2)/weights.sum(axis=2)
        fig=go.Figure(go.Heatmap(x=gx,y=gy,z=zz,colorscale=scale,colorbar={"title":label},hovertemplate="Campus x: %{x:.0f}<br>Campus y: %{y:.0f}<br>Interpolated value: %{z:.1f}<extra></extra>"))
        custom=latest[hover].to_numpy()
        fig.add_trace(go.Scatter(x=latest.map_x,y=latest.map_y,mode="markers+text",text=latest.zone_name,textposition="top center",
            marker={"size":np.clip(np.sqrt(latest.active_devices)*1.6,12,34),"color":latest[metric],"colorscale":scale,"line":{"width":2,"color":"#F8FAFC"},"showscale":False},customdata=custom,
            hovertemplate="<b>%{customdata[0]}</b><br>Users: %{customdata[1]}<br>Devices: %{customdata[2]}<br>Download: %{customdata[3]:.1f} Mbps<br>Upload: %{customdata[4]:.1f} Mbps<br>Signal: %{customdata[5]:.1f} dBm<br>Latency: %{customdata[6]:.1f} ms<br>Loss: %{customdata[7]:.2f}%<br>Utilisation: %{customdata[8]:.1f}%<br>Usability: %{customdata[9]:.1f}<br>Security events: %{customdata[10]}<extra></extra>"))
        fig.update_xaxes(visible=False,range=[15,87]); fig.update_yaxes(visible=False,range=[10,86],scaleanchor="x",scaleratio=1)
    elif mode=="Zone markers (offline)": fig=px.scatter(latest,x="map_x",y="map_y",size="active_devices",color=metric,hover_data=hover,text="zone_name",color_continuous_scale=scale)
    else: fig=px.scatter_3d(latest,x="map_x",y="map_y",z=metric,size="active_devices",color=metric,hover_name="zone_name",color_continuous_scale=scale)
    st.plotly_chart(style(fig,600),width="stretch"); st.caption(f"Legend: colour encodes {label.lower()}; marker size encodes active devices. Coordinates and infrastructure values are illustrative.")
    if mode=="Central Campus geolocation":
        st.info("The campus reference point identifies CHRIST Bangalore Central Campus. Zone markers are simulated analytical locations—not verified building coordinates or an RF survey. The OpenStreetMap basemap requires internet access; use an offline view when tiles are unavailable.")

def usage(metrics,zones,devices,flows):
    header("Wi-Fi Usage Analytics","Consumption patterns, peak periods, and bandwidth demand.")
    if empty(metrics): return
    m=metrics.assign(timestamp=pd.to_datetime(metrics.timestamp)); m["hour"]=m.timestamp.dt.hour; m["day"]=m.timestamp.dt.day_name(); m["is_weekend"]=np.where(m.timestamp.dt.day_of_week>=5,"Weekend","Weekday")
    hourly=m.groupby("hour",as_index=False)[["download_data_mb","upload_data_mb"]].sum(); peak=int(hourly.loc[hourly.download_data_mb.idxmax(),"hour"])
    st.metric("Dynamic peak usage hour",f"{peak:02d}:00–{peak:02d}:59")
    a,b=st.columns(2); a.plotly_chart(style(px.line(hourly,x="hour",y=["download_data_mb","upload_data_mb"],title="Hourly data transferred (MB)")),width="stretch")
    daily=m.groupby(m.timestamp.dt.date)[["download_data_mb","upload_data_mb"]].sum().reset_index(); b.plotly_chart(style(px.bar(daily,x="timestamp",y=["download_data_mb","upload_data_mb"],title="Daily consumption")),width="stretch")
    z=m.merge(zones,on="zone_id").groupby("zone_name",as_index=False).bandwidth_utilisation_pct.mean(); a.plotly_chart(style(px.bar(z,x="zone_name",y="bandwidth_utilisation_pct",title="Zone utilisation",color="bandwidth_utilisation_pct")),width="stretch")
    wh=m.groupby(["zone_id","hour"],as_index=False).bandwidth_utilisation_pct.mean(); pivot=wh.pivot(index="zone_id",columns="hour",values="bandwidth_utilisation_pct")
    b.plotly_chart(style(px.imshow(pivot,aspect="auto",color_continuous_scale="Turbo",title="Utilisation by zone and hour")),width="stretch")
    proto=flows.groupby("protocol",as_index=False).size(); a.plotly_chart(style(px.pie(proto,names="protocol",values="size",hole=.55,title="Protocol distribution")),width="stretch")
    scat=m.sample(min(2500,len(m)),random_state=1); b.plotly_chart(style(px.scatter(scat,x="active_devices",y="download_mbps",color="bandwidth_utilisation_pct",title="Devices vs throughput")),width="stretch")
    st.download_button("Download filtered metrics (CSV)",metrics.to_csv(index=False),"network_usage_metrics.csv","text/csv")

def performance(metrics,zones):
    header("Network Performance","Current quality, learned baselines, short-term forecasts, and scenario analysis.")
    if empty(metrics): return
    quality_tab, baseline_tab, forecast_tab, scenario_tab=st.tabs(["Current quality","Baseline deviations","Short-term forecast","What-if simulator"])
    latest=_latest(metrics)
    with quality_tab:
        cols=st.columns(7)
        values=[("Latency",latest.latency_ms.mean(),"ms"),("Jitter",latest.jitter_ms.mean(),"ms"),("Packet loss",latest.packet_loss_pct.mean(),"%"),("Signal",latest.signal_strength_dbm.mean(),"dBm"),("Availability",latest.availability_pct.mean(),"%"),("Utilisation",latest.bandwidth_utilisation_pct.mean(),"%"),("Usability",latest.usability_score.mean(),"/100")]
        for c,(label,val,unit) in zip(cols,values): c.metric(label,f"{val:.1f} {unit}")
        z=metrics.groupby("zone_id",as_index=False)[["usability_score","latency_ms","packet_loss_pct","signal_strength_dbm","bandwidth_utilisation_pct","availability_pct"]].mean().merge(zones,on="zone_id")
        a,b=st.columns(2); a.plotly_chart(style(px.bar(z.sort_values("usability_score"),x="usability_score",y="zone_name",orientation="h",color="usability_score",color_continuous_scale="RdYlGn",title="Zone usability ranking")),width="stretch")
        sample=metrics.sample(min(3000,len(metrics)),random_state=2); b.plotly_chart(style(px.scatter(sample,x="bandwidth_utilisation_pct",y="latency_ms",color="packet_loss_pct",title="Congestion versus latency")),width="stretch")
        chosen=st.multiselect("Compare zones",z.zone_name.tolist(),default=z.zone_name.head(3).tolist(),max_selections=5,key="quality_zone_compare"); radar=z[z.zone_name.isin(chosen)]
        fig=go.Figure()
        for r in radar.itertuples(): fig.add_trace(go.Scatterpolar(r=[r.usability_score,r.availability_pct,100-r.bandwidth_utilisation_pct],theta=["Usability","Availability","Low congestion"],fill="toself",name=r.zone_name))
        st.plotly_chart(style(fig),width="stretch")
        poor=z.nsmallest(3,"usability_score"); st.subheader("Condition-based recommendations")
        for r in poor.itertuples():
            causes=[]
            if r.bandwidth_utilisation_pct>70: causes.append("review capacity or load balancing")
            if r.availability_pct<98: causes.append("inspect unavailable access points")
            if r.signal_strength_dbm<-67: causes.append("assess placement and coverage")
            st.info(f"{r.zone_name}: usability {r.usability_score:.1f}. Recommended: {', '.join(causes) or 'continue monitoring latency and loss trends'}.")
        with st.expander("How the custom usability score works"):
            st.write("Higher is better. Latency: 100 − 1.25×(ms−10); loss: 100 − 20×%; signal: 2.5×(dBm+90); congestion: 100−utilisation%; availability uses the measured percentage; jitter: 100−4×ms. Components are clamped 0–100 and weighted 20/20/20/20/15/5%. This is a project heuristic, not an industry-certified score.")

    with baseline_tab:
        deviations=BaselineDeviationEngine().analyse(metrics)
        if deviations.empty:
            st.success("The latest interval is within the learned weekday/hour baselines for the selected scope.")
        else:
            adverse=deviations[deviations.adverse]
            k=st.columns(4); k[0].metric("Detected deviations",len(deviations)); k[1].metric("Adverse deviations",len(adverse)); k[2].metric("High priority",(deviations.severity=="High").sum()); k[3].metric("Affected zones",deviations.zone_id.nunique())
            named=deviations.merge(zones[["zone_id","zone_name"]],on="zone_id",how="left")
            left,right=st.columns([1.15,1])
            chart=named.head(20).copy(); chart["absolute_deviation"]=chart.deviation_pct.abs()
            left.plotly_chart(style(px.bar(chart,x="absolute_deviation",y="zone_name",orientation="h",color="severity",hover_data=["metric","deviation_pct","baseline_value","current_value"],title="Largest baseline deviations",color_discrete_map={"High":"#EF4444","Medium":"#F59E0B","Low":"#38BDF8"})),width="stretch")
            with right.container(border=True):
                st.markdown("#### Analyst summary")
                for row in named.head(6).itertuples():
                    st.markdown(f"**{row.severity} · {row.zone_name}**  \n{row.statement.replace(row.zone_id,row.zone_name)}")
            st.dataframe(named[["timestamp","zone_name","metric","current_value","baseline_value","deviation_pct","z_score","severity"]],hide_index=True,width="stretch")
        with st.expander("How baseline deviation detection works"):
            st.write("Each zone is compared with its own historical observations for the same weekday and hour. A deviation is shown when the difference is at least 20% or two standardised deviations. This is deterministic statistical comparison and is independent of Isolation Forest.")

    with forecast_tab:
        horizon_label=st.segmented_control("Forecast horizon",["30 minutes","1 hour","4 hours"],default="1 hour",selection_mode="single")
        horizon={"30 minutes":30,"1 hour":60,"4 hours":240}[horizon_label or "1 hour"]
        try:
            history,future,diagnostics=CongestionForecastEngine().forecast(metrics,horizon)
            current=history.iloc[-1]; predicted=future.iloc[-1]
            fcols=st.columns(4)
            forecast_metrics=[("Connected devices","connected_devices",""),("Utilisation","bandwidth_utilisation_pct","%"),("Latency","latency_ms","ms"),("Usability","usability_score","/100")]
            for col,(label,key,unit) in zip(fcols,forecast_metrics): col.metric(f"Forecast {label}",f"{predicted[key]:,.1f}{unit}",f"{predicted[key]-current[key]:+,.1f}")
            choice=st.selectbox("Forecast metric",[item[0] for item in forecast_metrics],key="forecast_metric")
            metric_key=next(item[1] for item in forecast_metrics if item[0]==choice)
            recent=history.tail(96)
            fig=go.Figure()
            fig.add_trace(go.Scatter(x=recent.timestamp,y=recent[metric_key],name="Observed",line={"color":"#38BDF8","width":2}))
            fig.add_trace(go.Scatter(x=future.timestamp,y=future[f"{metric_key}_upper"],line={"width":0},showlegend=False,hoverinfo="skip"))
            fig.add_trace(go.Scatter(x=future.timestamp,y=future[f"{metric_key}_lower"],fill="tonexty",fillcolor="rgba(99,102,241,.16)",line={"width":0},name="90% residual band",hoverinfo="skip"))
            fig.add_trace(go.Scatter(x=future.timestamp,y=future[metric_key],name="Forecast",line={"color":"#A78BFA","width":3,"dash":"dot"}))
            fig.add_vline(x=future.timestamp.min(),line_dash="dash",line_color="#64748B")
            fig.update_layout(title=f"{choice}: observed and forecast",xaxis_title=None,yaxis_title=choice)
            st.plotly_chart(style(fig,430),width="stretch")
            with st.expander("Model diagnostics and methodology"):
                st.dataframe(diagnostics,hide_index=True,width="stretch")
                st.write("The forecast uses explainable linear regression with trend, time-of-day, and day-of-week sine/cosine features trained on up to 14 days. The shaded range is based on training residual variation. It is a planning estimate, not a guaranteed future measurement.")
        except ValueError as exc: st.warning(str(exc))

    with scenario_tab:
        selected_zone=st.selectbox("Scenario zone",zones[zones.zone_id.isin(metrics.zone_id.unique())].zone_name.tolist(),key="scenario_zone")
        zone_row=zones[zones.zone_name==selected_zone].iloc[0]
        current=latest[latest.zone_id==zone_row.zone_id]
        if current.empty: st.warning("No latest observation is available for this zone.")
        else:
            current=current.iloc[0]; controls,results=st.columns([.85,1.6])
            with controls:
                st.markdown("#### Scenario controls")
                ap_failures=st.slider("Access points unavailable",0,int(current.total_access_points),0)
                user_increase=st.slider("Additional users",20,100,20,step=10)
                capacity_increase=st.slider("Capacity increase",0,100,0,step=10)
                signal_drop=st.slider("Signal reduction (dB)",0,25,0)
                security_spike=st.slider("Security-event traffic spike",0,100,0,step=10)
                st.caption("This scenario is temporary and does not change stored data.")
            base,simulated=NetworkScenarioEngine().simulate(current,zone_row,ap_failures,user_increase,capacity_increase,signal_drop,security_spike)
            with results:
                st.markdown("#### Estimated impact")
                impact=st.columns(4)
                for col,(label,key,unit,lower_is_better) in zip(impact,[("Usability","usability_score","/100",False),("Health","network_health_score","/100",False),("Latency","latency_ms"," ms",True),("Utilisation","bandwidth_utilisation_pct","%",True)]):
                    col.metric(label,f"{simulated[key]:.1f}{unit}",f"{simulated[key]-base[key]:+,.1f}",delta_color="inverse" if lower_is_better else "normal")
                comparison=pd.DataFrame({"Metric":["Usability","Health","Availability","Low congestion"],"Current":[base.usability_score,base.network_health_score,base.availability_pct,100-min(base.bandwidth_utilisation_pct,100)],"Scenario":[simulated.usability_score,simulated.network_health_score,simulated.availability_pct,100-min(simulated.bandwidth_utilisation_pct,100)]})
                melted=comparison.melt("Metric",var_name="Condition",value_name="Score")
                st.plotly_chart(style(px.bar(melted,x="Metric",y="Score",color="Condition",barmode="group",range_y=[0,100],title=f"Current versus scenario — {selected_zone}"),370),width="stretch")
                if simulated.usability_score < base.usability_score: st.warning(f"Estimated usability decreases by {base.usability_score-simulated.usability_score:.1f} points. Capacity and AP availability should be reviewed before this demand level.")
                else: st.success(f"Estimated usability improves by {simulated.usability_score-base.usability_score:.1f} points under this configuration.")

def device_intelligence(devices,metrics):
    header("Device Intelligence","Privacy-preserving analytics using synthetic anonymised identifiers.")
    if empty(devices): return
    search=st.text_input("Search synthetic device ID"); d=devices[devices.synthetic_device_id.str.contains(search,case=False)] if search else devices
    a,b=st.columns(2); a.plotly_chart(style(px.pie(d.groupby("device_type",as_index=False).size(),names="device_type",values="size",hole=.6,title="Device categories")),width="stretch")
    b.plotly_chart(style(px.pie(d.groupby("operating_system",as_index=False).size(),names="operating_system",values="size",hole=.6,title="Operating systems")),width="stretch")
    risk=d.groupby("synthetic_device_id",as_index=False).agg(risk_score=("risk_score","max"),download_mb=("download_mb","sum"),session_duration_minutes=("session_duration_minutes","mean"),zone_id=("zone_id","last"))
    risk["risk_class"]=pd.cut(risk.risk_score,[-1,25,50,75,100],labels=["Low","Moderate","High","Critical"])
    a.plotly_chart(style(px.histogram(d,x="session_duration_minutes",nbins=40,title="Session duration")),width="stretch"); b.plotly_chart(style(px.bar(risk.nlargest(15,"download_mb"),x="synthetic_device_id",y="download_mb",color="risk_score",title="Top bandwidth consumers")),width="stretch")
    st.caption("Risk is an explainable triage indicator derived from simulated behavior. A new or unknown device is not classified as malicious.")
    st.dataframe(risk.sort_values("risk_score",ascending=False),hide_index=True,width="stretch")

def threats(events,flows,zones,anomaly_results):
    header("Threat Detection Centre","Defensive rule-based analysis of synthetic network flows.")
    if events.empty: st.success("No rules triggered in the current selection."); return
    sev=st.multiselect("Severity",["Informational","Low","Medium","High","Critical"],default=["Medium","High","Critical"]); e=events[events.severity.isin(sev)]
    incidents=IncidentCorrelator().correlate(e,flows,anomaly_results)
    incident_tab,alert_tab,method_tab=st.tabs(["Correlated incidents","Individual alerts","Detection methodology"])
    with incident_tab:
        c=st.columns(4); c[0].metric("Correlated incidents",len(incidents)); c[1].metric("Critical incidents",(incidents.severity=="Critical").sum() if not incidents.empty else 0); c[2].metric("ML-supported",(incidents.ml_anomaly_count>0).sum() if not incidents.empty else 0); c[3].metric("Affected devices",incidents.synthetic_device_id.nunique() if not incidents.empty else 0)
        if incidents.empty:
            st.info("No related alerts were found within the 60-minute correlation window.")
        else:
            display=incidents.merge(zones[["zone_id","zone_name"]],on="zone_id",how="left")
            a,b=st.columns([1.2,1])
            a.plotly_chart(style(px.bar(display.groupby(["incident_title","severity"],as_index=False).size(),x="size",y="incident_title",orientation="h",color="severity",title="Correlated incident patterns",color_discrete_map={"Critical":"#EF4444","High":"#F97316","Medium":"#F59E0B","Low":"#38BDF8"})),width="stretch")
            b.plotly_chart(style(px.scatter(display,x="start_time",y="zone_name",size="alert_count",color="severity",hover_data=["incident_title","synthetic_device_id","ml_anomaly_count","confidence_pct"],title="Incident timeline",color_discrete_map={"Critical":"#EF4444","High":"#F97316","Medium":"#F59E0B","Low":"#38BDF8"})),width="stretch")
            st.dataframe(display[["incident_id","start_time","zone_name","synthetic_device_id","incident_title","severity","alert_count","ml_anomaly_count","confidence_pct","event_status"]],hide_index=True,width="stretch")
            selected=st.selectbox("Investigate correlated incident",display.incident_id.tolist())
            row=display[display.incident_id==selected].iloc[0]
            with st.container(border=True):
                st.markdown(f"#### {row.incident_title}")
                p=st.columns(4); p[0].metric("Severity",row.severity); p[1].metric("Rule alerts",row.alert_count); p[2].metric("ML signals",row.ml_anomaly_count); p[3].metric("Correlation confidence",f"{row.confidence_pct:.0f}%")
                st.write(f"**Zone:** {row.zone_name} · **Synthetic device:** {row.synthetic_device_id} · **Window:** {row.start_time:%d %b %H:%M}–{row.end_time:%H:%M}")
                st.write(f"**Related evidence:** {row.threat_types}. {row.evidence_summary}")
                st.caption("Correlation confidence is a deterministic evidence-strength indicator, not a probability that an attack occurred.")
            st.download_button("Export correlated incidents",display.to_csv(index=False),"network_usage_correlated_incidents.csv","text/csv")
    with alert_tab:
        c=st.columns(4); c[0].metric("Total alerts",len(e)); c[1].metric("Critical",(e.severity=="Critical").sum()); c[2].metric("Affected devices",e.synthetic_device_id.nunique()); c[3].metric("Zones",e.zone_id.nunique())
        a,b=st.columns(2); a.plotly_chart(style(px.bar(e.groupby("threat_type",as_index=False).size(),x="threat_type",y="size",color="threat_type",title="Threat distribution")),width="stretch")
        timeline=e.assign(timestamp=pd.to_datetime(e.timestamp)).set_index("timestamp").resample("D").size().rename("size").reset_index(); b.plotly_chart(style(px.area(timeline,x="timestamp",y="size",title="Alerts over time")),width="stretch")
        st.dataframe(e.sort_values("timestamp",ascending=False),hide_index=True,width="stretch")
        ids=e.event_id.tolist(); selected_alert=st.selectbox("Investigate individual alert",ids); row=e[e.event_id==selected_alert].iloc[0]
        st.markdown(f"**{row.threat_type} — {row.severity}**  \nEvidence: {row.event_description}  \nRecommendation: {row.recommended_action}  \nAssessment: suspected behavior requiring investigation; not a confirmed attack.")
        st.download_button("Export individual alerts",e.to_csv(index=False),"network_usage_alerts.csv","text/csv")
    with method_tab:
        st.markdown("#### Correlation logic")
        st.write("Alerts are grouped by synthetic device and zone when consecutive observations occur within 60 minutes. Isolation Forest anomalies from the same synthetic device and zone are attached when they occur within the expanded correlation window. Multiple rule types can then form a higher-level incident pattern.")
        st.markdown("#### Rule rationale")
        st.write("Rules flag high destination-port diversity, connection bursts, combined packet/connection floods, high-volume and long DNS queries, unusual outbound bytes, and repeated failures. DNS or encryption alone is never treated as malicious.")

def anomaly(flows,results,model_metrics):
    header("AI Anomaly Intelligence","Isolation Forest detection of unusual synthetic flow behavior.")
    if empty(results): return
    joined=flows.merge(results,on=["flow_id","timestamp","zone_id"]); an=joined[joined.prediction==1]
    c=st.columns(4); c[0].metric("Analysed",len(joined)); c[1].metric("Normal",(joined.prediction==0).sum()); c[2].metric("Anomalous",len(an)); c[3].metric("Anomaly %",f"{len(an)/len(joined)*100:.2f}%")
    a,b=st.columns(2); a.plotly_chart(style(px.histogram(joined,x="anomaly_score",color="prediction",nbins=45,title="Anomaly score distribution")),width="stretch")
    b.plotly_chart(style(px.scatter(joined.sample(min(4000,len(joined)),random_state=3),x="bytes_sent",y="connection_attempts",color="prediction",log_x=True,title="Normal vs anomalous traffic")),width="stretch")
    timeline=an.assign(timestamp=pd.to_datetime(an.timestamp)).set_index("timestamp").resample("D").size().rename("size").reset_index(); a.plotly_chart(style(px.area(timeline,x="timestamp",y="size",title="Anomalies over time")),width="stretch")
    b.plotly_chart(style(px.bar(an.groupby("zone_id",as_index=False).size(),x="zone_id",y="size",title="Anomalies by zone")),width="stretch")
    st.write(f"Ground-truth evaluation — precision **{model_metrics['precision']:.3f}**, recall **{model_metrics['recall']:.3f}**, F1 **{model_metrics['f1']:.3f}**; confusion matrix `{model_metrics['confusion_matrix']}`.")
    st.dataframe(an.nlargest(30,"anomaly_score")[["timestamp","zone_id","synthetic_device_id","anomaly_score","traffic_label","explanation"]],hide_index=True,width="stretch")
    with st.expander("How Isolation Forest works"):
        st.write("The model isolates rare records using random feature splits; unusual records need fewer splits. It was trained on the earliest 75% of normal flows after median imputation and robust scaling, avoiding labels as inputs and reducing leakage. Scores are ranking values—not probabilities or calibrated accuracy. Explanations compare values with baseline medians; they are not formal feature attribution.")

def live_monitoring(db):
    header("Live Local Monitoring","Actual statistics from this laptop only — never campus-wide measurements.","LIVE LOCAL")
    monitor=NetworkMonitor(); interfaces=monitor.interfaces()
    if not interfaces: st.warning("No active network interfaces are available."); return
    interface=st.selectbox("Network interface",interfaces); host=st.text_input("Permitted connectivity-test destination","1.1.1.1")
    details=monitor.wifi_details(); c=st.columns(5); c[0].metric("SSID",details.get("ssid") or "Unavailable"); c[1].metric("Local IP",monitor.local_ip()); c[2].metric("Signal",details.get("signal") or "Unavailable"); c[3].metric("Channel",details.get("channel") or "Unavailable"); c[4].metric("Latency",f"{monitor.ping(host):.0f} ms" if monitor.ping(host) is not None else "Unavailable")
    st.caption("A single safe ping and operating-system counters are used. No scanning, interception, or traffic inspection occurs.")
    running=st.toggle("Monitoring enabled",value=False); interval=st.slider("Sampling interval (seconds)",2,5,2)
    if "live_history" not in st.session_state: st.session_state.live_history=[]
    if st.button("Take throughput sample",type="primary",disabled=not running):
        first=monitor.counters(interface)
        if first is None: st.error("Interface-specific counters are unavailable; whole-system traffic was not substituted.")
        else:
            started=time.monotonic(); time.sleep(interval); second=monitor.counters(interface); elapsed=time.monotonic()-started
            up,down=calculate_throughput(first,second,elapsed); record={"timestamp":datetime.now().isoformat(),"interface_name":interface,"upload_mbps":up,"download_mbps":down,"latency_ms":monitor.ping(host),"signal_strength_pct":float(str(details.get("signal") or "0").replace("%","")),"bytes_sent":second.bytes_sent,"bytes_received":second.bytes_recv}
            st.session_state.live_history.append(record); db.append("live_measurements",pd.DataFrame([record])); st.success(f"Measured {down:.3f} Mbps down / {up:.3f} Mbps up over {elapsed:.2f}s")
    hist=pd.DataFrame(st.session_state.live_history)
    if not hist.empty: st.plotly_chart(style(px.line(hist,x="timestamp",y=["download_mbps","upload_mbps"],title="Live throughput history")),width="stretch"); st.download_button("Export live history",hist.to_csv(index=False),"live_history.csv")

def reports(datasets,zones):
    header("Reports & Data Explorer","Filter, inspect, summarise, and export project datasets.")
    name=st.selectbox("Dataset",list(datasets)); df=datasets[name].copy(); query=st.text_input("Search all text fields")
    if query: df=df[df.astype(str).apply(lambda row: row.str.contains(query,case=False).any(),axis=1)]
    st.metric("Records",len(df)); st.dataframe(df.head(5000),hide_index=True,width="stretch")
    if not df.empty:
        st.subheader("Descriptive statistics"); st.dataframe(df.describe(include="all").transpose(),width="stretch")
    st.download_button("Download selected data (CSV)",df.to_csv(index=False),f"network_usage_{name.lower().replace(' ','_')}.csv","text/csv")
    if name=="Network metrics" and not df.empty:
        st.markdown(f'<div class="notice">Simulation summary: {len(df):,} zone-interval observations from {df.timestamp.min()} to {df.timestamp.max()}; mean usability {df.usability_score.mean():.1f}/100; mean availability {df.availability_pct.mean():.1f}%.</div>',unsafe_allow_html=True)

def system_info():
    header("System Information","Methodology, architecture, ethics, and academic context.")
    st.markdown("""
### Network Usage — Monitor. Analyse. Detect. Secure.
**University:** CHRIST University · **Course:** MCA · **Subject:** Python Programming · **Component:** CIA 3  
**Developer:** Gerard Nicholas Paul · **Registration number:** 2647122

Network Usage is an educational smart-campus dashboard combining reproducible simulation, local endpoint monitoring, transparent defensive rules, and unsupervised anomaly detection. The campus mode is illustrative and does not claim access to university infrastructure.

### Architecture
`Zone configuration → Simulation engine → SQLite → analytics / rules / Isolation Forest → Streamlit views`  
`Windows OS counters + safe diagnostics → local history → Live Local Monitoring`

### Methodology and limitations
- Simulation uses fixed-seed, time-correlated occupancy profiles at 15-minute intervals for 30 days. Locations, AP counts, capacities, and conditions are illustrative.
- Local mode reads only this laptop's OS-exposed counters and safe diagnostics; it cannot describe campus-wide conditions.
- Threat rules are advisory indicators over synthetic flows. They do not execute attacks, block traffic, inspect packets, or prove malicious intent.
- Incident correlation groups related rule evidence and ML anomaly signals by synthetic device, zone, and a configurable time window; its confidence value measures evidence strength rather than attack probability.
- Isolation Forest learns normal baselines and identifies unusual behavior. It cannot identify an exact attack category or produce calibrated probabilities.
- Baseline deviations compare the latest interval with the same zone, weekday, and hour. Short-term forecasts use explainable seasonal linear regression and remain planning estimates.
- The what-if simulator is non-persistent and recalculates estimated network quality without modifying the historical database.
- The usability score is a documented project heuristic, not an industry certification or a substitute for an RF survey.

### Ethics and privacy
Only synthetic anonymised device IDs and reserved documentation IP ranges are generated. No real names, MAC addresses, credentials, packet payloads, or other students' traffic are collected. Recommendations are advisory.

### Technology
Python, Streamlit, Pandas, NumPy, Plotly, SQLite, scikit-learn, psutil, Joblib, Pytest, socket, and safe subprocess calls.

### Future enhancements
Authorised controller APIs, calibrated baselines by term schedule, role-based reporting, validated campus geometry, and supervised evaluation on an approved public dataset.
""")


