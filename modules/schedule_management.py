"""Streamlit UI for Part C: activity, dependency, resource, and Gantt management."""

from datetime import date, timedelta
import sqlite3

import plotly.graph_objects as go
import streamlit as st

from database import fetch_all, fetch_one, get_connection
from modules.scheduling_service import (
    add_dependency, parse_date, recalculate_schedule, validate_activity,
    validate_member,
)



def _inject_schedule_ui_styles():
    """Apply the shared premium dark dashboard theme to this page only."""
    st.markdown(
        """
        <style>
        .stApp {
            background: #0B1220;
            color: #F1F5F9;
        }
        [data-testid="stHeader"] {
            background: rgba(11, 18, 32, 0.92);
        }
        [data-testid="stSidebar"] {
            background: #0B1220;
            border-right: 1px solid rgba(167, 180, 200, 0.16);
        }
        .block-container {
            padding-top: 1.8rem;
            padding-bottom: 2.5rem;
            max-width: 1500px;
        }
        h1, h2, h3, h4, p, label, .stMarkdown, [data-testid="stCaptionContainer"] {
            color: #F1F5F9;
        }
        [data-testid="stCaptionContainer"] {
            color: #A7B4C8;
        }
        .schedule-hero {
            background: linear-gradient(120deg, #151F32 0%, #111B2D 100%);
            border: 1px solid rgba(167, 180, 200, 0.16);
            border-radius: 18px;
            padding: 1.45rem 1.6rem;
            margin: 0 0 1.3rem 0;
            box-shadow: 0 10px 28px rgba(0, 0, 0, 0.16);
        }
        .schedule-eyebrow {
            color: #2DD4BF;
            font-size: 0.76rem;
            font-weight: 700;
            letter-spacing: 0.12em;
            text-transform: uppercase;
            margin-bottom: 0.45rem;
        }
        .schedule-title {
            color: #F1F5F9;
            font-size: clamp(1.65rem, 3vw, 2.15rem);
            font-weight: 750;
            line-height: 1.2;
            margin: 0;
        }
        .schedule-subtitle {
            color: #A7B4C8;
            font-size: 0.96rem;
            margin-top: 0.55rem;
            margin-bottom: 0;
        }
        .schedule-section {
            color: #F1F5F9;
            font-size: 1.2rem;
            font-weight: 700;
            border-left: 3px solid #D6B36A;
            padding: 0.1rem 0 0.1rem 0.7rem;
            margin: 0.5rem 0 1rem 0;
        }
        div[data-testid="stTabs"] button {
            color: #A7B4C8;
            border-radius: 10px 10px 0 0;
        }
        div[data-testid="stTabs"] button[aria-selected="true"] {
            color: #D6B36A;
            background: #1C2940;
        }
        div[data-testid="stTabs"] [data-baseweb="tab-highlight"] {
            background-color: #D6B36A;
        }
        div[data-testid="stForm"], div[data-testid="stExpander"] {
            background: #151F32;
            border: 1px solid rgba(167, 180, 200, 0.16);
            border-radius: 14px;
            padding: 0.35rem 0.6rem;
        }
        div[data-testid="stExpander"] summary {
            color: #F1F5F9;
            font-weight: 600;
        }
        div[data-testid="stDataFrame"], div[data-testid="stTable"] {
            border: 1px solid rgba(167, 180, 200, 0.16);
            border-radius: 12px;
            overflow: hidden;
        }
        .stButton button, .stFormSubmitButton button {
            background: #D6B36A;
            color: #0B1220;
            border: 1px solid #D6B36A;
            border-radius: 10px;
            font-weight: 700;
            transition: all 0.18s ease;
        }
        .stButton button:hover, .stFormSubmitButton button:hover {
            background: #e4c783;
            border-color: #e4c783;
            color: #0B1220;
        }
        input, textarea {
            border-radius: 9px !important;
        }
        [data-testid="stMetric"] {
            background: #151F32;
            border: 1px solid rgba(167, 180, 200, 0.16);
            border-radius: 14px;
            padding: 1rem 1.1rem;
        }
        [data-testid="stMetricLabel"] {
            color: #A7B4C8;
        }
        [data-testid="stMetricValue"] {
            color: #D6B36A;
        }
        div[data-testid="stAlert"] {
            border-radius: 12px;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _section_header(text):
    st.markdown(f'<div class="schedule-section">{text}</div>', unsafe_allow_html=True)



def _errors(errors):
    for error in errors:
        st.error(error)


def _index(options, current):
    return options.index(current) if current in options else 0


def _run_schedule(project_id):
    with get_connection() as connection:
        return recalculate_schedule(connection, project_id)


def _activity_editor(activity, project_id, members):
    statuses = ("Not Started", "In Progress", "Completed", "Delayed", "Blocked")
    with st.expander(f"Edit activity: {activity['task_name']}"):
        with st.form(f"activity_{activity['task_id']}"):
            name = st.text_input("Activity name", activity["task_name"])
            description = st.text_area("Description", activity.get("description") or "")
            duration = st.number_input("Estimated duration (days)", min_value=1, value=int(activity["duration_days"]), step=1)
            status = st.selectbox("Status", statuses, _index(statuses, activity["status"]))
            progress = st.slider("Progress (%)", 0, 100, int(activity["progress"]))
            member_ids = [None] + [member["member_id"] for member in members]
            member_labels = ["Unassigned"] + [f"{member['name']} — {member['role']}" for member in members]
            assigned_member = st.selectbox("Assigned team member", member_ids, format_func=lambda value: member_labels[member_ids.index(value)], index=member_ids.index(activity.get("assigned_member_id")) if activity.get("assigned_member_id") in member_ids else 0)
            manual = st.checkbox("Use a manual earliest start date", value=bool(activity.get("schedule_is_manual")))
            manual_start = st.date_input("Manual start date", parse_date(activity.get("start_date")) or date.today(), disabled=not manual)
            if st.form_submit_button("Save activity and recalculate"):
                errors = validate_activity(name, int(duration), status, manual_start if manual else None)
                if errors:
                    _errors(errors)
                else:
                    try:
                        with get_connection() as connection:
                            validate_member(connection, project_id, assigned_member)
                            connection.execute(
                                "UPDATE wbs_tasks SET task_name=?, description=?, duration_days=?, status=?, progress=?, assigned_member_id=?, schedule_is_manual=?, start_date=? WHERE task_id=? AND project_id=?",
                                (name.strip(), description.strip(), int(duration), status, progress, assigned_member, int(manual), manual_start.isoformat() if manual else None, activity["task_id"], project_id),
                            )
                            recalculate_schedule(connection, project_id)
                        st.success("Activity saved and dependent dates recalculated.")
                        st.rerun()
                    except (sqlite3.Error, ValueError) as error:
                        st.error(f"Could not save activity: {error}")


_TASK_ORDER = (
    "project planning", "requirements approval", "database design",
    "healthcare database", "patient records database", "appointment management",
    "doctor schedule module", "laboratory reports module",
    "online consultation module", "hospital billing module",
    "ai diagnosis module", "ai diagnosis integration", "mobile application",
    "mobile appointment screens", "system testing", "critical defect resolution",
    "final validation and deployment",
)


def _gantt_category(task):
    """Map existing task status and criticality to the compact chart legend."""
    name = (task.get("task_name") or "").lower()
    if "critical" in name:
        return "Critical"
    if task.get("status") in ("Delayed", "Blocked") or task.get("delay_days", 0) > 0:
        return "At Risk"
    if task.get("status") == "Completed":
        return "Completed"
    return "Normal"


def _task_order(task):
    name = (task.get("task_name") or "").lower()
    return _TASK_ORDER.index(name) if name in _TASK_ORDER else len(_TASK_ORDER)


def _gantt_rows(tasks, view, project_start):
    """Return valid, filtered task rows for presentation without changing dates."""
    dated_tasks = []
    for task in tasks:
        try:
            start = parse_date(task.get("start_date"))
            finish = parse_date(task.get("end_date"))
        except (TypeError, ValueError):
            continue
        if not start or not finish or finish < start:
            continue
        dated_tasks.append((task, start, finish))

    chart_tasks = []
    name_counts = {}
    for task, _, _ in dated_tasks:
        name_counts[task["task_name"]] = name_counts.get(task["task_name"], 0) + 1
    for task, start, finish in sorted(
        dated_tasks,
        key=lambda row: (_task_order(row[0]), row[1], row[0]["task_name"].lower()),
    ):
        if view == "Completed" and task.get("status") != "Completed":
            continue
        if view == "Pending" and task.get("status") == "Completed":
            continue
        task_label = task["task_name"]
        if name_counts[task_label] > 1:
            task_label = f"{task_label} (#{task['task_id']})"
        chart_tasks.append({
            **task,
            "activity_label": task_label,
            "chart_start": start,
            # Schedule end dates are inclusive; Plotly timeline ends are exclusive.
            "chart_finish": finish + timedelta(days=1),
            "scheduled_start": start,
            "scheduled_finish": finish,
            "timeline_category": _gantt_category(task),
            "progress_label": f"{int(task.get('progress') or 0)}%" if int(task.get("progress") or 0) else "",
            "delay_days": int(task.get("delay_days") or 0),
            "start_week": max(1, ((start - project_start).days // 7) + 1),
            "end_week": max(1, ((finish - project_start).days // 7) + 1),
        })
    return chart_tasks


def _show_gantt(tasks, milestones, view, project_start, schedule_weeks):
    """Present saved task dates as a simple, weekly horizontal-bar Gantt chart."""
    chart_tasks = _gantt_rows(tasks, view, project_start)
    if not chart_tasks:
        st.info("No matching activities with valid scheduled dates are available for this timeline view.")
        return

    chart_weeks = max(schedule_weeks, max(task["end_week"] for task in chart_tasks))
    colors = ("#5B8FF9", "#61DDAA", "#F6BD16", "#7262FD", "#78D3F8", "#F6903D", "#9661BC", "#6DC8EC")
    figure = go.Figure()
    for position, task in enumerate(chart_tasks):
        bar_length = task["end_week"] - task["start_week"] + 1
        figure.add_trace(go.Bar(
            y=[task["activity_label"]],
            x=[bar_length],
            base=[task["start_week"] - 1],
            orientation="h",
            width=0.58,
            marker={"color": colors[position % len(colors)], "line": {"color": "#FFFFFF", "width": 1}},
            text=[task["progress_label"]],
            textposition="inside",
            insidetextanchor="middle",
            textfont={"color": "#FFFFFF", "size": 11},
            hovertemplate=(
                "<b>%{y}</b><br>Week %{customdata[0]:.0f} to %{customdata[1]:.0f}"
                "<br>Start: %{customdata[2]}<br>Finish: %{customdata[3]}"
                "<br>Progress: %{customdata[4]}%<extra></extra>"
            ),
            customdata=[[
                task["start_week"], task["end_week"],
                task["scheduled_start"].isoformat(), task["scheduled_finish"].isoformat(),
                task.get("progress", 0),
            ]],
            showlegend=False,
        ))

    key_milestones = [
        milestone for milestone in milestones
        if any(word in (milestone.get("name") or "").lower() for word in ("requirement", "testing", "final"))
    ]
    for milestone in key_milestones:
        try:
            due_date = parse_date(milestone.get("due_date"))
        except (TypeError, ValueError):
            continue
        if due_date:
            milestone_week = max(1, ((due_date - project_start).days // 7) + 1)
            if milestone_week <= chart_weeks:
                figure.add_vline(x=milestone_week - 0.5, line_dash="dot", line_color="#94A3B8", line_width=1)

    figure.update_layout(
        title={"text": "Smart Healthcare Project Schedule", "x": 0.5, "font": {"size": 20, "color": "#1F2937"}},
        height=max(520, 115 + len(chart_tasks) * 42),
        margin={"l": 290, "r": 28, "t": 72, "b": 76},
        paper_bgcolor="#FFFFFF",
        plot_bgcolor="#FFFFFF",
        font={"color": "#334155", "family": "Arial, sans-serif"},
        barmode="overlay",
        hoverlabel={"bgcolor": "#FFFFFF", "font": {"color": "#1F2937"}, "bordercolor": "#CBD5E1"},
    )
    figure.update_yaxes(
        categoryorder="array",
        categoryarray=[task["activity_label"] for task in chart_tasks],
        autorange="reversed",
        title=None,
        tickfont={"size": 12, "color": "#334155"},
        showgrid=False,
    )
    figure.update_xaxes(
        title="Project timeline",
        range=[0, chart_weeks],
        tickmode="array",
        tickvals=[week - 0.5 for week in range(1, chart_weeks + 1)],
        ticktext=[f"Week {week}" for week in range(1, chart_weeks + 1)],
        tickangle=-35 if chart_weeks > 12 else 0,
        showgrid=True,
        gridcolor="#E2E8F0",
        gridwidth=1,
        zeroline=False,
        tickfont={"size": 11, "color": "#475569"},
        title_font={"color": "#475569"},
    )
    st.plotly_chart(figure, use_container_width=True)
    st.caption("Bars are calculated from saved scheduled dates relative to the project start. Dotted lines mark existing key milestones; dependencies remain available in the Dependencies tab.")


def show_schedule_management():
    """Render Part C using existing WBS tasks as schedule activities."""
    _inject_schedule_ui_styles()
    st.markdown(
        """
        <div class="schedule-hero">
            <div class="schedule-eyebrow">Project Planning · Part C</div>
            <div class="schedule-title">Schedule &amp; Resource Management</div>
            <p class="schedule-subtitle">Manage activities, team assignments, dependencies, timelines, and project milestones.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    project = fetch_one("SELECT project_id, start_date, deadline, duration_weeks FROM projects ORDER BY project_id LIMIT 1")
    if not project:
        st.error("No project found. Initialize the database first.")
        return
    project_id = project["project_id"]
    activities_tab, dependencies_tab, timeline_tab = st.tabs(["Activities & Resources", "Dependencies", "Gantt & Milestones"])

    with activities_tab:
        _section_header("Activities and Team Assignments")
        members = fetch_all("SELECT member_id, name, role FROM team_members WHERE project_id=? ORDER BY name", (project_id,))
        with st.form("add_activity", clear_on_submit=True):
            name = st.text_input("Activity name *")
            description = st.text_area("Description")
            duration = st.number_input("Estimated duration (days)", min_value=1, value=1, step=1)
            member_ids = [None] + [member["member_id"] for member in members]
            member_labels = ["Unassigned"] + [f"{member['name']} — {member['role']}" for member in members]
            assigned_member = st.selectbox("Assigned team member", member_ids, format_func=lambda value: member_labels[member_ids.index(value)])
            manual = st.checkbox("Use a manual earliest start date")
            start = st.date_input("Manual start date", date.today(), disabled=not manual)
            if st.form_submit_button("Add activity"):
                errors = validate_activity(name, int(duration), "Not Started", start if manual else None)
                if errors:
                    _errors(errors)
                else:
                    try:
                        with get_connection() as connection:
                            validate_member(connection, project_id, assigned_member)
                            connection.execute(
                                "INSERT INTO wbs_tasks (project_id, task_name, description, wbs_type, duration_days, assigned_member_id, schedule_is_manual, start_date) VALUES (?, ?, ?, 'Task', ?, ?, ?, ?)",
                                (project_id, name.strip(), description.strip(), int(duration), assigned_member, int(manual), start.isoformat() if manual else None),
                            )
                            recalculate_schedule(connection, project_id)
                        st.success("Activity added and schedule calculated.")
                        st.rerun()
                    except (sqlite3.Error, ValueError) as error:
                        st.error(f"Could not add activity: {error}")
        try:
            schedule = _run_schedule(project_id)
        except (sqlite3.Error, ValueError) as error:
            st.error(f"Schedule cannot be calculated: {error}")
            schedule = {"tasks": [], "project_finish": None, "deadline_overrun_days": 0}
        if schedule["tasks"]:
            st.dataframe(schedule["tasks"], use_container_width=True, hide_index=True)
            for activity in schedule["tasks"]:
                _activity_editor(activity, project_id, members)
        else:
            st.info("No activities yet. Schedule activities are stored in the existing WBS table.")
        st.caption("Assumption: automatic activities start on the project start date (or today if it is blank) and on the day after their latest predecessor ends. A manual start date is retained as an earliest date, but moves later when dependencies require it. End dates are duration-based and dates captured at first calculation remain the baseline.")

    with dependencies_tab:
        _section_header("Task Dependencies")
        tasks = fetch_all("SELECT task_id, task_name, start_date, end_date FROM wbs_tasks WHERE project_id=? ORDER BY task_name", (project_id,))
        with st.form("add_dependency", clear_on_submit=True):
            task_ids = [task["task_id"] for task in tasks]
            labels = {task["task_id"]: f"{task['task_id']} — {task['task_name']}" for task in tasks}
            if task_ids:
                task_id = st.selectbox("Dependent task", task_ids, format_func=lambda value: labels[value])
                predecessor_id = st.selectbox("Must finish before it", task_ids, format_func=lambda value: labels[value])
                if st.form_submit_button("Add dependency"):
                    try:
                        with get_connection() as connection:
                            add_dependency(connection, project_id, task_id, predecessor_id)
                        st.success("Dependency added and dependent activities recalculated.")
                        st.rerun()
                    except (sqlite3.Error, ValueError) as error:
                        st.error(f"Could not add dependency: {error}")
            else:
                st.info("Add at least two activities before creating a dependency.")
        dependencies = fetch_all("SELECT dependency.dependency_id, task.task_name AS task, predecessor.task_name AS predecessor FROM task_dependencies dependency JOIN wbs_tasks task ON task.task_id=dependency.task_id JOIN wbs_tasks predecessor ON predecessor.task_id=dependency.depends_on_task_id WHERE task.project_id=? ORDER BY task.task_name", (project_id,))
        if dependencies:
            st.dataframe(dependencies, use_container_width=True, hide_index=True)
            selected = st.selectbox("Dependency to remove", [row["dependency_id"] for row in dependencies], format_func=lambda value: next(f"{row['task']} ← {row['predecessor']}" for row in dependencies if row["dependency_id"] == value))
            if st.button("Remove selected dependency"):
                with get_connection() as connection:
                    connection.execute("DELETE FROM task_dependencies WHERE dependency_id=?", (selected,))
                    recalculate_schedule(connection, project_id)
                st.success("Dependency removed and schedule recalculated.")
                st.rerun()
        else:
            st.info("No dependencies recorded.")

    with timeline_tab:
        schedule = _run_schedule(project_id)
        milestones = fetch_all("SELECT name, due_date, status, completed_date FROM milestones WHERE project_id=? ORDER BY due_date", (project_id,))
        approved_changes = fetch_all("SELECT extra_duration_weeks FROM change_requests WHERE project_id=? AND status='Approved'", (project_id,))
        deadline = parse_date(project.get("deadline"))
        finish = schedule["project_finish"]
        baseline_duration = int(project.get("duration_weeks") or 0)
        approved_change_weeks = sum(int(change["extra_duration_weeks"] or 0) for change in approved_changes)
        revised_duration = baseline_duration + approved_change_weeks
        project_start = parse_date(project.get("start_date"))
        if not project_start:
            valid_starts = [parse_date(task.get("start_date")) for task in schedule["tasks"] if task.get("start_date")]
            project_start = min((value for value in valid_starts if value), default=None)
        completed_count = sum(1 for task in schedule["tasks"] if task["status"] == "Completed")
        pending_count = len(schedule["tasks"]) - completed_count
        first, second, third, fourth, fifth = st.columns(5)
        first.metric("Project duration", f"{revised_duration} weeks", delta=f"Baseline: {baseline_duration} weeks" if approved_change_weeks else None)
        second.metric("Total tasks", len(schedule["tasks"]))
        third.metric("Completed tasks", completed_count)
        fourth.metric("Pending tasks", pending_count)
        fifth.metric("Project deadline", deadline.isoformat() if deadline else "Not set")
        st.caption(
            f"Scheduled finish: {finish.isoformat() if finish else '—'} · "
            f"Deadline overrun: {schedule['deadline_overrun_days']} day(s)"
        )
        view = st.selectbox("Timeline view", ("All Tasks", "Completed", "Pending"), key="gantt_view")
        delayed = [task for task in schedule["tasks"] if task["status"] == "Delayed" or task["delay_days"] > 0]
        if delayed:
            st.warning(f"{len(delayed)} delayed activity(s) detected.")
            st.dataframe(delayed, use_container_width=True, hide_index=True)
        else:
            st.success("No delayed activities against their stored baselines.")
        if project_start:
            _show_gantt(schedule["tasks"], milestones, view, project_start, revised_duration)
        else:
            st.info("Set a project start date or add an activity with a valid start date to display the weekly timeline.")
        _section_header("Existing Project Milestones")
        if milestones:
            st.dataframe(milestones, use_container_width=True, hide_index=True)
        else:
            st.info("No milestones have been recorded in Project Details.")
