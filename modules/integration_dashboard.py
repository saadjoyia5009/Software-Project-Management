"""Cross-module project-health aggregation for the integrated dashboard."""

from datetime import date
from math import isclose

from modules.evm_service import calculate_evm


def _safe_date(value):
    try:
        return date.fromisoformat(value) if value else None
    except (TypeError, ValueError):
        return None


def build_dashboard_snapshot(project, tasks, cost_records, changes, defects, checks, risks, status_date, unapproved_wbs_count=0):
    """Return stable dashboard figures from existing project-module records."""
    evm = calculate_evm(tasks, cost_records, status_date)
    dated_cost_records = [
        record for record in cost_records if _safe_date(record.get("record_date"))
    ]
    future_cost_record_count = sum(
        1 for record in dated_cost_records
        if _safe_date(record["record_date"]) > status_date
    )
    planned_cost = evm["total_planned_cost"]
    if planned_cost:
        progress = sum(float(task.get("planned_cost") or 0) * int(task.get("progress") or 0) for task in tasks) / planned_cost
    elif tasks:
        progress = sum(int(task.get("progress") or 0) for task in tasks) / len(tasks)
    else:
        progress = 0.0
    delayed = []
    for task in tasks:
        baseline = _safe_date(task.get("baseline_end_date"))
        current = _safe_date(task.get("end_date"))
        if task.get("status") == "Delayed" or (baseline and current and current > baseline):
            delayed.append(task)
    pending_changes = [change for change in changes if change["status"] == "Pending"]
    approved_changes = [change for change in changes if change["status"] == "Approved"]
    critical_defects = [
        defect for defect in defects
        if defect["severity"] == "Critical"
        and defect["status"] not in ("Resolved", "Verified", "Closed")
    ]
    attention_checks = [check for check in checks if check["result"] in ("Fail", "Not Tested")]
    open_risks = [risk for risk in risks if risk["status"] not in ("Mitigated", "Closed")]
    stored_baseline_budget = float(project.get("approved_budget") or 0)
    approved_change_cost = sum(
        float(change["extra_cost"] or 0) for change in approved_changes
    )
    baseline_duration_weeks = int(project.get("duration_weeks") or 0)
    approved_change_duration_weeks = sum(
        int(change["extra_duration_weeks"] or 0)
        for change in approved_changes
    )
    stored_revised_budget = float(project.get("revised_budget") or 0)
    derived_revised_budget = stored_baseline_budget + approved_change_cost
    if (
        stored_revised_budget > stored_baseline_budget
        and isclose(stored_revised_budget, derived_revised_budget)
    ):
        # The saved revised value already includes these approved changes.
        baseline_budget = stored_baseline_budget
        revised_approved_budget = stored_revised_budget
    else:
        # Older project records can retain the original baseline in
        # revised_budget. Use that saved value when it is higher, then apply
        # each currently approved change exactly once.
        baseline_budget = max(stored_baseline_budget, stored_revised_budget)
        revised_approved_budget = baseline_budget + approved_change_cost
    revised_duration_weeks = (
        baseline_duration_weeks + approved_change_duration_weeks
    )
    warnings = []
    if planned_cost > revised_approved_budget:
        warnings.append("Planned activity cost exceeds the current approved project budget.")
    if evm["ac"] > revised_approved_budget:
        warnings.append("Actual expenditure exceeds the current approved project budget.")
    if unapproved_wbs_count:
        warnings.append("Scope consistency issue: WBS work is linked to an unapproved requirement.")
    warnings.extend(evm["warnings"])
    return {
        "progress": progress,
        "evm": evm,
        "planned_cost": planned_cost,
        "approved_budget": baseline_budget,
        "revised_approved_budget": revised_approved_budget,
        "baseline_duration_weeks": baseline_duration_weeks,
        "revised_duration_weeks": revised_duration_weeks,
        "approved_change_duration_weeks": approved_change_duration_weeks,
        "delayed_tasks": delayed,
        "pending_changes": pending_changes,
        "approved_change_cost": approved_change_cost,
        "future_cost_record_count": future_cost_record_count,
        "critical_defects": critical_defects,
        "attention_checks": attention_checks,
        "open_risks": open_risks,
        "warnings": warnings,
        "unapproved_wbs_count": unapproved_wbs_count,
    }
