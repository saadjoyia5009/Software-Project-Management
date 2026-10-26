"""Validation helpers for Scope Management and WBS."""


REQUIREMENT_PRIORITIES = ("Low", "Medium", "High", "Critical")
REQUIREMENT_STATUSES = (
    "Proposed", "Pending Approval", "Approved", "Rejected", "Implemented",
)
WBS_TYPES = ("Deliverable", "Task", "Work Package")
WBS_STATUSES = ("Not Started", "In Progress", "Completed", "Delayed", "Blocked")
CHANGE_STATUSES = ("Pending", "Approved", "Rejected")


def _present(value):
    return bool(value and str(value).strip())


def validate_requirement(title, description, priority, status):
    errors = []
    if not _present(title):
        errors.append("Requirement title is required.")
    if not _present(description):
        errors.append("Requirement description is required.")
    if priority not in REQUIREMENT_PRIORITIES:
        errors.append("Select a valid requirement priority.")
    if status not in REQUIREMENT_STATUSES:
        errors.append("Select a valid requirement status.")
    return errors


def validate_wbs(name, wbs_type, duration, status):
    errors = []
    if not _present(name):
        errors.append("WBS name is required.")
    if wbs_type not in WBS_TYPES:
        errors.append("Select a valid WBS type.")
    if not isinstance(duration, int) or duration < 1:
        errors.append("Duration must be at least one day.")
    if status not in WBS_STATUSES:
        errors.append("Select a valid WBS status.")
    return errors


def validate_change(title, justification, cost, duration):
    errors = []
    if not _present(title):
        errors.append("Change request title is required.")
    if not _present(justification):
        errors.append("Change justification is required.")
    if cost < 0:
        errors.append("Additional cost cannot be negative.")
    if duration < 0:
        errors.append("Schedule impact cannot be negative.")
    return errors
