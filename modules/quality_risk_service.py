"""Reusable validation and prioritisation helpers for quality and risk records."""

from datetime import date


DEFECT_SEVERITIES = ("Low", "Medium", "High", "Critical")
DEFECT_STATUSES = ("Open", "In Progress", "Resolved", "Verified", "Closed")
QUALITY_RESULTS = ("Pending", "Pass", "Fail")
RISK_STATUSES = ("Open", "Monitoring", "Mitigated", "Closed")
PDPC_STATUSES = ("Planned", "In Progress", "Completed")


def risk_priority(score):
    """Convert a 1–25 risk score into a readable priority band."""
    if score >= 16:
        return "Critical"
    if score >= 10:
        return "High"
    if score >= 5:
        return "Medium"
    return "Low"


def validate_defect(title, severity, status, reported_date):
    errors = []
    if not title or not title.strip():
        errors.append("Defect title is required.")
    if severity not in DEFECT_SEVERITIES:
        errors.append("Select a valid defect severity.")
    if status not in DEFECT_STATUSES:
        errors.append("Select a valid defect status.")
    if not isinstance(reported_date, date):
        errors.append("Reported date must be valid.")
    return errors


def validate_quality_check(item_name, result, inspection_date):
    errors = []
    if not item_name or not item_name.strip():
        errors.append("Checklist item name is required.")
    if result not in QUALITY_RESULTS:
        errors.append("Select a valid quality result.")
    if not isinstance(inspection_date, date):
        errors.append("Inspection date must be valid.")
    return errors


def validate_risk(title, likelihood, impact, status):
    errors = []
    if not title or not title.strip():
        errors.append("Risk title is required.")
    if likelihood not in range(1, 6) or impact not in range(1, 6):
        errors.append("Likelihood and impact must be from 1 to 5.")
    if status not in RISK_STATUSES:
        errors.append("Select a valid risk status.")
    return errors


def validate_pdpc(problem, status):
    errors = []
    if not problem or not problem.strip():
        errors.append("Potential problem is required.")
    if status not in PDPC_STATUSES:
        errors.append("Select a valid PDPC status.")
    return errors


def validate_project_member(connection, project_id, member_id):
    """Require selected owners/testers/assignees to belong to the project."""
    if member_id is None:
        return
    row = connection.execute(
        "SELECT member_id FROM team_members WHERE member_id=? AND project_id=?",
        (member_id, project_id),
    ).fetchone()
    if not row:
        raise ValueError("Selected team member does not belong to this project.")
