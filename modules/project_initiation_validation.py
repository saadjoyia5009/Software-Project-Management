"""Validation helpers for Project Initiation and Integration Management."""

from datetime import date

PROJECT_STATUSES = ("Planning", "In Progress", "On Hold", "Completed", "Closed")
MILESTONE_STATUSES = ("Pending", "Achieved", "Delayed")


def text_is_present(value):
    """Return whether a text field has meaningful content."""
    return bool(value and str(value).strip())


def validate_charter(values):
    """Return human-readable errors for a project charter submission."""
    required = {
        "Project name": values.get("name"),
        "Project objectives": values.get("objective"),
        "Project sponsor": values.get("project_sponsor"),
        "Project manager": values.get("project_manager"),
        "In-scope boundary": values.get("scope_in"),
        "Out-of-scope boundary": values.get("scope_out"),
    }
    errors = [f"{label} is required." for label, value in required.items() if not text_is_present(value)]
    start_date, deadline = values.get("start_date"), values.get("deadline")
    if not isinstance(start_date, date) or not isinstance(deadline, date):
        errors.append("Start date and deadline must be valid dates.")
    elif deadline < start_date:
        errors.append("Deadline cannot be earlier than the start date.")
    try:
        if float(values.get("approved_budget")) <= 0:
            errors.append("Approved budget must be greater than zero.")
    except (TypeError, ValueError):
        errors.append("Approved budget must be a valid number.")
    if values.get("status") not in PROJECT_STATUSES:
        errors.append("Select a valid project status.")
    return errors


def validate_stakeholder(name, role):
    """Validate stakeholder fields."""
    errors = []
    if not text_is_present(name):
        errors.append("Stakeholder name is required.")
    if not text_is_present(role):
        errors.append("Stakeholder role is required.")
    return errors


def validate_milestone(name, due_date, status):
    """Validate milestone fields."""
    errors = []
    if not text_is_present(name):
        errors.append("Milestone name is required.")
    if not isinstance(due_date, date):
        errors.append("Milestone due date must be valid.")
    if status not in MILESTONE_STATUSES:
        errors.append("Select a valid milestone status.")
    return errors


def validate_closure(closure_date, final_status, summary):
    """Validate a closure record before it is stored."""
    errors = []
    if not isinstance(closure_date, date):
        errors.append("Closure date must be valid.")
    if final_status not in ("Completed", "Closed"):
        errors.append("Final status must be Completed or Closed.")
    if not text_is_present(summary):
        errors.append("Closure summary is required.")
    return errors
