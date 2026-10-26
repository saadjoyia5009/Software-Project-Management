
PRAGMA foreign_keys = ON;

-- 1. Project information
CREATE TABLE IF NOT EXISTS projects (
    project_id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    objective TEXT,
    scope TEXT,
    project_sponsor TEXT,
    project_manager TEXT,
    scope_in TEXT,
    scope_out TEXT,
    start_date TEXT,
    deadline TEXT,
    duration_weeks INTEGER NOT NULL DEFAULT 16
        CHECK (duration_weeks > 0),
    approved_budget REAL NOT NULL DEFAULT 5000000
        CHECK (approved_budget >= 0),
    revised_budget REAL NOT NULL DEFAULT 5000000
        CHECK (revised_budget >= 0),
    status TEXT NOT NULL DEFAULT 'Planning'
        CHECK (status IN (
            'Planning', 'In Progress', 'On Hold',
            'Completed', 'Closed'
        )),
    schedule_plan TEXT,
    cost_plan TEXT,
    quality_plan TEXT,
    closure_date TEXT,
    closure_final_status TEXT,
    closure_summary TEXT,
    outstanding_issues TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS stakeholders (
    stakeholder_id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    role TEXT NOT NULL,
    contact TEXT,
    responsibilities TEXT,
    FOREIGN KEY (project_id) REFERENCES projects(project_id)
        ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS team_members (
    member_id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    role TEXT NOT NULL,
    email TEXT,
    responsibilities TEXT,
    FOREIGN KEY (project_id) REFERENCES projects(project_id)
        ON DELETE CASCADE
);

-- 2. Requirements and scope
CREATE TABLE IF NOT EXISTS requirements (
    requirement_id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL,
    title TEXT NOT NULL,
    description TEXT,
    priority TEXT NOT NULL DEFAULT 'Medium'
        CHECK (priority IN ('Low', 'Medium', 'High', 'Critical')),
    status TEXT NOT NULL DEFAULT 'Proposed'
        CHECK (status IN (
            'Proposed', 'Pending Approval', 'Approved',
            'Rejected', 'Implemented'
        )),
    is_in_approved_scope INTEGER NOT NULL DEFAULT 0
        CHECK (is_in_approved_scope IN (0, 1)),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (project_id) REFERENCES projects(project_id)
        ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS wbs_tasks (
    task_id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL,
    parent_task_id INTEGER,
    requirement_id INTEGER,
    task_name TEXT NOT NULL,
    wbs_type TEXT NOT NULL DEFAULT 'Task'
        CHECK (wbs_type IN ('Deliverable', 'Task', 'Work Package')),
    description TEXT,
    duration_days INTEGER NOT NULL DEFAULT 1
        CHECK (duration_days > 0),
    start_date TEXT,
    end_date TEXT,
    schedule_is_manual INTEGER NOT NULL DEFAULT 0
        CHECK (schedule_is_manual IN (0, 1)),
    baseline_start_date TEXT,
    baseline_end_date TEXT,
    status TEXT NOT NULL DEFAULT 'Not Started'
        CHECK (status IN (
            'Not Started', 'In Progress', 'Completed',
            'Delayed', 'Blocked'
        )),
    progress INTEGER NOT NULL DEFAULT 0
        CHECK (progress BETWEEN 0 AND 100),
    assigned_member_id INTEGER,
    planned_cost REAL NOT NULL DEFAULT 0
        CHECK (planned_cost >= 0),
    FOREIGN KEY (project_id) REFERENCES projects(project_id)
        ON DELETE CASCADE,
    FOREIGN KEY (parent_task_id) REFERENCES wbs_tasks(task_id),
    FOREIGN KEY (requirement_id) REFERENCES requirements(requirement_id),
    FOREIGN KEY (assigned_member_id) REFERENCES team_members(member_id)
        ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS task_dependencies (
    dependency_id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id INTEGER NOT NULL,
    depends_on_task_id INTEGER NOT NULL,
    UNIQUE (task_id, depends_on_task_id),
    CHECK (task_id <> depends_on_task_id),
    FOREIGN KEY (task_id) REFERENCES wbs_tasks(task_id)
        ON DELETE CASCADE,
    FOREIGN KEY (depends_on_task_id) REFERENCES wbs_tasks(task_id)
        ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS milestones (
    milestone_id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    description TEXT,
    due_date TEXT,
    completed_date TEXT,
    status TEXT NOT NULL DEFAULT 'Pending'
        CHECK (status IN ('Pending', 'Achieved', 'Delayed')),
    FOREIGN KEY (project_id) REFERENCES projects(project_id)
        ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS change_requests (
    change_id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL,
    title TEXT NOT NULL,
    justification TEXT NOT NULL,
    extra_cost REAL NOT NULL DEFAULT 0 CHECK (extra_cost >= 0),
    extra_duration_weeks INTEGER NOT NULL DEFAULT 0
        CHECK (extra_duration_weeks >= 0),
    status TEXT NOT NULL DEFAULT 'Pending'
        CHECK (status IN ('Pending', 'Approved', 'Rejected')),
    requested_by TEXT,
    decision_date TEXT,
    decision_notes TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (project_id) REFERENCES projects(project_id)
        ON DELETE CASCADE
);

-- 3. Cost and Earned Value Management
CREATE TABLE IF NOT EXISTS cost_records (
    cost_id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id INTEGER NOT NULL,
    planned_cost REAL NOT NULL DEFAULT 0 CHECK (planned_cost >= 0),
    actual_cost REAL NOT NULL DEFAULT 0 CHECK (actual_cost >= 0),
    budgeted_value REAL NOT NULL DEFAULT 0 CHECK (budgeted_value >= 0),
    record_date TEXT NOT NULL DEFAULT CURRENT_DATE,
    FOREIGN KEY (task_id) REFERENCES wbs_tasks(task_id)
        ON DELETE CASCADE
);

-- 4. Defects, quality and testing
CREATE TABLE IF NOT EXISTS defects (
    defect_id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL,
    title TEXT NOT NULL,
    description TEXT,
    severity TEXT NOT NULL DEFAULT 'Medium'
        CHECK (severity IN ('Low', 'Medium', 'High', 'Critical')),
    assigned_member_id INTEGER,
    status TEXT NOT NULL DEFAULT 'Open'
        CHECK (status IN (
            'Open', 'In Progress', 'Resolved', 'Verified', 'Closed'
        )),
    reported_date TEXT NOT NULL DEFAULT CURRENT_DATE,
    resolution_notes TEXT,
    resolved_date TEXT,
    FOREIGN KEY (project_id) REFERENCES projects(project_id)
        ON DELETE CASCADE,
    FOREIGN KEY (assigned_member_id) REFERENCES team_members(member_id)
        ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS quality_checks (
    check_id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL,
    item_name TEXT NOT NULL,
    expected_result TEXT,
    actual_result TEXT,
    inspection_date TEXT,
    result TEXT NOT NULL DEFAULT 'Not Tested'
        CHECK (result IN ('Not Tested', 'Pass', 'Fail')),
    tester_id INTEGER,
    remarks TEXT,
    FOREIGN KEY (project_id) REFERENCES projects(project_id)
        ON DELETE CASCADE,
    FOREIGN KEY (tester_id) REFERENCES team_members(member_id)
        ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS test_cases (
    test_id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL,
    requirement_id INTEGER,
    test_name TEXT NOT NULL,
    expected_result TEXT,
    actual_result TEXT,
    status TEXT NOT NULL DEFAULT 'Not Run'
        CHECK (status IN ('Not Run', 'Pass', 'Fail', 'Blocked')),
    tested_by INTEGER,
    tested_at TEXT,
    FOREIGN KEY (project_id) REFERENCES projects(project_id)
        ON DELETE CASCADE,
    FOREIGN KEY (requirement_id) REFERENCES requirements(requirement_id),
    FOREIGN KEY (tested_by) REFERENCES team_members(member_id)
        ON DELETE SET NULL
);

-- 5. Risk matrix and PDPC
CREATE TABLE IF NOT EXISTS risks (
    risk_id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL,
    title TEXT NOT NULL,
    description TEXT,
    likelihood INTEGER NOT NULL CHECK (likelihood BETWEEN 1 AND 5),
    impact INTEGER NOT NULL CHECK (impact BETWEEN 1 AND 5),
    risk_score INTEGER NOT NULL CHECK (risk_score BETWEEN 1 AND 25),
    response_action TEXT,
    owner_id INTEGER,
    status TEXT NOT NULL DEFAULT 'Open'
        CHECK (status IN ('Open', 'Monitoring', 'Mitigated', 'Closed')),
    FOREIGN KEY (project_id) REFERENCES projects(project_id)
        ON DELETE CASCADE,
    FOREIGN KEY (owner_id) REFERENCES team_members(member_id)
        ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS pdpc_actions (
    action_id INTEGER PRIMARY KEY AUTOINCREMENT,
    risk_id INTEGER NOT NULL,
    possible_problem TEXT NOT NULL,
    preventive_action TEXT,
    corrective_action TEXT,
    responsible_member_id INTEGER,
    status TEXT NOT NULL DEFAULT 'Planned'
        CHECK (status IN ('Planned', 'In Progress', 'Completed')),
    FOREIGN KEY (risk_id) REFERENCES risks(risk_id)
        ON DELETE CASCADE,
    FOREIGN KEY (responsible_member_id) REFERENCES team_members(member_id)
        ON DELETE SET NULL
);

-- 6. Healthcare records
CREATE TABLE IF NOT EXISTS patients (
    patient_id INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_name TEXT NOT NULL,
    phone TEXT,
    date_of_birth TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS doctor_schedules (
    schedule_id INTEGER PRIMARY KEY AUTOINCREMENT,
    doctor_name TEXT NOT NULL,
    available_date TEXT NOT NULL,
    start_time TEXT NOT NULL,
    end_time TEXT NOT NULL,
    availability_status TEXT NOT NULL DEFAULT 'Available'
        CHECK (availability_status IN ('Available', 'Unavailable')),
    CHECK (start_time < end_time)
);

CREATE TABLE IF NOT EXISTS appointments (
    appointment_id INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id INTEGER NOT NULL,
    schedule_id INTEGER NOT NULL,
    appointment_date TEXT NOT NULL,
    start_time TEXT NOT NULL,
    end_time TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'Booked'
        CHECK (status IN ('Booked', 'Completed', 'Cancelled')),
    FOREIGN KEY (patient_id) REFERENCES patients(patient_id),
    FOREIGN KEY (schedule_id) REFERENCES doctor_schedules(schedule_id),
    CHECK (start_time < end_time)
);

CREATE TABLE IF NOT EXISTS lab_reports (
    report_id INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id INTEGER NOT NULL,
    test_name TEXT NOT NULL,
    test_date TEXT NOT NULL,
    result TEXT,
    report_status TEXT NOT NULL DEFAULT 'Pending'
        CHECK (report_status IN ('Pending', 'Completed', 'Reviewed')),
    FOREIGN KEY (patient_id) REFERENCES patients(patient_id)
);

CREATE TABLE IF NOT EXISTS consultations (
    consultation_id INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id INTEGER NOT NULL,
    doctor_name TEXT NOT NULL,
    scheduled_at TEXT NOT NULL,
    consultation_type TEXT NOT NULL DEFAULT 'Online',
    status TEXT NOT NULL DEFAULT 'Requested'
        CHECK (status IN (
            'Requested', 'Scheduled', 'Completed', 'Cancelled'
        )),
    notes TEXT,
    FOREIGN KEY (patient_id) REFERENCES patients(patient_id)
);

CREATE TABLE IF NOT EXISTS bills (
    bill_id INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id INTEGER NOT NULL,
    appointment_id INTEGER,
    bill_date TEXT NOT NULL DEFAULT CURRENT_DATE,
    total_amount REAL NOT NULL DEFAULT 0 CHECK (total_amount >= 0),
    paid_amount REAL NOT NULL DEFAULT 0 CHECK (paid_amount >= 0),
    payment_status TEXT NOT NULL DEFAULT 'Unpaid'
        CHECK (payment_status IN ('Unpaid', 'Partially Paid', 'Paid')),
    FOREIGN KEY (patient_id) REFERENCES patients(patient_id),
    FOREIGN KEY (appointment_id) REFERENCES appointments(appointment_id)
        ON DELETE SET NULL,
    CHECK (paid_amount <= total_amount)
);

CREATE TABLE IF NOT EXISTS bill_items (
    item_id INTEGER PRIMARY KEY AUTOINCREMENT,
    bill_id INTEGER NOT NULL,
    description TEXT NOT NULL,
    quantity INTEGER NOT NULL DEFAULT 1 CHECK (quantity > 0),
    unit_price REAL NOT NULL CHECK (unit_price >= 0),
    line_total REAL NOT NULL CHECK (line_total >= 0),
    FOREIGN KEY (bill_id) REFERENCES bills(bill_id)
        ON DELETE CASCADE
);

-- Helpful indexes
CREATE INDEX IF NOT EXISTS idx_tasks_project
    ON wbs_tasks(project_id);
CREATE INDEX IF NOT EXISTS idx_defects_project_status
    ON defects(project_id, status);
CREATE INDEX IF NOT EXISTS idx_changes_project_status
    ON change_requests(project_id, status);
CREATE INDEX IF NOT EXISTS idx_appointments_date
    ON appointments(appointment_date);
CREATE INDEX IF NOT EXISTS idx_bills_patient
    ON bills(patient_id);

-- A dated cost record is a daily snapshot for one activity, not a duplicate entry.
CREATE TRIGGER IF NOT EXISTS prevent_duplicate_cost_record
BEFORE INSERT ON cost_records
WHEN EXISTS (
    SELECT 1 FROM cost_records
    WHERE task_id = NEW.task_id AND record_date = NEW.record_date
)
BEGIN
    SELECT RAISE(ABORT, 'Only one cost record per activity and record date is allowed');
END;

CREATE TRIGGER IF NOT EXISTS validate_risk_score_insert
BEFORE INSERT ON risks
WHEN NEW.risk_score <> NEW.likelihood * NEW.impact
BEGIN
    SELECT RAISE(ABORT, 'Risk score must equal likelihood multiplied by impact');
END;

CREATE TRIGGER IF NOT EXISTS validate_risk_score_update
BEFORE UPDATE OF likelihood, impact, risk_score ON risks
WHEN NEW.risk_score <> NEW.likelihood * NEW.impact
BEGIN
    SELECT RAISE(ABORT, 'Risk score must equal likelihood multiplied by impact');
END;

-- Scope-control safeguards. These triggers apply even to direct SQLite writes.
CREATE TRIGGER IF NOT EXISTS validate_requirement_scope_insert
BEFORE INSERT ON requirements
WHEN NEW.is_in_approved_scope = 1 AND NEW.status <> 'Approved'
BEGIN
    SELECT RAISE(ABORT, 'Only approved requirements may enter approved scope');
END;

CREATE TRIGGER IF NOT EXISTS validate_requirement_scope_update
BEFORE UPDATE OF status, is_in_approved_scope ON requirements
WHEN NEW.is_in_approved_scope = 1 AND NEW.status <> 'Approved'
BEGIN
    SELECT RAISE(ABORT, 'Only approved requirements may enter approved scope');
END;

CREATE TRIGGER IF NOT EXISTS prevent_unapproving_linked_requirement
BEFORE UPDATE OF status, is_in_approved_scope ON requirements
WHEN (NEW.status <> 'Approved' OR NEW.is_in_approved_scope <> 1)
 AND EXISTS (SELECT 1 FROM wbs_tasks WHERE requirement_id = OLD.requirement_id)
BEGIN
    SELECT RAISE(ABORT, 'A requirement linked to WBS work must remain approved');
END;

CREATE TRIGGER IF NOT EXISTS validate_wbs_requirement_insert
BEFORE INSERT ON wbs_tasks
WHEN NEW.requirement_id IS NOT NULL
 AND NOT EXISTS (
    SELECT 1 FROM requirements
    WHERE requirement_id = NEW.requirement_id
      AND project_id = NEW.project_id
      AND status = 'Approved'
      AND is_in_approved_scope = 1
 )
BEGIN
    SELECT RAISE(ABORT, 'WBS work may only link to an approved requirement in this project');
END;

CREATE TRIGGER IF NOT EXISTS validate_wbs_requirement_update
BEFORE UPDATE OF requirement_id, project_id ON wbs_tasks
WHEN NEW.requirement_id IS NOT NULL
 AND NOT EXISTS (
    SELECT 1 FROM requirements
    WHERE requirement_id = NEW.requirement_id
      AND project_id = NEW.project_id
      AND status = 'Approved'
      AND is_in_approved_scope = 1
 )
BEGIN
    SELECT RAISE(ABORT, 'WBS work may only link to an approved requirement in this project');
END;

CREATE TRIGGER IF NOT EXISTS validate_wbs_parent_insert
BEFORE INSERT ON wbs_tasks
WHEN NEW.parent_task_id IS NOT NULL
 AND NOT EXISTS (
    SELECT 1 FROM wbs_tasks
    WHERE task_id = NEW.parent_task_id AND project_id = NEW.project_id
 )
BEGIN
    SELECT RAISE(ABORT, 'WBS parent must belong to the same project');
END;

CREATE TRIGGER IF NOT EXISTS validate_wbs_parent_update
BEFORE UPDATE OF parent_task_id, project_id ON wbs_tasks
WHEN NEW.parent_task_id IS NOT NULL
 AND (NEW.parent_task_id = NEW.task_id OR NOT EXISTS (
    SELECT 1 FROM wbs_tasks
    WHERE task_id = NEW.parent_task_id AND project_id = NEW.project_id
 ))
BEGIN
    SELECT RAISE(ABORT, 'WBS parent must belong to the same project and cannot be itself');
END;

CREATE TRIGGER IF NOT EXISTS prevent_wbs_parent_cycle
BEFORE UPDATE OF parent_task_id, project_id ON wbs_tasks
WHEN NEW.parent_task_id IS NOT NULL
 AND EXISTS (
    WITH RECURSIVE ancestors(task_id) AS (
        SELECT NEW.parent_task_id
        UNION
        SELECT task.parent_task_id
        FROM wbs_tasks task
        JOIN ancestors ON task.task_id = ancestors.task_id
        WHERE task.parent_task_id IS NOT NULL
    )
    SELECT 1 FROM ancestors WHERE task_id = NEW.task_id
 )
BEGIN
    SELECT RAISE(ABORT, 'WBS parent hierarchy cannot contain a cycle');
END;

-- Dependency safeguards. Circular and cross-project links are never allowed.
CREATE TRIGGER IF NOT EXISTS validate_dependency_project
BEFORE INSERT ON task_dependencies
WHEN NOT EXISTS (
    SELECT 1
    FROM wbs_tasks task
    JOIN wbs_tasks predecessor ON predecessor.task_id = NEW.depends_on_task_id
    WHERE task.task_id = NEW.task_id
      AND task.project_id = predecessor.project_id
)
BEGIN
    SELECT RAISE(ABORT, 'Task dependencies must be within one project');
END;

CREATE TRIGGER IF NOT EXISTS prevent_task_dependency_cycle
BEFORE INSERT ON task_dependencies
WHEN EXISTS (
    WITH RECURSIVE downstream(task_id) AS (
        SELECT task_id FROM task_dependencies WHERE depends_on_task_id = NEW.task_id
        UNION
        SELECT dependency.task_id
        FROM task_dependencies dependency
        JOIN downstream ON dependency.depends_on_task_id = downstream.task_id
    )
    SELECT 1 FROM downstream WHERE task_id = NEW.depends_on_task_id
)
BEGIN
    SELECT RAISE(ABORT, 'Circular task dependency is not allowed');
END;
