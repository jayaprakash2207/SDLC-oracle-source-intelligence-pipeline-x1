# Oracle Deep Parser Report — HRMS Source Code

## Summary

| Category | Count |
|---|---|
| PL/SQL Packages | 11 |
| Oracle Forms | 6 |
| PLL Libraries | 2 |
| Menu Modules | 1 |
| DDL Tables | 30 |
| Views | 6 |
| DB Triggers | 6 |
| Sequences | 29 |
| Seed rows | 133 |
| Business rules | 106 |
| Validation rules | 491 |
| Error codes | 55 |
| Check constraints | 28 |
| Unique constraints | 10 |
| Known bugs | 15 |
| **Total rules** | **795** |

---

## PL/SQL Packages

### HRMS.PKG_AUDIT

**PRAGMA AUTONOMOUS_TRANSACTION: YES**

**DBMS Packages:** DBMS_OUTPUT

**Validation Rules (3):**
- Package uses PRAGMA AUTONOMOUS_TRANSACTION — writes independent of caller
- Captures client IP via SYS_CONTEXT for audit trail
- Captures Oracle session ID via SYS_CONTEXT for audit trail

### HRMS.PKG_COMMON

**PRAGMA AUTONOMOUS_TRANSACTION: YES**

**DBMS Packages:** DBMS_OUTPUT

**Business Rules (2):**
- Only system parameters explicitly flagged as editable (EDITABLE_FLAG = 'Y') may be modified; parameters marked non-editable are protected from update
- _days_between

**Validation Rules (11):**
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
- Package uses PRAGMA AUTONOMOUS_TRANSACTION — writes independent of caller

### HRMS.PKG_EMPLOYEE
**Known Issues:**
- - Circular dependency with PKG_PAYROLL (salary validation)
- - get_org_chart uses recursive SQL that times out for deep hierarchies

**Exceptions (5):**
- `e_employee_not_found` (-20001)
- `e_duplicate_emp_number` (-20002)
- `e_invalid_department` (-20003)
- `e_invalid_manager` (-20004)
- `e_termination_error` (-20005)

**Constants (2):**
- `c_emp_number_prefix` = 'EMP'
- `c_max_hierarchy_depth` = 15

**PRAGMA AUTONOMOUS_TRANSACTION: YES**

**DBMS Packages:** DBMS_OUTPUT

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

**Validation Rules (34):**
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
- Package uses PRAGMA AUTONOMOUS_TRANSACTION — writes independent of caller

### HRMS.PKG_INTEGRATION
**Known Issues:**
- - GL posting uses flat file exchange (UTL_FILE) instead of API
- - Benefits feed format is vendor-specific (ADP format)
- - No retry logic for failed file transfers
- - FTP credentials stored in SYSTEM_PARAMETERS table (cleartext)

**Constants (3):**
- `c_gl_output_dir` = 'GL_FEED_OUT'
- `c_benefits_output_dir` = 'BENEFITS_FEED_OUT'
- `c_time_input_dir` = 'TIME_ATTENDANCE_IN'

**UTL Packages:** UTL_FILE

**Validation Rules (1):**
- File I/O uses UTL_FILE with Oracle directory objects

### HRMS.PKG_LEAVE
**Known Issues:**
- - Overlapping leave detection does not account for half-day requests
- - Carryover expiry job sometimes double-expires if run twice on same day
- - Holiday detection only checks exact date match, not observed dates

**Exceptions (4):**
- `e_insufficient_balance` (-20201)
- `e_overlapping_leave` (-20202)
- `e_invalid_leave_type` (-20203)
- `e_approval_error` (-20204)

**DBMS Packages:** DBMS_OUTPUT

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

### HRMS.PKG_NOTIFICATION
**Known Issues:**
- - UTL_MAIL configuration hard-coded to legacy SMTP server
- - No rate limiting - bulk operations can flood the queue
- - HTML email templates stored as string constants (maintenance nightmare)

**Constants (4):**
- `c_smtp_host` = 'smtp.internal.company.com'
- `c_smtp_port` = 25
- `c_from_address` = 'hrms-noreply@company.com'
- `c_from_name` = 'HRMS System'

**PRAGMA AUTONOMOUS_TRANSACTION: YES**

**UTL Packages:** UTL_SMTP, UTL_TCP

**Validation Rules (3):**
- Package uses PRAGMA AUTONOMOUS_TRANSACTION — writes independent of caller
- Email delivery uses UTL_SMTP (NOT UTL_MAIL)
- Contains hard-coded config values that should be in SYSTEM_PARAMETERS

### HRMS.PKG_PAYROLL
**Known Issues:**
- - Circular dependency with PKG_EMPLOYEE (is_active check)
- - Tax calculation uses hard-coded 2024 brackets in some paths
- - Overtime calculation does not account for holidays correctly
- - YTD accumulation resets incorrectly for mid-year hires in some edge cases

**Exceptions (4):**
- `e_invalid_salary` (-20101)
- `e_period_closed` (-20102)
- `e_run_already_paid` (-20103)
- `e_calculation_error` (-20104)

**Constants (8):**
- `c_ss_wage_base_2024` = 168600
- `c_ss_rate` = 0.062
- `c_medicare_rate` = 0.0145
- `c_medicare_addl_rate` = 0.009
- `c_medicare_addl_threshold` = 200000
- `c_standard_deduction_single` = 14600
- `c_standard_deduction_married` = 29200
- `c_allowance_amount` = 4300

**UTL Packages:** UTL_FILE

**DBMS Packages:** DBMS_OUTPUT

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

**Validation Rules (40):**
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
- File I/O uses UTL_FILE with Oracle directory objects
- Contains hard-coded config values that should be in SYSTEM_PARAMETERS

### HRMS.PKG_PERFORMANCE

**DBMS Packages:** DBMS_OUTPUT

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

**Validation Rules (16):**
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
- Contains hard-coded config values that should be in SYSTEM_PARAMETERS

### HRMS.PKG_SECURITY
**Known Issues:**
- - Password stored as MD5 hash (should be bcrypt/scrypt)
- - Session timeout check uses DB server time, not app server time
- - No account lockout after failed attempts
- - DBMS_CRYPTO key hard-coded in package body

**Exceptions (4):**
- `e_invalid_credentials` (-20301)
- `e_account_locked` (-20302)
- `e_session_expired` (-20303)
- `e_insufficient_priv` (-20304)

**Constants (2):**
- `c_session_timeout_min` = 30
- `c_encryption_key` = UTL_RAW.CAST_TO_RAW('HR$ystem_3ncrypt10n_K3y_2024!!') — VULNERABILITY: Encryption key hard-coded in source

**UTL Packages:** UTL_RAW

**DBMS Packages:** DBMS_CRYPTO

**Business Rules (2):**
- Only employees with EMPLOYMENT_STATUS = 'ACTIVE' are eligible to authenticate; terminated, suspended, or otherwise inactive employees are excluded
- When multiple active employees share the same email address, the employee with the lowest EMP_ID is selected as the authenticated user

**Validation Rules (14):**
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
- Contains hard-coded config values that should be in SYSTEM_PARAMETERS

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

---
## PLL Libraries

### HRMS_COMMON_LIB
- Procedures: 13, Functions: 4
  - `handle_error`: calls: MESSAGE, FORM_TRIGGER_FAILURE, RAISE; buffers: v_errmsg=VARCHAR2(500)
  - `toolbar_save`: calls: COMMIT_FORM
  - `toolbar_clear`: calls: CLEAR_FORM
  - `toolbar_query`: calls: ENTER_QUERY, EXECUTE_QUERY
  - `toolbar_first`: calls: FIRST_RECORD
  - `toolbar_prev`: calls: PREVIOUS_RECORD
  - `toolbar_next`: calls: NEXT_RECORD
  - `toolbar_last`: calls: LAST_RECORD
  - `toolbar_insert`: calls: CREATE_RECORD
  - `toolbar_delete`: calls: DELETE_RECORD
  - `toolbar_exit`: calls: EXIT_FORM
  - `check_session`: calls: MESSAGE, FORM_TRIGGER_FAILURE, RAISE
  - `refresh_lov`: calls: raise; buffers: v_rg_name=VARCHAR2(60)
  - `format_date`: masks: MM/DD/YYYY
  - `format_datetime`: masks: MM/DD/YYYY HH24:MI:SS

### HRMS_VALIDATION_LIB
- Procedures: 0, Functions: 5
  - `validate_salary_range`: calls: message; masks: FM$999,999

---
## Menu Modules

### HRMS_MENU — 7 menus, 31 items

**File** (4 items):
  - Save: `COMMIT_FORM`
  - Save & Exit: `COMMIT_FORM; EXIT_FORM`
  - Print: `RUN_PRODUCT`
  - Exit: `EXIT_FORM`

**Edit** (4 items):
  - Clear Record: `CLEAR_RECORD`
  - Duplicate Record: `DUPLICATE_RECORD`
  - Delete Record: `DELETE_RECORD`
  - Insert Record: `CREATE_RECORD`

**Query** (5 items):
  - Enter Query: `ENTER_QUERY`
  - Execute Query: `EXECUTE_QUERY`
  - Cancel Query: `EXIT_FORM`
  - Count Matching: `COUNT_QUERY`
  - Fetch Next Set: `SCROLL_DOWN`

**Navigate** (6 items):
  - First Record: `FIRST_RECORD`
  - Previous Record: `PREVIOUS_RECORD`
  - Next Record: `NEXT_RECORD`
  - Last Record: `LAST_RECORD`
  - Previous Block: `PREVIOUS_BLOCK`
  - Next Block: `NEXT_BLOCK`

**Modules** (6 items):
  - Employee Management: `OPEN_FORM('HRMS_EMPLOYEE')`
  - Payroll Processing: `OPEN_FORM('HRMS_PAYROLL')`
  - Leave Management: `OPEN_FORM('HRMS_LEAVE')`
  - Performance Reviews: `OPEN_FORM('HRMS_PERFORMANCE')`
  - Reports & Analytics: `OPEN_FORM('HRMS_REPORTS')`
  - System Admin: `OPEN_FORM('HRMS_ADMIN')`

**Admin** (3 items):
  - Change Password: `SHOW_WINDOW('WIN_CHANGE_PWD')`
  - System Parameters: `requires ADMIN permission`
  - User Management: `requires ADMIN permission`

**Help** (3 items):
  - Contents: `WEB.SHOW_DOCUMENT`
  - About HRMS: `SHOW_ALERT('ALT_ABOUT')`
  - Support: `WEB.SHOW_DOCUMENT`

- OPEN_FORM targets: HRMS_LEAVE, HRMS_ADMIN, HRMS_REPORTS, HRMS_PERFORMANCE, HRMS_PAYROLL, HRMS_EMPLOYEE
- Security calls: PKG_SECURITY.has_permission

---
## Oracle Forms

### HRMS_EMPLOYEE — HRMS - Employee Maintenance
- Libraries: HRMS_COMMON_LIB, HRMS_VALIDATION_LIB
- Canvas `CVS_MAIN` tab pages: TP_PERSONAL (Personal Information), TP_JOB (Job & Compensation), TP_DEPENDENTS (Dependents), TP_HISTORY (Employment History)

**Relations:**
- `EMP_SALARY_REL` → `SALARY` (delete: Cascading, auto_query: Yes)

**Alerts:**
- `ALT_CONFIRM_EXIT` [Caution]: "You have unsaved changes. Save before exiting?" Buttons: Save / Discard / Cancel
- `ALT_CONFIRM_DELETE` [Stop]: "Are you sure you want to delete this employee record?" Buttons: Yes / No / 

**LOV Queries (4):**
- `RG_DEPARTMENTS`: `SELECT DEPT_ID, DEPT_CODE, DEPT_NAME, COST_CENTER FROM HRMS.DEPARTMENTS WHERE ACTIVE_FLAG = 'Y' ORDER BY DEPT_NAME`
- `RG_JOB_TITLES`: `SELECT j.JOB_ID, j.JOB_CODE, j.JOB_TITLE, g.GRADE_NAME FROM HRMS.JOB_TITLES j JOIN HRMS.JOB_GRADES g ON j.GRADE_ID = g.GRADE_ID WHERE j.ACTIVE_FLAG = `
- `RG_MANAGERS`: `SELECT EMP_ID, EMP_NUMBER, FIRST_NAME || ' ' || LAST_NAME AS MANAGER_NAME FROM HRMS.EMPLOYEES WHERE EMPLOYMENT_STATUS = 'ACTIVE' ORDER BY LAST_NAME`
- `RG_LOCATIONS`: `SELECT LOCATION_CODE, LOCATION_NAME, CITY, STATE_PROVINCE FROM HRMS.LOCATIONS WHERE ACTIVE_FLAG = 'Y' ORDER BY LOCATION_NAME`

### HRMS_LEAVE — HRMS - Leave Management
- Libraries: HRMS_COMMON_LIB
- Canvas `CVS_MAIN` tab pages: TP_MY_REQUESTS (My Requests), TP_NEW_REQUEST (Submit Request), TP_APPROVALS (Pending Approvals), TP_CALENDAR (Team Calendar)

**Alerts:**
- `ALT_CONFIRM_CANCEL` [Caution]: "Are you sure you want to cancel this leave request?" Buttons: Yes / No / 

**LOV Queries (1):**
- `RG_LEAVE_TYPES`: `SELECT LEAVE_TYPE_ID, LEAVE_TYPE_CODE, LEAVE_TYPE_NAME FROM HRMS.LEAVE_TYPES WHERE ACTIVE_FLAG = 'Y' ORDER BY LEAVE_TYPE_NAME`

### HRMS_LOGIN — HRMS - Login
- Libraries: 

### HRMS_MENU — HRMS - Main Menu
- Libraries: HRMS_COMMON_LIB

### HRMS_PAYROLL — HRMS - Payroll Processing
- Libraries: HRMS_COMMON_LIB
- Canvas `CVS_MAIN` tab pages: TP_PERIODS (Pay Periods), TP_RUNS (Payroll Runs), TP_DETAILS (Pay Details)

**Relations:**
- `PERIOD_RUN_REL` → `PAYROLL_RUN` (delete: , auto_query: Yes)

### HRMS_PERFORMANCE — HRMS - Performance Management
- Libraries: HRMS_COMMON_LIB
- Canvas `CVS_MAIN` tab pages: TP_CYCLES (Review Cycles), TP_REVIEWS (My Reviews), TP_GOALS (Goals)

**Relations:**
- `CYCLE_REVIEW_REL` → `PERFORMANCE_REVIEW` (delete: , auto_query: Yes)
- `REVIEW_GOAL_REL` → `PERFORMANCE_GOAL` (delete: , auto_query: Yes)

---
## Sequences

| Name | Start | Inc | Cache |
|---|---|---|---|
| HRMS.SEQ_DEPARTMENT | 100 | 1 | NOCACHE |
| HRMS.SEQ_LOCATION | 100 | 1 | NOCACHE |
| HRMS.SEQ_JOB_GRADE | 100 | 1 | NOCACHE |
| HRMS.SEQ_JOB_TITLE | 100 | 1 | NOCACHE |
| HRMS.SEQ_EMPLOYEE | 10000 | 1 | NOCACHE |
| HRMS.SEQ_EMP_HISTORY | 1 | 1 | NOCACHE |
| HRMS.SEQ_DEPENDENT | 1 | 1 | NOCACHE |
| HRMS.SEQ_EMERGENCY_CONTACT | 1 | 1 | NOCACHE |
| HRMS.SEQ_EMP_NUMBER | 1000 | 1 | NOCACHE |
| HRMS.SEQ_SALARY | 1 | 1 | NOCACHE |
| HRMS.SEQ_PAY_ELEMENT | 1 | 1 | NOCACHE |
| HRMS.SEQ_EMP_PAY_ELEMENT | 1 | 1 | NOCACHE |
| HRMS.SEQ_PAY_PERIOD | 1 | 1 | NOCACHE |
| HRMS.SEQ_PAYROLL_RUN | 1 | 1 | NOCACHE |
| HRMS.SEQ_PAYROLL_DETAIL | 1 | 1 | NOCACHE |
| HRMS.SEQ_TAX_BRACKET | 1 | 1 | NOCACHE |
| HRMS.SEQ_LEAVE_TYPE | 1 | 1 | NOCACHE |
| HRMS.SEQ_LEAVE_BALANCE | 1 | 1 | NOCACHE |
| HRMS.SEQ_LEAVE_REQUEST | 1 | 1 | NOCACHE |
| HRMS.SEQ_LEAVE_ACCRUAL | 1 | 1 | NOCACHE |
| HRMS.SEQ_HOLIDAY | 1 | 1 | NOCACHE |
| HRMS.SEQ_REVIEW_CYCLE | 1 | 1 | NOCACHE |
| HRMS.SEQ_PERF_REVIEW | 1 | 1 | NOCACHE |
| HRMS.SEQ_PERF_GOAL | 1 | 1 | NOCACHE |
| HRMS.SEQ_AUDIT | 1 | 1 | CACHE 100 |
| HRMS.SEQ_NOTIFICATION | 1 | 1 | NOCACHE |
| HRMS.SEQ_USER_SESSION | 1 | 1 | NOCACHE |
| HRMS.SEQ_SYSTEM_PARAM | 1 | 1 | NOCACHE |
| HRMS.SEQ_LOOKUP | 1 | 1 | NOCACHE |

---
## DDL Tables

### HRMS.AUDIT_LOG
- Columns (10): AUDIT_ID(NUMBER(15)), TABLE_NAME(VARCHAR2(60)), RECORD_ID(NUMBER(15)), ACTION_TYPE(VARCHAR2(10)), OLD_VALUES(CLOB), NEW_VALUES(CLOB), CHANGED_BY(VARCHAR2(30)), CHANGED_DATE(DATE) DEFAULT SYSDATE, IP_ADDRESS(VARCHAR2(50)), SESSION_ID(VARCHAR2(100))
- PK: AUDIT_ID
- CHECK: `ACTION_TYPE IN ('INSERT', 'UPDATE', 'DELETE')`

### HRMS.DEPARTMENTS
- Columns (12): DEPT_ID(NUMBER(10)), DEPT_CODE(VARCHAR2(20)), DEPT_NAME(VARCHAR2(100)), PARENT_DEPT_ID(NUMBER(10)), COST_CENTER(VARCHAR2(20)), MANAGER_EMP_ID(NUMBER(10)), LOCATION_CODE(VARCHAR2(10)), ACTIVE_FLAG(CHAR(1)), CREATED_BY(VARCHAR2(30)), CREATED_DATE(DATE) DEFAULT SYSDATE, MODIFIED_BY(VARCHAR2(30)), MODIFIED_DATE(DATE)
- PK: DEPT_ID
- UNIQUE(DEPT_CODE) [UK_DEPT_CODE]
- CHECK: `ACTIVE_FLAG IN ('Y', 'N')`

### HRMS.EMERGENCY_CONTACTS
- Columns (13): CONTACT_ID(NUMBER(10)), EMP_ID(NUMBER(10)), CONTACT_NAME(VARCHAR2(100)), RELATIONSHIP(VARCHAR2(30)), PHONE_PRIMARY(VARCHAR2(30)), PHONE_SECONDARY(VARCHAR2(30)), EMAIL(VARCHAR2(100)), PRIORITY_ORDER(NUMBER(2)) DEFAULT 1, ACTIVE_FLAG(CHAR(1)), CREATED_BY(VARCHAR2(30)), CREATED_DATE(DATE) DEFAULT SYSDATE, MODIFIED_BY(VARCHAR2(30))
- PK: CONTACT_ID
- FK `EMP_ID` → `HRMS.EMPLOYEES(EMP_ID)`

### HRMS.EMPLOYEES
- Columns (35): EMP_ID(NUMBER(10)), EMP_NUMBER(VARCHAR2(20)), FIRST_NAME(VARCHAR2(50)), MIDDLE_NAME(VARCHAR2(50)), LAST_NAME(VARCHAR2(50)), DATE_OF_BIRTH(DATE), GENDER(CHAR(1)), MARITAL_STATUS(VARCHAR2(10)), NATIONALITY(VARCHAR2(50)), SSN_ENCRYPTED(VARCHAR2(200)), EMAIL(VARCHAR2(100)), PHONE_WORK(VARCHAR2(30))
- PK: EMP_ID
- FK `DEPT_ID` → `HRMS.DEPARTMENTS(DEPT_ID)`
- FK `JOB_ID` → `HRMS.JOB_TITLES(JOB_ID)`
- FK `MANAGER_EMP_ID` → `HRMS.EMPLOYEES(EMP_ID)`
- FK `LOCATION_CODE` → `HRMS.LOCATIONS(LOCATION_CODE)`
- UNIQUE(EMP_NUMBER) [UK_EMP_NUMBER]
- CHECK: `EMPLOYMENT_STATUS IN ('ACTIVE', 'ON_LEAVE', 'SUSPENDED', 'TERMINATED')`
- CHECK: `EMPLOYMENT_TYPE IN ('FULL_TIME', 'PART_TIME', 'CONTRACT', 'INTERN')`
- CHECK: `GENDER IN ('M', 'F', 'O')`

### HRMS.EMPLOYEE_BANK_ACCOUNTS
- Columns (17): BANK_ACCT_ID(NUMBER(10)), EMP_ID(NUMBER(10)), BANK_NAME(VARCHAR2(100)), ROUTING_NUMBER(VARCHAR2(20)), ACCOUNT_NUMBER_ENC(VARCHAR2(200)), ACCOUNT_TYPE(VARCHAR2(20)), DEPOSIT_TYPE(VARCHAR2(20)), DEPOSIT_AMOUNT(NUMBER(12,2)), DEPOSIT_PERCENTAGE(NUMBER(5,2)), PRIORITY_ORDER(NUMBER(2)) DEFAULT 1, PRENOTE_SENT(CHAR(1)), PRENOTE_DATE(DATE)
- PK: BANK_ACCT_ID
- FK `EMP_ID` → `HRMS.EMPLOYEES(EMP_ID)`
- CHECK: `ACCOUNT_TYPE IN ('CHECKING', 'SAVINGS')`
- CHECK: `DEPOSIT_TYPE IN ('FULL', 'PARTIAL_AMOUNT', 'PARTIAL_PERCENT', 'REMAINDER')`

### HRMS.EMPLOYEE_DEPENDENTS
- Columns (13): DEPENDENT_ID(NUMBER(10)), EMP_ID(NUMBER(10)), FIRST_NAME(VARCHAR2(50)), LAST_NAME(VARCHAR2(50)), RELATIONSHIP(VARCHAR2(20)), DATE_OF_BIRTH(DATE), SSN_ENCRYPTED(VARCHAR2(200)), BENEFITS_ENROLLED(CHAR(1)), ACTIVE_FLAG(CHAR(1)), CREATED_BY(VARCHAR2(30)), CREATED_DATE(DATE) DEFAULT SYSDATE, MODIFIED_BY(VARCHAR2(30))
- PK: DEPENDENT_ID
- FK `EMP_ID` → `HRMS.EMPLOYEES(EMP_ID)`
- CHECK: `RELATIONSHIP IN ('SPOUSE', 'CHILD', 'PARENT', 'DOMESTIC_PARTNER', 'OTHER')`

### HRMS.EMPLOYEE_HISTORY
- Columns (18): HIST_ID(NUMBER(15)), EMP_ID(NUMBER(10)), CHANGE_TYPE(VARCHAR2(30)), EFFECTIVE_DATE(DATE), OLD_DEPT_ID(NUMBER(10)), NEW_DEPT_ID(NUMBER(10)), OLD_JOB_ID(NUMBER(10)), NEW_JOB_ID(NUMBER(10)), OLD_MANAGER_ID(NUMBER(10)), NEW_MANAGER_ID(NUMBER(10)), OLD_SALARY(NUMBER(12,2)), NEW_SALARY(NUMBER(12,2))
- PK: HIST_ID
- FK `EMP_ID` → `HRMS.EMPLOYEES(EMP_ID)`

### HRMS.EMPLOYEE_PAY_ELEMENTS
- Columns (13): EMP_ELEMENT_ID(NUMBER(10)), EMP_ID(NUMBER(10)), ELEMENT_ID(NUMBER(10)), EFFECTIVE_DATE(DATE), END_DATE(DATE), AMOUNT(NUMBER(12,2)), PERCENTAGE(NUMBER(5,2)), OVERRIDE_AMOUNT(NUMBER(12,2)), ACTIVE_FLAG(CHAR(1)), CREATED_BY(VARCHAR2(30)), CREATED_DATE(DATE) DEFAULT SYSDATE, MODIFIED_BY(VARCHAR2(30))
- PK: EMP_ELEMENT_ID
- FK `EMP_ID` → `HRMS.EMPLOYEES(EMP_ID)`
- FK `ELEMENT_ID` → `HRMS.PAY_ELEMENTS(ELEMENT_ID)`

### HRMS.EMPLOYEE_TAX_INFO
- Columns (16): TAX_INFO_ID(NUMBER(10)), EMP_ID(NUMBER(10)), TAX_YEAR(NUMBER(4)), FILING_STATUS(VARCHAR2(30)), FEDERAL_ALLOWANCES(NUMBER(3)) DEFAULT 0, STATE_ALLOWANCES(NUMBER(3)) DEFAULT 0, ADDITIONAL_FED_WH(NUMBER(12,2)) DEFAULT 0, ADDITIONAL_STATE_WH(NUMBER(12,2)) DEFAULT 0, EXEMPT_FLAG(CHAR(1)), STATE_CODE(VARCHAR2(3)), W4_RECEIVED_DATE(DATE), ACTIVE_FLAG(CHAR(1))
- PK: TAX_INFO_ID
- FK `EMP_ID` → `HRMS.EMPLOYEES(EMP_ID)`
- UNIQUE(EMP_ID, TAX_YEAR) [UK_EMP_TAX_YEAR]

### HRMS.HOLIDAYS
- Columns (8): HOLIDAY_ID(NUMBER(5)), HOLIDAY_DATE(DATE), HOLIDAY_NAME(VARCHAR2(100)), LOCATION_CODE(VARCHAR2(10)), FLOATING_FLAG(CHAR(1)), ACTIVE_FLAG(CHAR(1)), CREATED_BY(VARCHAR2(30)), CREATED_DATE(DATE) DEFAULT SYSDATE
- PK: HOLIDAY_ID

### HRMS.JOB_GRADES
- Columns (11): GRADE_ID(NUMBER(5)), GRADE_CODE(VARCHAR2(10)), GRADE_NAME(VARCHAR2(50)), MIN_SALARY(NUMBER(12,2)), MAX_SALARY(NUMBER(12,2)), OVERTIME_ELIGIBLE(CHAR(1)), ACTIVE_FLAG(CHAR(1)), CREATED_BY(VARCHAR2(30)), CREATED_DATE(DATE) DEFAULT SYSDATE, MODIFIED_BY(VARCHAR2(30)), MODIFIED_DATE(DATE)
- PK: GRADE_ID
- UNIQUE(GRADE_CODE) [UK_GRADE_CODE]
- CHECK: `MAX_SALARY >= MIN_SALARY`

### HRMS.JOB_TITLES
- Columns (12): JOB_ID(NUMBER(10)), JOB_CODE(VARCHAR2(20)), JOB_TITLE(VARCHAR2(100)), JOB_FAMILY(VARCHAR2(50)), GRADE_ID(NUMBER(5)), EEO_CATEGORY(VARCHAR2(10)), FLSA_STATUS(VARCHAR2(10)), ACTIVE_FLAG(CHAR(1)), CREATED_BY(VARCHAR2(30)), CREATED_DATE(DATE) DEFAULT SYSDATE, MODIFIED_BY(VARCHAR2(30)), MODIFIED_DATE(DATE)
- PK: JOB_ID
- FK `GRADE_ID` → `HRMS.JOB_GRADES(GRADE_ID)`
- UNIQUE(JOB_CODE) [UK_JOB_CODE]

### HRMS.LEAVE_ACCRUAL_LOG
- Columns (9): ACCRUAL_ID(NUMBER(15)), EMP_ID(NUMBER(10)), LEAVE_TYPE_ID(NUMBER(5)), ACCRUAL_DATE(DATE), ACCRUAL_AMOUNT(NUMBER(6,2)), BALANCE_AFTER(NUMBER(6,2)), RUN_ID(NUMBER(10)), CREATED_BY(VARCHAR2(30)), CREATED_DATE(DATE) DEFAULT SYSDATE
- PK: ACCRUAL_ID
- FK `EMP_ID` → `HRMS.EMPLOYEES(EMP_ID)`
- FK `LEAVE_TYPE_ID` → `HRMS.LEAVE_TYPES(LEAVE_TYPE_ID)`

### HRMS.LEAVE_BALANCES
- Columns (16): BALANCE_ID(NUMBER(10)), EMP_ID(NUMBER(10)), LEAVE_TYPE_ID(NUMBER(5)), CALENDAR_YEAR(NUMBER(4)), OPENING_BALANCE(NUMBER(6,2)) DEFAULT 0, ACCRUED(NUMBER(6,2)) DEFAULT 0, USED(NUMBER(6,2)) DEFAULT 0, ADJUSTMENT(NUMBER(6,2)) DEFAULT 0, PENDING(NUMBER(6,2)) DEFAULT 0, AVAILABLE(NUMBER(6,2)) [VIRTUAL], CARRYOVER_FROM_PREV(NUMBER(6,2)) DEFAULT 0, CARRYOVER_EXPIRY_DT(DATE)
- PK: BALANCE_ID
- FK `EMP_ID` → `HRMS.EMPLOYEES(EMP_ID)`
- FK `LEAVE_TYPE_ID` → `HRMS.LEAVE_TYPES(LEAVE_TYPE_ID)`
- UNIQUE(EMP_ID, LEAVE_TYPE_ID, CALENDAR_YEAR) [UK_LEAVE_BAL]

### HRMS.LEAVE_REQUESTS
- Columns (20): REQUEST_ID(NUMBER(10)), EMP_ID(NUMBER(10)), LEAVE_TYPE_ID(NUMBER(5)), START_DATE(DATE), END_DATE(DATE), TOTAL_DAYS(NUMBER(5,1)), HALF_DAY_FLAG(CHAR(1)), HALF_DAY_PERIOD(VARCHAR2(10)), STATUS(VARCHAR2(20)), REASON(VARCHAR2(4000)), SUPPORTING_DOC_PATH(VARCHAR2(500)), APPROVER_EMP_ID(NUMBER(10))
- PK: REQUEST_ID
- FK `EMP_ID` → `HRMS.EMPLOYEES(EMP_ID)`
- FK `LEAVE_TYPE_ID` → `HRMS.LEAVE_TYPES(LEAVE_TYPE_ID)`
- FK `APPROVER_EMP_ID` → `HRMS.EMPLOYEES(EMP_ID)`
- CHECK: `STATUS IN ('PENDING', 'APPROVED', 'REJECTED', 'CANCELLED', 'TAKEN')`
- CHECK: `END_DATE >= START_DATE`
- CHECK: `HALF_DAY_PERIOD IN ('AM', 'PM', NULL)`

### HRMS.LEAVE_TYPES
- Columns (18): LEAVE_TYPE_ID(NUMBER(5)), LEAVE_TYPE_CODE(VARCHAR2(20)), LEAVE_TYPE_NAME(VARCHAR2(50)), PAID_FLAG(CHAR(1)), ACCRUAL_FLAG(CHAR(1)), ACCRUAL_RATE(NUMBER(6,2)), ACCRUAL_FREQUENCY(VARCHAR2(20)), MAX_BALANCE(NUMBER(6,2)), CARRYOVER_MAX(NUMBER(6,2)), CARRYOVER_EXPIRY(NUMBER(3)), MIN_TENURE_DAYS(NUMBER(5)) DEFAULT 0, REQUIRES_APPROVAL(CHAR(1))
- PK: LEAVE_TYPE_ID
- UNIQUE(LEAVE_TYPE_CODE) [UK_LEAVE_TYPE_CODE]
- CHECK: `ACCRUAL_FREQUENCY IN ('MONTHLY', 'BIWEEKLY', 'ANNUAL', NULL)`

### HRMS.LOCATIONS
- Columns (15): LOCATION_CODE(VARCHAR2(10)), LOCATION_NAME(VARCHAR2(100)), ADDRESS_LINE1(VARCHAR2(200)), ADDRESS_LINE2(VARCHAR2(200)), CITY(VARCHAR2(100)), STATE_PROVINCE(VARCHAR2(100)), POSTAL_CODE(VARCHAR2(20)), COUNTRY_CODE(VARCHAR2(3)), PHONE_NUMBER(VARCHAR2(30)), TIMEZONE(VARCHAR2(50)), ACTIVE_FLAG(CHAR(1)), CREATED_BY(VARCHAR2(30))
- PK: LOCATION_CODE

### HRMS.LOOKUP_VALUES
- Columns (9): LOOKUP_ID(NUMBER(10)), LOOKUP_TYPE(VARCHAR2(50)), LOOKUP_CODE(VARCHAR2(50)), LOOKUP_VALUE(VARCHAR2(200)), DISPLAY_ORDER(NUMBER(5)) DEFAULT 0, PARENT_LOOKUP_ID(NUMBER(10)), ACTIVE_FLAG(CHAR(1)), CREATED_BY(VARCHAR2(30)), CREATED_DATE(DATE) DEFAULT SYSDATE
- PK: LOOKUP_ID
- UNIQUE(LOOKUP_TYPE, LOOKUP_CODE) [UK_LOOKUP]

### HRMS.NOTIFICATION_QUEUE
- Columns (15): NOTIFICATION_ID(NUMBER(15)), RECIPIENT_EMP_ID(NUMBER(10)), RECIPIENT_EMAIL(VARCHAR2(100)), NOTIFICATION_TYPE(VARCHAR2(30)), SUBJECT(VARCHAR2(200)), BODY(CLOB), STATUS(VARCHAR2(20)), PRIORITY(NUMBER(2)) DEFAULT 5, SENT_DATE(DATE), ERROR_MESSAGE(VARCHAR2(4000)), RETRY_COUNT(NUMBER(3)) DEFAULT 0, REFERENCE_TABLE(VARCHAR2(60))
- PK: NOTIFICATION_ID
- CHECK: `STATUS IN ('PENDING', 'SENT', 'FAILED', 'CANCELLED')`
- CHECK: `NOTIFICATION_TYPE IN ('EMAIL', 'IN_APP', 'SMS')`

### HRMS.PAYROLL_DETAILS
- Columns (13): DETAIL_ID(NUMBER(15)), RUN_ID(NUMBER(10)), EMP_ID(NUMBER(10)), ELEMENT_ID(NUMBER(10)), ELEMENT_TYPE(VARCHAR2(20)), HOURS_WORKED(NUMBER(6,2)), RATE(NUMBER(12,4)), AMOUNT(NUMBER(12,2)), YTD_AMOUNT(NUMBER(15,2)), STATUS(VARCHAR2(20)), ERROR_MESSAGE(VARCHAR2(4000)), CREATED_BY(VARCHAR2(30))
- PK: DETAIL_ID
- FK `RUN_ID` → `HRMS.PAYROLL_RUNS(RUN_ID)`
- FK `EMP_ID` → `HRMS.EMPLOYEES(EMP_ID)`
- FK `ELEMENT_ID` → `HRMS.PAY_ELEMENTS(ELEMENT_ID)`

### HRMS.PAYROLL_RUNS
- Columns (19): RUN_ID(NUMBER(10)), PERIOD_ID(NUMBER(10)), RUN_TYPE(VARCHAR2(20)), RUN_DATE(DATE), STATUS(VARCHAR2(20)), TOTAL_GROSS(NUMBER(15,2)), TOTAL_DEDUCTIONS(NUMBER(15,2)), TOTAL_NET(NUMBER(15,2)), TOTAL_EMPLOYER_COST(NUMBER(15,2)), EMPLOYEE_COUNT(NUMBER(10)), ERROR_COUNT(NUMBER(10)) DEFAULT 0, SUBMITTED_BY(VARCHAR2(30))
- PK: RUN_ID
- FK `PERIOD_ID` → `HRMS.PAY_PERIODS(PERIOD_ID)`
- CHECK: `RUN_TYPE IN ('REGULAR', 'SUPPLEMENTAL', 'BONUS', 'FINAL')`
- CHECK: `STATUS IN ('PENDING', 'CALCULATING', 'CALCULATED', 'APPROVED', 'PAID', 'REVERSED', 'ERROR')`

### HRMS.PAY_ELEMENTS
- Columns (17): ELEMENT_ID(NUMBER(10)), ELEMENT_CODE(VARCHAR2(30)), ELEMENT_NAME(VARCHAR2(100)), ELEMENT_TYPE(VARCHAR2(20)), CALCULATION_TYPE(VARCHAR2(20)), DEFAULT_AMOUNT(NUMBER(12,2)), DEFAULT_PERCENTAGE(NUMBER(5,2)), TAXABLE_FLAG(CHAR(1)), PRETAX_FLAG(CHAR(1)), EMPLOYER_PAID(CHAR(1)), GL_ACCOUNT_CODE(VARCHAR2(30)), PRIORITY_ORDER(NUMBER(5)) DEFAULT 100
- PK: ELEMENT_ID
- UNIQUE(ELEMENT_CODE) [UK_PAY_ELEM_CODE]
- CHECK: `ELEMENT_TYPE IN ('EARNING', 'DEDUCTION', 'TAX', 'BENEFIT', 'REIMBURSEMENT')`
- CHECK: `CALCULATION_TYPE IN ('FLAT', 'PERCENTAGE', 'HOURS', 'FORMULA')`

### HRMS.PAY_PERIODS
- Columns (13): PERIOD_ID(NUMBER(10)), PERIOD_NAME(VARCHAR2(50)), PAY_FREQUENCY(VARCHAR2(20)), PERIOD_START_DATE(DATE), PERIOD_END_DATE(DATE), PAY_DATE(DATE), STATUS(VARCHAR2(20)), CLOSED_BY(VARCHAR2(30)), CLOSED_DATE(DATE), CREATED_BY(VARCHAR2(30)), CREATED_DATE(DATE) DEFAULT SYSDATE, MODIFIED_BY(VARCHAR2(30))
- PK: PERIOD_ID
- CHECK: `STATUS IN ('OPEN', 'PROCESSING', 'CLOSED', 'REVERSED')`

### HRMS.PERFORMANCE_GOALS
- Columns (17): GOAL_ID(NUMBER(10)), REVIEW_ID(NUMBER(10)), EMP_ID(NUMBER(10)), GOAL_TITLE(VARCHAR2(200)), GOAL_DESCRIPTION(CLOB), GOAL_CATEGORY(VARCHAR2(30)), WEIGHT_PCT(NUMBER(5,2)) DEFAULT 0, TARGET_DATE(DATE), STATUS(VARCHAR2(20)), PROGRESS_PCT(NUMBER(5,2)) DEFAULT 0, SELF_RATING(NUMBER(2,1)), MANAGER_RATING(NUMBER(2,1))
- PK: GOAL_ID
- FK `REVIEW_ID` → `HRMS.PERFORMANCE_REVIEWS(REVIEW_ID)`
- FK `EMP_ID` → `HRMS.EMPLOYEES(EMP_ID)`
- CHECK: `STATUS IN ('NOT_STARTED', 'IN_PROGRESS', 'COMPLETED', 'DEFERRED', 'CANCELLED')`
- CHECK: `GOAL_CATEGORY IN ('BUSINESS', 'DEVELOPMENT', 'LEADERSHIP', 'INNOVATION', 'COMPLIANCE')`

### HRMS.PERFORMANCE_REVIEWS
- Columns (21): REVIEW_ID(NUMBER(10)), CYCLE_ID(NUMBER(10)), EMP_ID(NUMBER(10)), REVIEWER_EMP_ID(NUMBER(10)), REVIEW_TYPE(VARCHAR2(20)), STATUS(VARCHAR2(20)), OVERALL_RATING(NUMBER(2,1)), RATING_LABEL(VARCHAR2(50)), SELF_ASSESSMENT(CLOB), MANAGER_ASSESSMENT(CLOB), STRENGTHS(CLOB), AREAS_FOR_IMPROVEMENT(CLOB)
- PK: REVIEW_ID
- FK `CYCLE_ID` → `HRMS.REVIEW_CYCLES(CYCLE_ID)`
- FK `EMP_ID` → `HRMS.EMPLOYEES(EMP_ID)`
- FK `REVIEWER_EMP_ID` → `HRMS.EMPLOYEES(EMP_ID)`
- CHECK: `STATUS IN ('NOT_STARTED', 'SELF_REVIEW', 'MANAGER_REVIEW', 'MEETING_SCHEDULED', 'COMPLETED', 'ACKNOWLEDGED')`
- CHECK: `OVERALL_RATING BETWEEN 1.0 AND 5.0`

### HRMS.REVIEW_CYCLES
- Columns (13): CYCLE_ID(NUMBER(10)), CYCLE_NAME(VARCHAR2(100)), CYCLE_YEAR(NUMBER(4)), START_DATE(DATE), END_DATE(DATE), SELF_REVIEW_DUE(DATE), MANAGER_REVIEW_DUE(DATE), CALIBRATION_DUE(DATE), STATUS(VARCHAR2(20)), CREATED_BY(VARCHAR2(30)), CREATED_DATE(DATE) DEFAULT SYSDATE, MODIFIED_BY(VARCHAR2(30))
- PK: CYCLE_ID
- CHECK: `STATUS IN ('DRAFT', 'OPEN', 'IN_PROGRESS', 'CALIBRATION', 'CLOSED')`

### HRMS.SALARY_RECORDS
- Columns (17): SALARY_ID(NUMBER(10)), EMP_ID(NUMBER(10)), EFFECTIVE_DATE(DATE), END_DATE(DATE), BASE_SALARY(NUMBER(12,2)), CURRENCY_CODE(VARCHAR2(3)), PAY_FREQUENCY(VARCHAR2(20)), SALARY_BASIS(VARCHAR2(20)), CHANGE_REASON(VARCHAR2(50)), CHANGE_PCT(NUMBER(5,2)), APPROVED_BY(NUMBER(10)), APPROVAL_DATE(DATE)
- PK: SALARY_ID
- FK `EMP_ID` → `HRMS.EMPLOYEES(EMP_ID)`
- CHECK: `PAY_FREQUENCY IN ('WEEKLY', 'BIWEEKLY', 'SEMIMONTHLY', 'MONTHLY')`
- CHECK: `SALARY_BASIS IN ('ANNUAL', 'HOURLY')`

### HRMS.SYSTEM_PARAMETERS
- Columns (11): PARAM_ID(NUMBER(5)), PARAM_GROUP(VARCHAR2(50)), PARAM_CODE(VARCHAR2(50)), PARAM_VALUE(VARCHAR2(4000)), PARAM_DESCRIPTION(VARCHAR2(200)), DATA_TYPE(VARCHAR2(20)), EDITABLE_FLAG(CHAR(1)), CREATED_BY(VARCHAR2(30)), CREATED_DATE(DATE) DEFAULT SYSDATE, MODIFIED_BY(VARCHAR2(30)), MODIFIED_DATE(DATE)
- PK: PARAM_ID
- UNIQUE(PARAM_GROUP, PARAM_CODE) [UK_PARAM_CODE]

### HRMS.TAX_BRACKETS
- Columns (11): BRACKET_ID(NUMBER(10)), TAX_YEAR(NUMBER(4)), FILING_STATUS(VARCHAR2(30)), BRACKET_MIN(NUMBER(12,2)), BRACKET_MAX(NUMBER(12,2)), TAX_RATE(NUMBER(5,4)), BASE_TAX(NUMBER(12,2)) DEFAULT 0, STATE_CODE(VARCHAR2(3)), ACTIVE_FLAG(CHAR(1)), CREATED_BY(VARCHAR2(30)), CREATED_DATE(DATE) DEFAULT SYSDATE
- PK: BRACKET_ID
- CHECK: `FILING_STATUS IN ('SINGLE', 'MARRIED_JOINT', 'MARRIED_SEPARATE', 'HEAD_OF_HOUSEHOLD')`

### HRMS.USER_SESSIONS
- Columns (9): SESSION_ID(NUMBER(15)), EMP_ID(NUMBER(10)), USERNAME(VARCHAR2(30)), LOGIN_TIME(DATE), LOGOUT_TIME(DATE), IP_ADDRESS(VARCHAR2(50)), FORMS_MODULE(VARCHAR2(100)), SESSION_STATUS(VARCHAR2(20)), CREATED_DATE(DATE) DEFAULT SYSDATE
- PK: SESSION_ID
- FK `EMP_ID` → `HRMS.EMPLOYEES(EMP_ID)`

---
## Triggers

### TRG_DEPARTMENT_AUDIT — AFTER INSERT OR UPDATE OR DELETE ON HRMS.DEPARTMENTS
- RULE: Every structural change to a department record (creation, modification, or removal) must be captured in the audit log to support organisational governance and accountability
- RULE: For department changes, the database session user (USER) is always recorded as the actor; there is no application-supplied MODIFIED_BY column on this table

### TRG_EMP_BEFORE_INSERT — BEFORE INSERT ON HRMS.EMPLOYEES
- Error -20501: Hire date cannot be more than 180 days in the future
- Error -20502: Email address already in use:
- RULE: CREATED_BY must be populated; defaults to the current database session user if not supplied by the caller
- RULE: CREATED_DATE must be populated; defaults to the current system timestamp if not supplied by the caller
- RULE: A new employee record is considered active by default unless ACTIVE_FLAG is explicitly set to a different value
- RULE: A new employee record defaults to ACTIVE employment status unless an alternative status is explicitly provided on insert
- RULE: Hire date cannot be more than 180 days in the future, preventing erroneous or speculative pre-dated hires beyond a 6-month planning horizon
- RULE: Inserting an employee with a hire date more than 180 days in the future is not permitted
- RULE: An email address already assigned to an active employee cannot be reused for a new employee record
- RULE: Inserting an employee whose email is already in use by an active employee record is not permitted

### TRG_EMP_BEFORE_UPDATE — BEFORE UPDATE ON HRMS.EMPLOYEES
- Error -20503: Cannot directly reactivate a terminated employee. Use the rehire process.
- RULE: A terminated employee cannot be directly reactivated by changing EMPLOYMENT_STATUS from TERMINATED to ACTIVE via a plain UPDATE; the formal rehire process (PKG_EMPLOYEE.rehire_employee) must be used instead
- RULE: Bypassing the rehire process to reactivate a terminated employee is not permitted
- RULE: Every change to an employee's EMPLOYMENT_STATUS must be recorded in the EMPLOYEE_HISTORY audit table with the old and new status values
- RULE: Every change to an employee's department assignment (DEPT_ID) must be recorded in the EMPLOYEE_HISTORY audit table as a DEPARTMENT_CHANGE event; NULL department is treated as a distinct value to catch assignments to or from an unassigned state
- RULE: Every change to an employee's job assignment (JOB_ID) must be recorded in the EMPLOYEE_HISTORY audit table as a JOB_CHANGE event; NULL job is treated as a distinct value to catch assignments to or from an unassigned state

### TRG_EMP_INSTEAD_OF_DELETE — BEFORE DELETE ON HRMS.EMPLOYEES
- Error -20504: Direct deletion not allowed. Use termination process or set ACTIVE_FLAG to N.
- RULE: Physical deletion of employee records is never permitted; callers must deactivate a record by setting ACTIVE_FLAG to 'N' or by running the formal termination process

### TRG_LEAVE_REQUEST_AUDIT — AFTER UPDATE OF STATUS ON HRMS.LEAVE_REQUESTS
- RULE: Only STATUS column changes on leave requests are subject to audit tracking; updates to other fields (e.g. comments, dates) do not generate an audit record

### TRG_SALARY_AUDIT — AFTER INSERT OR UPDATE OR DELETE ON HRMS.SALARY_RECORDS
- RULE: When a new salary record is inserted, the audit log must capture employee ID, base salary, and effective date to establish the initial compensation record
- RULE: When a salary record is updated, both the previous and new base salary and active status must be preserved in the audit trail to support compensation change reviews
- RULE: When a salary record is deleted, the employee identity and last known salary must be preserved in the audit log to maintain a complete compensation history
- RULE: Only STATUS column changes on leave requests are subject to audit tracking; updates to other fields (e.g. comments, dates) do not generate an audit record

---
## Seed Data

### 01_reference_data.sql — 86 rows
- **LOCATIONS**: 3 rows
- **JOB_GRADES**: 10 rows
- **DEPARTMENTS**: 10 rows
- **JOB_TITLES**: 26 rows
- **LEAVE_TYPES**: 6 rows
- **PAY_ELEMENTS**: 11 rows
- **HOLIDAYS**: 10 rows
- **SYSTEM_PARAMETERS**: 10 rows
### 02_employee_data.sql — 47 rows
- **EMPLOYEES**: 24 rows
- **SALARY_RECORDS**: 23 rows

---
## Business Rules (first 200)

| ID | Source | Category | Rule |
|---|---|---|---|
| BR-0001 | HRMS.PKG_AUDIT | validation_rule | Package uses PRAGMA AUTONOMOUS_TRANSACTION — writes independent of caller |
| BR-0002 | HRMS.PKG_AUDIT | validation_rule | Captures client IP via SYS_CONTEXT for audit trail |
| BR-0003 | HRMS.PKG_AUDIT | validation_rule | Captures Oracle session ID via SYS_CONTEXT for audit trail |
| BR-0004 | HRMS.PKG_AUDIT | known_bug | Exception swallowing: WHEN OTHERS THEN ROLLBACK/NULL — errors silently suppressed |
| BR-0005 | HRMS.PKG_AUDIT.log_action | validation_rule | log_action: Runs in autonomous transaction — committed independently of caller |
| BR-0006 | HRMS.PKG_AUDIT.log_action | validation_rule | log_action: Captures client IP via SYS_CONTEXT('USERENV','IP_ADDRESS') |
| BR-0007 | HRMS.PKG_AUDIT.log_action | validation_rule | log_action: Captures Oracle session ID via SYS_CONTEXT('USERENV','SESSIONID') |
| BR-0008 | HRMS.PKG_AUDIT.log_action | validation_rule | log_action: WHEN OTHERS THEN NULL/ROLLBACK — exceptions silently swallowed |
| BR-0009 | HRMS.PKG_COMMON | business_rule | Only system parameters explicitly flagged as editable (EDITABLE_FLAG = 'Y') may be modified; parameters marked |
| BR-0010 | HRMS.PKG_COMMON | business_rule | _days_between |
| BR-0011 | HRMS.PKG_COMMON | validation_rule | A parameter update must match exactly one editable row; if zero rows are updated the parameter either does not |
| BR-0012 | HRMS.PKG_COMMON | validation_rule | Attempting to modify a non-existent or non-editable system parameter is a fatal error; callers must not silent |
| BR-0013 | HRMS.PKG_COMMON | validation_rule | Saturday and Sunday are not counted as business days; only Monday through Friday increment the business day co |
| BR-0014 | HRMS.PKG_COMMON | validation_rule | Saturday and Sunday are skipped when advancing by business days; only weekdays (Monday through Friday) count t |
| BR-0015 | HRMS.PKG_COMMON | validation_rule | A date falling in October or later belongs to the fiscal year of the following calendar year (e.g. October 202 |
| BR-0016 | HRMS.PKG_COMMON | validation_rule | Fiscal quarters follow the October 1 fiscal year start: Q1 = October–December, Q2 = January–March, Q3 = April– |
| BR-0017 | HRMS.PKG_COMMON | validation_rule | A 10-digit number is formatted as a US domestic number in (NXX) NXX-XXXX notation |
| BR-0018 | HRMS.PKG_COMMON | validation_rule | An 11-digit number starting with '1' is formatted as a US/Canada international number with a +1 prefix; all ot |
| BR-0019 | HRMS.PKG_COMMON | validation_rule | A null SSN or one with fewer than 4 characters cannot be partially unmasked; the entire value is replaced with |
| BR-0020 | HRMS.PKG_COMMON | validation_rule | Format code 'LF' produces "Last, First" display order; any other value (including the default 'FL') produces " |
| BR-0021 | HRMS.PKG_COMMON | validation_rule | Package uses PRAGMA AUTONOMOUS_TRANSACTION — writes independent of caller |
| BR-0022 | HRMS.PKG_COMMON | validation_note | Currency symbol is resolved by ISO code: USD maps to '$', EUR maps to the euro sign (U+20AC), GBP maps to the  |
| BR-0023 | HRMS.PKG_COMMON | validation_note | s |
| BR-0024 | HRMS.PKG_COMMON | validation_note | A valid email address must have a non-empty local part, an '@' symbol, a domain name, and a top-level domain o |
| BR-0025 | HRMS.PKG_COMMON | validation_note | A valid phone number must contain exactly 10 digits (US domestic) or 11 digits (US/Canada with country code) a |
| BR-0026 | HRMS.PKG_COMMON | validation_note | A valid SSN must consist of exactly 9 digits after all non-numeric characters (dashes, spaces) are removed |
| BR-0027 | HRMS.PKG_COMMON | constraint | The fiscal year boundary is month 10 (October); the organisation's fiscal year begins on October 1 |
| BR-0028 | HRMS.PKG_COMMON | constraint | A standard US domestic phone number must contain exactly 10 digits |
| BR-0029 | HRMS.PKG_COMMON | constraint | An 11-digit phone number is only recognised as a valid US/Canada international number if it begins with countr |
| BR-0030 | HRMS.PKG_COMMON | constraint | An SSN must have at least 4 characters for the last-four-digit display to be meaningful |
| BR-0031 | HRMS.PKG_COMMON | known_bug | Exception swallowing: WHEN OTHERS THEN ROLLBACK/NULL — errors silently suppressed |
| BR-0032 | HRMS.PKG_COMMON.log_error | validation_rule | log_error: Runs in autonomous transaction — committed independently of caller |
| BR-0033 | HRMS.PKG_COMMON.log_error | validation_rule | log_error: WHEN OTHERS THEN NULL/ROLLBACK — exceptions silently swallowed |
| BR-0034 | HRMS.PKG_COMMON.log_info | validation_rule | log_info: Runs in autonomous transaction — committed independently of caller |
| BR-0035 | HRMS.PKG_COMMON.log_info | validation_rule | log_info: WHEN OTHERS THEN NULL/ROLLBACK — exceptions silently swallowed |
| BR-0036 | HRMS.PKG_COMMON.get_param | validation_rule | get_param: Buffer v_value capped at VARCHAR2(4000) |
| BR-0037 | HRMS.PKG_COMMON.set_param | business_rule | Only system parameters explicitly flagged as editable (EDITABLE_FLAG = 'Y') may be modified; parameters marked |
| BR-0038 | HRMS.PKG_COMMON.set_param | business_rule | _days_between |
| BR-0039 | HRMS.PKG_COMMON.set_param | validation_rule | A parameter update must match exactly one editable row; if zero rows are updated the parameter either does not |
| BR-0040 | HRMS.PKG_COMMON.set_param | validation_rule | Attempting to modify a non-existent or non-editable system parameter is a fatal error; callers must not silent |
| BR-0041 | HRMS.PKG_COMMON.set_param | error_rule | Error -20900: Parameter not found or not editable: |
| BR-0042 | HRMS.PKG_COMMON.business_days_between | validation_rule | Saturday and Sunday are not counted as business days; only Monday through Friday increment the business day co |
| BR-0043 | HRMS.PKG_COMMON.business_days_between | validation_rule | business_days_between: Uses format mask 'DY' |
| BR-0044 | HRMS.PKG_COMMON.add_business_days | validation_rule | Saturday and Sunday are skipped when advancing by business days; only weekdays (Monday through Friday) count t |
| BR-0045 | HRMS.PKG_COMMON.add_business_days | validation_rule | add_business_days: Uses format mask 'DY' |
| BR-0046 | HRMS.PKG_COMMON.get_fiscal_year | validation_rule | A date falling in October or later belongs to the fiscal year of the following calendar year (e.g. October 202 |
| BR-0047 | HRMS.PKG_COMMON.get_fiscal_quarter | validation_rule | Fiscal quarters follow the October 1 fiscal year start: Q1 = October–December, Q2 = January–March, Q3 = April– |
| BR-0048 | HRMS.PKG_COMMON.format_phone | validation_rule | A 10-digit number is formatted as a US domestic number in (NXX) NXX-XXXX notation |
| BR-0049 | HRMS.PKG_COMMON.format_phone | validation_rule | An 11-digit number starting with '1' is formatted as a US/Canada international number with a +1 prefix; all ot |
| BR-0050 | HRMS.PKG_COMMON.format_ssn_masked | validation_rule | A null SSN or one with fewer than 4 characters cannot be partially unmasked; the entire value is replaced with |
| BR-0051 | HRMS.PKG_COMMON.format_currency | validation_rule | format_currency: Uses format mask 'FM999,999,990.00' |
| BR-0052 | HRMS.PKG_COMMON.format_currency | validation_note | Currency symbol is resolved by ISO code: USD maps to '$', EUR maps to the euro sign (U+20AC), GBP maps to the  |
| BR-0053 | HRMS.PKG_COMMON.format_name | validation_rule | Format code 'LF' produces "Last, First" display order; any other value (including the default 'FL') produces " |
| BR-0054 | HRMS.PKG_COMMON.format_name | validation_note | s |
| BR-0055 | HRMS.PKG_COMMON.is_valid_email | validation_note | A valid email address must have a non-empty local part, an '@' symbol, a domain name, and a top-level domain o |
| BR-0056 | HRMS.PKG_COMMON.is_valid_phone | validation_note | A valid phone number must contain exactly 10 digits (US domestic) or 11 digits (US/Canada with country code) a |
| BR-0057 | HRMS.PKG_COMMON.is_valid_ssn | validation_note | A valid SSN must consist of exactly 9 digits after all non-numeric characters (dashes, spaces) are removed |
| BR-0058 | HRMS.PKG_EMPLOYEE | error_rule | PRAGMA EXCEPTION_INIT e_employee_not_found = -20001 |
| BR-0059 | HRMS.PKG_EMPLOYEE | error_rule | PRAGMA EXCEPTION_INIT e_duplicate_emp_number = -20002 |
| BR-0060 | HRMS.PKG_EMPLOYEE | error_rule | PRAGMA EXCEPTION_INIT e_invalid_department = -20003 |
| BR-0061 | HRMS.PKG_EMPLOYEE | error_rule | PRAGMA EXCEPTION_INIT e_invalid_manager = -20004 |
| BR-0062 | HRMS.PKG_EMPLOYEE | error_rule | PRAGMA EXCEPTION_INIT e_termination_error = -20005 |
| BR-0063 | HRMS.PKG_EMPLOYEE | business_rule | Only departments flagged as active (ACTIVE_FLAG = 'Y') are considered valid for employee assignment |
| BR-0064 | HRMS.PKG_EMPLOYEE | business_rule | Only employees with EMPLOYMENT_STATUS = 'ACTIVE' are eligible to be assigned as a manager |
| BR-0065 | HRMS.PKG_EMPLOYEE | business_rule | Only job titles with ACTIVE_FLAG = 'Y' are valid for assignment to a new employee |
| BR-0066 | HRMS.PKG_EMPLOYEE | business_rule | The current salary is the active salary record that became effective on or before today and whose end date is  |
| BR-0067 | HRMS.PKG_EMPLOYEE | business_rule | When provided, the status filter restricts search results to employees with the specified EMPLOYMENT_STATUS va |
| BR-0068 | HRMS.PKG_EMPLOYEE | business_rule | The most recent active salary record is used as the pre-promotion baseline for computing the percentage salary |
| BR-0069 | HRMS.PKG_EMPLOYEE | business_rule | Only leave requests in PENDING status are identified for automatic cancellation upon employee termination |
| BR-0070 | HRMS.PKG_EMPLOYEE | business_rule | Only currently active salary records (ACTIVE_FLAG = 'Y') are closed upon termination; previously ended records |
| BR-0071 | HRMS.PKG_EMPLOYEE | business_rule | Only currently active pay elements (ACTIVE_FLAG = 'Y') are deactivated at termination; previously ended pay el |
| BR-0072 | HRMS.PKG_EMPLOYEE | business_rule | Only employees with EMPLOYMENT_STATUS = 'ACTIVE' are returned as direct reports; terminated or inactive employ |
| BR-0073 | HRMS.PKG_EMPLOYEE | business_rule | The org chart hierarchy traversal includes only employees with EMPLOYMENT_STATUS = 'ACTIVE'; terminated employ |
| BR-0074 | HRMS.PKG_EMPLOYEE | business_rule | Headcount counts only employees who were actively employed on the specified as-of date — hired on or before th |
| BR-0075 | HRMS.PKG_EMPLOYEE | validation_rule | Department must exist and be active before it can be assigned to an employee |
| BR-0076 | HRMS.PKG_EMPLOYEE | validation_rule | Assigning an inactive or non-existent department to an employee raises an application error |
| BR-0077 | HRMS.PKG_EMPLOYEE | validation_rule | A NULL manager assignment is valid and indicates the employee is at the top of the reporting hierarchy with no |
| BR-0078 | HRMS.PKG_EMPLOYEE | validation_rule | The designated manager must exist in the system and have EMPLOYMENT_STATUS = 'ACTIVE' |
| BR-0079 | HRMS.PKG_EMPLOYEE | validation_rule | Specifying a manager who does not exist or is not currently active raises an application error |
| BR-0080 | HRMS.PKG_EMPLOYEE | validation_rule | When updating an existing employee, the new manager assignment must not create a circular reporting chain |
| BR-0081 | HRMS.PKG_EMPLOYEE | validation_rule | An employee cannot directly or indirectly report to themselves; circular reporting chains are prohibited |
| BR-0082 | HRMS.PKG_EMPLOYEE | validation_rule | Assigning a manager who already reports (directly or indirectly) to this employee creates a circular chain and |
| BR-0083 | HRMS.PKG_EMPLOYEE | validation_rule | Both first name and last name are mandatory fields when creating a new employee record |
| BR-0084 | HRMS.PKG_EMPLOYEE | validation_rule | An employee cannot be created without both a first name and a last name |
| BR-0085 | HRMS.PKG_EMPLOYEE | validation_rule | The job title specified at hire must exist in the JOB_TITLES table and be currently active |
| BR-0086 | HRMS.PKG_EMPLOYEE | validation_rule | Employee starting salary must fall within the minimum and maximum range for their assigned job grade (soft war |
| BR-0087 | HRMS.PKG_EMPLOYEE | validation_rule | A salary record is only created at hire when a starting salary is explicitly provided; employees may be hired  |
| BR-0088 | HRMS.PKG_EMPLOYEE | validation_rule | Employee numbers must be unique; a duplicate generated during concurrent inserts requires the caller to retry  |
| BR-0089 | HRMS.PKG_EMPLOYEE | validation_rule | Employee must exist in the system before their contact or personal information can be updated |
| BR-0090 | HRMS.PKG_EMPLOYEE | validation_rule | Attempting to update a non-existent employee record raises an application error |
| BR-0091 | HRMS.PKG_EMPLOYEE | validation_rule | If the update affects zero rows, an error is raised to signal an unexpected data integrity failure |
| BR-0092 | HRMS.PKG_EMPLOYEE | validation_rule | Zero rows updated after a successful existence check indicates a concurrent deletion between the two operation |
| BR-0093 | HRMS.PKG_EMPLOYEE | validation_rule | Requesting an employee by ID that does not exist in the EMPLOYEES table raises an application error |
| BR-0094 | HRMS.PKG_EMPLOYEE | validation_rule | Requesting an employee by employee number that does not exist in the EMPLOYEES table raises an application err |
| BR-0095 | HRMS.PKG_EMPLOYEE | validation_rule | Only employees with EMPLOYMENT_STATUS = 'ACTIVE' may be transferred; transferring a non-active employee is pro |
| BR-0096 | HRMS.PKG_EMPLOYEE | validation_rule | Attempting to transfer an employee who is not in ACTIVE status raises an application error |
| BR-0097 | HRMS.PKG_EMPLOYEE | validation_rule | A new manager for the transfer is validated (including circular-chain detection) only when one is explicitly p |
| BR-0098 | HRMS.PKG_EMPLOYEE | validation_rule | An employee who is already terminated cannot be terminated again; re-termination is blocked |
| BR-0099 | HRMS.PKG_EMPLOYEE | validation_rule | Attempting to terminate an already-terminated employee raises an application error |
| BR-0100 | HRMS.PKG_EMPLOYEE | validation_rule | All pending leave requests for a terminating employee are automatically cancelled; no manual action is require |
| BR-0101 | HRMS.PKG_EMPLOYEE | validation_rule | A termination notification is sent to the employee's direct manager only when a manager is assigned; top-level |
| BR-0102 | HRMS.PKG_EMPLOYEE | validation_rule | Rehiring an employee overwrites their hire date with the rehire date and clears all prior termination data; th |
| BR-0103 | HRMS.PKG_EMPLOYEE | validation_rule | Attempting to rehire an employee ID that does not exist in the EMPLOYEES table raises an application error |
| BR-0104 | HRMS.PKG_EMPLOYEE | validation_rule | An employee is considered active if and only if their EMPLOYMENT_STATUS column value equals 'ACTIVE' |
| BR-0105 | HRMS.PKG_EMPLOYEE | validation_rule | An employee record is considered invalid if either the first name or the last name is absent |
| BR-0106 | HRMS.PKG_EMPLOYEE | validation_rule | An employee record is considered invalid if no hire date has been recorded |
| BR-0107 | HRMS.PKG_EMPLOYEE | validation_rule | An employee record is considered inconsistent if EMPLOYMENT_STATUS is 'ACTIVE' but ACTIVE_FLAG is not 'Y'; bot |
| BR-0108 | HRMS.PKG_EMPLOYEE | validation_rule | Package uses PRAGMA AUTONOMOUS_TRANSACTION — writes independent of caller |
| BR-0109 | HRMS.PKG_EMPLOYEE | validation_note | When no location is explicitly provided, the employee's work location defaults to the location defined on thei |
| BR-0110 | HRMS.PKG_EMPLOYEE | validation_note | Each field is updated only when a non-NULL value is passed; NULL parameters preserve the existing stored value |
| BR-0111 | HRMS.PKG_EMPLOYEE | validation_note | Job title and work location default to the employee's current values when not explicitly specified in the tran |
| BR-0112 | HRMS.PKG_EMPLOYEE | validation_note | Salary change percentage is calculated only when the employee has a non-zero prior salary; a zero or missing p |
| BR-0113 | HRMS.PKG_EMPLOYEE | validation_note | For currently active employees with no termination date, today's date is substituted as the tenure end point s |
| BR-0114 | HRMS.PKG_EMPLOYEE | constraint | The reporting hierarchy is limited to a maximum depth of 15 levels to prevent unbounded traversal during circu |
| BR-0115 | HRMS.PKG_EMPLOYEE | constraint | The default maximum depth for org chart traversal is 10 levels; callers may override this, but deeper traversa |
| BR-0116 | HRMS.PKG_EMPLOYEE | known_bug | race condition under concurrent inserts - no SELECT FOR UPDATE |
| BR-0117 | HRMS.PKG_EMPLOYEE | known_bug | SQL injection possible via p_last_name if called with unvalidated input |
| BR-0118 | HRMS.PKG_EMPLOYEE | known_bug | Exception swallowing: WHEN OTHERS THEN ROLLBACK/NULL — errors silently suppressed |
| BR-0119 | HRMS.PKG_EMPLOYEE.get_next_emp_id | validation_rule | get_next_emp_id: Uses SELECT FOR UPDATE to lock rows during processing |
| BR-0120 | HRMS.PKG_EMPLOYEE.generate_emp_number | validation_rule | generate_emp_number: WHEN OTHERS THEN NULL/ROLLBACK — exceptions silently swallowed |
| BR-0121 | HRMS.PKG_EMPLOYEE.validate_dept | business_rule | Only departments flagged as active (ACTIVE_FLAG = 'Y') are considered valid for employee assignment |
| BR-0122 | HRMS.PKG_EMPLOYEE.validate_dept | validation_rule | Department must exist and be active before it can be assigned to an employee |
| BR-0123 | HRMS.PKG_EMPLOYEE.validate_dept | validation_rule | Assigning an inactive or non-existent department to an employee raises an application error |
| BR-0124 | HRMS.PKG_EMPLOYEE.validate_dept | error_rule | Error -20003: Invalid or inactive department: |
| BR-0125 | HRMS.PKG_EMPLOYEE.validate_manager | business_rule | Only employees with EMPLOYMENT_STATUS = 'ACTIVE' are eligible to be assigned as a manager |
| BR-0126 | HRMS.PKG_EMPLOYEE.validate_manager | validation_rule | A NULL manager assignment is valid and indicates the employee is at the top of the reporting hierarchy with no |
| BR-0127 | HRMS.PKG_EMPLOYEE.validate_manager | validation_rule | The designated manager must exist in the system and have EMPLOYMENT_STATUS = 'ACTIVE' |
| BR-0128 | HRMS.PKG_EMPLOYEE.validate_manager | validation_rule | Specifying a manager who does not exist or is not currently active raises an application error |
| BR-0129 | HRMS.PKG_EMPLOYEE.validate_manager | validation_rule | When updating an existing employee, the new manager assignment must not create a circular reporting chain |
| BR-0130 | HRMS.PKG_EMPLOYEE.validate_manager | validation_rule | An employee cannot directly or indirectly report to themselves; circular reporting chains are prohibited |
| BR-0131 | HRMS.PKG_EMPLOYEE.validate_manager | validation_rule | Assigning a manager who already reports (directly or indirectly) to this employee creates a circular chain and |
| BR-0132 | HRMS.PKG_EMPLOYEE.validate_manager | error_rule | Error -20004: Invalid or inactive manager: |
| BR-0133 | HRMS.PKG_EMPLOYEE.log_history | validation_rule | log_history: Runs in autonomous transaction — committed independently of caller |
| BR-0134 | HRMS.PKG_EMPLOYEE.log_history | validation_rule | log_history: WHEN OTHERS THEN NULL/ROLLBACK — exceptions silently swallowed |
| BR-0135 | HRMS.PKG_EMPLOYEE.create_employee | business_rule | Only job titles with ACTIVE_FLAG = 'Y' are valid for assignment to a new employee |
| BR-0136 | HRMS.PKG_EMPLOYEE.create_employee | validation_rule | Both first name and last name are mandatory fields when creating a new employee record |
| BR-0137 | HRMS.PKG_EMPLOYEE.create_employee | validation_rule | An employee cannot be created without both a first name and a last name |
| BR-0138 | HRMS.PKG_EMPLOYEE.create_employee | validation_rule | The job title specified at hire must exist in the JOB_TITLES table and be currently active |
| BR-0139 | HRMS.PKG_EMPLOYEE.create_employee | validation_rule | Employee starting salary must fall within the minimum and maximum range for their assigned job grade (soft war |
| BR-0140 | HRMS.PKG_EMPLOYEE.create_employee | validation_rule | A salary record is only created at hire when a starting salary is explicitly provided; employees may be hired  |
| BR-0141 | HRMS.PKG_EMPLOYEE.create_employee | validation_rule | Employee numbers must be unique; a duplicate generated during concurrent inserts requires the caller to retry  |
| BR-0142 | HRMS.PKG_EMPLOYEE.create_employee | validation_rule | create_employee: Uses format mask 'MM/DD/YYYY' |
| BR-0143 | HRMS.PKG_EMPLOYEE.create_employee | validation_note | When no location is explicitly provided, the employee's work location defaults to the location defined on thei |
| BR-0144 | HRMS.PKG_EMPLOYEE.create_employee | error_rule | Error -20010: First name and last name are required |
| BR-0145 | HRMS.PKG_EMPLOYEE.create_employee | error_rule | Error -20011: Invalid or inactive job: |
| BR-0146 | HRMS.PKG_EMPLOYEE.create_employee | error_rule | Error -20002: Duplicate employee number generated. Please retry. |
| BR-0147 | HRMS.PKG_EMPLOYEE.update_employee | validation_rule | Employee must exist in the system before their contact or personal information can be updated |
| BR-0148 | HRMS.PKG_EMPLOYEE.update_employee | validation_rule | Attempting to update a non-existent employee record raises an application error |
| BR-0149 | HRMS.PKG_EMPLOYEE.update_employee | validation_rule | If the update affects zero rows, an error is raised to signal an unexpected data integrity failure |
| BR-0150 | HRMS.PKG_EMPLOYEE.update_employee | validation_rule | Zero rows updated after a successful existence check indicates a concurrent deletion between the two operation |
| BR-0151 | HRMS.PKG_EMPLOYEE.update_employee | validation_note | Each field is updated only when a non-NULL value is passed; NULL parameters preserve the existing stored value |
| BR-0152 | HRMS.PKG_EMPLOYEE.update_employee | error_rule | Error -20001: Employee not found: |
| BR-0153 | HRMS.PKG_EMPLOYEE.get_employee | business_rule | The current salary is the active salary record that became effective on or before today and whose end date is  |
| BR-0154 | HRMS.PKG_EMPLOYEE.get_employee | validation_rule | Requesting an employee by ID that does not exist in the EMPLOYEES table raises an application error |
| BR-0155 | HRMS.PKG_EMPLOYEE.get_employee | error_rule | Error -20001: Employee not found: |
| BR-0156 | HRMS.PKG_EMPLOYEE.get_employee_by_number | validation_rule | Requesting an employee by employee number that does not exist in the EMPLOYEES table raises an application err |
| BR-0157 | HRMS.PKG_EMPLOYEE.get_employee_by_number | error_rule | Error -20001: Employee not found: |
| BR-0158 | HRMS.PKG_EMPLOYEE.search_employees | business_rule | When provided, the status filter restricts search results to employees with the specified EMPLOYMENT_STATUS va |
| BR-0159 | HRMS.PKG_EMPLOYEE.search_employees | validation_rule | search_employees: BUG — dynamic SQL built by concatenating user input (p_last_name etc.) — SQL injection risk |
| BR-0160 | HRMS.PKG_EMPLOYEE.search_employees | validation_rule | search_employees: Uses format mask 'YYYY-MM-DD' |
| BR-0161 | HRMS.PKG_EMPLOYEE.search_employees | validation_rule | search_employees: Uses format mask 'YYYY-MM-DD' |
| BR-0162 | HRMS.PKG_EMPLOYEE.search_employees | validation_rule | search_employees: Buffer v_sql capped at VARCHAR2(4000) |
| BR-0163 | HRMS.PKG_EMPLOYEE.transfer_employee | validation_rule | Only employees with EMPLOYMENT_STATUS = 'ACTIVE' may be transferred; transferring a non-active employee is pro |
| BR-0164 | HRMS.PKG_EMPLOYEE.transfer_employee | validation_rule | Attempting to transfer an employee who is not in ACTIVE status raises an application error |
| BR-0165 | HRMS.PKG_EMPLOYEE.transfer_employee | validation_rule | A new manager for the transfer is validated (including circular-chain detection) only when one is explicitly p |
| BR-0166 | HRMS.PKG_EMPLOYEE.transfer_employee | validation_rule | transfer_employee: Uses SELECT FOR UPDATE to lock rows during processing |
| BR-0167 | HRMS.PKG_EMPLOYEE.transfer_employee | validation_note | Job title and work location default to the employee's current values when not explicitly specified in the tran |
| BR-0168 | HRMS.PKG_EMPLOYEE.transfer_employee | error_rule | Error -20012: Cannot transfer non-active employee. Status: |
| BR-0169 | HRMS.PKG_EMPLOYEE.promote_employee | business_rule | The most recent active salary record is used as the pre-promotion baseline for computing the percentage salary |
| BR-0170 | HRMS.PKG_EMPLOYEE.promote_employee | validation_note | Salary change percentage is calculated only when the employee has a non-zero prior salary; a zero or missing p |
| BR-0171 | HRMS.PKG_EMPLOYEE.terminate_employee | business_rule | Only leave requests in PENDING status are identified for automatic cancellation upon employee termination |
| BR-0172 | HRMS.PKG_EMPLOYEE.terminate_employee | business_rule | Only currently active salary records (ACTIVE_FLAG = 'Y') are closed upon termination; previously ended records |
| BR-0173 | HRMS.PKG_EMPLOYEE.terminate_employee | business_rule | Only currently active pay elements (ACTIVE_FLAG = 'Y') are deactivated at termination; previously ended pay el |
| BR-0174 | HRMS.PKG_EMPLOYEE.terminate_employee | validation_rule | An employee who is already terminated cannot be terminated again; re-termination is blocked |
| BR-0175 | HRMS.PKG_EMPLOYEE.terminate_employee | validation_rule | Attempting to terminate an already-terminated employee raises an application error |
| BR-0176 | HRMS.PKG_EMPLOYEE.terminate_employee | validation_rule | All pending leave requests for a terminating employee are automatically cancelled; no manual action is require |
| BR-0177 | HRMS.PKG_EMPLOYEE.terminate_employee | validation_rule | A termination notification is sent to the employee's direct manager only when a manager is assigned; top-level |
| BR-0178 | HRMS.PKG_EMPLOYEE.terminate_employee | validation_rule | terminate_employee: Uses SELECT FOR UPDATE to lock rows during processing |
| BR-0179 | HRMS.PKG_EMPLOYEE.terminate_employee | validation_rule | terminate_employee: Uses format mask 'MM/DD/YYYY' |
| BR-0180 | HRMS.PKG_EMPLOYEE.terminate_employee | error_rule | Error -20005: Employee |
| BR-0181 | HRMS.PKG_EMPLOYEE.rehire_employee | validation_rule | Rehiring an employee overwrites their hire date with the rehire date and clears all prior termination data; th |
| BR-0182 | HRMS.PKG_EMPLOYEE.rehire_employee | validation_rule | Attempting to rehire an employee ID that does not exist in the EMPLOYEES table raises an application error |
| BR-0183 | HRMS.PKG_EMPLOYEE.rehire_employee | error_rule | Error -20001: Employee not found for rehire: |
| BR-0184 | HRMS.PKG_EMPLOYEE.get_direct_reports | business_rule | Only employees with EMPLOYMENT_STATUS = 'ACTIVE' are returned as direct reports; terminated or inactive employ |
| BR-0185 | HRMS.PKG_EMPLOYEE.get_org_chart | business_rule | The org chart hierarchy traversal includes only employees with EMPLOYMENT_STATUS = 'ACTIVE'; terminated employ |
| BR-0186 | HRMS.PKG_EMPLOYEE.get_headcount_by_dept | business_rule | Headcount counts only employees who were actively employed on the specified as-of date — hired on or before th |
| BR-0187 | HRMS.PKG_EMPLOYEE.get_tenure_years | validation_note | For currently active employees with no termination date, today's date is substituted as the tenure end point s |
| BR-0188 | HRMS.PKG_EMPLOYEE.is_active | validation_rule | An employee is considered active if and only if their EMPLOYMENT_STATUS column value equals 'ACTIVE' |
| BR-0189 | HRMS.PKG_EMPLOYEE.validate_employee | validation_rule | An employee record is considered invalid if either the first name or the last name is absent |
| BR-0190 | HRMS.PKG_EMPLOYEE.validate_employee | validation_rule | An employee record is considered invalid if no hire date has been recorded |
| BR-0191 | HRMS.PKG_EMPLOYEE.validate_employee | validation_rule | An employee record is considered inconsistent if EMPLOYMENT_STATUS is 'ACTIVE' but ACTIVE_FLAG is not 'Y'; bot |
| BR-0192 | HRMS.PKG_INTEGRATION | validation_rule | File I/O uses UTL_FILE with Oracle directory objects |
| BR-0193 | HRMS.PKG_INTEGRATION.generate_gl_journal | validation_rule | generate_gl_journal: Writes file via UTL_FILE (pattern: GL_JOURNAL_) |
| BR-0194 | HRMS.PKG_INTEGRATION.generate_gl_journal | validation_rule | generate_gl_journal: LEGACY fixed-width format for ADP vendor |
| BR-0195 | HRMS.PKG_INTEGRATION.generate_gl_journal | validation_rule | generate_gl_journal: Pipe-delimited output — H/ header row and T/ trailer row |
| BR-0196 | HRMS.PKG_INTEGRATION.generate_gl_journal | validation_rule | generate_gl_journal: GL: EARNING elements = debit; non-EARNING elements = credit |
| BR-0197 | HRMS.PKG_INTEGRATION.generate_gl_journal | validation_rule | generate_gl_journal: Uses format mask 'YYYYMMDD' |
| BR-0198 | HRMS.PKG_INTEGRATION.generate_gl_journal | validation_rule | generate_gl_journal: Uses format mask 'YYYY-MM-DD' |
| BR-0199 | HRMS.PKG_INTEGRATION.generate_gl_journal | validation_rule | generate_gl_journal: Uses format mask 'FM999999990.00' |
| BR-0200 | HRMS.PKG_INTEGRATION.generate_gl_journal | validation_rule | generate_gl_journal: Uses format mask 'FM999999990.00' |

*... and 595 more in business_rules.json*