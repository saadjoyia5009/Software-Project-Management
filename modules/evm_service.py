"""Reusable cost and earned-value calculations for project activities."""

from datetime import date


def safe_ratio(numerator, denominator):
    """Return a ratio or None when it is not meaningful to divide by zero."""
    return numerator / denominator if denominator else None


def _safe_date(value):
    """Return an ISO date or None so legacy bad data cannot break reporting."""
    try:
        return date.fromisoformat(value) if value else None
    except (TypeError, ValueError):
        return None


def planned_percent_by_date(start_date, end_date, status_date):
    """Return planned elapsed work as a fraction of an inclusive activity period."""
    if not start_date or not end_date or status_date < start_date:
        return 0.0
    if status_date >= end_date:
        return 1.0
    total_days = (end_date - start_date).days + 1
    elapsed_days = (status_date - start_date).days + 1
    return elapsed_days / total_days


def calculate_evm(tasks, cost_records, status_date, threshold=0.90):
    """Calculate PV, EV, AC, variances, indices, and warnings for a status date.

    PV is prorated across each activity's scheduled inclusive duration. EV uses
    stored activity progress, treated as the reported progress at status date.
    AC is the total of dated cost records on or before status date.
    """
    total_planned_cost = 0.0
    planned_value = 0.0
    earned_value = 0.0
    activity_rows = []
    for task in tasks:
        planned_cost = float(task.get("planned_cost") or 0)
        progress = min(100, max(0, int(task.get("progress") or 0)))
        start_date = _safe_date(task.get("start_date"))
        end_date = _safe_date(task.get("end_date"))
        planned_fraction = planned_percent_by_date(start_date, end_date, status_date)
        pv = planned_cost * planned_fraction
        ev = planned_cost * progress / 100
        total_planned_cost += planned_cost
        planned_value += pv
        earned_value += ev
        activity_rows.append({
            "task_id": task["task_id"],
            "activity": task["task_name"],
            "planned_cost": planned_cost,
            "progress": progress,
            "pv": pv,
            "ev": ev,
        })
    actual_cost = sum(
        float(record.get("actual_cost") or 0)
        for record in cost_records
        if _safe_date(record.get("record_date"))
        and _safe_date(record["record_date"]) <= status_date
    )
    cost_variance = earned_value - actual_cost
    schedule_variance = earned_value - planned_value
    cpi = safe_ratio(earned_value, actual_cost)
    spi = safe_ratio(earned_value, planned_value)
    warnings = []
    if cost_variance < 0:
        warnings.append("Cost overrun: actual cost exceeds earned value.")
    if schedule_variance < 0:
        warnings.append("Schedule deviation: earned value is behind planned value.")
    if cpi is not None and cpi < threshold:
        warnings.append(f"CPI is below the {threshold:.2f} threshold.")
    if spi is not None and spi < threshold:
        warnings.append(f"SPI is below the {threshold:.2f} threshold.")
    return {
        "status_date": status_date,
        "total_planned_cost": total_planned_cost,
        "pv": planned_value,
        "ev": earned_value,
        "ac": actual_cost,
        "cv": cost_variance,
        "sv": schedule_variance,
        "cpi": cpi,
        "spi": spi,
        "warnings": warnings,
        "activities": activity_rows,
    }


def validate_cost_values(planned_cost, actual_cost, budgeted_value, record_date):
    """Validate user-entered costs and their ISO date before persistence."""
    errors = []
    if planned_cost < 0 or actual_cost < 0 or budgeted_value < 0:
        errors.append("Costs cannot be negative.")
    if actual_cost == 0 and budgeted_value == 0:
        errors.append("Enter actual expenditure or budgeted completed-work value.")
    if not isinstance(record_date, date):
        errors.append("Record date must be valid.")
    return errors


def save_cost_record(connection, project_id, task_id, actual_cost, budgeted_value, record_date):
    """Create or update the single daily cost record for an existing project activity."""
    task = connection.execute(
        "SELECT planned_cost FROM wbs_tasks WHERE task_id=? AND project_id=?",
        (task_id, project_id),
    ).fetchone()
    if not task:
        raise ValueError("Select an existing activity from this project.")
    errors = validate_cost_values(float(task["planned_cost"]), actual_cost, budgeted_value, record_date)
    if errors:
        raise ValueError(" ".join(errors))
    existing = connection.execute(
        "SELECT cost_id FROM cost_records WHERE task_id=? AND record_date=?",
        (task_id, record_date.isoformat()),
    ).fetchone()
    values = (float(task["planned_cost"]), actual_cost, budgeted_value, record_date.isoformat())
    if existing:
        connection.execute(
            "UPDATE cost_records SET planned_cost=?, actual_cost=?, budgeted_value=? WHERE cost_id=?",
            (*values[:3], existing["cost_id"]),
        )
        return existing["cost_id"], False
    cursor = connection.execute(
        "INSERT INTO cost_records (task_id, planned_cost, actual_cost, budgeted_value, record_date) VALUES (?, ?, ?, ?, ?)",
        (task_id, *values),
    )
    return cursor.lastrowid, True


def update_cost_record(connection, project_id, cost_id, actual_cost, budgeted_value, record_date):
    """Correct one existing cost record without inserting or replacing another row."""
    record = connection.execute(
        """SELECT record.task_id, task.planned_cost
           FROM cost_records record
           JOIN wbs_tasks task ON task.task_id=record.task_id
           WHERE record.cost_id=? AND task.project_id=?""",
        (cost_id, project_id),
    ).fetchone()
    if not record:
        raise ValueError("Select an existing cost record from this project.")
    errors = validate_cost_values(
        float(record["planned_cost"]), actual_cost, budgeted_value, record_date,
    )
    if errors:
        raise ValueError(" ".join(errors))
    conflict = connection.execute(
        """SELECT cost_id FROM cost_records
           WHERE task_id=? AND record_date=? AND cost_id<>?""",
        (record["task_id"], record_date.isoformat(), cost_id),
    ).fetchone()
    if conflict:
        raise ValueError("This activity already has a cost record for the selected date.")
    connection.execute(
        """UPDATE cost_records
           SET planned_cost=?, actual_cost=?, budgeted_value=?, record_date=?
           WHERE cost_id=?""",
        (
            float(record["planned_cost"]), actual_cost, budgeted_value,
            record_date.isoformat(), cost_id,
        ),
    )
