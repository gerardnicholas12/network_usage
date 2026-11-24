import base64
from functools import lru_cache
import streamlit as st
import streamlit.components.v1 as components
from config.settings import ROOT

CSS = """
<style>
.stApp {background:radial-gradient(circle at 88% 4%,rgba(56,189,248,.08),transparent 27%),#0B1120;color:#F8FAFC}
[data-testid="stSidebar"] {background:linear-gradient(180deg,#101827 0%,#0c1321 100%);border-right:1px solid rgba(56,189,248,.14);box-shadow:10px 0 35px rgba(0,0,0,.16)}
[data-testid="stSidebar"]>div:first-child{padding-top:1rem}
.sidebar-brand{position:relative;padding:1.05rem 1rem .95rem;margin:.15rem 0 1rem;border-bottom:1px solid rgba(148,163,184,.14);overflow:hidden}
.sidebar-brand:after{content:"";position:absolute;width:110px;height:110px;right:-44px;top:-50px;border-radius:50%;background:rgba(56,189,248,.09);filter:blur(2px)}
.brand-row{display:flex;align-items:center;gap:.72rem}.brand-mark{position:relative;width:38px;height:38px;border-radius:11px;background:linear-gradient(145deg,#38BDF8,#6366F1);box-shadow:0 8px 22px rgba(56,189,248,.22)}
.brand-mark:before,.brand-mark:after{content:"";position:absolute;bottom:9px;width:4px;border-radius:4px;background:#fff}.brand-mark:before{height:10px;left:10px;box-shadow:7px -5px 0 #fff,14px -12px 0 #fff}.brand-mark:after{width:24px;height:2px;left:7px;bottom:7px;opacity:.65}
.brand-name{font-weight:760;font-size:1.08rem;letter-spacing:.01em;color:#F8FAFC}.brand-subtitle{color:#7DD3FC;font-size:.68rem;letter-spacing:.13em;text-transform:uppercase;margin-top:.12rem}
.sidebar-section-label{color:#64748B;font-size:.66rem;font-weight:750;letter-spacing:.15em;text-transform:uppercase;margin:.55rem 0 .45rem;padding-left:.2rem}
.sidebar-status{display:flex;align-items:center;justify-content:space-between;gap:.6rem;margin:.8rem 0 .25rem;padding:.75rem .82rem;border:1px solid rgba(56,189,248,.15);border-radius:12px;background:rgba(15,23,42,.62)}
.status-copy{line-height:1.25}.status-label{font-size:.65rem;color:#64748B;text-transform:uppercase;letter-spacing:.11em}.status-value{font-size:.79rem;color:#CBD5E1;margin-top:.18rem}.status-dot{width:8px;height:8px;border-radius:50%;background:#22C55E;box-shadow:0 0 0 4px rgba(34,197,94,.12),0 0 12px rgba(34,197,94,.45);animation:pulse 2.2s ease-in-out infinite}
[data-testid="stSidebar"] [role="radiogroup"]{gap:.22rem}
[data-testid="stSidebar"] [role="radiogroup"] label{padding:.58rem .68rem;border:1px solid transparent;border-radius:10px;color:#94A3B8;transition:background .16s ease,border-color .16s ease,color .16s ease,transform .16s ease}
[data-testid="stSidebar"] [role="radiogroup"] label:hover{background:rgba(56,189,248,.07);border-color:rgba(56,189,248,.14);color:#E2E8F0;transform:translateX(2px)}
[data-testid="stSidebar"] [role="radiogroup"] label:has(input:checked){background:linear-gradient(90deg,rgba(56,189,248,.16),rgba(99,102,241,.07));border-color:rgba(56,189,248,.25);color:#F8FAFC;box-shadow:inset 3px 0 0 #38BDF8}
[data-testid="stSidebar"] [role="radiogroup"] label:has(input:checked) p{font-weight:650}
[data-testid="stSidebar"] [data-testid="stRadioOption"]>div>div:first-child{display:none}
[data-testid="stSidebar"] [data-baseweb="select"]>div,[data-testid="stSidebar"] [data-baseweb="input"]>div{background:#0B1220;border-color:#26354d;border-radius:10px}
[data-baseweb="tab-list"]{gap:.35rem;border-bottom:1px solid rgba(148,163,184,.12)}
[data-baseweb="tab"]{height:2.8rem;padding:0 .85rem;border-radius:9px 9px 0 0;color:#94A3B8}
[data-baseweb="tab"][aria-selected="true"]{color:#F8FAFC;background:rgba(56,189,248,.07)}
[data-testid="stVerticalBlockBorderWrapper"]{border-color:rgba(56,189,248,.13)!important;background:rgba(17,24,39,.45);border-radius:13px}
.hero {position:relative;display:flex;align-items:center;justify-content:space-between;gap:1rem;min-height:116px;padding:1.25rem 1.5rem;border:1px solid rgba(56,189,248,.14);border-radius:16px;background:linear-gradient(112deg,rgba(17,24,39,.98) 0%,rgba(17,24,39,.96) 66%,rgba(17,36,58,.72) 100%);margin-bottom:1rem;overflow:hidden;box-shadow:0 12px 38px rgba(0,0,0,.20);animation:fadeUp .42s ease-out both}
.hero:before{content:"";position:absolute;inset:0;background-image:linear-gradient(rgba(56,189,248,.025) 1px,transparent 1px),linear-gradient(90deg,rgba(56,189,248,.025) 1px,transparent 1px);background-size:22px 22px;mask-image:linear-gradient(90deg,transparent 40%,#000)}
.hero-copy{position:relative;z-index:2;min-width:0}.hero-logo-window{position:relative;z-index:1;width:250px;height:100px;flex:0 0 250px;overflow:hidden;opacity:.86;mix-blend-mode:screen;mask-image:linear-gradient(90deg,transparent 0%,#000 18%,#000 100%)}
.hero-logo-window img{display:block;width:250px;height:250px;transform:translateY(-74px);filter:invert(1) grayscale(1) brightness(1.8) contrast(1.18)}
.hero h1 {margin:0;color:#F8FAFC;font-size:2rem}.hero p {margin:.3rem 0 0;color:#94A3B8}
.source {display:inline-block;padding:.25rem .65rem;border-radius:999px;background:#172554;color:#7DD3FC;font-size:.78rem;font-weight:700}
[data-testid="stMetric"] {background:#111827;border:1px solid #1E293B;padding:.85rem;border-radius:12px;transition:transform .18s ease,border-color .18s ease,box-shadow .18s ease;animation:fadeUp .42s ease-out both}
[data-testid="stMetric"]:hover {transform:translateY(-3px);border-color:#38BDF8;box-shadow:0 10px 28px rgba(56,189,248,.10)}
[data-testid="stMetricLabel"] {color:#94A3B8}.stDataFrame{border:1px solid #1E293B;border-radius:10px}
div[data-testid="stExpander"] {background:#111827;border-color:#1E293B;border-radius:12px}
.stButton>button,.stDownloadButton>button{transition:transform .16s ease,box-shadow .16s ease,border-color .16s ease;border-radius:9px}
.stButton>button:hover,.stDownloadButton>button:hover{transform:translateY(-2px);box-shadow:0 8px 22px rgba(56,189,248,.14);border-color:#38BDF8}
.notice {padding:.8rem 1rem;background:#111827;border-left:3px solid #38BDF8;border-radius:8px;color:#CBD5E1}
@keyframes fadeUp{from{opacity:0;transform:translateY(8px)}to{opacity:1;transform:translateY(0)}}
@keyframes pulse{0%,100%{opacity:1}50%{opacity:.48}}
@media (prefers-reduced-motion:reduce){*{animation:none!important;transition:none!important}}
@media(max-width:760px){.hero-logo-window{display:none}.hero h1{font-size:1.55rem}}
</style>
"""

def apply_styles(): st.markdown(CSS, unsafe_allow_html=True)

@lru_cache(maxsize=1)
def _logo_uri():
    path=ROOT/"assets"/"christ_university.jpg"
    return "data:image/jpeg;base64,"+base64.b64encode(path.read_bytes()).decode() if path.exists() else ""

def header(title, subtitle, source="Campus Simulation"):
    logo=f'<div class="hero-logo-window"><img src="{_logo_uri()}" alt="CHRIST University logo"></div>' if _logo_uri() else ""
    st.markdown(f'<div class="hero"><div class="hero-copy"><span class="source">{source}</span><h1>{title}</h1><p>{subtitle}</p></div>{logo}</div>', unsafe_allow_html=True)

def sidebar_brand():
    st.sidebar.markdown('''<div class="sidebar-brand"><div class="brand-row"><div class="brand-mark"></div><div><div class="brand-name">Network Usage</div><div class="brand-subtitle">Campus Intelligence</div></div></div></div><div class="sidebar-section-label">Workspace navigation</div>''',unsafe_allow_html=True)

def sidebar_status(updated):
    stamp=updated.strftime("%d %b %Y · %H:%M")
    st.sidebar.markdown(f'''<div class="sidebar-status"><div class="status-copy"><div class="status-label">Campus simulation</div><div class="status-value">Updated {stamp}</div></div><div class="status-dot" title="Data ready"></div></div>''',unsafe_allow_html=True)

def scroll_to_top():
    """Reset Streamlit's scroll container after a page navigation rerun."""
    components.html("""<script>
    const resetScroll=()=>{
      const main=window.parent.document.querySelector('[data-testid="stMain"]');
      if(main){main.scrollTop=0;main.scrollLeft=0;}
      window.parent.scrollTo(0,0);
    };
    resetScroll();
    window.requestAnimationFrame(resetScroll);
    [80,200,450,800,1300].forEach(delay=>window.setTimeout(resetScroll,delay));
    </script>""",height=0,width=0)

