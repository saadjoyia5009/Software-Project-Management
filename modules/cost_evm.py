"""Streamlit UI for Part D: activity cost management and earned value analysis."""

from datetime import date
import sqlite3

import plotly.express as px
import streamlit as st

from database import fetch_all, fetch_one, get_connection
from modules.evm_service import calculate_evm, save_cost_record, update_cost_record


def _inject_cost_evm_styles():
    st.markdown("""
    <style>
    :root { color-scheme: dark; }
    .stApp { background: #0B1220; color: #F1F5F9; }
    [data-testid="stHeader"] { background: rgba(11,18,32,.92); }
    [data-testid="stSidebar"] { background: #101A2B; border-right: 1px solid rgba(167,180,200,.16); }
    [data-testid="stMetric"] { background: #151F32; border: 1px solid rgba(167,180,200,.16); padding: 16px 18px; border-radius: 15px; }
    [data-testid="stMetricLabel"] { color: #A7B4C8; }
    [data-testid="stMetricValue"] { color: #D6B36A; }
    [data-testid="stTabs"] button { color: #A7B4C8; border-radius: 10px 10px 0 0; }
    [data-testid="stTabs"] button[aria-selected="true"] { color: #D6B36A; border-bottom-color: #D6B36A; background: #1C2940; }
    [data-testid="stExpander"] { background: #151F32; border: 1px solid rgba(167,180,200,.16); border-radius: 14px; }
    [data-testid="stForm"] { background: #151F32; border: 1px solid rgba(167,180,200,.13); padding: 18px; border-radius: 15px; }
    [data-testid="stDataFrame"] { border: 1px solid rgba(167,180,200,.16); border-radius: 12px; overflow: hidden; }
    .stTextInput input, .stTextArea textarea, [data-baseweb="select"] > div, [data-baseweb="input"] > div { background: #1C2940; border-color: rgba(167,180,200,.22); color: #F1F5F9; border-radius: 9px; }
    [data-testid="stDateInput"] input, [data-testid="stNumberInput"] input { background: #1C2940; color: #F1F5F9; }
    .stButton button, .stFormSubmitButton button { border-radius: 10px; border: 1px solid rgba(214,179,106,.42); background: #D6B36A; color: #0B1220; font-weight: 650; }
    .stButton button:hover, .stFormSubmitButton button:hover { border-color: #2DD4BF; background: #2DD4BF; color: #0B1220; }
    [data-testid="stAlert"] { border-radius: 12px; }
    h1, h2, h3 { color: #F1F5F9; }
    p, label, [data-testid="stCaptionContainer"] { color: #A7B4C8; }
    .cost-hero { padding: 24px 26px; margin: 0 0 22px 0; border-radius: 18px; background: linear-gradient(115deg, #151F32, #1C2940); border: 1px solid rgba(214,179,106,.24); box-shadow: 0 12px 30px rgba(0,0,0,.16); }
    .cost-eyebrow { color: #2DD4BF; font-size: .76rem; letter-spacing: .14em; font-weight: 700; text-transform: uppercase; margin-bottom: 8px; }
    .cost-title { color: #F1F5F9; font-size: 1.85rem; font-weight: 750; line-height: 1.2; margin: 0; }
    .cost-subtitle { color: #A7B4C8; margin-top: 8px; font-size: .96rem; }
    .cost-section { border-left: 3px solid #D6B36A; padding: 3px 0 3px 12px; margin: 8px 0 16px 0; color: #F1F5F9; font-size: 1.18rem; font-weight: 700; }
    </style>
    """, unsafe_allow_html=True)


def _section_header(title):
    st.markdown(f'<div class="cost-section">{title}</div>', unsafe_allow_html=True)


def _currency(value):
    return f"PKR {value:,.2f}"


def _ratio(value):
    return f"{value:.2f}" if value is not None else "N/A"


def _show_evm_summary(evm):
    first, second, third, fourth = st.columns(4)
    first.metric("Planned activity cost", _currency(evm["total_planned_cost"]))
    second.metric("PV", _currency(evm["pv"]))
    third.metric("EV", _currency(evm["ev"]))
    fourth.metric("AC", _currency(evm["ac"]))
    first, second, third, fourth = st.columns(4)
    first.metric("Cost variance (EV − AC)", _currency(evm["cv"]))
    second.metric("Schedule variance (EV − PV)", _currency(evm["sv"]))
    third.metric("CPI (EV / AC)", _ratio(evm["cpi"]))
    fourth.metric("SPI (EV / PV)", _ratio(evm["spi"]))
    if evm["warnings"]:
        for warning in evm["warnings"]:
            st.warning(warning)
    else:
        st.success("No EVM cost or schedule performance warnings at this status date.")


def _planned_cost_editor(task, project_id):
    with st.expander(f"Set planned cost: {task['task_name']}"):
        with st.form(f"planned_cost_{task['task_id']}"):
            planned_cost = st.number_input("Estimated planned cost (PKR)", min_value=0.0, value=float(task["planned_cost"] or 0), step=1000.0)
            if st.form_submit_button("Save planned cost"):
                try:
                    with get_connection() as connection:
                        connection.execute("UPDATE wbs_tasks SET planned_cost=? WHERE task_id=? AND project_id=?", (planned_cost, task["task_id"], project_id))
                    st.success("Planned activity cost saved.")
                    st.rerun()
                except sqlite3.Error as error:
                    st.error(f"Could not save planned cost: {error}")


def show_cost_evm():
    """Render the cost and EVM page using the existing activity schedule."""
    _inject_cost_evm_styles()
    st.markdown('''<div class="cost-hero"><div class="cost-eyebrow">PROJECT CONTROLS · PART D</div><div class="cost-title">Cost Management &amp; Earned Value Analysis</div><div class="cost-subtitle">Track planned activity costs, monitor project performance, and maintain expenditure records.</div></div>''', unsafe_allow_html=True)
    project = fetch_one("SELECT project_id, approved_budget FROM projects ORDER BY project_id LIMIT 1")
    if not project:
        st.error("No project found. Initialize the database first.")
        return
    project_id = project["project_id"]
    costs_tab, evm_tab, records_tab = st.tabs(["Activity Costs", "EVM Dashboard", "Cost Records"])

    with costs_tab:
        _section_header("Activity Cost Estimates")
        tasks = fetch_all("SELECT task_id, task_name, planned_cost, progress, start_date, end_date, status FROM wbs_tasks WHERE project_id=? ORDER BY task_name", (project_id,))
        total = sum(float(task["planned_cost"] or 0) for task in tasks)
        st.metric("Total planned activity cost", _currency(total), delta=f"Approved budget: {_currency(float(project['approved_budget']))}")
        if total > float(project["approved_budget"]):
            st.warning("Total activity planned cost exceeds the approved project budget.")
        if tasks:
            st.dataframe(tasks, use_container_width=True, hide_index=True)
            for task in tasks:
                _planned_cost_editor(task, project_id)
        else:
            st.info("Add activities in Schedule & Gantt before estimating costs.")

    with evm_tab:
        _section_header("Earned Value Monitoring")
        status_date = st.date_input("EVM status date", date.today())
        threshold = st.number_input("CPI/SPI warning threshold", min_value=0.01, max_value=2.0, value=0.90, step=0.05)
        tasks = fetch_all("SELECT task_id, task_name, planned_cost, progress, start_date, end_date FROM wbs_tasks WHERE project_id=?", (project_id,))
        records = fetch_all("SELECT record.task_id, record.planned_cost, record.actual_cost, record.budgeted_value, record.record_date, task.task_name FROM cost_records record JOIN wbs_tasks task ON task.task_id=record.task_id WHERE task.project_id=?", (project_id,))
        evm = calculate_evm(tasks, records, status_date, threshold)
        st.caption(f"All values are PKR and are calculated for {status_date.isoformat()}.")
        _show_evm_summary(evm)
        if evm["activities"]:
            _section_header("PV and EV by Activity")
            st.dataframe(evm["activities"], use_container_width=True, hide_index=True)
            chart_rows = []
            for activity in evm["activities"]:
                chart_rows.extend([
                    {"Activity": activity["activity"], "Measure": "PV", "Value": activity["pv"]},
                    {"Activity": activity["activity"], "Measure": "EV", "Value": activity["ev"]},
                ])
            figure = px.bar(chart_rows, x="Activity", y="Value", color="Measure", barmode="group", title="Planned vs earned value by activity (PKR)", color_discrete_map={"PV": "#D6B36A", "EV": "#2DD4BF"})
            figure.update_layout(paper_bgcolor="#151F32", plot_bgcolor="#151F32", font={"color": "#F1F5F9"}, title_font={"color": "#F1F5F9"}, xaxis={"gridcolor": "rgba(167,180,200,.12)"}, yaxis={"gridcolor": "rgba(167,180,200,.12)", "title": "Value (PKR)"}, legend_title_text="Measure")
            st.plotly_chart(figure, use_container_width=True)
        else:
            st.info("EVM needs scheduled activities with planned costs.")
        st.caption("PV is prorated across each scheduled activity through the status date. EV equals activity planned cost × recorded progress. AC is the sum of dated actual-expenditure records through the status date. CPI/SPI show N/A when their denominator is zero.")

    with records_tab:
        _section_header("Actual Expenditure and Budgeted Completed Work")
        tasks = fetch_all("SELECT task_id, task_name, planned_cost FROM wbs_tasks WHERE project_id=? ORDER BY task_name", (project_id,))
        with st.form("save_cost_record", clear_on_submit=True):
            if tasks:
                task_ids = [task["task_id"] for task in tasks]
                labels = {task["task_id"]: f"{task['task_name']} (planned {_currency(float(task['planned_cost'] or 0))})" for task in tasks}
                task_id = st.selectbox("Activity", task_ids, format_func=lambda value: labels[value])
                actual_cost = st.number_input("Actual expenditure (PKR)", min_value=0.0, value=0.0, step=1000.0)
                budgeted_value = st.number_input("Budgeted cost of completed work (PKR)", min_value=0.0, value=0.0, step=1000.0)
                record_date = st.date_input("Cost record date", date.today())
                if st.form_submit_button("Save cost record"):
                    try:
                        with get_connection() as connection:
                            _, created = save_cost_record(connection, project_id, task_id, actual_cost, budgeted_value, record_date)
                        st.success("Cost record added." if created else "Existing cost record for this date updated.")
                        st.rerun()
                    except (sqlite3.Error, ValueError) as error:
                        st.error(f"Could not save cost record: {error}")
            else:
                st.info("Add an activity before recording costs.")
        records = fetch_all("SELECT record.cost_id, task.task_name AS activity, record.planned_cost, record.actual_cost, record.budgeted_value, record.record_date FROM cost_records record JOIN wbs_tasks task ON task.task_id=record.task_id WHERE task.project_id=? ORDER BY record.record_date DESC, record.cost_id DESC", (project_id,))
        if records:
            st.dataframe(records, use_container_width=True, hide_index=True)
            record_ids = [record["cost_id"] for record in records]
            labels = {
                record["cost_id"]: (
                    f"#{record['cost_id']} — {record['activity']} "
                    f"({record['record_date']})"
                )
                for record in records
            }
            selected_id = st.selectbox(
                "Cost record to edit",
                record_ids,
                format_func=lambda value: labels[value],
            )
            selected = next(record for record in records if record["cost_id"] == selected_id)
            try:
                selected_date = date.fromisoformat(selected["record_date"])
            except (TypeError, ValueError):
                st.error("This cost record has an invalid date and cannot be edited until it is corrected in the database.")
                return
            with st.form(f"edit_cost_record_{selected_id}"):
                st.text_input("Activity", selected["activity"], disabled=True)
                actual_cost = st.number_input(
                    "Actual expenditure (PKR)",
                    min_value=0.0,
                    value=float(selected["actual_cost"]),
                    step=1000.0,
                    key=f"edit_actual_{selected_id}",
                )
                budgeted_value = st.number_input(
                    "Budgeted cost of completed work (PKR)",
                    min_value=0.0,
                    value=float(selected["budgeted_value"]),
                    step=1000.0,
                    key=f"edit_budgeted_{selected_id}",
                )
                record_date = st.date_input(
                    "Cost record date",
                    selected_date,
                    key=f"edit_date_{selected_id}",
                )
                save_column, cancel_column = st.columns(2)
                save_changes = save_column.form_submit_button("Save changes")
                cancel = cancel_column.form_submit_button("Cancel")
                if cancel:
                    st.rerun()
                if save_changes:
                    try:
                        with get_connection() as connection:
                            update_cost_record(
                                connection,
                                project_id,
                                selected_id,
                                actual_cost,
                                budgeted_value,
                                record_date,
                            )
                        st.success("Cost record updated. EVM metrics have been recalculated.")
                        st.rerun()
                    except (sqlite3.Error, ValueError) as error:
                        st.error(f"Could not update cost record: {error}")
        else:
            st.info("No cost records have been saved.")
