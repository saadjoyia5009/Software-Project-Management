"""Database-backed scheduling helpers for WBS activities and dependencies."""

from datetime import date, timedelta


def parse_date(value):
    """Parse an ISO date, returning None for an empty value."""
    return date.fromisoformat(value) if value else None


def validate_activity(name, duration, status, start_date=None, end_date=None):
    """Validate activity values before storing them."""
    valid_statuses = {"Not Started", "In Progress", "Completed", "Delayed", "Blocked"}
    errors = []
    if not name or not name.strip():
        errors.append("Activity name is required.")
    if not isinstance(duration, int) or duration < 1:
        errors.append("Estimated duration must be at least one day.")
    if status not in valid_statuses:
        errors.append("Select a valid activity status.")
    if start_date and end_date and end_date < start_date:
        errors.append("End date cannot be earlier than start date.")
    return errors


def _project_start(connection, project_id):
    row = connection.execute(
        "SELECT start_date FROM projects WHERE project_id=?", (project_id,)
    ).fetchone()
    return parse_date(row["start_date"] if row else None) or date.today()


def _project_tasks(connection, project_id):
    return connection.execute(
        "SELECT * FROM wbs_tasks WHERE project_id=? ORDER BY task_id", (project_id,)
    ).fetchall()


def _topological_order(connection, project_id, tasks):
    """Return task IDs in predecessor-first order or raise for a cycle."""
    task_ids = {task["task_id"] for task in tasks}
    dependencies = connection.execute(
        """SELECT dependency.task_id, dependency.depends_on_task_id
           FROM task_dependencies dependency
           JOIN wbs_tasks task ON task.task_id=dependency.task_id
           WHERE task.project_id=?""",
        (project_id,),
    ).fetchall()
    predecessors = {task_id: set() for task_id in task_ids}
    successors = {task_id: set() for task_id in task_ids}
    for dependency in dependencies:
        task_id, predecessor_id = dependency["task_id"], dependency["depends_on_task_id"]
        if predecessor_id not in task_ids:
            raise ValueError("A dependency points to a task outside this project.")
        predecessors[task_id].add(predecessor_id)
        successors[predecessor_id].add(task_id)
    ready = sorted(task_id for task_id, links in predecessors.items() if not links)
    order = []
    while ready:
        task_id = ready.pop(0)
        order.append(task_id)
        for successor in sorted(successors[task_id]):
            predecessors[successor].remove(task_id)
            if not predecessors[successor]:
                ready.append(successor)
        ready.sort()
    if len(order) != len(task_ids):
        raise ValueError("Circular task dependencies cannot be scheduled.")
    return order, dependencies


def recalculate_schedule(connection, project_id):
    """Recalculate dates in a transaction, preserving manual dates as earliest dates.

    Automatic tasks start on the project start date or the day after their latest
    predecessor ends. A manual start date is retained when possible, but moves
    forward if a predecessor finishes later. Baseline dates are set once only.
    """
    tasks = _project_tasks(connection, project_id)
    if not tasks:
        return {"tasks": [], "project_finish": None, "deadline_overrun_days": 0}
    by_id = {task["task_id"]: task for task in tasks}
    order, dependencies = _topological_order(connection, project_id, tasks)
    predecessor_map = {task_id: [] for task_id in by_id}
    for dependency in dependencies:
        predecessor_map[dependency["task_id"]].append(dependency["depends_on_task_id"])
    dates = {}
    project_start = _project_start(connection, project_id)
    for task_id in order:
        task = by_id[task_id]
        earliest_start = project_start
        for predecessor_id in predecessor_map[task_id]:
            predecessor_end = dates[predecessor_id][1]
            earliest_start = max(earliest_start, predecessor_end + timedelta(days=1))
        saved_start = parse_date(task["start_date"])
        start = max(earliest_start, saved_start) if task["schedule_is_manual"] and saved_start else earliest_start
        end = start + timedelta(days=int(task["duration_days"]) - 1)
        dates[task_id] = (start, end)
        baseline_start = task["baseline_start_date"] or start.isoformat()
        baseline_end = task["baseline_end_date"] or end.isoformat()
        connection.execute(
            "UPDATE wbs_tasks SET start_date=?, end_date=?, baseline_start_date=?, baseline_end_date=? WHERE task_id=?",
            (start.isoformat(), end.isoformat(), baseline_start, baseline_end, task_id),
        )
    project_finish = max(end for _, end in dates.values())
    deadline_row = connection.execute("SELECT deadline FROM projects WHERE project_id=?", (project_id,)).fetchone()
    deadline = parse_date(deadline_row["deadline"] if deadline_row else None)
    overrun = max(0, (project_finish - deadline).days) if deadline else 0
    scheduled_tasks = []
    for task in _project_tasks(connection, project_id):
        baseline_end = parse_date(task["baseline_end_date"])
        current_end = parse_date(task["end_date"])
        delay = max(0, (current_end - baseline_end).days) if baseline_end and current_end else 0
        scheduled_tasks.append({**dict(task), "delay_days": delay})
    return {"tasks": scheduled_tasks, "project_finish": project_finish, "deadline_overrun_days": overrun}


def add_dependency(connection, project_id, task_id, predecessor_id):
    """Add a predecessor relationship and recalculate all affected work."""
    if task_id == predecessor_id:
        raise ValueError("A task cannot depend on itself.")
    rows = connection.execute(
        "SELECT task_id FROM wbs_tasks WHERE project_id=? AND task_id IN (?, ?)",
        (project_id, task_id, predecessor_id),
    ).fetchall()
    if len(rows) != 2:
        raise ValueError("Select two existing tasks from this project.")
    existing = connection.execute(
        "SELECT dependency_id FROM task_dependencies WHERE task_id=? AND depends_on_task_id=?",
        (task_id, predecessor_id),
    ).fetchone()
    if existing:
        raise ValueError("This dependency already exists.")
    connection.execute(
        "INSERT INTO task_dependencies (task_id, depends_on_task_id) VALUES (?, ?)",
        (task_id, predecessor_id),
    )
    return recalculate_schedule(connection, project_id)


def validate_member(connection, project_id, member_id):
    """Ensure a selected team member belongs to the activity's project."""
    if member_id is None:
        return
    member = connection.execute(
        "SELECT member_id FROM team_members WHERE member_id=? AND project_id=?",
        (member_id, project_id),
    ).fetchone()
    if not member:
        raise ValueError("Selected team member does not belong to this project.")
