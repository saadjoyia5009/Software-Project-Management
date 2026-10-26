"""Integrated Part F dashboard and downloadable project health report."""

import csv
from datetime import date
from html import escape
from io import StringIO

import plotly.express as px
import streamlit as st

from database import fetch_all, fetch_one
from modules.integration_dashboard import build_dashboard_snapshot


def _currency(value):
    return f"PKR {value:,.2f}"


def _ratio(value):
    return f"{value:.2f}" if value is not None else "N/A"


def _report_csv(snapshot, status_date):
    """Create a small portable report using dashboard values only."""
    rows = [
        ("Report date", status_date.isoformat()),
        ("Overall progress (%)", f"{snapshot['progress']:.2f}"),
        ("Baseline duration (weeks)", str(snapshot["baseline_duration_weeks"])),
        ("Revised duration (weeks)", str(snapshot["revised_duration_weeks"])),
        ("Baseline approved budget (PKR)", f"{snapshot['approved_budget']:.2f}"),
        ("Revised approved budget (PKR)", f"{snapshot['revised_approved_budget']:.2f}"),
        ("Approved change cost (PKR)", f"{snapshot['approved_change_cost']:.2f}"),
        ("Planned activity cost (PKR)", f"{snapshot['planned_cost']:.2f}"),
        ("Actual cost (PKR)", f"{snapshot['evm']['ac']:.2f}"),
        ("Planned value (PKR)", f"{snapshot['evm']['pv']:.2f}"),
        ("Earned value (PKR)", f"{snapshot['evm']['ev']:.2f}"),
        ("CPI", _ratio(snapshot['evm']['cpi'])),
        ("SPI", _ratio(snapshot['evm']['spi'])),
        ("Delayed activities", str(len(snapshot['delayed_tasks']))),
        ("Pending change requests", str(len(snapshot['pending_changes']))),
        ("Unresolved critical defects", str(len(snapshot['critical_defects']))),
        ("Failed/pending quality checks", str(len(snapshot['attention_checks']))),
        ("Open risks", str(len(snapshot['open_risks']))),
    ]
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(("Metric", "Value"))
    writer.writerows(rows)
    return output.getvalue()


def _load_snapshot(project_id, status_date):
    project = fetch_one("SELECT * FROM projects WHERE project_id=?", (project_id,))
    tasks = fetch_all("SELECT * FROM wbs_tasks WHERE project_id=?", (project_id,))
    cost_records = fetch_all("SELECT record.* FROM cost_records record JOIN wbs_tasks task ON task.task_id=record.task_id WHERE task.project_id=?", (project_id,))
    changes = fetch_all("SELECT * FROM change_requests WHERE project_id=?", (project_id,))
    defects = fetch_all("SELECT * FROM defects WHERE project_id=?", (project_id,))
    checks = fetch_all("SELECT * FROM quality_checks WHERE project_id=?", (project_id,))
    risks = fetch_all("SELECT * FROM risks WHERE project_id=?", (project_id,))
    inconsistency = fetch_one(
        """SELECT COUNT(*) AS total FROM wbs_tasks task
           JOIN requirements requirement ON requirement.requirement_id=task.requirement_id
           WHERE task.project_id=?
             AND (requirement.status <> 'Approved' OR requirement.is_in_approved_scope <> 1)""",
        (project_id,),
    )
    return build_dashboard_snapshot(
        project, tasks, cost_records, changes, defects, checks, risks,
        status_date, inconsistency["total"],
    ), tasks


def _default_status_date(project_id):
    """Use today's date unless saved cost data has a later valid reporting date."""
    latest_record = fetch_one(
        """SELECT MAX(record.record_date) AS latest_date
           FROM cost_records record
           JOIN wbs_tasks task ON task.task_id=record.task_id
           WHERE task.project_id=?""",
        (project_id,),
    )
    try:
        latest_date = date.fromisoformat(latest_record["latest_date"])
    except (TypeError, ValueError):
        latest_date = None
    return max(date.today(), latest_date) if latest_date else date.today()


def _inject_dashboard_styles():
    """Apply presentation-only styling for the integrated dashboard."""
    st.markdown(
        """
        <style>
        [data-testid="stAppViewContainer"] {
            background: #0B1220;
            color: #F1F5F9;
        }
        [data-testid="stAppViewContainer"] .main .block-container {
            max-width: 1440px;
            padding-top: 2.25rem;
            padding-bottom: 3rem;
        }
        .dashboard-hero {
            display: flex;
            align-items: flex-end;
            justify-content: space-between;
            gap: 1.5rem;
            margin: 0 0 1.5rem;
            padding: 1.8rem 2rem;
            background: #151F32;
            border: 1px solid rgba(214, 179, 106, 0.28);
            border-radius: 18px;
            box-shadow: 0 18px 45px rgba(0, 0, 0, 0.20);
        }
        .dashboard-eyebrow {
            color: #D6B36A;
            font-size: 0.72rem;
            font-weight: 700;
            letter-spacing: 0.14em;
            text-transform: uppercase;
        }
        .dashboard-hero h1 {
            color: #F1F5F9;
            font-size: clamp(1.8rem, 3vw, 2.5rem);
            line-height: 1.12;
            letter-spacing: -0.04em;
            margin: 0.35rem 0 0.5rem;
        }
        .dashboard-hero p {
            color: #A7B4C8;
            font-size: 0.98rem;
            margin: 0;
        }
        .dashboard-project-pill {
            min-width: 220px;
            padding: 0.85rem 1rem;
            background: #1C2940;
            border: 1px solid rgba(45, 212, 191, 0.25);
            border-radius: 12px;
        }
        .dashboard-project-pill span {
            color: #A7B4C8;
            display: block;
            font-size: 0.73rem;
            font-weight: 600;
            letter-spacing: 0.08em;
            text-transform: uppercase;
        }
        .dashboard-project-pill strong {
            color: #F1F5F9;
            display: block;
            font-size: 0.98rem;
            margin-top: 0.28rem;
        }
        .dashboard-section-heading {
            color: #F1F5F9;
            font-size: 1.1rem;
            font-weight: 700;
            letter-spacing: -0.015em;
            margin: 0.2rem 0 0.2rem;
        }
        .dashboard-section-copy {
            color: #A7B4C8;
            font-size: 0.9rem;
            margin: 0 0 1rem;
        }
        [data-testid="stMetric"] {
            min-height: 128px;
            padding: 1rem 1.1rem;
            background: #151F32;
            border: 1px solid rgba(167, 180, 200, 0.16);
            border-top: 2px solid rgba(45, 212, 191, 0.72);
            border-radius: 14px;
            box-shadow: 0 10px 24px rgba(0, 0, 0, 0.16);
        }
        [data-testid="stMetricLabel"] {
            color: #A7B4C8;
            font-size: 0.83rem;
            font-weight: 600;
        }
        [data-testid="stMetricValue"] {
            color: #F1F5F9;
            font-size: 1.48rem;
            font-weight: 700;
            letter-spacing: -0.03em;
        }
        [data-testid="stTabs"] [data-baseweb="tab-list"] {
            gap: 0.45rem;
            border-bottom: 1px solid rgba(167, 180, 200, 0.18);
        }
        [data-testid="stTabs"] button[role="tab"] {
            color: #A7B4C8;
            border-radius: 8px 8px 0 0;
            font-weight: 600;
            padding: 0.7rem 1rem;
        }
        [data-testid="stTabs"] button[aria-selected="true"] {
            color: #F1F5F9;
            background: #1C2940;
        }
        [data-testid="stTabs"] [data-baseweb="tab-highlight"] {
            background-color: #D6B36A;
        }
        [data-testid="stDataFrame"] {
            border: 1px solid rgba(167, 180, 200, 0.18);
            border-radius: 12px;
            overflow: hidden;
        }
        [data-testid="stAlert"] {
            border-radius: 12px;
        }
        .dashboard-empty-state,
        .dashboard-report-panel {
            padding: 1.25rem 1.35rem;
            background: #151F32;
            border: 1px solid rgba(167, 180, 200, 0.16);
            border-radius: 14px;
        }
        .dashboard-empty-state {
            color: #A7B4C8;
            text-align: center;
        }
        .dashboard-report-panel {
            border-color: rgba(214, 179, 106, 0.30);
            margin-bottom: 1rem;
        }
        .dashboard-report-panel h3 {
            color: #F1F5F9;
            margin: 0 0 0.35rem;
        }
        .dashboard-report-panel p {
            color: #A7B4C8;
            margin: 0;
        }
        [data-testid="stDownloadButton"] > button {
            background: #D6B36A;
            border: 1px solid #D6B36A;
            border-radius: 9px;
            color: #0B1220;
            font-weight: 700;
            padding: 0.55rem 1rem;
        }
        [data-testid="stDownloadButton"] > button:hover {
            background: #e0c080;
            border-color: #e0c080;
            color: #0B1220;
        }
        @media (max-width: 700px) {
            .dashboard-hero { align-items: stretch; flex-direction: column; padding: 1.35rem; }
            .dashboard-project-pill { min-width: 0; }
            [data-testid="stAppViewContainer"] .main .block-container { padding-top: 1.25rem; }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _style_chart(chart, color):
    """Use the dashboard palette without changing the chart's underlying data."""
    chart.update_layout(
        paper_bgcolor="#151F32",
        plot_bgcolor="#151F32",
        font={"color": "#F1F5F9", "family": "Inter, ui-sans-serif, system-ui, sans-serif"},
        title={"font": {"color": "#F1F5F9", "size": 18}, "x": 0.02},
        margin={"l": 16, "r": 16, "t": 56, "b": 16},
        xaxis={"gridcolor": "rgba(167, 180, 200, 0.12)", "linecolor": "rgba(167, 180, 200, 0.20)"},
        yaxis={"gridcolor": "rgba(167, 180, 200, 0.12)", "linecolor": "rgba(167, 180, 200, 0.20)"},
    )
    chart.update_traces(marker_color=color, marker_line_color="#0B1220", marker_line_width=1)
    return chart


def show_dashboard():
    """Render the project-wide Part F monitoring dashboard and export report."""
    project = fetch_one("SELECT project_id, name FROM projects ORDER BY project_id LIMIT 1")
    if not project:
        st.error("No project found. Initialize the database first.")
        return

    _inject_dashboard_styles()
    st.markdown(
        f"""
        <section class="dashboard-hero">
            <div>
                <div class="dashboard-eyebrow">Healthcare project intelligence</div>
                <h1>Project Command Center</h1>
                <p>A consolidated view of delivery, financial performance, quality, and risk.</p>
            </div>
            <div class="dashboard-project-pill">
                <span>Active project</span>
                <strong>{escape(project['name'])}</strong>
            </div>
        </section>
        """,
        unsafe_allow_html=True,
    )
    _, date_column = st.columns([3, 1])
    with date_column:
        default_status_date = _default_status_date(project["project_id"])
        status_date = st.date_input(
            "Status date",
            default_status_date,
            key=(
                f"dashboard_status_date_{project['project_id']}_"
                f"{default_status_date.isoformat()}"
            ),
        )
    snapshot, tasks = _load_snapshot(project["project_id"], status_date)
    overview, evm_tab, exceptions, report = st.tabs(["Overview", "EVM & Budget", "Exceptions", "Export Report"])

    with overview:
        st.markdown('<div class="dashboard-section-heading">Delivery overview</div>', unsafe_allow_html=True)
        st.markdown('<p class="dashboard-section-copy">Current delivery health, active exceptions, and workload status.</p>', unsafe_allow_html=True)
        first, second, third, fourth, fifth, sixth = st.columns(6)
        first.metric("Overall progress", f"{snapshot['progress']:.1f}%")
        second.metric("Baseline duration", f"{snapshot['baseline_duration_weeks']} weeks")
        third.metric(
            "Revised duration",
            f"{snapshot['revised_duration_weeks']} weeks",
            delta=(
                f"+{snapshot['approved_change_duration_weeks']} approved week(s)"
                if snapshot["approved_change_duration_weeks"] else None
            ),
        )
        fourth.metric("Delayed activities", len(snapshot["delayed_tasks"]))
        fifth.metric("Pending changes", len(snapshot["pending_changes"]))
        sixth.metric("Critical defects", len(snapshot["critical_defects"]))
        st.markdown("<br>", unsafe_allow_html=True)
        if snapshot["warnings"]:
            st.markdown('<div class="dashboard-section-heading">Attention required</div>', unsafe_allow_html=True)
            for warning in dict.fromkeys(snapshot["warnings"]):
                st.warning(warning)
        else:
            st.success("No cross-module consistency, budget, or EVM warnings at this status date.")
        if tasks:
            status_counts = {}
            for task in tasks:
                status_counts[task["status"]] = status_counts.get(task["status"], 0) + 1
            rows = [{"Status": key, "Activities": value} for key, value in status_counts.items()]
            chart = px.bar(rows, x="Status", y="Activities", title="Activity status summary")
            st.plotly_chart(_style_chart(chart, "#2DD4BF"), use_container_width=True)
        else:
            st.markdown('<div class="dashboard-empty-state">No activities are available yet. Add project activities to populate the delivery timeline.</div>', unsafe_allow_html=True)

    with evm_tab:
        st.markdown('<div class="dashboard-section-heading">Financial performance</div>', unsafe_allow_html=True)
        st.markdown('<p class="dashboard-section-copy">Approved funding, activity costs, and earned value metrics as of the selected status date.</p>', unsafe_allow_html=True)
        first, second, third, fourth, fifth = st.columns(5)
        first.metric("Baseline approved budget", _currency(snapshot["approved_budget"]))
        second.metric("Revised approved budget", _currency(snapshot["revised_approved_budget"]))
        third.metric("Planned activity cost", _currency(snapshot["planned_cost"]))
        fourth.metric("Actual Cost (AC)", _currency(snapshot["evm"]["ac"]))
        fifth.metric("Approved change cost", _currency(snapshot["approved_change_cost"]))
        if snapshot["future_cost_record_count"]:
            st.info(
                f"{snapshot['future_cost_record_count']} saved cost record(s) are dated after "
                f"{status_date.isoformat()} and are excluded from Actual Expenditure."
            )
        st.markdown("<br>", unsafe_allow_html=True)
        first, second, third, fourth, fifth, sixth = st.columns(6)
        first.metric("PV", _currency(snapshot["evm"]["pv"]))
        second.metric("EV", _currency(snapshot["evm"]["ev"]))
        third.metric("Cost Variance (CV)", _currency(snapshot["evm"]["cv"]))
        fourth.metric("Schedule Variance (SV)", _currency(snapshot["evm"]["sv"]))
        fifth.metric("CPI", _ratio(snapshot["evm"]["cpi"]))
        sixth.metric("SPI", _ratio(snapshot["evm"]["spi"]))
        chart = [
            {"Measure": "Baseline budget", "PKR": snapshot["approved_budget"]},
            {"Measure": "Revised budget", "PKR": snapshot["revised_approved_budget"]},
            {"Measure": "Planned cost", "PKR": snapshot["planned_cost"]},
            {"Measure": "PV", "PKR": snapshot["evm"]["pv"]},
            {"Measure": "EV", "PKR": snapshot["evm"]["ev"]},
            {"Measure": "AC", "PKR": snapshot["evm"]["ac"]},
        ]
        evm_chart = px.bar(chart, x="Measure", y="PKR", title="Budget and EVM indicators")
        st.plotly_chart(_style_chart(evm_chart, "#D6B36A"), use_container_width=True)
        st.caption("Baseline and revised values are derived from saved project data. Approved change costs and schedule impacts are included once only; pending and rejected changes are excluded.")

    with exceptions:
        st.markdown('<div class="dashboard-section-heading">Exceptions requiring review</div>', unsafe_allow_html=True)
        st.markdown('<p class="dashboard-section-copy">Operational issues are grouped below so teams can focus on the items requiring action.</p>', unsafe_allow_html=True)
        if snapshot["delayed_tasks"]:
            st.subheader("Delayed activities")
            st.dataframe(snapshot["delayed_tasks"], use_container_width=True, hide_index=True)
        else:
            st.markdown('<div class="dashboard-empty-state">No delayed activities at this status date.</div>', unsafe_allow_html=True)
        if snapshot["pending_changes"]:
            st.subheader("Pending change requests")
            st.dataframe(snapshot["pending_changes"], use_container_width=True, hide_index=True)
        else:
            st.markdown('<div class="dashboard-empty-state">No change requests are awaiting a decision.</div>', unsafe_allow_html=True)
        if snapshot["critical_defects"]:
            st.subheader("Unresolved critical defects")
            st.dataframe(snapshot["critical_defects"], use_container_width=True, hide_index=True)
        else:
            st.markdown('<div class="dashboard-empty-state">No unresolved critical defects.</div>', unsafe_allow_html=True)
        if snapshot["attention_checks"]:
            st.subheader("Failed or pending quality checks")
            st.dataframe(snapshot["attention_checks"], use_container_width=True, hide_index=True)
        else:
            st.markdown('<div class="dashboard-empty-state">No failed or pending quality checks.</div>', unsafe_allow_html=True)
        if snapshot["open_risks"]:
            st.subheader("Open risks")
            st.dataframe(snapshot["open_risks"], use_container_width=True, hide_index=True)
        else:
            st.markdown('<div class="dashboard-empty-state">No open risks are currently recorded.</div>', unsafe_allow_html=True)

    with report:
        st.markdown(
            """
            <section class="dashboard-report-panel">
                <h3>Project health report</h3>
                <p>Download a portable snapshot of the selected date's delivery, cost, earned value, quality, and risk indicators.</p>
            </section>
            """,
            unsafe_allow_html=True,
        )
        st.download_button(
            "Download dashboard report (CSV)",
            data=_report_csv(snapshot, status_date),
            file_name=f"project_health_{status_date.isoformat()}.csv",
            mime="text/csv",
        )
        st.caption("The export contains the current consolidated project health metrics and no patient data.")
