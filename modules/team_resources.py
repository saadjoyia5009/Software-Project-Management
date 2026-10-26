"""Team and responsibility management using the shared team_members table."""

import sqlite3

import streamlit as st

from database import fetch_all, fetch_one, get_connection


def _inject_team_ui_styles():
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
                radial-gradient(ellipse at 8% 0%, rgba(45, 212, 191, 0.05), transparent 32%),
                var(--hc-bg);
            color: var(--hc-text);
        }
        [data-testid="stHeader"] { background: rgba(11, 18, 32, 0.88); }
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
            margin: 0 0 1.25rem 0;
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
            max-width: 780px;
            margin-top: 0.65rem;
            color: var(--hc-muted);
            font-size: 0.98rem;
            line-height: 1.6;
        }
        .hc-section {
            display: flex;
            align-items: center;
            gap: 0.8rem;
            margin: 0.45rem 0 1rem 0;
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
        .hc-stat-card {
            padding: 1rem 1.1rem;
            min-height: 105px;
            border: 1px solid var(--hc-border);
            border-top: 3px solid var(--hc-teal);
            border-radius: 14px;
            background: linear-gradient(145deg, #18243A, var(--hc-card));
            box-shadow: 0 10px 24px rgba(0, 0, 0, 0.13);
        }
        .hc-stat-label {
            color: var(--hc-muted);
            font-size: 0.78rem;
            font-weight: 650;
            letter-spacing: 0.04em;
            text-transform: uppercase;
        }
        .hc-stat-value {
            margin-top: 0.5rem;
            color: var(--hc-text);
            font-size: 1.55rem;
            line-height: 1.2;
            font-weight: 750;
            overflow-wrap: anywhere;
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
        .stTextInput label, .stTextArea label {
            color: var(--hc-muted) !important;
            font-weight: 600 !important;
        }
        div[data-baseweb="input"] > div,
        div[data-baseweb="textarea"] > div {
            background: #101A2B;
            border-color: rgba(167, 180, 200, 0.22);
            border-radius: 10px;
        }
        div[data-baseweb="input"] input,
        div[data-baseweb="textarea"] textarea {
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
        [data-testid="stCaptionContainer"] { color: var(--hc-muted); }
        hr { border-color: var(--hc-border); }
        @media (max-width: 760px) {
            .block-container {
                padding-top: 1rem;
                padding-left: 1rem;
                padding-right: 1rem;
            }
            .hc-hero { padding: 1.25rem; border-radius: 14px; }
            div[data-testid="stForm"] { padding: 0.9rem; }
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


def validate_team_member(name, role):
    """Return validation errors for a team member record."""
    errors = []
    if not name or not name.strip():
        errors.append("Team member name is required.")
    if not role or not role.strip():
        errors.append("Project role is required.")
    return errors


def _show_errors(errors):
    for error in errors:
        st.error(error)


def _member_editor(member, project_id):
    with st.expander(f"Edit: {member['name']} ({member['role']})"):
        with st.form(f"team_member_{member['member_id']}"):
            name = st.text_input("Name", member["name"])
            role = st.text_input("Project role", member["role"])
            email = st.text_input("Email", member.get("email") or "")
            responsibilities = st.text_area(
                "Project responsibilities", member.get("responsibilities") or ""
            )
            save = st.form_submit_button("Save team member")
            delete = st.form_submit_button("Delete team member")
            if save:
                errors = validate_team_member(name, role)
                if errors:
                    _show_errors(errors)
                else:
                    try:
                        with get_connection() as connection:
                            duplicate = connection.execute(
                                """SELECT member_id FROM team_members
                                   WHERE project_id=? AND lower(name)=lower(?)
                                     AND lower(COALESCE(email, ''))=lower(?)
                                     AND member_id<>?""",
                                (project_id, name.strip(), email.strip(), member["member_id"]),
                            ).fetchone()
                            if duplicate:
                                raise ValueError("A matching team member already exists.")
                            connection.execute(
                                """UPDATE team_members
                                   SET name=?, role=?, email=?, responsibilities=?
                                   WHERE member_id=? AND project_id=?""",
                                (name.strip(), role.strip(), email.strip(), responsibilities.strip(),
                                 member["member_id"], project_id),
                            )
                        st.success("Team member updated.")
                        st.rerun()
                    except (sqlite3.Error, ValueError) as error:
                        st.error(f"Could not update team member: {error}")
            if delete:
                try:
                    with get_connection() as connection:
                        connection.execute(
                            "DELETE FROM team_members WHERE member_id=? AND project_id=?",
                            (member["member_id"], project_id),
                        )
                    st.success("Team member deleted. Existing activity assignments were safely cleared.")
                    st.rerun()
                except sqlite3.Error as error:
                    st.error(f"Could not delete team member: {error}")


def show_team_resources():
    """Render team CRUD used by activities, quality, risk, and project views."""
    _inject_team_ui_styles()

    project = fetch_one("SELECT project_id FROM projects ORDER BY project_id LIMIT 1")
    if not project:
        st.markdown(
            """
            <div class="hc-hero">
                <div class="hc-eyebrow">Healthcare Project Intelligence · Resources</div>
                <h1 class="hc-hero-title">Team &amp; Resources</h1>
                <div class="hc-hero-subtitle">Manage project ownership and responsibilities in one place.</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.error("No project found. Initialize the database first.")
        return

    project_id = project["project_id"]
    members = fetch_all(
        "SELECT * FROM team_members WHERE project_id=? ORDER BY name", (project_id,)
    )

    st.markdown(
        """
        <div class="hc-hero">
            <div class="hc-eyebrow">Healthcare Project Intelligence · Resources</div>
            <h1 class="hc-hero-title">Team &amp; Resources</h1>
            <div class="hc-hero-subtitle">Manage project ownership, clarify responsibilities, and keep the delivery team organized across project activities.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.caption("Members here are reused by activities, defects, quality checks, risks, and PDPC actions.")

    total_members = len(members)
    roles_count = len({(member.get("role") or "").strip().lower() for member in members if (member.get("role") or "").strip()})
    with st.container():
        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown(
                f'<div class="hc-stat-card"><div class="hc-stat-label">Team members</div><div class="hc-stat-value">{total_members}</div></div>',
                unsafe_allow_html=True,
            )
        with col2:
            st.markdown(
                f'<div class="hc-stat-card"><div class="hc-stat-label">Distinct roles</div><div class="hc-stat-value">{roles_count}</div></div>',
                unsafe_allow_html=True,
            )
        with col3:
            with_email = sum(1 for member in members if (member.get("email") or "").strip())
            st.markdown(
                f'<div class="hc-stat-card"><div class="hc-stat-label">Email contacts</div><div class="hc-stat-value">{with_email}</div></div>',
                unsafe_allow_html=True,
            )

    st.markdown("")
    add_tab, directory_tab = st.tabs(["＋ Add Team Member", "Team Directory"])

    with add_tab:
        _section_header("Add a team member", "Create a project team record that can be reused throughout the system.")
        with st.form("add_team_member", clear_on_submit=True):
            name = st.text_input("Team member name *")
            role = st.text_input("Project role *")
            email = st.text_input("Email")
            responsibilities = st.text_area("Project responsibilities")
            if st.form_submit_button("Add team member"):
                errors = validate_team_member(name, role)
                if errors:
                    _show_errors(errors)
                else:
                    try:
                        with get_connection() as connection:
                            duplicate = connection.execute(
                                """SELECT member_id FROM team_members
                                   WHERE project_id=? AND lower(name)=lower(?)
                                     AND lower(COALESCE(email, ''))=lower(?)""",
                                (project_id, name.strip(), email.strip()),
                            ).fetchone()
                            if duplicate:
                                raise ValueError("A matching team member already exists.")
                            connection.execute(
                                """INSERT INTO team_members
                                   (project_id, name, role, email, responsibilities)
                                   VALUES (?, ?, ?, ?, ?)""",
                                (project_id, name.strip(), role.strip(), email.strip(),
                                 responsibilities.strip()),
                            )
                        st.success("Team member added.")
                        st.rerun()
                    except (sqlite3.Error, ValueError) as error:
                        st.error(f"Could not add team member: {error}")

    with directory_tab:
        _section_header("Team directory", "Browse and edit the people assigned to this project.")
        if members:
            st.dataframe(members, use_container_width=True, hide_index=True)
            st.markdown("#### Manage team members")
            for member in members:
                _member_editor(member, project_id)
        else:
            st.info("No team members have been added.")
