# Oracle Deep Parser Report — HRMS Source Code

## Summary

| Category | Count |
|---|---|
| PL/SQL Packages parsed | 11 |
| Oracle Forms parsed | 6 |
| DDL Tables parsed | 30 |
| Views parsed | 6 |
| DB Triggers parsed | 5 |
| Business rules extracted | 101 |
| Validation rules extracted | 376 |
| Constraints extracted | 33 |
| Known bugs extracted | 5 |
| Error codes extracted | 37 |
| Check constraints extracted | 29 |
| **Total rules** | **581** |

---

## PL/SQL Packages — Deep Extraction

### HRMS.PKG_AUDIT

**Procedures (2):**
- `log_action(p_table_name, p_record_id, p_action, p_user, p_old_values)`
- `purge_old_records(p_days_to_keep, p_user)`

**Functions (1):**
- `get_change_history(p_table_name, p_record_id, p_from_date, p_to_date) RETURN SYS_REFCURSOR`

**Tables accessed (1):** AUDIT_LOG

**Sequences used:** SEQ_AUDIT

### HRMS.PKG_COMMON

**Business Rules (2):**
- Only system parameters explicitly flagged as editable (EDITABLE_FLAG = 'Y') may be modified; parameters marked non-editable are protected from update
- _days_between

**Validation Rules (10):**
- A parameter update must match exactly one editable row; if zero rows are updated the parameter either does not exist in the given group/code or has been locked as non-editable
- Attempting to modify a non-existent or non-editable system parameter is a fatal error; callers must not silently ignore this condition
- Saturday and Sunday are not counted as business days; only Monday through Friday increment the business day counter
- Saturday and Sunday are skipped when advancing by business days; only weekdays (Monday through Friday) count toward the requested number of days added
- A date falling in October or later belongs to the fiscal year of the following calendar year (e.g. October 2024 is in fiscal year 2025)
- Fiscal quarters follow the October 1 fiscal year start: Q1 = October–December, Q2 = January–March, Q3 = April–June, Q4 = July–September
- A 10-digit number is formatted as a US domestic number in (NXX) NXX-XXXX notation
- An 11-digit number starting with '1' is formatted as a US/Canada international number with a +1 prefix; all other lengths or leading digits are returned unmodified
- A null SSN or one with fewer than 4 characters cannot be partially unmasked; the entire value is replaced with the full mask '***-**-****' to prevent partial PII exposure
- Format code 'LF' produces "Last, First" display order; any other value (including the default 'FL') produces "First Last" display order

**Constraints (4):**
- The fiscal year boundary is month 10 (October); the organisation's fiscal year begins on October 1
- A standard US domestic phone number must contain exactly 10 digits
- An 11-digit phone number is only recognised as a valid US/Canada international number if it begins with country code '1'
- An SSN must have at least 4 characters for the last-four-digit display to be meaningful

**Error Codes (1):**
- `-20900`: Parameter not found or not editable: 

**Procedures (3):**
- `log_error(p_package, p_procedure, p_message, p_user)`
- `log_info(p_package, p_procedure, p_message, p_user)`
- `set_param(p_group, p_code, p_value, p_user)`

**Functions (14):**
- `get_param(p_group, p_code) RETURN VARCHAR2`
- `get_param_number(p_group, p_code) RETURN NUMBER`
- `get_param_date(p_group, p_code) RETURN DATE`
- `business_days_between(p_start_date, p_end_date) RETURN NUMBER`
- `add_business_days(p_date, p_days) RETURN DATE`
- `get_fiscal_year(p_date) RETURN NUMBER`
- `get_fiscal_quarter(p_date) RETURN NUMBER`
- `format_phone(p_phone) RETURN VARCHAR2`
- `format_ssn_masked(p_ssn) RETURN VARCHAR2`
- `format_currency(p_amount, p_currency_code) RETURN VARCHAR2`
- `format_name(p_first_name, p_last_name, p_format, LF=Last, First) RETURN VARCHAR2`
- `is_valid_email(p_email) RETURN BOOLEAN`
- `is_valid_phone(p_phone) RETURN BOOLEAN`
- `is_valid_ssn(p_ssn) RETURN BOOLEAN`

**Tables accessed (6):** AND, AUDIT_LOG, MUST, P_DATE, SYSTEM_PARAMETERS, UPDATE

**Sequences used:** SEQ_AUDIT

### HRMS.PKG_EMPLOYEE
**Known Issues:**
- - Circular dependency with PKG_PAYROLL (salary validation)
- - get_org_chart uses recursive SQL that times out for deep hierarchies

**Constants (2):**
- `c_max_hierarchy_depth` = `15` — The reporting hierarchy is limited to a maximum depth of 15 levels to prevent unbounded traversal during circular reference detection
- `c_emp_number_prefix` = `'EMP'`

**Business Rules (12):**
- Only departments flagged as active (ACTIVE_FLAG = 'Y') are considered valid for employee assignment
- Only employees with EMPLOYMENT_STATUS = 'ACTIVE' are eligible to be assigned as a manager
- Only job titles with ACTIVE_FLAG = 'Y' are valid for assignment to a new employee
- The current salary is the active salary record that became effective on or before today and whose end date is either open-ended or in the future
- When provided, the status filter restricts search results to employees with the specified EMPLOYMENT_STATUS value (e.g., ACTIVE, TERMINATED)
- The most recent active salary record is used as the pre-promotion baseline for computing the percentage salary increase
- Only leave requests in PENDING status are identified for automatic cancellation upon employee termination
- Only currently active salary records (ACTIVE_FLAG = 'Y') are closed upon termination; previously ended records are not modified
- Only currently active pay elements (ACTIVE_FLAG = 'Y') are deactivated at termination; previously ended pay elements are not affected
- Only employees with EMPLOYMENT_STATUS = 'ACTIVE' are returned as direct reports; terminated or inactive employees are excluded
- The org chart hierarchy traversal includes only employees with EMPLOYMENT_STATUS = 'ACTIVE'; terminated employees are excluded from the hierarchy
- Headcount counts only employees who were actively employed on the specified as-of date — hired on or before that date and not yet terminated at that point

**Validation Rules (33):**
- Department must exist and be active before it can be assigned to an employee
- Assigning an inactive or non-existent department to an employee raises an application error
- A NULL manager assignment is valid and indicates the employee is at the top of the reporting hierarchy with no manager above them
- The designated manager must exist in the system and have EMPLOYMENT_STATUS = 'ACTIVE'
- Specifying a manager who does not exist or is not currently active raises an application error
- When updating an existing employee, the new manager assignment must not create a circular reporting chain
- An employee cannot directly or indirectly report to themselves; circular reporting chains are prohibited
- Assigning a manager who already reports (directly or indirectly) to this employee creates a circular chain and raises an error
- Both first name and last name are mandatory fields when creating a new employee record
- An employee cannot be created without both a first name and a last name
- The job title specified at hire must exist in the JOB_TITLES table and be currently active
- Employee starting salary must fall within the minimum and maximum range for their assigned job grade (soft warning — manager approval via the Forms layer allows override)
- A salary record is only created at hire when a starting salary is explicitly provided; employees may be hired without an initial salary record
- Employee numbers must be unique; a duplicate generated during concurrent inserts requires the caller to retry the operation
- Employee must exist in the system before their contact or personal information can be updated
- Attempting to update a non-existent employee record raises an application error
- If the update affects zero rows, an error is raised to signal an unexpected data integrity failure
- Zero rows updated after a successful existence check indicates a concurrent deletion between the two operations
- Requesting an employee by ID that does not exist in the EMPLOYEES table raises an application error
- Requesting an employee by employee number that does not exist in the EMPLOYEES table raises an application error
- Only employees with EMPLOYMENT_STATUS = 'ACTIVE' may be transferred; transferring a non-active employee is prohibited
- Attempting to transfer an employee who is not in ACTIVE status raises an application error
- A new manager for the transfer is validated (including circular-chain detection) only when one is explicitly provided; omitting the manager preserves the existing assignment
- An employee who is already terminated cannot be terminated again; re-termination is blocked
- Attempting to terminate an already-terminated employee raises an application error
- All pending leave requests for a terminating employee are automatically cancelled; no manual action is required from the employee or their manager
- A termination notification is sent to the employee's direct manager only when a manager is assigned; top-level employees with no manager do not trigger a manager notification
- Rehiring an employee overwrites their hire date with the rehire date and clears all prior termination data; the employee is treated as starting fresh from the rehire date
- Attempting to rehire an employee ID that does not exist in the EMPLOYEES table raises an application error
- An employee is considered active if and only if their EMPLOYMENT_STATUS column value equals 'ACTIVE'
- An employee record is considered invalid if either the first name or the last name is absent
- An employee record is considered invalid if no hire date has been recorded
- An employee record is considered inconsistent if EMPLOYMENT_STATUS is 'ACTIVE' but ACTIVE_FLAG is not 'Y'; both fields must be in agreement for active employees

**Constraints (2):**
- The reporting hierarchy is limited to a maximum depth of 15 levels to prevent unbounded traversal during circular reference detection
- The default maximum depth for org chart traversal is 10 levels; callers may override this, but deeper traversal risks timeout on large organisations

**Known Bugs (2):**
- race condition under concurrent inserts - no SELECT FOR UPDATE
- SQL injection possible via p_last_name if called with unvalidated input

**Error Codes (13):**
- `-20003`: Invalid or inactive department: 
- `-20004`: Invalid or inactive manager: 
- `-20004`: Circular reporting chain detected: Employee 
- `-20010`: First name and last name are required
- `-20011`: Invalid or inactive job: 
- `-20002`: Duplicate employee number generated. Please retry.
- `-20001`: Employee not found: 
- `-20001`: Employee update failed: 
- `-20001`: Employee not found: 
- `-20001`: Employee not found: 
- `-20012`: Cannot transfer non-active employee. Status: 
- `-20005`: Employee 
- `-20001`: Employee not found for rehire: 

**Procedures (7):**
- `update_employee(p_emp_id, p_first_name, p_last_name, p_email, p_phone_work)`
- `search_employees(p_cursor, p_last_name, p_first_name, p_dept_id, p_status)`
- `transfer_employee(p_emp_id, p_new_dept_id, p_new_job_id, p_new_manager_id, p_new_location)`
- `promote_employee(p_emp_id, p_new_job_id, p_new_salary, p_effective_date, p_comments)`
- `terminate_employee(p_emp_id, p_termination_date, p_reason, p_comments, p_user)`
- `rehire_employee(p_emp_id, p_rehire_date, p_dept_id, p_job_id, p_base_salary)`
- `set_session_context(p_user, p_emp_id)`

**Functions (10):**
- `create_employee(p_first_name, p_last_name, p_hire_date, p_dept_id, p_job_id) RETURN NUMBER`
- `get_employee(p_emp_id) RETURN t_emp_rec`
- `get_employee_by_number(p_emp_number) RETURN t_emp_rec`
- `get_direct_reports(p_manager_emp_id) RETURN t_emp_id_table`
- `get_org_chart(p_root_emp_id, p_max_depth) RETURN t_emp_cursor`
- `get_headcount_by_dept(p_dept_id, p_as_of_date) RETURN NUMBER`
- `get_tenure_years(p_emp_id) RETURN NUMBER`
- `is_active(p_emp_id) RETURN BOOLEAN`
- `validate_employee(p_emp_id) RETURN BOOLEAN`
- `emp_exists(p_emp_id) RETURN BOOLEAN`

**Tables accessed (19):** A, AFFECTS, DEPARTMENT, DEPARTMENTS, EMPLOYEE, EMPLOYEES, EMPLOYEE_HISTORY, EMPLOYEE_PAY_ELEMENTS, FAILED, IN, IS, JOB, JOB_GRADES, JOB_TITLES, LEAVE_REQUESTS, NOWAIT, PATTERN, SALARY_RECORDS, THE

**Sequences used:** SEQ_EMP_HISTORY, SEQ_EMPLOYEE

### HRMS.PKG_INTEGRATION
**Known Issues:**
- - GL posting uses flat file exchange (UTL_FILE) instead of API
- - Benefits feed format is vendor-specific (ADP format)
- - No retry logic for failed file transfers
- - FTP credentials stored in SYSTEM_PARAMETERS table (cleartext)

**Constants (3):**
- `c_gl_output_dir` = `'GL_FEED_OUT'`
- `c_benefits_output_dir` = `'BENEFITS_FEED_OUT'`
- `c_time_input_dir` = `'TIME_ATTENDANCE_IN'`

**Procedures (4):**
- `generate_gl_journal(p_run_id, p_user)`
- `export_benefits_feed(p_effective_date, p_user)`
- `import_time_attendance(p_file_name, p_user)`
- `sync_org_structure(p_user)`

**Functions (1):**
- `get_integration_status(p_integration_name) RETURN VARCHAR2`

**Tables accessed (5):** CSV, EMPLOYEES, PAYROLL, PAYROLL_DETAILS, V_IMPORTED

### HRMS.PKG_LEAVE
**Known Issues:**
- - Overlapping leave detection does not account for half-day requests
- - Carryover expiry job sometimes double-expires if run twice on same day
- - Holiday detection only checks exact date match, not observed dates

**Business Rules (10):**
- Only holidays marked as currently active (ACTIVE_FLAG = 'Y') are
- An employee's date range conflicts if any existing leave request
- Only employees with EMPLOYMENT_STATUS = 'ACTIVE' are eligible
- Only leave types flagged as active (ACTIVE_FLAG = 'Y') may be
- Balance records are created only for leave types that are currently
- Monthly accrual runs only for employees who are currently active
- Accrual is processed only for leave types that are active,
- Only employees who have a positive remaining balance at year-end
- Returns only leave requests in PENDING status that are assigned
- The team calendar shows only leave that has been approved or

**Validation Rules (31):**
- Employee must exist and have ACTIVE employment status to submit leave
- The requested leave type must exist and be currently active
- Some leave types require a minimum period of employment before an
- Employee's time since hire date must meet the leave type's minimum
- Employee has not yet served the minimum tenure required for this leave type
- Leave request start date must not be later than the end date
- A leave request with a start date after the end date is invalid
- Backdated leave requests are permitted only within a limited window;
- Backdated leave requests more than 5 calendar days in the past
- A half-day leave request is always counted as exactly 0.5 days regardless
- A leave request must span at least one business day; requests that fall
- The requested date range contains no working days after excluding
- An employee cannot have two leave requests for overlapping date ranges
- The requested leave period overlaps with a leave request that is
- Balance enforcement only applies to leave types that are accrual-based
- The employee's available leave balance must be sufficient to cover
- Insufficient accrued leave balance to cover the requested duration
- An approval notification is sent to the employee's direct manager only
- Leave types with REQUIRES_APPROVAL = 'N' bypass the approval workflow
- Only a leave request currently in PENDING status can be approved;
- Attempt to approve a leave request that is not in PENDING status
- Only a leave request currently in PENDING status can be rejected;
- Attempt to reject a leave request that is not in PENDING status
- Only leave requests in PENDING or APPROVED status can be cancelled;
- Attempt to cancel a leave request that is in an unmodifiable status
- When a PENDING request is cancelled, the reserved (pending) balance is
- When an APPROVED request is cancelled, the consumed (used) balance is
- An employee must have been employed for at least the leave type's
- An employee's leave balance cannot exceed the leave type's
- When a leave type has a defined carryover ceiling, any unused balance
- Carried-over leave days that have passed their expiry date and have not

**Constraints (2):**
- The maximum number of calendar days into the past an employee
- The batch commits after every 100 employees to limit transaction

**Known Bugs (2):**
- Does not handle "observed" holidays (e.g., if July 4 falls on
- If run twice on same day, can double-subtract

**Error Codes (11):**
- `-20001`: Employee not found or not active: 
- `-20203`: Invalid leave type: 
- `-20203`: Minimum tenure of 
- `-20210`: Start date must be before or equal to end date
- `-20211`: Cannot submit leave requests more than 5 days in the past
- `-20212`: No business days in the selected range
- `-20202`: Leave request overlaps with an existing request
- `-20201`: Insufficient leave balance. Available: 
- `-20204`: Cannot approve request in status: 
- `-20204`: Cannot reject request in status: 
- `-20204`: Cannot cancel request in status: 

**Procedures (10):**
- `approve_leave_request(p_request_id, p_approver_emp_id, p_comments, p_user)`
- `reject_leave_request(p_request_id, p_approver_emp_id, p_comments, p_user)`
- `cancel_leave_request(p_request_id, p_reason, p_user)`
- `adjust_leave_balance(p_emp_id, p_leave_type_id, p_adjustment, p_reason, p_user)`
- `initialize_balances(p_emp_id, p_year, p_user)`
- `run_monthly_accrual(p_accrual_date, p_user)`
- `process_carryover(p_year, p_user)`
- `expire_carryover(p_user)`
- `get_pending_requests(p_cursor, p_approver_id)`
- `get_team_calendar(p_cursor, p_manager_id, p_start_date, p_end_date)`

**Functions (3):**
- `submit_leave_request(p_emp_id, p_leave_type_id, p_start_date, p_end_date, p_half_day_flag) RETURN NUMBER`
- `calculate_business_days(p_start_date, p_end_date, p_location_code) RETURN NUMBER`
- `check_leave_overlap(p_emp_id, p_start_date, p_end_date, p_exclude_request_id) RETURN BOOLEAN`

**Tables accessed (14):** BALANCE, BUSINESS, EMPLOYEES, HOLIDAYS, LEAVE_ACCRUAL_LOG, LEAVE_BALANCES, LEAVE_REQUESTS, LEAVE_TYPES, PENDING, P_ACCRUAL_DATE, P_START_DATE, REQUEST, THE, V_REQUEST

**Sequences used:** SEQ_LEAVE_REQUEST, SEQ_LEAVE_BALANCE, SEQ_LEAVE_ACCRUAL

### HRMS.PKG_NOTIFICATION
**Known Issues:**
- - UTL_MAIL configuration hard-coded to legacy SMTP server
- - No rate limiting - bulk operations can flood the queue
- - HTML email templates stored as string constants (maintenance nightmare)

**Constants (4):**
- `c_smtp_host` = `'smtp.internal.company.com'`
- `c_smtp_port` = `25`
- `c_from_address` = `'hrms-noreply@company.com'`
- `c_from_name` = `'HRMS System'`

**Procedures (4):**
- `send_notification(p_recipient_emp_id, p_recipient_email, p_type, p_subject, p_body)`
- `process_queue(p_batch_size, p_user)`
- `retry_failed(p_max_retries, p_user)`
- `cancel_notification(p_notification_id, p_user)`

**Tables accessed (3):** EMPLOYEE, EMPLOYEES, NOTIFICATION_QUEUE

**Sequences used:** SEQ_NOTIFICATION

### HRMS.PKG_PAYROLL
**Known Issues:**
- - Circular dependency with PKG_EMPLOYEE (is_active check)
- - Tax calculation uses hard-coded 2024 brackets in some paths
- - Overtime calculation does not account for holidays correctly
- - YTD accumulation resets incorrectly for mid-year hires in some edge cases

**Constants (8):**
- `c_ss_wage_base_2024` = `168600` — 2024 Social Security wage base; earnings above this amount are exempt from SS tax
- `c_ss_rate` = `0.062` — Employee share of Social Security tax is 6.2% of wages up to the wage base
- `c_medicare_rate` = `0.0145` — Employee share of standard Medicare tax is 1.45% of all wages with no cap
- `c_medicare_addl_rate` = `0.009` — Additional Medicare surtax rate of 0.9% applies above the high-earner threshold
- `c_medicare_addl_threshold` = `200000` — Annual earnings above $200,000 trigger the additional 0.9% Medicare surtax
- `c_standard_deduction_single` = `14600` — 2024 standard deduction for single or non-jointly-filing taxpayers is $14,600
- `c_standard_deduction_married` = `29200` — 2024 standard deduction for married filing jointly taxpayers is $29,200
- `c_allowance_amount` = `4300` — Each W-4 withholding allowance reduces annualised taxable income by $4,300

**Business Rules (13):**
- Targets the currently active salary record (ACTIVE_FLAG = 'Y') that predates
- Retrieves only the salary record that is currently active (ACTIVE_FLAG = 'Y'),
- Retrieves the salary record effective on a specific point-in-time date;
- Current pay period is defined as an OPEN period whose date range
- Only employees with EMPLOYMENT_STATUS = 'ACTIVE' and ACTIVE_FLAG = 'Y'
- Run gross total sums only EARNING-type detail lines; deduction total sums
- W-4 tax elections are matched to the employee and the tax year of the pay period;
- Only active (ACTIVE_FLAG = 'Y') deduction and benefit elements are applied;
- Gross pay is the sum of all EARNING-type detail lines for the employee
- Total deductions aggregate all DEDUCTION, TAX, and BENEFIT lines
- Payslip excludes any detail lines that failed processing (STATUS = 'ERROR');
- Year-to-date earnings are the sum of successfully CALCULATED EARNING-type
- Pay register excludes detail lines in ERROR status; one row per employee

**Validation Rules (38):**
- Base salary must be a positive number; zero or negative values are not permitted
- Salary must be positive — raises error -20101 if violated
- Monthly pay periods run from the 1st to the last calendar day of each month
- When the monthly pay date falls on a Saturday, it is moved back one day to Friday
- When the monthly pay date falls on a Sunday, it is moved back two days to Friday
- Biweekly pay periods are 14 days long, anchored so that the pay date falls on a Friday;
- A biweekly period is included in the year's set if either the period start
- A pay period that is already in CLOSED status cannot be closed again
- Attempting to close an already-closed period raises error -20102
- A payroll run cannot be created against a pay period that has already been closed
- Attempting to create a run for a closed period raises error -20102
- If any employee-level errors were encountered, the entire payroll run is marked ERROR;
- Gross pay per period is calculated by dividing annual salary by the number of
- An employee must have an active salary record as of the period end date
- Employee with no salary record on the period end date cannot be processed — raises error -20104
- If no W-4 is on file for the current tax year, the employee is treated
- Federal income tax withholding is only recorded when the calculated amount is greater than zero
- State income tax is only calculated and withheld when the employee has a
- State income tax withholding is only recorded when the calculated amount is greater than zero
- Social Security withholding is only recorded when there is a taxable wage amount
- Medicare withholding is only recorded when the calculated amount is greater than zero
- An employee-level override amount takes absolute precedence over any
- For FLAT deductions, use the employee's specific amount; if none is set,
- For PERCENTAGE deductions, apply the employee's rate (or the element default
- Only positive deduction amounts are written to payroll details;
- A payroll run can only be approved when it is in CALCULATED status; runs
- Attempting to approve a run that is not in CALCULATED status raises error -20103
- Employees filing as MARRIED_JOINT receive the married standard deduction ($29,200);
- Each W-4 withholding allowance reduces the employee's annualised taxable income
- If annualised income after applying the standard deduction and allowances is zero
- SINGLE and MARRIED_SEPARATE filers are taxed under the 2024 seven-bracket
- MARRIED_JOINT filers are taxed under the 2024 seven-bracket progressive schedule
- Employees working in TX, FL, or WA have no state income tax withheld because
- Once an employee's year-to-date earnings equal or exceed the Social Security
- If a pay period would cause year-to-date earnings to cross the wage base,
- When an employee's cumulative year-to-date earnings plus the current period gross
- If the employee's YTD earnings have already exceeded $200,000 before this
- If the $200,000 threshold is crossed during this pay period, only the portion

**Constraints (11):**
- 2024 Social Security wage base; earnings above this amount are exempt from SS tax
- Employee share of Social Security tax is 6.2% of wages up to the wage base
- Employee share of standard Medicare tax is 1.45% of all wages with no cap
- Additional Medicare surtax rate of 0.9% applies above the high-earner threshold
- Annual earnings above $200,000 trigger the additional 0.9% Medicare surtax
- 2024 standard deduction for single or non-jointly-filing taxpayers is $14,600
- 2024 standard deduction for married filing jointly taxpayers is $29,200
- Each W-4 withholding allowance reduces annualised taxable income by $4,300
- Biweekly pay date is 5 calendar days after the period end date
- Payroll changes are committed to the database every 50 employees processed
- State flat withholding rates: CA 7.25%, NY 6.85%, IL 4.95%, PA 3.07%,

**Known Bugs (1):**
- Cursor loop - should use BULK COLLECT + FORALL

**Error Codes (5):**
- `-20101`: Salary must be positive: 
- `-20102`: Period already closed: 
- `-20102`: Cannot create run for closed period: 
- `-20104`: No active salary record for employee 
- `-20103`: Cannot approve run in status: 

**Procedures (9):**
- `create_salary_record(p_emp_id, p_effective_date, p_base_salary, p_change_reason, p_change_pct)`
- `create_pay_periods(p_year, p_frequency, p_user)`
- `close_pay_period(p_period_id, p_user)`
- `calculate_payroll(p_run_id, p_user)`
- `calculate_employee_pay(p_run_id, p_emp_id, p_period_id, p_user)`
- `approve_payroll(p_run_id, p_user)`
- `reverse_payroll(p_run_id, p_reason, p_user)`
- `get_payslip(p_cursor, p_run_id, p_emp_id)`
- `generate_pay_register(p_run_id, p_user)`

**Functions (7):**
- `get_current_salary(p_emp_id) RETURN NUMBER`
- `get_salary_as_of(p_emp_id, p_as_of) RETURN NUMBER`
- `create_payroll_run(p_period_id, p_run_type, p_user) RETURN NUMBER`
- `calculate_federal_tax(p_taxable_income, p_filing_status, p_allowances, p_additional_wh, p_pay_frequency) RETURN NUMBER`
- `calculate_state_tax(p_taxable_income, p_state_code, p_filing_status, p_allowances, p_pay_frequency) RETURN NUMBER`
- `calculate_fica(p_gross_pay, p_ytd_gross) RETURN NUMBER`
- `calculate_medicare(p_gross_pay, p_ytd_gross) RETURN NUMBER`

**Tables accessed (17):** EMPLOYEES, EMPLOYEE_PAY_ELEMENTS, EMPLOYEE_TAX_INFO, GET_SALARY_AS_OF, PAYROLL_DETAILS, PAYROLL_RUNS, PAY_PERIODS, PP, RUN, SALARY_RECORDS, SS, STATUS, TAX_BRACKETS, THE, V_END_DATE, V_PERIOD_END, V_START_DATE

**Sequences used:** SEQ_PAY_PERIOD, SEQ_PAYROLL_RUN, SEQ_PAYROLL_DETAIL, SEQ_SALARY

### HRMS.PKG_PERFORMANCE

**Business Rules (3):**
- Returns only the reviews where the given employee is the designated reviewer, scoped to a single review cycle
- Includes only reviews that have received a final rating (completed reviews); optionally scoped to employees in a single department
- Only employees with ACTIVE employment status are eligible for bulk performance review generation

**Validation Rules (10):**
- A review cycle can only be transitioned to OPEN status if it is currently in DRAFT status
- Zero rows updated indicates the cycle was not in DRAFT status; the open transition is rejected
- Attempting to open a review cycle that is not in DRAFT status raises application error -20401
- A self-assessment can only be submitted when the review is in NOT_STARTED or SELF_REVIEW status; submission advances the review to MANAGER_REVIEW
- Zero rows updated indicates the review does not exist or is not in an eligible status for self-assessment submission
- Submitting a self-assessment for a review not in NOT_STARTED or SELF_REVIEW status raises application error -20402
- The overall performance rating must fall within the valid scoring range of 1.0 (lowest) to 5.0 (highest)
- Submitting a rating outside the 1.0 to 5.0 range raises application error -20403 and the review record is not updated
- An employee can only acknowledge a review that has been marked COMPLETED by the manager; reviews in any other status are silently unaffected
- Employees without a designated manager are excluded from bulk review generation; a manager assignment is required to create a review

**Constraints (6):**
- A score of 4.5 or above qualifies as 'Exceptional', the highest performance band
- A score of 3.5 or above (but below 4.5) qualifies as 'Exceeds Expectations'
- A score of 2.5 or above (but below 3.5) qualifies as 'Meets Expectations'
- A score of 1.5 or above (but below 2.5) qualifies as 'Needs Improvement'
- A progress percentage of 100 or above automatically advances the goal status to COMPLETED
- Any non-zero progress percentage below 100 automatically sets the goal status to IN_PROGRESS

**Error Codes (3):**
- `-20401`: Cannot open cycle - must be in DRAFT status
- `-20402`: Review not found or not in correct status
- `-20403`: Rating must be between 1.0 and 5.0

**Procedures (8):**
- `open_review_cycle(p_cycle_id, p_user)`
- `close_review_cycle(p_cycle_id, p_user)`
- `submit_self_assessment(p_review_id, p_self_assessment, p_user)`
- `submit_manager_review(p_review_id, p_overall_rating, p_manager_assessment, p_strengths, p_improvement_areas)`
- `acknowledge_review(p_review_id, p_emp_comments, p_user)`
- `update_goal_progress(p_goal_id, p_progress_pct, p_status, p_comments, p_user)`
- `get_team_reviews(p_cursor, p_manager_id, p_cycle_id)`
- `generate_reviews_for_cycle(p_cycle_id, p_user)`

**Functions (4):**
- `create_review_cycle(p_cycle_name, p_cycle_year, p_start_date, p_end_date, p_self_review_due) RETURN NUMBER`
- `create_review(p_cycle_id, p_emp_id, p_reviewer_emp_id, p_user) RETURN NUMBER`
- `add_goal(p_review_id, p_emp_id, p_goal_title, p_goal_description, p_goal_category) RETURN NUMBER`
- `get_rating_distribution(p_cycle_id, p_dept_id) RETURN SYS_REFCURSOR`

**Tables accessed (6):** BULK, EMPLOYEES, PERFORMANCE_GOALS, PERFORMANCE_REVIEWS, REVIEW_CYCLES, THE

**Sequences used:** SEQ_PERF_GOAL, SEQ_REVIEW_CYCLE, SEQ_PERF_REVIEW

### HRMS.PKG_REPORTING
**Known Issues:**
- - Denormalized reporting tables refreshed nightly; stale during business hours
- - Some reports use hard-coded fiscal year start (Oct 1)

**Business Rules (8):**
- Only employees with EMPLOYMENT_STATUS = 'ACTIVE' are included in headcount; inactive, suspended, or terminated records are excluded
- Only the currently active salary record (ACTIVE_FLAG = 'Y') is used for compensation analysis; historical salary rows are excluded
- Compensation analysis is restricted to employees with EMPLOYMENT_STATUS = 'ACTIVE'
- Only the currently active salary record (ACTIVE_FLAG = 'Y') is retrieved; a new hire without an active salary record still appears in the report with a NULL base salary
- Report is scoped to employees whose hire date falls within the specified date range, capturing all starters in the period
- Leave utilisation data is scoped to a single calendar year; balances from different years are not combined
- Only currently active employees are included; departed employees' unused leave balances are excluded from utilisation analysis
- EEO compliance report covers only employees with EMPLOYMENT_STATUS = 'ACTIVE'; former employees are excluded from all compliance headcount figures

**Validation Rules (15):**
- Headcount is segmented into three mutually exclusive employment classifications: FULL_TIME, PART_TIME, and CONTRACT
- Gender breakdown uses codes 'M' (male) and 'F' (female); employees with any other gender code are not counted in either gender total
- Employee must have been hired on or before the reporting snapshot date to be counted in headcount
- Employee must not be terminated as of the snapshot date; a NULL termination date or a future termination date both satisfy this requirement
- A departure is counted as a termination only when TERMINATION_DATE falls within the specified reporting window (inclusive on both boundaries)
- Current headcount reflects employees whose EMPLOYMENT_STATUS is 'ACTIVE' at query time, not as of a historical snapshot date
- A departure is classified as voluntary when TERMINATION_REASON = 'VOLUNTARY', indicating the employee resigned or chose to leave
- A departure is classified as involuntary when TERMINATION_REASON is any value other than 'VOLUNTARY', covering layoffs, dismissals, and other employer-initiated separations
- Only departments that had at least one employee hired on or before the period end date are shown; departments with no historical headcount are suppressed from the report
- Gross pay is the sum of all payroll lines with ELEMENT_TYPE = 'EARNING'; deduction, benefit, and tax lines are excluded from the gross total
- Total deductions aggregates all lines classified as ELEMENT_TYPE 'DEDUCTION' or 'BENEFIT'; ABS() is applied because these amounts are stored as negative values in PAYROLL_DETAILS
- Payroll lines with STATUS = 'ERROR' are excluded from all totals; only successfully processed lines contribute to departmental payroll figures
- EEO gender breakdown uses three declared codes — 'M' (male), 'F' (female), 'O' (other/non-binary) — plus a separate count for employees who have not disclosed gender
- Employees with a NULL gender value are counted separately as 'not disclosed' and are not rolled into the male, female, or other gender totals
- Only employees hired on or before the reporting snapshot date are counted; future-dated hires are excluded from the compliance figures

**Constraints (4):**
- Payroll element ID 100 is the hard-coded identifier for Federal Income Tax withholding
- Payroll element ID 101 is the hard-coded identifier for State Income Tax withholding
- Payroll element ID 102 is the hard-coded identifier for Social Security (FICA) withholding
- Payroll element ID 103 is the hard-coded identifier for Medicare withholding

**Procedures (8):**
- `headcount_report(p_cursor, p_as_of_date, p_dept_id, p_location)`
- `compensation_summary(p_cursor, p_dept_id, p_grade_id)`
- `turnover_report(p_cursor, p_start_date, p_end_date, p_dept_id)`
- `new_hires_report(p_cursor, p_start_date, p_end_date, p_dept_id)`
- `leave_utilization_report(p_cursor, p_year)`
- `payroll_summary_report(p_cursor, p_period_id)`
- `eeo_compliance_report(p_cursor, p_as_of_date)`
- `refresh_reporting_tables(p_user)`

**Tables accessed (7):** ALL, DIFFERENT, EMPLOYEES, LEAVE_BALANCES, PAYROLL_DETAILS, THE, UTILISATION

### HRMS.PKG_SECURITY
**Known Issues:**
- - Password stored as MD5 hash (should be bcrypt/scrypt)
- - Session timeout check uses DB server time, not app server time
- - No account lockout after failed attempts
- - DBMS_CRYPTO key hard-coded in package body

**Constants (1):**
- `c_session_timeout_min` = `30` — Session inactivity timeout is fixed at 30 minutes; sessions older than this threshold are automatically expired

**Business Rules (2):**
- Only employees with EMPLOYMENT_STATUS = 'ACTIVE' are eligible to authenticate; terminated, suspended, or otherwise inactive employees are excluded
- When multiple active employees share the same email address, the employee with the lowest EMP_ID is selected as the authenticated user

**Validation Rules (13):**
- Authentication is rejected with a generic message when no active employee is found for the supplied email, preventing username enumeration
- A session is only considered valid when SESSION_STATUS is exactly 'ACTIVE'; any other status (e.g. 'CLOSED', 'EXPIRED') immediately invalidates the session
- A session is automatically expired and invalidated if more than 30 minutes have elapsed since the login time
- Employees at job grade 8 or above are granted full access to every module and every action without further restriction
- Employees at job grade 5 or above may perform VIEW actions on any module regardless of their department
- All employees regardless of job grade are permitted to create and view their own leave requests in the LEAVE module
- All employees regardless of job grade are permitted to view their own record in the EMPLOYEE module
- A new password must be at least 8 characters long; shorter passwords are rejected before any update is applied
- Password change is blocked when the new password contains fewer than 8 characters
- A new password must contain at least one uppercase letter; passwords composed entirely of lowercase characters are rejected
- Password change is blocked when the new password contains no uppercase letters
- A new password must contain at least one numeric digit; passwords with no numbers are rejected
- Password change is blocked when the new password contains no numeric digits

**Constraints (4):**
- Session inactivity timeout is fixed at 30 minutes; sessions older than this threshold are automatically expired
- Job grade 8 is the minimum threshold for unrestricted (senior management) access to all modules and actions
- Job grade 5 is the minimum threshold for read-only access across all modules
- Minimum allowable password length is 8 characters

**Error Codes (4):**
- `-20301`: Invalid username or password
- `-20310`: Password must be at least 8 characters
- `-20311`: Password must contain an uppercase letter
- `-20312`: Password must contain a number

**Procedures (2):**
- `logout(p_session_id)`
- `change_password(p_emp_id, p_old_password, p_new_password)`

**Functions (6):**
- `authenticate(p_username, p_password, p_ip_address) RETURN NUMBER`
- `is_session_valid(p_session_id) RETURN BOOLEAN`
- `has_permission(p_emp_id, p_module, p_action) RETURN BOOLEAN`
- `encrypt_ssn(p_ssn) RETURN VARCHAR2`
- `decrypt_ssn(p_encrypted) RETURN VARCHAR2`
- `hash_password(p_password) RETURN VARCHAR2`

**Tables accessed (4):** EMPLOYEES, IS, USER_SESSIONS, WOULD

**Sequences used:** SEQ_USER_SESSION

### HRMS.PKG_VALIDATION

**Business Rules (2):**
- Look up the minimum and maximum salary boundaries defined for the specified job grade
- Only active holidays (ACTIVE_FLAG = 'Y') that apply globally (LOCATION_CODE IS NULL) or match the specific location block a date from being a business day

**Validation Rules (11):**
- Both start date and end date must be provided; a null in either makes the range invalid
- End date must be on or after start date for a valid date range
- Both salary amount and job grade must be supplied before salary validation can proceed
- Salary must not fall below the minimum pay band defined for the employee's job grade
- Salary must not exceed the maximum pay band defined for the employee's job grade
- Employee number must follow the format EMP- followed by exactly 6 digits (e.g. EMP-001234)
- A date qualifies as a future date only if its calendar day is strictly after today; same-day dates are not considered future
- Saturday and Sunday are never valid business days regardless of location or holiday configuration
- A weekday is a valid business day only when no active holiday record exists for that date and location
- Required-field validation is currently only implemented for the EMPLOYEES table; other tables pass through without checks
- An employee record must have First Name, Last Name, Hire Date, Department, and Job Title populated before it is considered complete

**Functions (8):**
- `validate_date_range(p_start_date, p_end_date) RETURN BOOLEAN`
- `validate_salary_for_grade(p_salary, p_grade_id) RETURN VARCHAR2`
- `validate_email_format(p_email) RETURN BOOLEAN`
- `validate_phone_format(p_phone) RETURN BOOLEAN`
- `validate_emp_number_format(p_emp_number) RETURN BOOLEAN`
- `is_future_date(p_date) RETURN BOOLEAN`
- `is_business_day(p_date, p_location_code) RETURN BOOLEAN`
- `validate_required_fields(p_table_name, p_record_id) RETURN VARCHAR2`

**Tables accessed (4):** BEING, EMPLOYEES, HOLIDAYS, JOB_GRADES

---

## Oracle Forms — Deep Extraction

### HRMS_EMPLOYEE — HRMS - Employee Maintenance
- **First block:** EMPLOYEE
- **Libraries:** HRMS_COMMON_LIB, HRMS_VALIDATION_LIB

**Blocks (2):**

#### Block: EMPLOYEE
- Table: `HRMS.EMPLOYEES`
- Items (31): EMP_ID, EMP_NUMBER, FIRST_NAME, LAST_NAME, DATE_OF_BIRTH, GENDER, MARITAL_STATUS, EMAIL, PHONE_WORK, PHONE_MOBILE
- Triggers (4): PRE-INSERT, PRE-UPDATE, POST-QUERY, WHEN-VALIDATE-ITEM

#### Block: SALARY
- Items (7): SALARY_ID, EMP_ID, EFFECTIVE_DATE, END_DATE, BASE_SALARY, CHANGE_REASON, CHANGE_PCT

**Form Triggers (3):**
- `WHEN-NEW-FORM-INSTANCE` — pkg calls: PKG_SECURITY.has_permission, PKG_SECURITY.is_session_valid
- `ON-ERROR` — pkg calls: none
- `KEY-EXIT` — pkg calls: none

**Record Groups / LOV Queries (4):**

**All package calls:** PKG_EMPLOYEE.generate_emp_number, PKG_SECURITY.has_permission, PKG_SECURITY.is_session_valid, PKG_VALIDATION.validate_email_format

### HRMS_LEAVE — HRMS - Leave Management
- **First block:** LEAVE_REQUEST
- **Libraries:** HRMS_COMMON_LIB

**Blocks (3):**

#### Block: LEAVE_REQUEST
- Items (9): REQUEST_ID, EMP_ID, LEAVE_TYPE_NAME_DISP, START_DATE, END_DATE, TOTAL_DAYS, STATUS, REASON, BTN_CANCEL_REQUEST
- Triggers (2): WHEN-BUTTON-PRESSED, POST-QUERY

#### Block: NEW_REQUEST
- Items (9): NR_LEAVE_TYPE_ID, NR_LEAVE_TYPE_DISP, NR_START_DATE, NR_END_DATE, NR_HALF_DAY, NR_REASON, NR_CALC_DAYS, NR_BALANCE_DISP, BTN_SUBMIT
- Triggers (1): WHEN-BUTTON-PRESSED

#### Block: LEAVE_BALANCE
- Items (6): LEAVE_TYPE_NAME_DISP, OPENING_BALANCE, ACCRUED, USED, PENDING, AVAILABLE

**Form Triggers (1):**
- `WHEN-NEW-FORM-INSTANCE` — pkg calls: PKG_SECURITY.is_session_valid

**Record Groups / LOV Queries (1):**

**All package calls:** PKG_LEAVE.cancel_leave_request, PKG_LEAVE.submit_leave_request, PKG_SECURITY.is_session_valid

### HRMS_LOGIN — HRMS - Login
- **First block:** LOGIN
- **Libraries:** 

**Blocks (1):**

#### Block: LOGIN
- Items (5): COMPANY_LOGO, USERNAME, PASSWORD, ERROR_MSG, BTN_LOGIN
- Triggers (2): WHEN-BUTTON-PRESSED, KEY-NEXT-ITEM

**Form Triggers (1):**
- `WHEN-NEW-FORM-INSTANCE` — pkg calls: none

**All package calls:** PKG_SECURITY.authenticate

### HRMS_MENU — HRMS - Main Menu
- **First block:** MENU_CONTROL
- **Libraries:** HRMS_COMMON_LIB

**Blocks (1):**

#### Block: MENU_CONTROL
- Items (8): WELCOME_TEXT, USER_INFO, BTN_EMPLOYEES, BTN_PAYROLL, BTN_LEAVE, BTN_PERFORMANCE, BTN_REPORTS, BTN_LOGOUT
- Triggers (6): WHEN-BUTTON-PRESSED, WHEN-BUTTON-PRESSED, WHEN-BUTTON-PRESSED, WHEN-BUTTON-PRESSED, WHEN-BUTTON-PRESSED, WHEN-BUTTON-PRESSED

**Form Triggers (1):**
- `WHEN-NEW-FORM-INSTANCE` — pkg calls: PKG_SECURITY.has_permission

**All package calls:** PKG_SECURITY.has_permission, PKG_SECURITY.logout

### HRMS_PAYROLL — HRMS - Payroll Processing
- **First block:** PAY_PERIOD
- **Libraries:** HRMS_COMMON_LIB

**Blocks (2):**

#### Block: PAY_PERIOD
- Items (6): PERIOD_ID, PERIOD_NAME, PERIOD_START_DATE, PERIOD_END_DATE, PAY_DATE, STATUS

#### Block: PAYROLL_RUN
- Items (11): RUN_ID, PERIOD_ID, RUN_TYPE, RUN_DATE, STATUS, EMPLOYEE_COUNT, TOTAL_GROSS, TOTAL_NET, BTN_CREATE_RUN, BTN_CALCULATE
- Triggers (3): WHEN-BUTTON-PRESSED, WHEN-BUTTON-PRESSED, WHEN-BUTTON-PRESSED

**Form Triggers (1):**
- `WHEN-NEW-FORM-INSTANCE` — pkg calls: PKG_SECURITY.has_permission, PKG_SECURITY.is_session_valid

**All package calls:** PKG_PAYROLL.approve_payroll, PKG_PAYROLL.calculate_payroll, PKG_PAYROLL.create_payroll_run, PKG_SECURITY.has_permission, PKG_SECURITY.is_session_valid

### HRMS_PERFORMANCE — HRMS - Performance Management
- **First block:** REVIEW_CYCLE
- **Libraries:** HRMS_COMMON_LIB

**Blocks (3):**

#### Block: REVIEW_CYCLE
- Items (6): CYCLE_ID, CYCLE_NAME, CYCLE_YEAR, START_DATE, END_DATE, STATUS

#### Block: PERFORMANCE_REVIEW
- Items (9): REVIEW_ID, CYCLE_ID, EMP_ID, EMP_NAME_DISP, STATUS, OVERALL_RATING, RATING_LABEL, SELF_ASSESSMENT, MANAGER_ASSESSMENT
- Triggers (1): POST-QUERY

#### Block: PERFORMANCE_GOAL
- Items (7): GOAL_ID, REVIEW_ID, GOAL_TITLE, GOAL_CATEGORY, WEIGHT_PCT, PROGRESS_PCT, STATUS

**Form Triggers (1):**
- `WHEN-NEW-FORM-INSTANCE` — pkg calls: PKG_SECURITY.is_session_valid

**All package calls:** PKG_SECURITY.is_session_valid

---

## DDL Tables — Deep Extraction

### HRMS.AUDIT_LOG
- **Columns (10):** AUDIT_ID, TABLE_NAME, RECORD_ID, ACTION_TYPE, OLD_VALUES, NEW_VALUES, CHANGED_BY, CHANGED_DATE, IP_ADDRESS, SESSION_ID
- **Primary Key:** AUDIT_ID
- **CHECK:** `ACTION_TYPE IN ('INSERT', 'UPDATE', 'DELETE'`

### HRMS.DEPARTMENTS
- **Columns (12):** DEPT_ID, DEPT_CODE, DEPT_NAME, PARENT_DEPT_ID, COST_CENTER, MANAGER_EMP_ID, LOCATION_CODE, ACTIVE_FLAG, CREATED_BY, CREATED_DATE, MODIFIED_BY, MODIFIED_DATE
- **Primary Key:** DEPT_ID
- **CHECK:** `ACTIVE_FLAG IN ('Y', 'N'`

### HRMS.EMERGENCY_CONTACTS
- **Columns (13):** CONTACT_ID, EMP_ID, CONTACT_NAME, RELATIONSHIP, PHONE_PRIMARY, PHONE_SECONDARY, EMAIL, PRIORITY_ORDER, ACTIVE_FLAG, CREATED_BY, CREATED_DATE, MODIFIED_BY, MODIFIED_DATE
- **Primary Key:** CONTACT_ID
- **FK** `EMP_ID` → `HRMS.EMPLOYEES(EMP_ID)`

### HRMS.EMPLOYEES
- **Columns (35):** EMP_ID, EMP_NUMBER, FIRST_NAME, MIDDLE_NAME, LAST_NAME, DATE_OF_BIRTH, GENDER, MARITAL_STATUS, NATIONALITY, SSN_ENCRYPTED, EMAIL, PHONE_WORK, PHONE_MOBILE, ADDRESS_LINE1, ADDRESS_LINE2
- **Primary Key:** EMP_ID
- **FK** `DEPT_ID` → `HRMS.DEPARTMENTS(DEPT_ID)`
- **FK** `JOB_ID` → `HRMS.JOB_TITLES(JOB_ID)`
- **FK** `MANAGER_EMP_ID` → `HRMS.EMPLOYEES(EMP_ID)`
- **FK** `LOCATION_CODE` → `HRMS.LOCATIONS(LOCATION_CODE)`
- **CHECK:** `EMPLOYMENT_STATUS IN ('ACTIVE', 'ON_LEAVE', 'SUSPENDED', 'TERMINATED'`
- **CHECK:** `EMPLOYMENT_TYPE IN ('FULL_TIME', 'PART_TIME', 'CONTRACT', 'INTERN'`
- **CHECK:** `GENDER IN ('M', 'F', 'O'`

### HRMS.EMPLOYEE_BANK_ACCOUNTS
- **Columns (17):** BANK_ACCT_ID, EMP_ID, BANK_NAME, ROUTING_NUMBER, ACCOUNT_NUMBER_ENC, ACCOUNT_TYPE, DEPOSIT_TYPE, DEPOSIT_AMOUNT, DEPOSIT_PERCENTAGE, PRIORITY_ORDER, PRENOTE_SENT, PRENOTE_DATE, ACTIVE_FLAG, CREATED_BY, CREATED_DATE
- **Primary Key:** BANK_ACCT_ID
- **FK** `EMP_ID` → `HRMS.EMPLOYEES(EMP_ID)`
- **CHECK:** `ACCOUNT_TYPE IN ('CHECKING', 'SAVINGS'`
- **CHECK:** `DEPOSIT_TYPE IN ('FULL', 'PARTIAL_AMOUNT', 'PARTIAL_PERCENT', 'REMAINDER'`

### HRMS.EMPLOYEE_DEPENDENTS
- **Columns (13):** DEPENDENT_ID, EMP_ID, FIRST_NAME, LAST_NAME, RELATIONSHIP, DATE_OF_BIRTH, SSN_ENCRYPTED, BENEFITS_ENROLLED, ACTIVE_FLAG, CREATED_BY, CREATED_DATE, MODIFIED_BY, MODIFIED_DATE
- **Primary Key:** DEPENDENT_ID
- **FK** `EMP_ID` → `HRMS.EMPLOYEES(EMP_ID)`
- **CHECK:** `RELATIONSHIP IN ('SPOUSE', 'CHILD', 'PARENT', 'DOMESTIC_PARTNER', 'OTHER'`

### HRMS.EMPLOYEE_HISTORY
- **Columns (18):** HIST_ID, EMP_ID, CHANGE_TYPE, EFFECTIVE_DATE, OLD_DEPT_ID, NEW_DEPT_ID, OLD_JOB_ID, NEW_JOB_ID, OLD_MANAGER_ID, NEW_MANAGER_ID, OLD_SALARY, NEW_SALARY, OLD_LOCATION, NEW_LOCATION, REASON_CODE
- **Primary Key:** HIST_ID
- **FK** `EMP_ID` → `HRMS.EMPLOYEES(EMP_ID)`
- **CHECK:** `CHANGE_TYPE IN (
        'HIRE', 'TRANSFER', 'PROMOTION', 'DEMOTION', 'SALARY_CHANGE',
        'TERMINATION', 'REHIRE', 'LEAVE_START', 'LEAVE_END', 'STATUS_CHANGE'
    `

### HRMS.EMPLOYEE_PAY_ELEMENTS
- **Columns (13):** EMP_ELEMENT_ID, EMP_ID, ELEMENT_ID, EFFECTIVE_DATE, END_DATE, AMOUNT, PERCENTAGE, OVERRIDE_AMOUNT, ACTIVE_FLAG, CREATED_BY, CREATED_DATE, MODIFIED_BY, MODIFIED_DATE
- **Primary Key:** EMP_ELEMENT_ID
- **FK** `EMP_ID` → `HRMS.EMPLOYEES(EMP_ID)`
- **FK** `ELEMENT_ID` → `HRMS.PAY_ELEMENTS(ELEMENT_ID)`

### HRMS.EMPLOYEE_TAX_INFO
- **Columns (16):** TAX_INFO_ID, EMP_ID, TAX_YEAR, FILING_STATUS, FEDERAL_ALLOWANCES, STATE_ALLOWANCES, ADDITIONAL_FED_WH, ADDITIONAL_STATE_WH, EXEMPT_FLAG, STATE_CODE, W4_RECEIVED_DATE, ACTIVE_FLAG, CREATED_BY, CREATED_DATE, MODIFIED_BY
- **Primary Key:** TAX_INFO_ID
- **FK** `EMP_ID` → `HRMS.EMPLOYEES(EMP_ID)`

### HRMS.HOLIDAYS
- **Columns (8):** HOLIDAY_ID, HOLIDAY_DATE, HOLIDAY_NAME, LOCATION_CODE, FLOATING_FLAG, ACTIVE_FLAG, CREATED_BY, CREATED_DATE
- **Primary Key:** HOLIDAY_ID

### HRMS.JOB_GRADES
- **Columns (11):** GRADE_ID, GRADE_CODE, GRADE_NAME, MIN_SALARY, MAX_SALARY, OVERTIME_ELIGIBLE, ACTIVE_FLAG, CREATED_BY, CREATED_DATE, MODIFIED_BY, MODIFIED_DATE
- **Primary Key:** GRADE_ID
- **CHECK:** `MAX_SALARY >= MIN_SALARY`

### HRMS.JOB_TITLES
- **Columns (12):** JOB_ID, JOB_CODE, JOB_TITLE, JOB_FAMILY, GRADE_ID, EEO_CATEGORY, FLSA_STATUS, ACTIVE_FLAG, CREATED_BY, CREATED_DATE, MODIFIED_BY, MODIFIED_DATE
- **Primary Key:** JOB_ID
- **FK** `GRADE_ID` → `HRMS.JOB_GRADES(GRADE_ID)`

### HRMS.LEAVE_ACCRUAL_LOG
- **Columns (9):** ACCRUAL_ID, EMP_ID, LEAVE_TYPE_ID, ACCRUAL_DATE, ACCRUAL_AMOUNT, BALANCE_AFTER, RUN_ID, CREATED_BY, CREATED_DATE
- **Primary Key:** ACCRUAL_ID
- **FK** `EMP_ID` → `HRMS.EMPLOYEES(EMP_ID)`
- **FK** `LEAVE_TYPE_ID` → `HRMS.LEAVE_TYPES(LEAVE_TYPE_ID)`

### HRMS.LEAVE_BALANCES
- **Columns (15):** BALANCE_ID, EMP_ID, LEAVE_TYPE_ID, CALENDAR_YEAR, OPENING_BALANCE, ACCRUED, USED, ADJUSTMENT, PENDING, CARRYOVER_FROM_PREV, CARRYOVER_EXPIRY_DT, CREATED_BY, CREATED_DATE, MODIFIED_BY, MODIFIED_DATE
- **Primary Key:** BALANCE_ID
- **FK** `EMP_ID` → `HRMS.EMPLOYEES(EMP_ID)`
- **FK** `LEAVE_TYPE_ID` → `HRMS.LEAVE_TYPES(LEAVE_TYPE_ID)`

### HRMS.LEAVE_REQUESTS
- **Columns (20):** REQUEST_ID, EMP_ID, LEAVE_TYPE_ID, START_DATE, END_DATE, TOTAL_DAYS, HALF_DAY_FLAG, HALF_DAY_PERIOD, STATUS, REASON, SUPPORTING_DOC_PATH, APPROVER_EMP_ID, APPROVAL_DATE, APPROVAL_COMMENTS, CANCEL_REASON
- **Primary Key:** REQUEST_ID
- **FK** `EMP_ID` → `HRMS.EMPLOYEES(EMP_ID)`
- **FK** `LEAVE_TYPE_ID` → `HRMS.LEAVE_TYPES(LEAVE_TYPE_ID)`
- **FK** `APPROVER_EMP_ID` → `HRMS.EMPLOYEES(EMP_ID)`
- **CHECK:** `STATUS IN ('PENDING', 'APPROVED', 'REJECTED', 'CANCELLED', 'TAKEN'`
- **CHECK:** `END_DATE >= START_DATE`
- **CHECK:** `HALF_DAY_PERIOD IN ('AM', 'PM', NULL`

### HRMS.LEAVE_TYPES
- **Columns (18):** LEAVE_TYPE_ID, LEAVE_TYPE_CODE, LEAVE_TYPE_NAME, PAID_FLAG, ACCRUAL_FLAG, ACCRUAL_RATE, ACCRUAL_FREQUENCY, MAX_BALANCE, CARRYOVER_MAX, CARRYOVER_EXPIRY, MIN_TENURE_DAYS, REQUIRES_APPROVAL, REQUIRES_DOCUMENT, ACTIVE_FLAG, CREATED_BY
- **Primary Key:** LEAVE_TYPE_ID
- **CHECK:** `ACCRUAL_FREQUENCY IN ('MONTHLY', 'BIWEEKLY', 'ANNUAL', NULL`

### HRMS.LOCATIONS
- **Columns (15):** LOCATION_CODE, LOCATION_NAME, ADDRESS_LINE1, ADDRESS_LINE2, CITY, STATE_PROVINCE, POSTAL_CODE, COUNTRY_CODE, PHONE_NUMBER, TIMEZONE, ACTIVE_FLAG, CREATED_BY, CREATED_DATE, MODIFIED_BY, MODIFIED_DATE
- **Primary Key:** LOCATION_CODE

### HRMS.LOOKUP_VALUES
- **Columns (9):** LOOKUP_ID, LOOKUP_TYPE, LOOKUP_CODE, LOOKUP_VALUE, DISPLAY_ORDER, PARENT_LOOKUP_ID, ACTIVE_FLAG, CREATED_BY, CREATED_DATE
- **Primary Key:** LOOKUP_ID

### HRMS.NOTIFICATION_QUEUE
- **Columns (15):** NOTIFICATION_ID, RECIPIENT_EMP_ID, RECIPIENT_EMAIL, NOTIFICATION_TYPE, SUBJECT, BODY, STATUS, PRIORITY, SENT_DATE, ERROR_MESSAGE, RETRY_COUNT, REFERENCE_TABLE, REFERENCE_ID, CREATED_BY, CREATED_DATE
- **Primary Key:** NOTIFICATION_ID
- **CHECK:** `STATUS IN ('PENDING', 'SENT', 'FAILED', 'CANCELLED'`
- **CHECK:** `NOTIFICATION_TYPE IN ('EMAIL', 'IN_APP', 'SMS'`

### HRMS.PAYROLL_DETAILS
- **Columns (13):** DETAIL_ID, RUN_ID, EMP_ID, ELEMENT_ID, ELEMENT_TYPE, HOURS_WORKED, RATE, AMOUNT, YTD_AMOUNT, STATUS, ERROR_MESSAGE, CREATED_BY, CREATED_DATE
- **Primary Key:** DETAIL_ID
- **FK** `RUN_ID` → `HRMS.PAYROLL_RUNS(RUN_ID)`
- **FK** `EMP_ID` → `HRMS.EMPLOYEES(EMP_ID)`
- **FK** `ELEMENT_ID` → `HRMS.PAY_ELEMENTS(ELEMENT_ID)`

### HRMS.PAYROLL_RUNS
- **Columns (19):** RUN_ID, PERIOD_ID, RUN_TYPE, RUN_DATE, STATUS, TOTAL_GROSS, TOTAL_DEDUCTIONS, TOTAL_NET, TOTAL_EMPLOYER_COST, EMPLOYEE_COUNT, ERROR_COUNT, SUBMITTED_BY, SUBMITTED_DATE, APPROVED_BY, APPROVED_DATE
- **Primary Key:** RUN_ID
- **FK** `PERIOD_ID` → `HRMS.PAY_PERIODS(PERIOD_ID)`
- **CHECK:** `RUN_TYPE IN ('REGULAR', 'SUPPLEMENTAL', 'BONUS', 'FINAL'`
- **CHECK:** `STATUS IN ('PENDING', 'CALCULATING', 'CALCULATED', 'APPROVED', 'PAID', 'REVERSED', 'ERROR'`

### HRMS.PAY_ELEMENTS
- **Columns (17):** ELEMENT_ID, ELEMENT_CODE, ELEMENT_NAME, ELEMENT_TYPE, CALCULATION_TYPE, DEFAULT_AMOUNT, DEFAULT_PERCENTAGE, TAXABLE_FLAG, PRETAX_FLAG, EMPLOYER_PAID, GL_ACCOUNT_CODE, PRIORITY_ORDER, ACTIVE_FLAG, CREATED_BY, CREATED_DATE
- **Primary Key:** ELEMENT_ID
- **CHECK:** `ELEMENT_TYPE IN ('EARNING', 'DEDUCTION', 'TAX', 'BENEFIT', 'REIMBURSEMENT'`
- **CHECK:** `CALCULATION_TYPE IN ('FLAT', 'PERCENTAGE', 'HOURS', 'FORMULA'`

### HRMS.PAY_PERIODS
- **Columns (13):** PERIOD_ID, PERIOD_NAME, PAY_FREQUENCY, PERIOD_START_DATE, PERIOD_END_DATE, PAY_DATE, STATUS, CLOSED_BY, CLOSED_DATE, CREATED_BY, CREATED_DATE, MODIFIED_BY, MODIFIED_DATE
- **Primary Key:** PERIOD_ID
- **CHECK:** `STATUS IN ('OPEN', 'PROCESSING', 'CLOSED', 'REVERSED'`

### HRMS.PERFORMANCE_GOALS
- **Columns (17):** GOAL_ID, REVIEW_ID, EMP_ID, GOAL_TITLE, GOAL_DESCRIPTION, GOAL_CATEGORY, WEIGHT_PCT, TARGET_DATE, STATUS, PROGRESS_PCT, SELF_RATING, MANAGER_RATING, COMMENTS, CREATED_BY, CREATED_DATE
- **Primary Key:** GOAL_ID
- **FK** `REVIEW_ID` → `HRMS.PERFORMANCE_REVIEWS(REVIEW_ID)`
- **FK** `EMP_ID` → `HRMS.EMPLOYEES(EMP_ID)`
- **CHECK:** `STATUS IN ('NOT_STARTED', 'IN_PROGRESS', 'COMPLETED', 'DEFERRED', 'CANCELLED'`
- **CHECK:** `GOAL_CATEGORY IN ('BUSINESS', 'DEVELOPMENT', 'LEADERSHIP', 'INNOVATION', 'COMPLIANCE'`

### HRMS.PERFORMANCE_REVIEWS
- **Columns (21):** REVIEW_ID, CYCLE_ID, EMP_ID, REVIEWER_EMP_ID, REVIEW_TYPE, STATUS, OVERALL_RATING, RATING_LABEL, SELF_ASSESSMENT, MANAGER_ASSESSMENT, STRENGTHS, AREAS_FOR_IMPROVEMENT, DEVELOPMENT_PLAN, EMPLOYEE_COMMENTS, EMPLOYEE_ACK_DATE
- **Primary Key:** REVIEW_ID
- **FK** `CYCLE_ID` → `HRMS.REVIEW_CYCLES(CYCLE_ID)`
- **FK** `EMP_ID` → `HRMS.EMPLOYEES(EMP_ID)`
- **FK** `REVIEWER_EMP_ID` → `HRMS.EMPLOYEES(EMP_ID)`
- **CHECK:** `STATUS IN ('NOT_STARTED', 'SELF_REVIEW', 'MANAGER_REVIEW', 'MEETING_SCHEDULED', 'COMPLETED', 'ACKNOWLEDGED'`
- **CHECK:** `OVERALL_RATING BETWEEN 1.0 AND 5.0`

### HRMS.REVIEW_CYCLES
- **Columns (13):** CYCLE_ID, CYCLE_NAME, CYCLE_YEAR, START_DATE, END_DATE, SELF_REVIEW_DUE, MANAGER_REVIEW_DUE, CALIBRATION_DUE, STATUS, CREATED_BY, CREATED_DATE, MODIFIED_BY, MODIFIED_DATE
- **Primary Key:** CYCLE_ID
- **CHECK:** `STATUS IN ('DRAFT', 'OPEN', 'IN_PROGRESS', 'CALIBRATION', 'CLOSED'`

### HRMS.SALARY_RECORDS
- **Columns (17):** SALARY_ID, EMP_ID, EFFECTIVE_DATE, END_DATE, BASE_SALARY, CURRENCY_CODE, PAY_FREQUENCY, SALARY_BASIS, CHANGE_REASON, CHANGE_PCT, APPROVED_BY, APPROVAL_DATE, ACTIVE_FLAG, CREATED_BY, CREATED_DATE
- **Primary Key:** SALARY_ID
- **FK** `EMP_ID` → `HRMS.EMPLOYEES(EMP_ID)`
- **CHECK:** `PAY_FREQUENCY IN ('WEEKLY', 'BIWEEKLY', 'SEMIMONTHLY', 'MONTHLY'`
- **CHECK:** `SALARY_BASIS IN ('ANNUAL', 'HOURLY'`

### HRMS.SYSTEM_PARAMETERS
- **Columns (11):** PARAM_ID, PARAM_GROUP, PARAM_CODE, PARAM_VALUE, PARAM_DESCRIPTION, DATA_TYPE, EDITABLE_FLAG, CREATED_BY, CREATED_DATE, MODIFIED_BY, MODIFIED_DATE
- **Primary Key:** PARAM_ID

### HRMS.TAX_BRACKETS
- **Columns (11):** BRACKET_ID, TAX_YEAR, FILING_STATUS, BRACKET_MIN, BRACKET_MAX, TAX_RATE, BASE_TAX, STATE_CODE, ACTIVE_FLAG, CREATED_BY, CREATED_DATE
- **Primary Key:** BRACKET_ID
- **CHECK:** `FILING_STATUS IN ('SINGLE', 'MARRIED_JOINT', 'MARRIED_SEPARATE', 'HEAD_OF_HOUSEHOLD'`

### HRMS.USER_SESSIONS
- **Columns (9):** SESSION_ID, EMP_ID, USERNAME, LOGIN_TIME, LOGOUT_TIME, IP_ADDRESS, FORMS_MODULE, SESSION_STATUS, CREATED_DATE
- **Primary Key:** SESSION_ID
- **FK** `EMP_ID` → `HRMS.EMPLOYEES(EMP_ID)`

---

## Consolidated Business Rules

Total: 581 rules extracted from all source files

| ID | Source | Type | Rule |
|---|---|---|---|
| BR-0001 | HRMS.PKG_COMMON | business_rule | Only system parameters explicitly flagged as editable (EDITABLE_FLAG = 'Y') may be modified; parameters marked non-edita |
| BR-0002 | HRMS.PKG_COMMON | business_rule | _days_between |
| BR-0003 | HRMS.PKG_COMMON | validation_rule | A parameter update must match exactly one editable row; if zero rows are updated the parameter either does not exist in  |
| BR-0004 | HRMS.PKG_COMMON | validation_rule | Attempting to modify a non-existent or non-editable system parameter is a fatal error; callers must not silently ignore  |
| BR-0005 | HRMS.PKG_COMMON | validation_rule | Saturday and Sunday are not counted as business days; only Monday through Friday increment the business day counter |
| BR-0006 | HRMS.PKG_COMMON | validation_rule | Saturday and Sunday are skipped when advancing by business days; only weekdays (Monday through Friday) count toward the  |
| BR-0007 | HRMS.PKG_COMMON | validation_rule | A date falling in October or later belongs to the fiscal year of the following calendar year (e.g. October 2024 is in fi |
| BR-0008 | HRMS.PKG_COMMON | validation_rule | Fiscal quarters follow the October 1 fiscal year start: Q1 = October–December, Q2 = January–March, Q3 = April–June, Q4 = |
| BR-0009 | HRMS.PKG_COMMON | validation_rule | A 10-digit number is formatted as a US domestic number in (NXX) NXX-XXXX notation |
| BR-0010 | HRMS.PKG_COMMON | validation_rule | An 11-digit number starting with '1' is formatted as a US/Canada international number with a +1 prefix; all other length |
| BR-0011 | HRMS.PKG_COMMON | validation_rule | A null SSN or one with fewer than 4 characters cannot be partially unmasked; the entire value is replaced with the full  |
| BR-0012 | HRMS.PKG_COMMON | validation_rule | Format code 'LF' produces "Last, First" display order; any other value (including the default 'FL') produces "First Last |
| BR-0013 | HRMS.PKG_COMMON | constraint | The fiscal year boundary is month 10 (October); the organisation's fiscal year begins on October 1 |
| BR-0014 | HRMS.PKG_COMMON | constraint | A standard US domestic phone number must contain exactly 10 digits |
| BR-0015 | HRMS.PKG_COMMON | constraint | An 11-digit phone number is only recognised as a valid US/Canada international number if it begins with country code '1' |
| BR-0016 | HRMS.PKG_COMMON | constraint | An SSN must have at least 4 characters for the last-four-digit display to be meaningful |
| BR-0017 | HRMS.PKG_COMMON.set_param | business_rule | Only system parameters explicitly flagged as editable (EDITABLE_FLAG = 'Y') may be modified; parameters marked non-edita |
| BR-0018 | HRMS.PKG_COMMON.set_param | business_rule | _days_between |
| BR-0019 | HRMS.PKG_COMMON.set_param | validation_rule | A parameter update must match exactly one editable row; if zero rows are updated the parameter either does not exist in  |
| BR-0020 | HRMS.PKG_COMMON.set_param | validation_rule | Attempting to modify a non-existent or non-editable system parameter is a fatal error; callers must not silently ignore  |
| BR-0021 | HRMS.PKG_COMMON.set_param | error_rule | Error -20900: Parameter not found or not editable:  |
| BR-0022 | HRMS.PKG_COMMON.business_days_between | validation_rule | Saturday and Sunday are not counted as business days; only Monday through Friday increment the business day counter |
| BR-0023 | HRMS.PKG_COMMON.add_business_days | validation_rule | Saturday and Sunday are skipped when advancing by business days; only weekdays (Monday through Friday) count toward the  |
| BR-0024 | HRMS.PKG_COMMON.get_fiscal_year | validation_rule | A date falling in October or later belongs to the fiscal year of the following calendar year (e.g. October 2024 is in fi |
| BR-0025 | HRMS.PKG_COMMON.get_fiscal_quarter | validation_rule | Fiscal quarters follow the October 1 fiscal year start: Q1 = October–December, Q2 = January–March, Q3 = April–June, Q4 = |
| BR-0026 | HRMS.PKG_COMMON.format_phone | validation_rule | A 10-digit number is formatted as a US domestic number in (NXX) NXX-XXXX notation |
| BR-0027 | HRMS.PKG_COMMON.format_phone | validation_rule | An 11-digit number starting with '1' is formatted as a US/Canada international number with a +1 prefix; all other length |
| BR-0028 | HRMS.PKG_COMMON.format_ssn_masked | validation_rule | A null SSN or one with fewer than 4 characters cannot be partially unmasked; the entire value is replaced with the full  |
| BR-0029 | HRMS.PKG_COMMON.format_name | validation_rule | Format code 'LF' produces "Last, First" display order; any other value (including the default 'FL') produces "First Last |
| BR-0030 | HRMS.PKG_EMPLOYEE | business_rule | Only departments flagged as active (ACTIVE_FLAG = 'Y') are considered valid for employee assignment |
| BR-0031 | HRMS.PKG_EMPLOYEE | business_rule | Only employees with EMPLOYMENT_STATUS = 'ACTIVE' are eligible to be assigned as a manager |
| BR-0032 | HRMS.PKG_EMPLOYEE | business_rule | Only job titles with ACTIVE_FLAG = 'Y' are valid for assignment to a new employee |
| BR-0033 | HRMS.PKG_EMPLOYEE | business_rule | The current salary is the active salary record that became effective on or before today and whose end date is either ope |
| BR-0034 | HRMS.PKG_EMPLOYEE | business_rule | When provided, the status filter restricts search results to employees with the specified EMPLOYMENT_STATUS value (e.g., |
| BR-0035 | HRMS.PKG_EMPLOYEE | business_rule | The most recent active salary record is used as the pre-promotion baseline for computing the percentage salary increase |
| BR-0036 | HRMS.PKG_EMPLOYEE | business_rule | Only leave requests in PENDING status are identified for automatic cancellation upon employee termination |
| BR-0037 | HRMS.PKG_EMPLOYEE | business_rule | Only currently active salary records (ACTIVE_FLAG = 'Y') are closed upon termination; previously ended records are not m |
| BR-0038 | HRMS.PKG_EMPLOYEE | business_rule | Only currently active pay elements (ACTIVE_FLAG = 'Y') are deactivated at termination; previously ended pay elements are |
| BR-0039 | HRMS.PKG_EMPLOYEE | business_rule | Only employees with EMPLOYMENT_STATUS = 'ACTIVE' are returned as direct reports; terminated or inactive employees are ex |
| BR-0040 | HRMS.PKG_EMPLOYEE | business_rule | The org chart hierarchy traversal includes only employees with EMPLOYMENT_STATUS = 'ACTIVE'; terminated employees are ex |
| BR-0041 | HRMS.PKG_EMPLOYEE | business_rule | Headcount counts only employees who were actively employed on the specified as-of date — hired on or before that date an |
| BR-0042 | HRMS.PKG_EMPLOYEE | validation_rule | Department must exist and be active before it can be assigned to an employee |
| BR-0043 | HRMS.PKG_EMPLOYEE | validation_rule | Assigning an inactive or non-existent department to an employee raises an application error |
| BR-0044 | HRMS.PKG_EMPLOYEE | validation_rule | A NULL manager assignment is valid and indicates the employee is at the top of the reporting hierarchy with no manager a |
| BR-0045 | HRMS.PKG_EMPLOYEE | validation_rule | The designated manager must exist in the system and have EMPLOYMENT_STATUS = 'ACTIVE' |
| BR-0046 | HRMS.PKG_EMPLOYEE | validation_rule | Specifying a manager who does not exist or is not currently active raises an application error |
| BR-0047 | HRMS.PKG_EMPLOYEE | validation_rule | When updating an existing employee, the new manager assignment must not create a circular reporting chain |
| BR-0048 | HRMS.PKG_EMPLOYEE | validation_rule | An employee cannot directly or indirectly report to themselves; circular reporting chains are prohibited |
| BR-0049 | HRMS.PKG_EMPLOYEE | validation_rule | Assigning a manager who already reports (directly or indirectly) to this employee creates a circular chain and raises an |
| BR-0050 | HRMS.PKG_EMPLOYEE | validation_rule | Both first name and last name are mandatory fields when creating a new employee record |
| BR-0051 | HRMS.PKG_EMPLOYEE | validation_rule | An employee cannot be created without both a first name and a last name |
| BR-0052 | HRMS.PKG_EMPLOYEE | validation_rule | The job title specified at hire must exist in the JOB_TITLES table and be currently active |
| BR-0053 | HRMS.PKG_EMPLOYEE | validation_rule | Employee starting salary must fall within the minimum and maximum range for their assigned job grade (soft warning — man |
| BR-0054 | HRMS.PKG_EMPLOYEE | validation_rule | A salary record is only created at hire when a starting salary is explicitly provided; employees may be hired without an |
| BR-0055 | HRMS.PKG_EMPLOYEE | validation_rule | Employee numbers must be unique; a duplicate generated during concurrent inserts requires the caller to retry the operat |
| BR-0056 | HRMS.PKG_EMPLOYEE | validation_rule | Employee must exist in the system before their contact or personal information can be updated |
| BR-0057 | HRMS.PKG_EMPLOYEE | validation_rule | Attempting to update a non-existent employee record raises an application error |
| BR-0058 | HRMS.PKG_EMPLOYEE | validation_rule | If the update affects zero rows, an error is raised to signal an unexpected data integrity failure |
| BR-0059 | HRMS.PKG_EMPLOYEE | validation_rule | Zero rows updated after a successful existence check indicates a concurrent deletion between the two operations |
| BR-0060 | HRMS.PKG_EMPLOYEE | validation_rule | Requesting an employee by ID that does not exist in the EMPLOYEES table raises an application error |
| BR-0061 | HRMS.PKG_EMPLOYEE | validation_rule | Requesting an employee by employee number that does not exist in the EMPLOYEES table raises an application error |
| BR-0062 | HRMS.PKG_EMPLOYEE | validation_rule | Only employees with EMPLOYMENT_STATUS = 'ACTIVE' may be transferred; transferring a non-active employee is prohibited |
| BR-0063 | HRMS.PKG_EMPLOYEE | validation_rule | Attempting to transfer an employee who is not in ACTIVE status raises an application error |
| BR-0064 | HRMS.PKG_EMPLOYEE | validation_rule | A new manager for the transfer is validated (including circular-chain detection) only when one is explicitly provided; o |
| BR-0065 | HRMS.PKG_EMPLOYEE | validation_rule | An employee who is already terminated cannot be terminated again; re-termination is blocked |
| BR-0066 | HRMS.PKG_EMPLOYEE | validation_rule | Attempting to terminate an already-terminated employee raises an application error |
| BR-0067 | HRMS.PKG_EMPLOYEE | validation_rule | All pending leave requests for a terminating employee are automatically cancelled; no manual action is required from the |
| BR-0068 | HRMS.PKG_EMPLOYEE | validation_rule | A termination notification is sent to the employee's direct manager only when a manager is assigned; top-level employees |
| BR-0069 | HRMS.PKG_EMPLOYEE | validation_rule | Rehiring an employee overwrites their hire date with the rehire date and clears all prior termination data; the employee |
| BR-0070 | HRMS.PKG_EMPLOYEE | validation_rule | Attempting to rehire an employee ID that does not exist in the EMPLOYEES table raises an application error |
| BR-0071 | HRMS.PKG_EMPLOYEE | validation_rule | An employee is considered active if and only if their EMPLOYMENT_STATUS column value equals 'ACTIVE' |
| BR-0072 | HRMS.PKG_EMPLOYEE | validation_rule | An employee record is considered invalid if either the first name or the last name is absent |
| BR-0073 | HRMS.PKG_EMPLOYEE | validation_rule | An employee record is considered invalid if no hire date has been recorded |
| BR-0074 | HRMS.PKG_EMPLOYEE | validation_rule | An employee record is considered inconsistent if EMPLOYMENT_STATUS is 'ACTIVE' but ACTIVE_FLAG is not 'Y'; both fields m |
| BR-0075 | HRMS.PKG_EMPLOYEE | constraint | The reporting hierarchy is limited to a maximum depth of 15 levels to prevent unbounded traversal during circular refere |
| BR-0076 | HRMS.PKG_EMPLOYEE | constraint | The default maximum depth for org chart traversal is 10 levels; callers may override this, but deeper traversal risks ti |
| BR-0077 | HRMS.PKG_EMPLOYEE | known_bug | race condition under concurrent inserts - no SELECT FOR UPDATE |
| BR-0078 | HRMS.PKG_EMPLOYEE | known_bug | SQL injection possible via p_last_name if called with unvalidated input |
| BR-0079 | HRMS.PKG_EMPLOYEE.validate_dept | business_rule | Only departments flagged as active (ACTIVE_FLAG = 'Y') are considered valid for employee assignment |
| BR-0080 | HRMS.PKG_EMPLOYEE.validate_dept | validation_rule | Department must exist and be active before it can be assigned to an employee |
| BR-0081 | HRMS.PKG_EMPLOYEE.validate_dept | validation_rule | Assigning an inactive or non-existent department to an employee raises an application error |
| BR-0082 | HRMS.PKG_EMPLOYEE.validate_dept | error_rule | Error -20003: Invalid or inactive department:  |
| BR-0083 | HRMS.PKG_EMPLOYEE.validate_manager | business_rule | Only employees with EMPLOYMENT_STATUS = 'ACTIVE' are eligible to be assigned as a manager |
| BR-0084 | HRMS.PKG_EMPLOYEE.validate_manager | validation_rule | A NULL manager assignment is valid and indicates the employee is at the top of the reporting hierarchy with no manager a |
| BR-0085 | HRMS.PKG_EMPLOYEE.validate_manager | validation_rule | The designated manager must exist in the system and have EMPLOYMENT_STATUS = 'ACTIVE' |
| BR-0086 | HRMS.PKG_EMPLOYEE.validate_manager | validation_rule | Specifying a manager who does not exist or is not currently active raises an application error |
| BR-0087 | HRMS.PKG_EMPLOYEE.validate_manager | validation_rule | When updating an existing employee, the new manager assignment must not create a circular reporting chain |
| BR-0088 | HRMS.PKG_EMPLOYEE.validate_manager | validation_rule | An employee cannot directly or indirectly report to themselves; circular reporting chains are prohibited |
| BR-0089 | HRMS.PKG_EMPLOYEE.validate_manager | validation_rule | Assigning a manager who already reports (directly or indirectly) to this employee creates a circular chain and raises an |
| BR-0090 | HRMS.PKG_EMPLOYEE.validate_manager | error_rule | Error -20004: Invalid or inactive manager:  |
| BR-0091 | HRMS.PKG_EMPLOYEE.validate_manager | error_rule | Error -20004: Circular reporting chain detected: Employee  |
| BR-0092 | HRMS.PKG_EMPLOYEE.create_employee | business_rule | Only job titles with ACTIVE_FLAG = 'Y' are valid for assignment to a new employee |
| BR-0093 | HRMS.PKG_EMPLOYEE.create_employee | validation_rule | Both first name and last name are mandatory fields when creating a new employee record |
| BR-0094 | HRMS.PKG_EMPLOYEE.create_employee | validation_rule | An employee cannot be created without both a first name and a last name |
| BR-0095 | HRMS.PKG_EMPLOYEE.create_employee | validation_rule | The job title specified at hire must exist in the JOB_TITLES table and be currently active |
| BR-0096 | HRMS.PKG_EMPLOYEE.create_employee | validation_rule | Employee starting salary must fall within the minimum and maximum range for their assigned job grade (soft warning — man |
| BR-0097 | HRMS.PKG_EMPLOYEE.create_employee | validation_rule | A salary record is only created at hire when a starting salary is explicitly provided; employees may be hired without an |
| BR-0098 | HRMS.PKG_EMPLOYEE.create_employee | validation_rule | Employee numbers must be unique; a duplicate generated during concurrent inserts requires the caller to retry the operat |
| BR-0099 | HRMS.PKG_EMPLOYEE.create_employee | error_rule | Error -20010: First name and last name are required |
| BR-0100 | HRMS.PKG_EMPLOYEE.create_employee | error_rule | Error -20011: Invalid or inactive job:  |

*... and 481 more rules in business_rules.json*