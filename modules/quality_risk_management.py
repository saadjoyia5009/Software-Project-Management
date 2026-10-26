"""Streamlit UI for Part E: defects, quality checks, risks, and PDPC actions."""

from datetime import date
import sqlite3

import plotly.graph_objects as go
import streamlit as st

from database import fetch_all, fetch_one, get_connection
from modules.quality_risk_service import (
    DEFECT_SEVERITIES, DEFECT_STATUSES, PDPC_STATUSES, QUALITY_RESULTS,
    RISK_STATUSES, risk_priority, validate_defect, validate_pdpc,
    validate_project_member, validate_quality_check, validate_risk,
)


def _inject_quality_risk_styles():
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
    .stButton button, .stFormSubmitButton button { border-radius: 10px; border: 1px solid rgba(214,179,106,.42); background: #D6B36A; color: #0B1220; font-weight: 650; }
    .stButton button:hover, .stFormSubmitButton button:hover { border-color: #2DD4BF; background: #2DD4BF; color: #0B1220; }
    [data-testid="stAlert"] { border-radius: 12px; }
    h1, h2, h3 { color: #F1F5F9; }
    p, label, [data-testid="stCaptionContainer"] { color: #A7B4C8; }
    .quality-hero { padding: 24px 26px; margin: 0 0 22px 0; border-radius: 18px; background: linear-gradient(115deg, #151F32, #1C2940); border: 1px solid rgba(214,179,106,.24); box-shadow: 0 12px 30px rgba(0,0,0,.16); }
    .quality-eyebrow { color: #2DD4BF; font-size: .76rem; letter-spacing: .14em; font-weight: 700; text-transform: uppercase; margin-bottom: 8px; }
    .quality-title { color: #F1F5F9; font-size: 1.85rem; font-weight: 750; line-height: 1.2; margin: 0; }
    .quality-subtitle { color: #A7B4C8; margin-top: 8px; font-size: .96rem; }
    .quality-section { border-left: 3px solid #D6B36A; padding: 3px 0 3px 12px; margin: 8px 0 16px 0; color: #F1F5F9; font-size: 1.18rem; font-weight: 700; }
    </style>
    """, unsafe_allow_html=True)


def _section_header(title):
    st.markdown(f'<div class="quality-section">{title}</div>', unsafe_allow_html=True)


def _errors(errors):
    for error in errors:
        st.error(error)


def _index(options, current):
    return options.index(current) if current in options else 0


def _member_select(label, members, current=None):
    ids = [None] + [member["member_id"] for member in members]
    labels = ["Unassigned"] + [f"{member['name']} — {member['role']}" for member in members]
    return st.selectbox(label, ids, format_func=lambda value: labels[ids.index(value)], index=ids.index(current) if current in ids else 0)


def _defect_editor(item, project_id, members):
    with st.expander(f"Edit defect: {item['title']}"):
        with st.form(f"defect_{item['defect_id']}"):
            title = st.text_input("Title", item["title"])
            description = st.text_area("Description", item.get("description") or "")
            severity = st.selectbox("Severity", DEFECT_SEVERITIES, _index(DEFECT_SEVERITIES, item["severity"]))
            status = st.selectbox("Status", DEFECT_STATUSES, _index(DEFECT_STATUSES, item["status"]))
            assignee = _member_select("Assigned team member", members, item.get("assigned_member_id"))
            reported = st.date_input("Reported date", date.fromisoformat(item["reported_date"]))
            resolution = st.text_area("Resolution details", item.get("resolution_notes") or "")
            save = st.form_submit_button("Save defect")
            delete = st.form_submit_button("Delete defect")
            if save:
                errors = validate_defect(title, severity, status, reported)
                if errors:
                    _errors(errors)
                else:
                    try:
                        with get_connection() as connection:
                            validate_project_member(connection, project_id, assignee)
                            resolved = date.today().isoformat() if status in ("Resolved", "Verified", "Closed") else None
                            connection.execute("UPDATE defects SET title=?, description=?, severity=?, assigned_member_id=?, status=?, reported_date=?, resolution_notes=?, resolved_date=? WHERE defect_id=? AND project_id=?", (title.strip(), description.strip(), severity, assignee, status, reported.isoformat(), resolution.strip(), resolved, item["defect_id"], project_id))
                        st.success("Defect updated.")
                        st.rerun()
                    except (sqlite3.Error, ValueError) as error:
                        st.error(f"Could not update defect: {error}")
            if delete:
                try:
                    with get_connection() as connection:
                        connection.execute("DELETE FROM defects WHERE defect_id=? AND project_id=?", (item["defect_id"], project_id))
                    st.success("Defect deleted.")
                    st.rerun()
                except sqlite3.Error as error:
                    st.error(f"Could not delete defect: {error}")


def _quality_editor(item, project_id, members):
    with st.expander(f"Edit check: {item['item_name']}"):
        with st.form(f"quality_{item['check_id']}"):
            name = st.text_input("Checklist item", item["item_name"])
            expected = st.text_area("Expected result", item.get("expected_result") or "")
            actual = st.text_area("Actual result / observation", item.get("actual_result") or "")
            current = "Pending" if item["result"] == "Not Tested" else item["result"]
            result = st.selectbox("Result", QUALITY_RESULTS, _index(QUALITY_RESULTS, current))
            tester = _member_select("Responsible person", members, item.get("tester_id"))
            inspected = st.date_input("Inspection date", date.fromisoformat(item["inspection_date"]) if item.get("inspection_date") else date.today())
            remarks = st.text_area("Remarks", item.get("remarks") or "")
            if st.form_submit_button("Save quality check"):
                errors = validate_quality_check(name, result, inspected)
                if errors:
                    _errors(errors)
                else:
                    try:
                        with get_connection() as connection:
                            validate_project_member(connection, project_id, tester)
                            stored_result = "Not Tested" if result == "Pending" else result
                            connection.execute("UPDATE quality_checks SET item_name=?, expected_result=?, actual_result=?, inspection_date=?, result=?, tester_id=?, remarks=? WHERE check_id=? AND project_id=?", (name.strip(), expected.strip(), actual.strip(), inspected.isoformat(), stored_result, tester, remarks.strip(), item["check_id"], project_id))
                        st.success("Quality check updated.")
                        st.rerun()
                    except (sqlite3.Error, ValueError) as error:
                        st.error(f"Could not update quality check: {error}")


def _risk_editor(item, project_id, members):
    with st.expander(f"Edit risk: {item['title']} ({item['risk_score']})"):
        with st.form(f"risk_{item['risk_id']}"):
            title = st.text_input("Title", item["title"])
            description = st.text_area("Description", item.get("description") or "")
            likelihood = st.slider("Likelihood (1–5)", 1, 5, int(item["likelihood"])
            )
            impact = st.slider("Impact (1–5)", 1, 5, int(item["impact"]))
            st.caption(f"Calculated score: {likelihood * impact} — {risk_priority(likelihood * impact)}")
            response = st.text_area("Response strategy", item.get("response_action") or "")
            owner = _member_select("Risk owner", members, item.get("owner_id"))
            status = st.selectbox("Status", RISK_STATUSES, _index(RISK_STATUSES, item["status"]))
            if st.form_submit_button("Save risk"):
                errors = validate_risk(title, likelihood, impact, status)
                if errors:
                    _errors(errors)
                else:
                    try:
                        with get_connection() as connection:
                            validate_project_member(connection, project_id, owner)
                            connection.execute("UPDATE risks SET title=?, description=?, likelihood=?, impact=?, risk_score=?, response_action=?, owner_id=?, status=? WHERE risk_id=? AND project_id=?", (title.strip(), description.strip(), likelihood, impact, likelihood * impact, response.strip(), owner, status, item["risk_id"], project_id))
                        st.success("Risk updated.")
                        st.rerun()
                    except (sqlite3.Error, ValueError) as error:
                        st.error(f"Could not update risk: {error}")


def _pdpc_editor(item, project_id, members):
    with st.expander(f"Edit PDPC action: {item['possible_problem']}"):
        with st.form(f"pdpc_{item['action_id']}"):
            problem = st.text_area("Potential problem", item["possible_problem"])
            preventive = st.text_area("Preventive action", item.get("preventive_action") or "")
            corrective = st.text_area("Corrective action", item.get("corrective_action") or "")
            responsible = _member_select("Responsible person", members, item.get("responsible_member_id"))
            status = st.selectbox("Status", PDPC_STATUSES, _index(PDPC_STATUSES, item["status"]))
            if st.form_submit_button("Save PDPC action"):
                errors = validate_pdpc(problem, status)
                if errors:
                    _errors(errors)
                else:
                    try:
                        with get_connection() as connection:
                            validate_project_member(connection, project_id, responsible)
                            connection.execute("UPDATE pdpc_actions SET possible_problem=?, preventive_action=?, corrective_action=?, responsible_member_id=?, status=? WHERE action_id=?", (problem.strip(), preventive.strip(), corrective.strip(), responsible, status, item["action_id"]))
                        st.success("PDPC action updated.")
                        st.rerun()
                    except (sqlite3.Error, ValueError) as error:
                        st.error(f"Could not update PDPC action: {error}")


def _show_matrix(risks):
    cells = [["" for _ in range(5)] for _ in range(5)]
    for risk in risks:
        row, column = 5 - int(risk["likelihood"]), int(risk["impact"]) - 1
        label = f"{risk['title']} ({risk['risk_score']})"
        cells[row][column] = (cells[row][column] + "<br>" + label).strip("<br>")
    scores = [[(5 - row) * (column + 1) for column in range(5)] for row in range(5)]
    figure = go.Figure(go.Heatmap(z=scores, x=[1, 2, 3, 4, 5], y=[5, 4, 3, 2, 1], text=cells, texttemplate="%{text}", colorscale=[[0, "#1C2940"], [0.45, "#D6B36A"], [1, "#2DD4BF"]], showscale=True, colorbar_title="Risk score"))
    figure.update_layout(title="5×5 Likelihood–Impact Risk Matrix", xaxis_title="Impact", yaxis_title="Likelihood", paper_bgcolor="#151F32", plot_bgcolor="#151F32", font={"color": "#F1F5F9"}, title_font={"color": "#D6B36A"}, margin={"l": 35, "r": 20, "t": 60, "b": 35})
    st.plotly_chart(figure, use_container_width=True)


def show_quality_risk_management():
    """Render integrated Part E quality and risk controls."""
    _inject_quality_risk_styles()
    st.markdown('<div class="quality-hero"><div class="quality-eyebrow">PROJECT CONTROLS · PART E</div><div class="quality-title">Quality Management &amp; Risk Control</div><div class="quality-subtitle">Track defects, quality checks, project risks, and preventive actions in one workspace.</div></div>', unsafe_allow_html=True)
    project = fetch_one("SELECT project_id FROM projects ORDER BY project_id LIMIT 1")
    if not project:
        st.error("No project found. Initialize the database first.")
        return
    project_id = project["project_id"]
    members = fetch_all("SELECT member_id, name, role FROM team_members WHERE project_id=? ORDER BY name", (project_id,))
    defects_tab, quality_tab, risks_tab, pdpc_tab = st.tabs(["Defects", "Quality Checklist", "Risk Matrix", "PDPC / Responses"])

    with defects_tab:
        _section_header("Defect Tracking")
        with st.form("add_defect", clear_on_submit=True):
            title = st.text_input("Defect title *")
            description = st.text_area("Description")
            severity = st.selectbox("Severity", DEFECT_SEVERITIES)
            assignee = _member_select("Assigned team member", members)
            reported = st.date_input("Reported date", date.today())
            if st.form_submit_button("Add defect"):
                errors = validate_defect(title, severity, "Open", reported)
                if errors:
                    _errors(errors)
                else:
                    try:
                        with get_connection() as connection:
                            validate_project_member(connection, project_id, assignee)
                            connection.execute("INSERT INTO defects (project_id, title, description, severity, assigned_member_id, status, reported_date) VALUES (?, ?, ?, ?, ?, 'Open', ?)", (project_id, title.strip(), description.strip(), severity, assignee, reported.isoformat()))
                        st.success("Defect added.")
                        st.rerun()
                    except (sqlite3.Error, ValueError) as error:
                        st.error(f"Could not add defect: {error}")
        defects = fetch_all("SELECT * FROM defects WHERE project_id=? ORDER BY CASE severity WHEN 'Critical' THEN 1 WHEN 'High' THEN 2 WHEN 'Medium' THEN 3 ELSE 4 END, reported_date DESC", (project_id,))
        critical = [item for item in defects if item["severity"] == "Critical" and item["status"] not in ("Resolved", "Verified", "Closed")]
        if critical:
            st.error(f"{len(critical)} unresolved critical defect(s) require immediate attention.")
        if defects:
            st.dataframe(defects, use_container_width=True, hide_index=True)
            for item in defects:
                _defect_editor(item, project_id, members)
        else:
            st.info("No defects recorded.")

    with quality_tab:
        _section_header("Quality Checklist")
        with st.form("add_quality_check", clear_on_submit=True):
            name = st.text_input("Checklist item *")
            expected = st.text_area("Expected result")
            actual = st.text_area("Actual result / observation")
            result = st.selectbox("Result", QUALITY_RESULTS)
            tester = _member_select("Responsible person", members)
            inspected = st.date_input("Inspection date", date.today())
            remarks = st.text_area("Remarks")
            if st.form_submit_button("Add quality check"):
                errors = validate_quality_check(name, result, inspected)
                if errors:
                    _errors(errors)
                else:
                    try:
                        with get_connection() as connection:
                            validate_project_member(connection, project_id, tester)
                            stored = "Not Tested" if result == "Pending" else result
                            connection.execute("INSERT INTO quality_checks (project_id, item_name, expected_result, actual_result, inspection_date, result, tester_id, remarks) VALUES (?, ?, ?, ?, ?, ?, ?, ?)", (project_id, name.strip(), expected.strip(), actual.strip(), inspected.isoformat(), stored, tester, remarks.strip()))
                        st.success("Quality check added.")
                        st.rerun()
                    except (sqlite3.Error, ValueError) as error:
                        st.error(f"Could not add quality check: {error}")
        checks = fetch_all("SELECT * FROM quality_checks WHERE project_id=? ORDER BY inspection_date DESC", (project_id,))
        attention = [item for item in checks if item["result"] in ("Fail", "Not Tested")]
        if attention:
            st.warning(f"{len(attention)} failed or pending quality check(s) need attention.")
        if checks:
            st.dataframe(checks, use_container_width=True, hide_index=True)
            for item in checks:
                _quality_editor(item, project_id, members)
        else:
            st.info("No quality checks recorded.")

    with risks_tab:
        _section_header("Risk Assessment")
        with st.form("add_risk", clear_on_submit=True):
            title = st.text_input("Risk title *")
            description = st.text_area("Description")
            likelihood = st.slider("Likelihood (1–5)", 1, 5, 3)
            impact = st.slider("Impact (1–5)", 1, 5, 3)
            st.caption(f"Calculated score: {likelihood * impact} — {risk_priority(likelihood * impact)}")
            response = st.text_area("Response strategy")
            owner = _member_select("Risk owner", members)
            if st.form_submit_button("Add risk"):
                errors = validate_risk(title, likelihood, impact, "Open")
                if errors:
                    _errors(errors)
                else:
                    try:
                        with get_connection() as connection:
                            validate_project_member(connection, project_id, owner)
                            connection.execute("INSERT INTO risks (project_id, title, description, likelihood, impact, risk_score, response_action, owner_id, status) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'Open')", (project_id, title.strip(), description.strip(), likelihood, impact, likelihood * impact, response.strip(), owner))
                        st.success("Risk added.")
                        st.rerun()
                    except (sqlite3.Error, ValueError) as error:
                        st.error(f"Could not add risk: {error}")
        risks = fetch_all("SELECT * FROM risks WHERE project_id=? ORDER BY risk_score DESC, likelihood DESC, impact DESC", (project_id,))
        if risks:
            display_risks = [{**risk, "priority": risk_priority(risk["risk_score"])} for risk in risks]
            st.dataframe(display_risks, use_container_width=True, hide_index=True)
            _show_matrix(risks)
            for item in risks:
                _risk_editor(item, project_id, members)
        else:
            st.info("No risks recorded.")

    with pdpc_tab:
        _section_header("Preventive & Corrective Actions")
        risks = fetch_all("SELECT risk_id, title, risk_score FROM risks WHERE project_id=? ORDER BY risk_score DESC", (project_id,))
        with st.form("add_pdpc", clear_on_submit=True):
            if risks:
                risk_ids = [risk["risk_id"] for risk in risks]
                labels = {risk["risk_id"]: f"{risk['title']} ({risk['risk_score']})" for risk in risks}
                risk_id = st.selectbox("Linked risk", risk_ids, format_func=lambda value: labels[value])
                problem = st.text_area("Potential problem *")
                preventive = st.text_area("Preventive action")
                corrective = st.text_area("Corrective action")
                responsible = _member_select("Responsible person", members)
                status = st.selectbox("Status", PDPC_STATUSES)
                if st.form_submit_button("Add PDPC action"):
                    errors = validate_pdpc(problem, status)
                    if errors:
                        _errors(errors)
                    else:
                        try:
                            with get_connection() as connection:
                                validate_project_member(connection, project_id, responsible)
                                connection.execute("INSERT INTO pdpc_actions (risk_id, possible_problem, preventive_action, corrective_action, responsible_member_id, status) VALUES (?, ?, ?, ?, ?, ?)", (risk_id, problem.strip(), preventive.strip(), corrective.strip(), responsible, status))
                            st.success("PDPC action added.")
                            st.rerun()
                        except (sqlite3.Error, ValueError) as error:
                            st.error(f"Could not add PDPC action: {error}")
            else:
                st.info("Add a risk before creating a PDPC action.")
        actions = fetch_all("SELECT action.*, risk.title AS risk_title FROM pdpc_actions action JOIN risks risk ON risk.risk_id=action.risk_id WHERE risk.project_id=? ORDER BY risk.risk_score DESC, action.action_id DESC", (project_id,))
        if actions:
            st.dataframe(actions, use_container_width=True, hide_index=True)
            for item in actions:
                _pdpc_editor(item, project_id, members)
        else:
            st.info("No PDPC actions recorded.")
