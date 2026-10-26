"""Streamlit UI for Part B: requirements, WBS, and scope change control."""

from datetime import date, timedelta
import sqlite3

import streamlit as st

from database import execute_query, fetch_all, fetch_one, get_connection
from modules.scope_wbs_validation import (
    CHANGE_STATUSES, REQUIREMENT_PRIORITIES, REQUIREMENT_STATUSES, WBS_STATUSES,
    WBS_TYPES, validate_change, validate_requirement, validate_wbs,
)



def _inject_scope_ui_styles():
    """Apply the shared premium dark healthcare dashboard theme."""
    st.markdown(
        """
        <style>
        :root {
            --scope-navy: #0B1220;
            --scope-slate: #151F32;
            --scope-surface: #1C2940;
            --scope-gold: #D6B36A;
            --scope-teal: #2DD4BF;
            --scope-text: #F1F5F9;
            --scope-muted: #A7B4C8;
            --scope-border: rgba(167, 180, 200, 0.16);
        }
        .stApp { background: #0B1220; color: #F1F5F9; }
        [data-testid="stHeader"] { background: rgba(11, 18, 32, 0.92); }
        [data-testid="stMainBlockContainer"] { padding-top: 1.8rem; }
        h1, h2, h3, h4, p, label, .stMarkdown, [data-testid="stCaptionContainer"] {
            color: #F1F5F9;
        }
        [data-testid="stCaptionContainer"] { color: #A7B4C8; }
        .scope-hero {
            padding: 1.45rem 1.6rem;
            margin: 0 0 1.2rem 0;
            border: 1px solid rgba(167, 180, 200, 0.16);
            border-left: 4px solid #D6B36A;
            border-radius: 16px;
            background: linear-gradient(115deg, #151F32 0%, #111B2D 100%);
            box-shadow: 0 12px 28px rgba(0,0,0,0.16);
        }
        .scope-eyebrow {
            color: #2DD4BF; font-size: 0.76rem; font-weight: 700;
            letter-spacing: 0.13em; text-transform: uppercase; margin-bottom: 0.35rem;
        }
        .scope-title {
            color: #F1F5F9; font-size: 1.8rem; line-height: 1.2;
            font-weight: 750; margin: 0 0 0.45rem 0;
        }
        .scope-description { color: #A7B4C8; font-size: 0.96rem; margin: 0; }
        .scope-section {
            margin: 0.4rem 0 0.85rem 0; padding: 0.65rem 0 0.6rem 0;
            border-bottom: 1px solid rgba(167, 180, 200, 0.16);
        }
        .scope-section-title {
            font-size: 1.16rem; font-weight: 700; color: #F1F5F9; margin: 0;
        }
        .scope-section-subtitle { color: #A7B4C8; font-size: 0.86rem; margin-top: 0.2rem; }
        [data-testid="stTabs"] [data-baseweb="tab-list"] {
            gap: 0.45rem; background: #151F32; padding: 0.4rem;
            border: 1px solid rgba(167, 180, 200, 0.16); border-radius: 12px;
        }
        [data-testid="stTabs"] button[role="tab"] {
            color: #A7B4C8; border-radius: 9px; padding: 0.55rem 1rem;
        }
        [data-testid="stTabs"] button[role="tab"][aria-selected="true"] {
            background: #1C2940; color: #D6B36A; font-weight: 700;
        }
        [data-testid="stTabs"] [data-baseweb="tab-highlight"] { background: #D6B36A; }
        [data-testid="stForm"], [data-testid="stExpander"] {
            border: 1px solid rgba(167, 180, 200, 0.16);
            border-radius: 14px; background: #151F32;
        }
        [data-testid="stForm"] { padding: 1rem 1.1rem; }
        [data-testid="stExpander"] { margin: 0.5rem 0; overflow: hidden; }
        [data-testid="stExpander"] summary { color: #F1F5F9; font-weight: 600; }
        [data-testid="stDataFrame"], [data-testid="stTable"] {
            border: 1px solid rgba(167, 180, 200, 0.16); border-radius: 12px;
            overflow: hidden;
        }
        input, textarea { border-radius: 9px !important; }
        [data-testid="stTextInput"] input, [data-testid="stTextArea"] textarea,
        [data-testid="stNumberInput"] input, [data-testid="stSelectbox"] > div > div {
            background: #0B1220 !important; color: #F1F5F9 !important;
            border-color: rgba(167, 180, 200, 0.22) !important;
        }
        [data-testid="stFormSubmitButton"] button, .stButton button {
            border-radius: 9px; font-weight: 650; border: 1px solid #D6B36A;
            background: #D6B36A; color: #0B1220; transition: all 0.15s ease;
        }
        [data-testid="stFormSubmitButton"] button:hover, .stButton button:hover {
            background: #e4c784; border-color: #e4c784; color: #0B1220;
        }
        [data-testid="stAlert"] { border-radius: 10px; }
        hr { border-color: rgba(167, 180, 200, 0.16); }
        </style>
        <div class="scope-hero">
            <div class="scope-eyebrow">Project Planning · Part B</div>
            <div class="scope-title">Scope Management &amp; WBS</div>
            <p class="scope-description">Manage project requirements, organize the work breakdown structure, and review scope change requests.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _scope_section(title, subtitle=None):
    """Render a themed section heading without changing page behavior."""
    subtitle_html = (
        f'<div class="scope-section-subtitle">{subtitle}</div>' if subtitle else ""
    )
    st.markdown(
        f'<div class="scope-section"><div class="scope-section-title">{title}</div>{subtitle_html}</div>',
        unsafe_allow_html=True,
    )



def _show_errors(errors):
    for error in errors:
        st.error(error)


def _option_index(options, current):
    return options.index(current) if current in options else 0


def _requirement_editor(item):
    with st.expander(f"Edit requirement: {item['title']}"):
        with st.form(f"requirement_{item['requirement_id']}"):
            title = st.text_input("Title", item["title"])
            description = st.text_area("Description", item.get("description") or "")
            priority = st.selectbox("Priority", REQUIREMENT_PRIORITIES, _option_index(REQUIREMENT_PRIORITIES, item["priority"]))
            status = st.selectbox("Status", REQUIREMENT_STATUSES, _option_index(REQUIREMENT_STATUSES, item["status"]))
            save = st.form_submit_button("Save requirement")
            approve = st.form_submit_button("Approve and add to scope")
            reject = st.form_submit_button("Reject requirement")
            if save:
                errors = validate_requirement(title, description, priority, status)
                if errors:
                    _show_errors(errors)
                elif status != "Approved" and item["is_in_approved_scope"]:
                    st.error("A requirement linked to approved scope must remain Approved.")
                else:
                    try:
                        execute_query("UPDATE requirements SET title=?, description=?, priority=?, status=?, is_in_approved_scope=CASE WHEN ?='Approved' THEN 1 ELSE is_in_approved_scope END WHERE requirement_id=? AND project_id=?", (title.strip(), description.strip(), priority, status, status, item["requirement_id"], item["project_id"]))
                        st.success("Requirement updated.")
                        st.rerun()
                    except sqlite3.Error as error:
                        st.error(f"Could not update requirement: {error}")
            if approve:
                try:
                    execute_query("UPDATE requirements SET status='Approved', is_in_approved_scope=1 WHERE requirement_id=? AND project_id=?", (item["requirement_id"], item["project_id"]))
                    st.success("Requirement approved and added to approved scope.")
                    st.rerun()
                except sqlite3.Error as error:
                    st.error(f"Could not approve requirement: {error}")
            if reject:
                try:
                    execute_query("UPDATE requirements SET status='Rejected', is_in_approved_scope=0 WHERE requirement_id=? AND project_id=?", (item["requirement_id"], item["project_id"]))
                    st.success("Requirement rejected.")
                    st.rerun()
                except sqlite3.Error as error:
                    st.error(f"Could not reject requirement: {error}")


def _wbs_editor(item, parents, approved_requirements):
    with st.expander(f"Edit WBS: {item['task_name']}"):
        with st.form(f"wbs_{item['task_id']}"):
            name = st.text_input("Name", item["task_name"])
            description = st.text_area("Description", item.get("description") or "")
            wbs_type = st.selectbox("Type", WBS_TYPES, _option_index(WBS_TYPES, item.get("wbs_type")))
            duration = st.number_input("Duration (days)", min_value=1, value=int(item["duration_days"]), step=1)
            status = st.selectbox("Status", WBS_STATUSES, _option_index(WBS_STATUSES, item["status"]))
            available_parents = [parent for parent in parents if parent["task_id"] != item["task_id"]]
            parent_ids = [None] + [parent["task_id"] for parent in available_parents]
            parent_labels = ["No parent (top level)"] + [f"{parent['task_id']} — {parent['task_name']}" for parent in available_parents]
            parent_id = st.selectbox("Parent", parent_ids, format_func=lambda value: parent_labels[parent_ids.index(value)], index=parent_ids.index(item.get("parent_task_id")) if item.get("parent_task_id") in parent_ids else 0)
            requirement_ids = [None] + [requirement["requirement_id"] for requirement in approved_requirements]
            requirement_labels = ["No linked requirement"] + [f"{requirement['requirement_id']} — {requirement['title']}" for requirement in approved_requirements]
            requirement_id = st.selectbox("Approved requirement", requirement_ids, format_func=lambda value: requirement_labels[requirement_ids.index(value)], index=requirement_ids.index(item.get("requirement_id")) if item.get("requirement_id") in requirement_ids else 0)
            if st.form_submit_button("Save WBS item"):
                errors = validate_wbs(name, wbs_type, int(duration), status)
                if errors:
                    _show_errors(errors)
                else:
                    try:
                        execute_query("UPDATE wbs_tasks SET task_name=?, description=?, wbs_type=?, duration_days=?, status=?, parent_task_id=?, requirement_id=? WHERE task_id=? AND project_id=?", (name.strip(), description.strip(), wbs_type, int(duration), status, parent_id, requirement_id, item["task_id"], item["project_id"]))
                        st.success("WBS item updated.")
                        st.rerun()
                    except sqlite3.Error as error:
                        st.error(f"Could not update WBS item: {error}")


def _change_editor(item):
    with st.expander(f"Review change: {item['title']}"):
        with st.form(f"change_{item['change_id']}"):
            title = st.text_input("Title", item["title"])
            justification = st.text_area("Justification", item["justification"])
            requester = st.text_input("Requested by", item.get("requested_by") or "")
            extra_cost = st.number_input("Additional cost (PKR)", min_value=0.0, value=float(item["extra_cost"]), step=1000.0)
            impact = st.number_input("Schedule impact (weeks)", min_value=0, value=int(item["extra_duration_weeks"]), step=1)
            decision = st.selectbox("Decision", CHANGE_STATUSES, _option_index(CHANGE_STATUSES, item["status"]))
            notes = st.text_area("Decision notes", item.get("decision_notes") or "")
            if st.form_submit_button("Save review"):
                errors = validate_change(title, justification, extra_cost, int(impact))
                if errors:
                    _show_errors(errors)
                else:
                    decision_date = date.today().isoformat() if decision != "Pending" else None
                    try:
                        _save_change_review(
                            item["change_id"], item["project_id"], title.strip(),
                            justification.strip(), requester.strip(), extra_cost,
                            int(impact), decision, decision_date, notes.strip(),
                        )
                        st.success("Change request review saved.")
                        st.rerun()
                    except (sqlite3.Error, ValueError) as error:
                        st.error(f"Could not save change request: {error}")


def _save_change_review(
    change_id, project_id, title, justification, requester, extra_cost,
    extra_duration_weeks, decision, decision_date, notes,
):
    """Save a change decision and apply only its approved deadline impact.

    The adjustment is based on the saved decision, so reopening an already
    approved request does not add its duration a second time. Reversing an
    approval, or changing its approved duration, applies the matching delta.
    """
    with get_connection() as connection:
        saved_change = connection.execute(
            "SELECT status, extra_duration_weeks FROM change_requests "
            "WHERE change_id=? AND project_id=?",
            (change_id, project_id),
        ).fetchone()
        if not saved_change:
            raise ValueError("The change request no longer exists for this project.")

        old_approved_weeks = (
            int(saved_change["extra_duration_weeks"] or 0)
            if saved_change["status"] == "Approved" else 0
        )
        new_approved_weeks = (
            int(extra_duration_weeks) if decision == "Approved" else 0
        )
        deadline_delta_weeks = new_approved_weeks - old_approved_weeks

        if deadline_delta_weeks:
            project = connection.execute(
                "SELECT deadline FROM projects WHERE project_id=?", (project_id,)
            ).fetchone()
            try:
                current_deadline = date.fromisoformat(project["deadline"] if project else "")
            except (TypeError, ValueError) as error:
                raise ValueError(
                    "Set a valid project deadline before approving a schedule-impacting change."
                ) from error
            revised_deadline = current_deadline + timedelta(weeks=deadline_delta_weeks)
            connection.execute(
                "UPDATE projects SET deadline=? WHERE project_id=?",
                (revised_deadline.isoformat(), project_id),
            )

        connection.execute(
            "UPDATE change_requests SET title=?, justification=?, requested_by=?, "
            "extra_cost=?, extra_duration_weeks=?, status=?, decision_date=?, "
            "decision_notes=? WHERE change_id=? AND project_id=?",
            (title, justification, requester, extra_cost, extra_duration_weeks,
             decision, decision_date, notes, change_id, project_id),
        )


def show_scope_wbs():
    """Render Part B in one integrated Scope Management and WBS page."""
    _inject_scope_ui_styles()
    project = fetch_one("SELECT project_id FROM projects ORDER BY project_id LIMIT 1")
    if not project:
        st.error("No project found. Initialize the database first.")
        return
    project_id = project["project_id"]
    requirements_tab, wbs_tab, changes_tab = st.tabs(["Requirements", "WBS", "Change Requests"])

    with requirements_tab:
        _scope_section("Requirements Management", "Define, prioritize, and approve project requirements.")
        with st.form("add_requirement", clear_on_submit=True):
            title = st.text_input("Requirement title *")
            description = st.text_area("Description *")
            priority = st.selectbox("Priority", REQUIREMENT_PRIORITIES, index=1)
            if st.form_submit_button("Add requirement"):
                errors = validate_requirement(title, description, priority, "Proposed")
                if errors:
                    _show_errors(errors)
                else:
                    duplicate = fetch_one("SELECT requirement_id FROM requirements WHERE project_id=? AND lower(title)=lower(?)", (project_id, title.strip()))
                    if duplicate:
                        st.error("A requirement with this title already exists for the project.")
                    else:
                        try:
                            execute_query("INSERT INTO requirements (project_id, title, description, priority, status, is_in_approved_scope) VALUES (?, ?, ?, ?, 'Proposed', 0)", (project_id, title.strip(), description.strip(), priority))
                            st.success("Requirement added as Proposed.")
                            st.rerun()
                        except sqlite3.Error as error:
                            st.error(f"Could not add requirement: {error}")
        requirements = fetch_all("SELECT * FROM requirements WHERE project_id=? ORDER BY CASE priority WHEN 'Critical' THEN 1 WHEN 'High' THEN 2 WHEN 'Medium' THEN 3 ELSE 4 END, title", (project_id,))
        if requirements:
            st.dataframe(requirements, use_container_width=True, hide_index=True)
            for requirement in requirements:
                _requirement_editor(requirement)
        else:
            st.info("No requirements added yet.")

    with wbs_tab:
        _scope_section("Hierarchical Work Breakdown Structure", "Break approved project scope into manageable work items.")
        approved = fetch_all("SELECT requirement_id, title FROM requirements WHERE project_id=? AND status='Approved' AND is_in_approved_scope=1 ORDER BY title", (project_id,))
        existing = fetch_all("SELECT task_id, task_name FROM wbs_tasks WHERE project_id=? ORDER BY task_name", (project_id,))
        with st.form("add_wbs_item", clear_on_submit=True):
            name = st.text_input("WBS name *")
            description = st.text_area("Description")
            wbs_type = st.selectbox("WBS type", WBS_TYPES)
            duration = st.number_input("Duration (days)", min_value=1, value=1, step=1)
            status = st.selectbox("Status", WBS_STATUSES)
            parent_ids = [None] + [row["task_id"] for row in existing]
            parent_labels = ["No parent (top level)"] + [f"{row['task_id']} — {row['task_name']}" for row in existing]
            parent_id = st.selectbox("Parent item", parent_ids, format_func=lambda value: parent_labels[parent_ids.index(value)])
            requirement_ids = [None] + [row["requirement_id"] for row in approved]
            requirement_labels = ["No linked requirement"] + [f"{row['requirement_id']} — {row['title']}" for row in approved]
            requirement_id = st.selectbox("Approved requirement", requirement_ids, format_func=lambda value: requirement_labels[requirement_ids.index(value)])
            if st.form_submit_button("Add WBS item"):
                errors = validate_wbs(name, wbs_type, int(duration), status)
                if errors:
                    _show_errors(errors)
                else:
                    try:
                        execute_query("INSERT INTO wbs_tasks (project_id, parent_task_id, requirement_id, task_name, description, wbs_type, duration_days, status) VALUES (?, ?, ?, ?, ?, ?, ?, ?)", (project_id, parent_id, requirement_id, name.strip(), description.strip(), wbs_type, int(duration), status))
                        st.success("WBS item added.")
                        st.rerun()
                    except sqlite3.Error as error:
                        st.error(f"Could not add WBS item: {error}")
        items = fetch_all("SELECT task_id, project_id, parent_task_id, requirement_id, task_name, description, wbs_type, duration_days, status, progress FROM wbs_tasks WHERE project_id=? ORDER BY parent_task_id, task_id", (project_id,))
        if items:
            st.dataframe(items, use_container_width=True, hide_index=True)
            all_parents = fetch_all("SELECT task_id, task_name FROM wbs_tasks WHERE project_id=? ORDER BY task_name", (project_id,))
            for item in items:
                _wbs_editor(item, all_parents, approved)
        else:
            st.info("No WBS items added yet.")

    with changes_tab:
        _scope_section("Change Requests", "Record proposed changes and document their cost and schedule impact.")
        with st.form("add_change_request", clear_on_submit=True):
            title = st.text_input("Change title *")
            justification = st.text_area("Justification *")
            requester = st.text_input("Requested by")
            cost = st.number_input("Additional cost (PKR)", min_value=0.0, value=0.0, step=1000.0)
            impact = st.number_input("Schedule impact (weeks)", min_value=0, value=0, step=1)
            if st.form_submit_button("Record change request"):
                errors = validate_change(title, justification, cost, int(impact))
                if errors:
                    _show_errors(errors)
                else:
                    try:
                        execute_query("INSERT INTO change_requests (project_id, title, justification, extra_cost, extra_duration_weeks, status, requested_by) VALUES (?, ?, ?, ?, ?, 'Pending', ?)", (project_id, title.strip(), justification.strip(), cost, int(impact), requester.strip()))
                        st.success("Change request recorded as Pending.")
                        st.rerun()
                    except sqlite3.Error as error:
                        st.error(f"Could not record change request: {error}")
        changes = fetch_all("SELECT * FROM change_requests WHERE project_id=? ORDER BY created_at DESC, change_id DESC", (project_id,))
        if changes:
            st.dataframe(changes, use_container_width=True, hide_index=True)
            for change in changes:
                _change_editor(change)
        else:
            st.info("No change requests recorded yet.")
