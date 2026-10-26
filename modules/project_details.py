"""Streamlit UI for Part A: Project Initiation and Integration Management."""

from datetime import date
import sqlite3
import streamlit as st

from database import execute_query, fetch_all, fetch_one
from modules.project_initiation_validation import (
    MILESTONE_STATUSES, PROJECT_STATUSES, validate_charter, validate_closure,
    validate_milestone, validate_stakeholder,
)


def _inject_part_a_styles():
    """Apply the shared Dark Healthcare Analytics SaaS visual theme."""
    st.markdown(
        """
        <style>
        :root {
            --hc-bg: #0B1220;
            --hc-card: #151F32;
            --hc-surface: #1C2940;
            --hc-gold: #D6B36A;
            --hc-teal: #2DD4BF;
            --hc-text: #F1F5F9;
            --hc-muted: #A7B4C8;
            --hc-border: rgba(167, 180, 200, 0.16);
        }

        .stApp {
            background:
                radial-gradient(ellipse at 8% 0%, rgba(45, 212, 191, 0.055), transparent 32%),
                var(--hc-bg);
            color: var(--hc-text);
        }

        [data-testid="stHeader"] {
            background: rgba(11, 18, 32, 0.88);
        }

        [data-testid="stSidebar"] {
            background: #0A101D;
            border-right: 1px solid var(--hc-border);
        }

        .block-container {
            max-width: 1450px;
            padding-top: 2rem;
            padding-bottom: 3rem;
        }

        .hc-hero {
            position: relative;
            overflow: hidden;
            padding: 1.7rem 1.8rem;
            margin: 0 0 1.35rem 0;
            border: 1px solid var(--hc-border);
            border-radius: 18px;
            background: linear-gradient(125deg, rgba(28, 41, 64, 0.98), rgba(21, 31, 50, 0.97));
            box-shadow: 0 16px 42px rgba(0, 0, 0, 0.18);
        }

        .hc-hero:after {
            content: "";
            position: absolute;
            width: 210px;
            height: 210px;
            right: -70px;
            top: -105px;
            border-radius: 50%;
            border: 1px solid rgba(214, 179, 106, 0.20);
            box-shadow: 0 0 0 24px rgba(214, 179, 106, 0.025),
                        0 0 0 48px rgba(214, 179, 106, 0.018);
            pointer-events: none;
        }

        .hc-eyebrow {
            margin-bottom: 0.45rem;
            color: var(--hc-gold);
            font-size: 0.72rem;
            font-weight: 750;
            letter-spacing: 0.15em;
            text-transform: uppercase;
        }

        .hc-hero-title {
            margin: 0;
            color: var(--hc-text);
            font-size: clamp(1.65rem, 3vw, 2.35rem);
            line-height: 1.15;
            font-weight: 760;
            letter-spacing: -0.035em;
        }

        .hc-hero-subtitle {
            max-width: 760px;
            margin-top: 0.65rem;
            color: var(--hc-muted);
            font-size: 0.98rem;
            line-height: 1.6;
        }

        .hc-section {
            display: flex;
            align-items: center;
            gap: 0.8rem;
            margin: 0.35rem 0 1rem 0;
        }

        .hc-section-mark {
            width: 4px;
            min-width: 4px;
            height: 34px;
            border-radius: 8px;
            background: linear-gradient(180deg, var(--hc-gold), var(--hc-teal));
        }

        .hc-section-title {
            margin: 0;
            color: var(--hc-text);
            font-size: 1.22rem;
            font-weight: 700;
            letter-spacing: -0.02em;
        }

        .hc-section-caption {
            margin-top: 0.18rem;
            color: var(--hc-muted);
            font-size: 0.86rem;
        }

        .hc-project-pill {
            display: inline-flex;
            align-items: center;
            gap: 0.5rem;
            margin-top: 1.1rem;
            padding: 0.48rem 0.8rem;
            border: 1px solid rgba(214, 179, 106, 0.30);
            border-radius: 999px;
            background: rgba(214, 179, 106, 0.07);
            color: var(--hc-text);
            font-size: 0.86rem;
        }

        .hc-project-dot {
            width: 7px;
            height: 7px;
            border-radius: 50%;
            background: var(--hc-teal);
            box-shadow: 0 0 12px rgba(45, 212, 191, 0.45);
        }

        div[data-testid="stTabs"] button[data-baseweb="tab"] {
            color: var(--hc-muted);
            font-weight: 650;
            padding: 0.8rem 1rem;
            border-radius: 10px 10px 0 0;
        }

        div[data-testid="stTabs"] button[data-baseweb="tab"][aria-selected="true"] {
            color: var(--hc-gold);
            background: rgba(28, 41, 64, 0.72);
        }

        div[data-testid="stTabs"] div[data-baseweb="tab-highlight"] {
            background: var(--hc-gold);
            height: 3px;
        }

        div[data-testid="stTabs"] div[data-baseweb="tab-border"] {
            background: var(--hc-border);
        }

        div[data-testid="stForm"] {
            padding: 1.25rem 1.3rem 1.05rem 1.3rem;
            border: 1px solid var(--hc-border);
            border-radius: 16px;
            background: rgba(21, 31, 50, 0.72);
            box-shadow: 0 12px 28px rgba(0, 0, 0, 0.12);
        }

        div[data-testid="stExpander"] {
            overflow: hidden;
            margin: 0.65rem 0;
            border: 1px solid var(--hc-border);
            border-radius: 13px;
            background: rgba(21, 31, 50, 0.58);
        }

        div[data-testid="stExpander"] summary {
            color: var(--hc-text);
            font-weight: 650;
        }

        .stTextInput label, .stTextArea label, .stNumberInput label,
        .stDateInput label, .stSelectbox label, .stMultiSelect label {
            color: var(--hc-muted) !important;
            font-weight: 600 !important;
        }

        div[data-baseweb="input"] > div,
        div[data-baseweb="textarea"] > div,
        div[data-baseweb="select"] > div,
        div[data-testid="stNumberInput"] div[data-baseweb="input"] > div {
            background: #101A2B;
            border-color: rgba(167, 180, 200, 0.22);
            border-radius: 10px;
        }

        div[data-baseweb="input"] input,
        div[data-baseweb="textarea"] textarea,
        div[data-baseweb="select"] *,
        div[data-testid="stNumberInput"] input {
            color: var(--hc-text);
        }

        div[data-testid="stFormSubmitButton"] button,
        div[data-testid="stButton"] button {
            border-radius: 10px;
            border: 1px solid rgba(214, 179, 106, 0.55);
            background: var(--hc-gold);
            color: #111827;
            font-weight: 750;
            transition: transform 120ms ease, filter 120ms ease;
        }

        div[data-testid="stFormSubmitButton"] button:hover,
        div[data-testid="stButton"] button:hover {
            filter: brightness(1.06);
            transform: translateY(-1px);
            border-color: var(--hc-gold);
            color: #111827;
        }

        div[data-testid="stFormSubmitButton"] button[kind="secondary"] {
            background: var(--hc-surface);
            color: var(--hc-text);
            border-color: var(--hc-border);
        }

        div[data-testid="stDataFrame"] {
            overflow: hidden;
            border: 1px solid var(--hc-border);
            border-radius: 13px;
            background: var(--hc-card);
        }

        div[data-testid="stAlert"] {
            border-radius: 12px;
            border: 1px solid var(--hc-border);
        }

        [data-testid="stCaptionContainer"] {
            color: var(--hc-muted);
        }

        hr {
            border-color: var(--hc-border);
        }

        @media (max-width: 760px) {
            .block-container {
                padding-top: 1rem;
                padding-left: 1rem;
                padding-right: 1rem;
            }
            .hc-hero {
                padding: 1.25rem;
                border-radius: 14px;
            }
            div[data-testid="stForm"] {
                padding: 0.9rem;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _section_header(title, caption):
    st.markdown(
        f"""
        <div class="hc-section">
            <div class="hc-section-mark"></div>
            <div>
                <div class="hc-section-title">{title}</div>
                <div class="hc-section-caption">{caption}</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _date_or_today(value):
    try:
        return date.fromisoformat(value) if value else date.today()
    except ValueError:
        return date.today()


def _errors(errors):
    for error in errors:
        st.error(error)


def _stakeholder_editor(item):
    with st.expander(f"Edit: {item['name']} ({item['role']})"):
        with st.form(f"stakeholder_{item['stakeholder_id']}"):
            name = st.text_input("Name", item["name"])
            role = st.text_input("Role", item["role"])
            contact = st.text_input("Contact", item.get("contact") or "")
            responsibility = st.text_area("Responsibilities", item.get("responsibilities") or "")
            save = st.form_submit_button("Save changes")
            delete = st.form_submit_button("Delete stakeholder")
            if save:
                validation = validate_stakeholder(name, role)
                if validation:
                    _errors(validation)
                else:
                    execute_query("UPDATE stakeholders SET name=?, role=?, contact=?, responsibilities=? WHERE stakeholder_id=? AND project_id=?", (name.strip(), role.strip(), contact.strip(), responsibility.strip(), item["stakeholder_id"], item["project_id"]))
                    st.success("Stakeholder updated.")
                    st.rerun()
            if delete:
                execute_query("DELETE FROM stakeholders WHERE stakeholder_id=? AND project_id=?", (item["stakeholder_id"], item["project_id"]))
                st.success("Stakeholder deleted.")
                st.rerun()


def _milestone_editor(item):
    with st.expander(f"Edit: {item['name']}"):
        with st.form(f"milestone_{item['milestone_id']}"):
            name = st.text_input("Milestone name", item["name"])
            description = st.text_area("Description", item.get("description") or "")
            due_date = st.date_input("Due date", _date_or_today(item.get("due_date")))
            old_status = item.get("status") or "Pending"
            status = st.selectbox("Status", MILESTONE_STATUSES, index=MILESTONE_STATUSES.index(old_status) if old_status in MILESTONE_STATUSES else 0)
            save = st.form_submit_button("Save changes")
            delete = st.form_submit_button("Delete milestone")
            if save:
                validation = validate_milestone(name, due_date, status)
                if validation:
                    _errors(validation)
                else:
                    completed = date.today().isoformat() if status == "Achieved" else None
                    execute_query("UPDATE milestones SET name=?, description=?, due_date=?, status=?, completed_date=? WHERE milestone_id=? AND project_id=?", (name.strip(), description.strip(), due_date.isoformat(), status, completed, item["milestone_id"], item["project_id"]))
                    st.success("Milestone updated.")
                    st.rerun()
            if delete:
                execute_query("DELETE FROM milestones WHERE milestone_id=? AND project_id=?", (item["milestone_id"], item["project_id"]))
                st.success("Milestone deleted.")
                st.rerun()


def show_project_details():
    """Render the Part A workspace using existing project data."""
    _inject_part_a_styles()

    project = fetch_one("SELECT * FROM projects ORDER BY project_id LIMIT 1")
    if not project:
        st.markdown(
            """
            <div class="hc-hero">
                <div class="hc-eyebrow">Healthcare Project Intelligence</div>
                <h1 class="hc-hero-title">Project Initiation &amp; Integration</h1>
                <div class="hc-hero-subtitle">Define the project foundation, align stakeholders, and document delivery commitments.</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.error("No project found. Initialize the database first.")
        return

    project_id = project["project_id"]
    st.markdown(
        f"""
        <div class="hc-hero">
            <div class="hc-eyebrow">Healthcare Project Intelligence · Part A</div>
            <h1 class="hc-hero-title">Project Initiation &amp; Integration</h1>
            <div class="hc-hero-subtitle">Set the project foundation, align stakeholders, track key milestones, and keep closure records organized.</div>
            <div class="hc-project-pill"><span class="hc-project-dot"></span>Active project&nbsp; · &nbsp;{project['name']}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    charter, plan, stakeholders_tab, milestones_tab, team, closure = st.tabs([
        "Project Charter", "Management Plan", "Stakeholders", "Milestones",
        "Team Responsibilities", "Project Closure",
    ])

    with charter:
        _section_header("Project Charter", "Core objectives, ownership, scope, timeline and approved budget.")
        with st.form("project_charter_form"):
            name = st.text_input("Project name *", project.get("name") or "")
            objective = st.text_area("Project objectives *", project.get("objective") or "")
            sponsor = st.text_input("Project sponsor *", project.get("project_sponsor") or "")
            manager = st.text_input("Project manager *", project.get("project_manager") or "")
            scope = st.text_area("Project scope", project.get("scope") or "")
            left, right = st.columns(2)
            with left:
                scope_in = st.text_area("In scope *", project.get("scope_in") or "")
                start = st.date_input("Start date", _date_or_today(project.get("start_date")))
            with right:
                scope_out = st.text_area("Out of scope *", project.get("scope_out") or "")
                deadline = st.date_input("Deadline", _date_or_today(project.get("deadline")))
            budget = st.number_input("Approved budget (PKR) *", min_value=0.0, value=float(project.get("approved_budget") or 0), step=50000.0)
            duration = st.number_input("Duration (weeks)", min_value=1, max_value=520, value=int(project.get("duration_weeks") or 16))
            current = project.get("status") or "Planning"
            status = st.selectbox("Project status", PROJECT_STATUSES, index=PROJECT_STATUSES.index(current) if current in PROJECT_STATUSES else 0)
            if st.form_submit_button("Save project charter"):
                values = {"name": name, "objective": objective, "project_sponsor": sponsor, "project_manager": manager, "scope_in": scope_in, "scope_out": scope_out, "start_date": start, "deadline": deadline, "approved_budget": budget, "status": status}
                validation = validate_charter(values)
                if validation:
                    _errors(validation)
                else:
                    try:
                        execute_query("UPDATE projects SET name=?, objective=?, project_sponsor=?, project_manager=?, scope=?, scope_in=?, scope_out=?, start_date=?, deadline=?, approved_budget=?, duration_weeks=?, status=? WHERE project_id=?", (name.strip(), objective.strip(), sponsor.strip(), manager.strip(), scope.strip(), scope_in.strip(), scope_out.strip(), start.isoformat(), deadline.isoformat(), budget, int(duration), status, project_id))
                        st.success("Project charter saved.")
                        st.rerun()
                    except sqlite3.Error as error:
                        st.error(f"Could not save project charter: {error}")

    with plan:
        _section_header("Management Plan", "Document the approach for scope, schedule, cost and quality control.")
        with st.form("management_plan_form"):
            scope_plan = st.text_area("Scope management plan", project.get("scope") or "")
            schedule = st.text_area("Schedule management plan", project.get("schedule_plan") or "")
            cost = st.text_area("Cost management plan", project.get("cost_plan") or "")
            quality = st.text_area("Quality management plan", project.get("quality_plan") or "")
            if st.form_submit_button("Save management plan"):
                if not all(item.strip() for item in (scope_plan, schedule, cost, quality)):
                    st.error("Scope, schedule, cost, and quality plans are required.")
                else:
                    execute_query("UPDATE projects SET scope=?, schedule_plan=?, cost_plan=?, quality_plan=? WHERE project_id=?", (scope_plan.strip(), schedule.strip(), cost.strip(), quality.strip(), project_id))
                    st.success("Project management plan saved.")
                    st.rerun()

    with stakeholders_tab:
        _section_header("Stakeholders", "Maintain project contacts, roles and responsibilities.")
        with st.form("add_stakeholder", clear_on_submit=True):
            name, role = st.text_input("Stakeholder name *"), st.text_input("Role *")
            contact, responsibility = st.text_input("Contact"), st.text_area("Responsibilities")
            if st.form_submit_button("Add stakeholder"):
                validation = validate_stakeholder(name, role)
                if validation:
                    _errors(validation)
                else:
                    try:
                        execute_query("INSERT INTO stakeholders (project_id, name, role, contact, responsibilities) VALUES (?, ?, ?, ?, ?)", (project_id, name.strip(), role.strip(), contact.strip(), responsibility.strip()))
                        st.success("Stakeholder added.")
                        st.rerun()
                    except sqlite3.IntegrityError as error:
                        st.error(f"Could not add stakeholder: {error}")
        records = fetch_all("SELECT * FROM stakeholders WHERE project_id=? ORDER BY name", (project_id,))
        if records:
            st.markdown("#### Stakeholder directory")
            st.dataframe(records, use_container_width=True, hide_index=True)
            for item in records:
                _stakeholder_editor(item)
        else:
            st.info("No stakeholders added yet.")

    with milestones_tab:
        _section_header("Milestones", "Track delivery checkpoints, due dates and achievement status.")
        with st.form("add_milestone", clear_on_submit=True):
            name = st.text_input("Milestone name *")
            description = st.text_area("Description")
            due = st.date_input("Due date", date.today())
            status = st.selectbox("Status", MILESTONE_STATUSES)
            if st.form_submit_button("Add milestone"):
                validation = validate_milestone(name, due, status)
                if validation:
                    _errors(validation)
                else:
                    completed = date.today().isoformat() if status == "Achieved" else None
                    execute_query("INSERT INTO milestones (project_id, name, description, due_date, status, completed_date) VALUES (?, ?, ?, ?, ?, ?)", (project_id, name.strip(), description.strip(), due.isoformat(), status, completed))
                    st.success("Milestone added.")
                    st.rerun()
        records = fetch_all("SELECT * FROM milestones WHERE project_id=? ORDER BY due_date", (project_id,))
        if records:
            st.markdown("#### Milestone register")
            st.dataframe(records, use_container_width=True, hide_index=True)
            for item in records:
                _milestone_editor(item)
        else:
            st.info("No milestones added yet.")

    with team:
        _section_header("Team Responsibilities", "View assigned project team members and their responsibilities.")
        members = fetch_all("SELECT member_id, name, role, email, responsibilities FROM team_members WHERE project_id=? ORDER BY name", (project_id,))
        if members:
            st.dataframe(members, use_container_width=True, hide_index=True)
        else:
            st.info("No team members found. Add members through Team & Resources.")
        st.caption("This view reuses the existing team_members table; it does not duplicate team data.")

    with closure:
        _section_header("Project Closure", "Record the final project status, closure summary and outstanding issues.")
        with st.form("project_closure_form"):
            closed_on = st.date_input("Closure date", _date_or_today(project.get("closure_date")))
            final = st.selectbox("Final status", ("Completed", "Closed"), index=1 if project.get("closure_final_status") == "Closed" else 0)
            summary = st.text_area("Closure summary *", project.get("closure_summary") or "")
            outstanding = st.text_area("Outstanding issues", project.get("outstanding_issues") or "")
            if st.form_submit_button("Save closure record"):
                validation = validate_closure(closed_on, final, summary)
                if validation:
                    _errors(validation)
                else:
                    execute_query("UPDATE projects SET closure_date=?, closure_final_status=?, closure_summary=?, outstanding_issues=?, status=? WHERE project_id=?", (closed_on.isoformat(), final, summary.strip(), outstanding.strip(), final, project_id))
                    st.success("Project closure record saved.")
                    st.rerun()
