import streamlit as st
from modules.project_details import show_project_details
from modules.scope_wbs import show_scope_wbs
from modules.schedule_management import show_schedule_management
from modules.cost_evm import show_cost_evm
from modules.quality_risk_management import show_quality_risk_management
from modules.dashboard import show_dashboard
from modules.team_resources import show_team_resources

from config import PROJECT_NAME, DATABASE_PATH
from database import initialize_db, fetch_one, fetch_all

st.set_page_config(
    page_title="Smart Healthcare PM",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Premium dark theme and spacious sidebar styling.
st.markdown(r"""
<style>
:root{--app-bg:#0b1220;--surface:#151f32;--border:rgba(148,163,184,.16);--muted:#a7b4c8}
.stApp{background:radial-gradient(ellipse at 10% 0%,rgba(79,140,255,.08),transparent 35%),radial-gradient(ellipse at 95% 5%,rgba(128,103,255,.07),transparent 30%),var(--app-bg);color:#f1f5f9}
[data-testid="stHeader"]{background:rgba(11,18,32,.86)}
[data-testid="stSidebar"]{background:linear-gradient(180deg,#101a2d 0%,#0c1423 100%);border-right:1px solid var(--border)}
[data-testid="stSidebar"]>div:first-child{padding-top:1.2rem}
.sidebar-brand{padding:1rem .85rem 1.2rem;margin:.1rem 0 1.1rem;border:1px solid rgba(129,160,255,.16);border-radius:20px;background:linear-gradient(135deg,rgba(79,140,255,.13),rgba(128,103,255,.07));box-shadow:0 12px 35px rgba(0,0,0,.12)}
.brand-top{display:flex;align-items:center;gap:.75rem}.brand-icon{display:flex;align-items:center;justify-content:center;min-width:3rem;height:3rem;border-radius:15px;background:linear-gradient(135deg,#2563eb,#6656e8);box-shadow:0 6px 20px rgba(79,140,255,.25);font-size:1.65rem}
.brand-title{color:#f8fafc;font-size:1.18rem;font-weight:800;line-height:1.2;letter-spacing:-.03em}.brand-subtitle{color:#a7b4c8;font-size:.82rem;margin-top:.35rem;line-height:1.4}
.nav-heading{color:#a7b4c8;font-size:.76rem;font-weight:750;letter-spacing:.13em;text-transform:uppercase;margin:.6rem 0 .25rem .25rem}
[data-testid="stSidebar"] [data-testid="stRadio"]>label{display:none}
[data-testid="stSidebar"] [data-testid="stRadio"]>div{gap:.42rem}
[data-testid="stSidebar"] [data-testid="stRadio"] label{background:rgba(255,255,255,.025);border:1px solid transparent;border-radius:13px;padding:.68rem .72rem;margin:0;transition:background 160ms ease,border-color 160ms ease,transform 160ms ease}
[data-testid="stSidebar"] [data-testid="stRadio"] label:hover{background:rgba(79,140,255,.09);border-color:rgba(129,160,255,.18);transform:translateX(2px)}
[data-testid="stSidebar"] [data-testid="stRadio"] label:has(input:checked){background:linear-gradient(105deg,rgba(59,130,246,.30),rgba(109,80,240,.23));border:1px solid rgba(110,143,255,.5);box-shadow:inset 3px 0 0 #5b8cff,0 5px 18px rgba(0,0,0,.12)}
[data-testid="stSidebar"] [data-testid="stRadio"] label p{color:#dbe5f5;font-weight:550;font-size:.91rem}
[data-testid="stSidebar"] [data-testid="stRadio"] label:has(input:checked) p{color:#fff;font-weight:700}
[data-testid="stSidebar"] [data-testid="stRadio"] [data-testid="stMarkdownContainer"] p{margin-bottom:0}
.sidebar-footer{margin-top:1.3rem;padding:1rem .85rem;border-top:1px solid var(--border);color:#91a0b8;font-size:.78rem;line-height:1.6}
.footer-pill{display:inline-block;margin-top:.6rem;padding:.35rem .65rem;border:1px solid rgba(129,160,255,.2);border-radius:999px;background:rgba(79,140,255,.07);color:#bdc9e0;font-size:.72rem}
.page-hero{padding:1.35rem 1.55rem;margin:.25rem 0 1.4rem;border:1px solid var(--border);border-radius:22px;background:linear-gradient(115deg,rgba(21,31,50,.96),rgba(20,29,49,.75));box-shadow:0 14px 35px rgba(0,0,0,.12);position:relative;overflow:hidden}
.page-hero:after{content:"";position:absolute;top:-65px;right:-35px;width:190px;height:190px;border-radius:50%;background:radial-gradient(circle,rgba(79,140,255,.18),transparent 70%);pointer-events:none}
.hero-eyebrow{color:#75a5ff;font-size:.76rem;font-weight:750;letter-spacing:.12em;text-transform:uppercase;margin-bottom:.55rem}
.hero-title{color:#f8fafc;font-size:clamp(1.55rem,2.5vw,2.2rem);font-weight:800;line-height:1.2;letter-spacing:-.04em;margin:0}
.hero-description{color:#a7b4c8;margin-top:.55rem;font-size:.98rem;line-height:1.55;max-width:760px}
div[data-testid="stMetric"]{background:linear-gradient(145deg,rgba(21,31,50,.92),rgba(16,26,44,.92));border:1px solid var(--border);padding:1rem 1.1rem;border-radius:16px}
div[data-testid="stMetric"] label{color:#a7b4c8!important}
.stButton>button{border-radius:10px;border:1px solid rgba(129,160,255,.28)}
hr{border-color:var(--border)}
@media(max-width:700px){.sidebar-brand{padding:.85rem .7rem}.brand-title{font-size:1.05rem}.page-hero{padding:1.1rem;border-radius:17px}}
</style>
""", unsafe_allow_html=True)

@st.cache_resource
def setup_database():
    """Initialize database once per Streamlit process."""
    initialize_db()
    return True

try:
    setup_database()
    database_ready = True
except Exception as error:
    database_ready = False
    st.error(f"Database initialization failed: {error}")

with st.sidebar:
    st.markdown("""
    <div class="sidebar-brand">
      <div class="brand-top">
        <div class="brand-icon">🏥</div>
        <div><div class="brand-title">Healthcare <span style="color:#7c91ff">PM</span></div>
        <div class="brand-subtitle">Project Management System</div></div>
      </div>
    </div>
    <div class="nav-heading">Navigation</div>
    """, unsafe_allow_html=True)

    pages = [
        "Dashboard",
        "Project Details",
        "Team & Resources",
        "Scope Management & WBS",
        "Schedule & Gantt",
        "Cost Management & EVM",
        "Quality & Risk Control",
    ]
    selected_page = st.radio(
        "Navigation", pages, label_visibility="collapsed", key="main_navigation"
    )
    st.markdown("""
    <div class="sidebar-footer">
      <div>Better planning. Clearer decisions.</div>
      <div class="footer-pill">🛡️ Smart Healthcare PM &nbsp; • &nbsp; v1.0</div>
    </div>
    """, unsafe_allow_html=True)

st.markdown(f"""
<div class="page-hero">
  <div class="hero-eyebrow">SMART HEALTHCARE • PROJECT CONTROL</div>
  <div class="hero-title">🏥 {PROJECT_NAME if PROJECT_NAME else "Smart Healthcare Project Management"}</div>
  <div class="hero-description">Plan activities, monitor schedules and budgets, track quality, and manage project risks from one workspace.</div>
</div>
""", unsafe_allow_html=True)

# Existing page routing preserved.
if database_ready:
    project = fetch_one("""
        SELECT *
        FROM projects
        ORDER BY project_id
        LIMIT 1
    """)

    if project:
        if selected_page == "Dashboard":
            show_dashboard()
        elif selected_page == "Project Details":
            show_project_details()
        elif selected_page == "Team & Resources":
            show_team_resources()
        elif selected_page == "Scope Management & WBS":
            show_scope_wbs()
        elif selected_page == "Schedule & Gantt":
            show_schedule_management()
        elif selected_page == "Cost Management & EVM":
            show_cost_evm()
        elif selected_page == "Quality & Risk Control":
            show_quality_risk_management()
        else:
            st.subheader(selected_page)
            st.info(f"The {selected_page} module will be implemented in the next development steps.")
    else:
        st.warning("No project record was found.")
else:
    st.error("The application could not connect to the database. Check the schema.sql file and terminal error.")
