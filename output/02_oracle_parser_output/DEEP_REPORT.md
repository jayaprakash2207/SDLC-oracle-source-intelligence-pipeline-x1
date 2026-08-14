# Oracle Deep Parser Report — HRMS Source Code (v2 Full Coverage)

## Summary

| Category | Count |
|---|---|
| PL/SQL Packages parsed | 11 |
| Oracle Forms parsed | 6 |
| PLL Libraries parsed | 2 |
| Menu Modules parsed | 1 |
| DDL Tables parsed | 30 |
| Views parsed | 6 |
| DB Triggers parsed | 5 |
| Sequences parsed | 29 |
| Seed data rows | 133 |
| Business rules extracted | 100 |
| Validation rules extracted | 440 |
| Constraints extracted | 33 |
| Known bugs extracted | 17 |
| Error codes extracted | 37 |
| Check constraints extracted | 29 |
| **Total rules** | **656** |

---

## PL/SQL Packages

### HRMS.PKG_AUDIT

**PRAGMA AUTONOMOUS_TRANSACTION: YES**

**Validation Rules (3):**
- Package uses PRAGMA AUTONOMOUS_TRANSACTION — audit/notification writes are independent of caller transactions
- Captures client IP address for audit trail via SYS_CONTEXT
- Captures Oracle session ID for audit trail via SYS_CONTEXT

**Tables accessed (1):** AUDIT_LOG

**Sequences used:** SEQ_AUDIT

### HRMS.PKG_COMMON

**PRAGMA AUTONOMOUS_TRANSACTION: YES**

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
- Package uses PRAGMA AUTONOMOUS_TRANSACTION — audit/notification writes are independent of caller transactions

**Tables accessed (6):** AND, AUDIT_LOG, MUST, P_DATE, SYSTEM_PARAMETERS, UPDATE

**Sequences used:** SEQ_AUDIT

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

**PRAGMA AUTONOMOUS_TRANSACTION: YES**

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
- Package uses PRAGMA AUTONOMOUS_TRANSACTION — audit/notification writes are independent of caller transactions

**Tables accessed (19):** A, AFFECTS, DEPARTMENT, DEPARTMENTS, EMPLOYEE, EMPLOYEES, EMPLOYEE_HISTORY, EMPLOYEE_PAY_ELEMENTS, FAILED, IN, IS, JOB, JOB_GRADES, JOB_TITLES, LEAVE_REQUESTS, NOWAIT, PATTERN, SALARY_RECORDS, THE

**Sequences used:** SEQ_EMP_HISTORY, SEQ_EMPLOYEE

### HRMS.PKG_INTEGRATION
**Known Issues:**
- - GL posting uses flat file exchange (UTL_FILE) instead of API
- - Benefits feed format is vendor-specific (ADP format)
- - No retry logic for failed file transfers
- - FTP credentials stored in SYSTEM_PARAMETERS table (cleartext)

**UTL Packages used:** UTL_FILE

**Validation Rules (1):**
- File I/O uses UTL_FILE with Oracle directory objects

**Tables accessed (5):** CSV, EMPLOYEES, PAYROLL, PAYROLL_DETAILS, V_IMPORTED

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

**Tables accessed (14):** BALANCE, BUSINESS, EMPLOYEES, HOLIDAYS, LEAVE_ACCRUAL_LOG, LEAVE_BALANCES, LEAVE_REQUESTS, LEAVE_TYPES, PENDING, P_ACCRUAL_DATE, P_START_DATE, REQUEST, THE, V_REQUEST

**Sequences used:** SEQ_LEAVE_BALANCE, SEQ_LEAVE_ACCRUAL, SEQ_LEAVE_REQUEST

### HRMS.PKG_NOTIFICATION
**Known Issues:**
- - UTL_MAIL configuration hard-coded to legacy SMTP server
- - No rate limiting - bulk operations can flood the queue
- - HTML email templates stored as string constants (maintenance nightmare)

**PRAGMA AUTONOMOUS_TRANSACTION: YES**

**UTL Packages used:** UTL_SMTP, UTL_TCP

**Validation Rules (3):**
- Package uses PRAGMA AUTONOMOUS_TRANSACTION — audit/notification writes are independent of caller transactions
- Email delivery uses UTL_SMTP (not UTL_MAIL)
- Contains hard-coded configuration values that should be in SYSTEM_PARAMETERS table

**Tables accessed (3):** EMPLOYEE, EMPLOYEES, NOTIFICATION_QUEUE

**Sequences used:** SEQ_NOTIFICATION

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

**UTL Packages used:** UTL_FILE

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
- Contains hard-coded configuration values that should be in SYSTEM_PARAMETERS table

**Tables accessed (17):** EMPLOYEES, EMPLOYEE_PAY_ELEMENTS, EMPLOYEE_TAX_INFO, GET_SALARY_AS_OF, PAYROLL_DETAILS, PAYROLL_RUNS, PAY_PERIODS, PP, RUN, SALARY_RECORDS, SS, STATUS, TAX_BRACKETS, THE, V_END_DATE, V_PERIOD_END, V_START_DATE

**Sequences used:** SEQ_PAYROLL_RUN, SEQ_PAY_PERIOD, SEQ_PAYROLL_DETAIL, SEQ_SALARY

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

**Tables accessed (6):** BULK, EMPLOYEES, PERFORMANCE_GOALS, PERFORMANCE_REVIEWS, REVIEW_CYCLES, THE

**Sequences used:** SEQ_PERF_REVIEW, SEQ_PERF_GOAL, SEQ_REVIEW_CYCLE

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
- Contains hard-coded configuration values that should be in SYSTEM_PARAMETERS table

**Tables accessed (7):** ALL, DIFFERENT, EMPLOYEES, LEAVE_BALANCES, PAYROLL_DETAILS, THE, UTILISATION

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

**UTL Packages used:** UTL_RAW

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
- Contains hard-coded configuration values that should be in SYSTEM_PARAMETERS table

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

**Tables accessed (4):** BEING, EMPLOYEES, HOLIDAYS, JOB_GRADES

---

## PLL Libraries

### HRMS_COMMON_LIB
- Attached by: All HRMS forms via ATTACH_LIBRARY
- Procedures: 2
- Functions: 2

**Validation Rules (6):**
- Toolbar Query button behaviour depends on current form mode — pressing it once opens query mode ('NORMAL'), pressing it again while already in query-entry mode ('ENTER-QUERY') executes the query
- A valid HRMS session ID must exist in the global context before any form operation is permitted — absence of a session ID means the user has not logged in
- Abort form processing when no session exists; the user must authenticate before continuing
- Even when a session ID is present, it must pass the PKG_SECURITY validity check — an ID that fails this check is treated as an expired session, blocking further use of the form
- Abort form processing when the session has expired; the user must re-authenticate
- A record group is only refreshed if it already exists in the form — attempting to populate a non-existent group would raise a runtime error

### HRMS_VALIDATION_LIB
- Attached by: 
- Procedures: 0
- Functions: 5

**Validation Rules (10):**
- Email address is not a required field; NULL is treated as valid and bypasses all format checks
- Email must contain exactly one '@' symbol, which must not appear as the first or last character (both local-part and domain must be non-empty)
- The domain portion of an email must contain at least one dot, it must not immediately follow '@', and it must not be the final character (a valid TLD must follow)
- Phone number is not a required field; NULL is treated as valid
- SSN is not a required field; NULL is treated as valid
- Each of the three SSN segments must contain at least one non-zero digit: the area number (digits 1-3), the group number (digits 4-5), and the serial number (digits 6-9) must never be all zeros, in accordance with SSA issuance rules
- A date value must not be in the future; only today's date or any prior date is accepted; NULL bypasses the check
- Salary range validation is skipped when either the salary amount or the job grade identifier is absent; both values must be present for the range check to execute
- An employee's salary must not fall below the minimum pay threshold defined for their job grade
- An employee's salary must not exceed the maximum pay threshold defined for their job grade

**Known Bugs (2):**
- Only checks for one dot after @, rejects valid subdomains
- Uses a hard-coded cache that's populated at form startup

---

## Menu Module

### HRMS_MENU
- Menu bar: MAIN_MENUBAR
- Menus: File, Edit, Query, Navigate, Modules, Admin
- Total items: 31
- OPEN_FORM calls: HRMS_PERFORMANCE, HRMS_LEAVE, HRMS_PAYROLL, HRMS_EMPLOYEE, HRMS_REPORTS, HRMS_ADMIN
- Security calls: PKG_SECURITY.has_permission
- NOTE: Menu items are enabled/disabled at runtime based on PKG_SECURITY.has_permission() checks in WHEN-NEW-FORM-INSTANCE
- NOTE: Compiled binary: HRMS_MENU.mmb — this file is the source representation

---

## Oracle Forms

### HRMS_EMPLOYEE — HRMS - Employee Maintenance
- Libraries: HRMS_COMMON_LIB, HRMS_VALIDATION_LIB
- Relations: 1
- Canvases: 2
- Windows: 1
- Alerts: 2

**Relations:**
- `EMP_SALARY_REL` → detail block: `SALARY`

**Record Groups / LOV Queries (4):**
- `RG_DEPARTMENTS`: `SELECT DEPT_ID, DEPT_CODE, DEPT_NAME, COST_CENTER FROM HRMS.DEPARTMENTS WHERE ACTIVE_FLAG = 'Y' ORDER BY DEPT_NAME`
- `RG_JOB_TITLES`: `SELECT j.JOB_ID, j.JOB_CODE, j.JOB_TITLE, g.GRADE_NAME FROM HRMS.JOB_TITLES j JOIN HRMS.JOB_GRADES g ON j.GRADE_ID = g.G`
- `RG_MANAGERS`: `SELECT EMP_ID, EMP_NUMBER, FIRST_NAME || ' ' || LAST_NAME AS MANAGER_NAME FROM HRMS.EMPLOYEES WHERE EMPLOYMENT_STATUS = `
- `RG_LOCATIONS`: `SELECT LOCATION_CODE, LOCATION_NAME, CITY, STATE_PROVINCE FROM HRMS.LOCATIONS WHERE ACTIVE_FLAG = 'Y' ORDER BY LOCATION_`

**Validation Rules (7):**
- WHEN-NEW-FORM-INSTANCE: Session must be valid before form operations are permitted
- WHEN-NEW-FORM-INSTANCE: Requires EDIT permission on EMPLOYEE
- WHEN-NEW-FORM-INSTANCE: Insert operations may be disabled based on user permissions
- WHEN-NEW-FORM-INSTANCE: Update operations may be disabled based on user permissions
- WHEN-NEW-FORM-INSTANCE: Delete operations may be disabled based on user permissions
- KEY-EXIT: Manages transaction commit/rollback
- EMPLOYEE.WHEN-VALIDATE-ITEM: Calls PKG_VALIDATION.validate_email_format for server-side validation

### HRMS_LEAVE — HRMS - Leave Management
- Libraries: HRMS_COMMON_LIB
- Relations: 0
- Canvases: 1
- Windows: 1
- Alerts: 1

**Record Groups / LOV Queries (1):**
- `RG_LEAVE_TYPES`: `SELECT LEAVE_TYPE_ID, LEAVE_TYPE_CODE, LEAVE_TYPE_NAME FROM HRMS.LEAVE_TYPES WHERE ACTIVE_FLAG = 'Y' ORDER BY LEAVE_TYPE`

**Validation Rules (1):**
- WHEN-NEW-FORM-INSTANCE: Session must be valid before form operations are permitted

### HRMS_LOGIN — HRMS - Login
- Libraries: 
- Relations: 0
- Canvases: 1
- Windows: 1
- Alerts: 0

### HRMS_MENU — HRMS - Main Menu
- Libraries: HRMS_COMMON_LIB
- Relations: 0
- Canvases: 1
- Windows: 1
- Alerts: 0

**Validation Rules (5):**
- WHEN-NEW-FORM-INSTANCE: Requires VIEW permission on PAYROLL
- WHEN-NEW-FORM-INSTANCE: Requires VIEW permission on ADMIN
- WHEN-NEW-FORM-INSTANCE: Requires VIEW permission on REPORTS
- MENU_CONTROL.WHEN-BUTTON-PRESSED: Requires VIEW permission on PAYROLL
- MENU_CONTROL.WHEN-BUTTON-PRESSED: Requires VIEW permission on REPORTS

### HRMS_PAYROLL — HRMS - Payroll Processing
- Libraries: HRMS_COMMON_LIB
- Relations: 1
- Canvases: 1
- Windows: 1
- Alerts: 0

**Relations:**
- `PERIOD_RUN_REL` → detail block: `PAYROLL_RUN`

**Validation Rules (3):**
- WHEN-NEW-FORM-INSTANCE: Session must be valid before form operations are permitted
- WHEN-NEW-FORM-INSTANCE: Requires VIEW permission on PAYROLL
- PAYROLL_RUN.WHEN-BUTTON-PRESSED: Requires APPROVE permission on PAYROLL

### HRMS_PERFORMANCE — HRMS - Performance Management
- Libraries: HRMS_COMMON_LIB
- Relations: 2
- Canvases: 1
- Windows: 1
- Alerts: 0

**Relations:**
- `CYCLE_REVIEW_REL` → detail block: `PERFORMANCE_REVIEW`
- `REVIEW_GOAL_REL` → detail block: `PERFORMANCE_GOAL`

**Validation Rules (1):**
- WHEN-NEW-FORM-INSTANCE: Session must be valid before form operations are permitted

---

## Sequences

Total: 29 sequences

| Name | Start | Increment | Cache |
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

## Seed Data

### 01_reference_data.sql (86 rows)
- **LOCATIONS**: 3 rows — columns: LOCATION_CODE, LOCATION_NAME, ADDRESS_LINE1, CITY, STATE_PROVINCE, POSTAL_CODE, COUNTRY_CODE, PHONE
- **JOB_GRADES**: 10 rows — columns: GRADE_ID, GRADE_NAME, GRADE_LEVEL, MIN_SALARY, MAX_SALARY, ACTIVE_FLAG, CREATED_BY, CREATED_DATE
- **DEPARTMENTS**: 10 rows — columns: DEPT_ID, DEPT_CODE, DEPT_NAME, COST_CENTER, PARENT_DEPT_ID, MANAGER_EMP_ID, LOCATION_CODE, ACTIVE_FLAG
- **JOB_TITLES**: 26 rows — columns: JOB_ID, JOB_CODE, JOB_TITLE, GRADE_ID, EEO_CATEGORY, ACTIVE_FLAG, CREATED_BY, CREATED_DATE
- **LEAVE_TYPES**: 6 rows — columns: LEAVE_TYPE_ID, LEAVE_TYPE_CODE, LEAVE_TYPE_NAME, ACCRUAL_FLAG, ACCRUAL_RATE, ACCRUAL_FREQUENCY, MAX_BALANCE, CARRYOVER_MAX
- **PAY_ELEMENTS**: 11 rows — columns: ELEMENT_ID, ELEMENT_CODE, ELEMENT_NAME, ELEMENT_TYPE, CALCULATION_TYPE, DEFAULT_AMOUNT, DEFAULT_PERCENTAGE, GL_ACCOUNT_CODE
- **HOLIDAYS**: 10 rows — columns: HOLIDAY_ID, HOLIDAY_NAME, HOLIDAY_DATE, LOCATION_CODE, ACTIVE_FLAG, CREATED_BY, CREATED_DATE
- **SYSTEM_PARAMETERS**: 10 rows — columns: PARAM_ID, PARAM_GROUP, PARAM_CODE, PARAM_VALUE, DESCRIPTION, EDITABLE_FLAG, CREATED_BY, CREATED_DATE

### 02_employee_data.sql (47 rows)
- **EMPLOYEES**: 24 rows — columns: EMP_ID, EMP_NUMBER, FIRST_NAME, LAST_NAME, EMAIL, PHONE_WORK, HIRE_DATE, DEPT_ID
- **SALARY_RECORDS**: 23 rows — columns: SALARY_ID, EMP_ID, EFFECTIVE_DATE, END_DATE, BASE_SALARY, CURRENCY_CODE, PAY_FREQUENCY, SALARY_BASIS

---

## DDL Tables

### HRMS.AUDIT_LOG
- Columns (8): AUDIT_ID, TABLE_NAME, RECORD_ID, ACTION_TYPE, OLD_VALUES, CHANGED_BY, CHANGED_DATE, IP_ADDRESS
- Primary Key: AUDIT_ID
- CHECK: `ACTION_TYPE IN ('INSERT', 'UPDATE', 'DELETE'`

### HRMS.DEPARTMENTS
- Columns (9): DEPT_ID, DEPT_CODE, DEPT_NAME, PARENT_DEPT_ID, MANAGER_EMP_ID, ACTIVE_FLAG, CREATED_BY, CREATED_DATE, MODIFIED_BY
- Primary Key: DEPT_ID
- CHECK: `ACTIVE_FLAG IN ('Y', 'N'`

### HRMS.EMERGENCY_CONTACTS
- Columns (10): CONTACT_ID, EMP_ID, CONTACT_NAME, RELATIONSHIP, PHONE_SECONDARY, PRIORITY_ORDER, ACTIVE_FLAG, CREATED_BY, CREATED_DATE, MODIFIED_BY
- Primary Key: CONTACT_ID
- FK `EMP_ID` → `HRMS.EMPLOYEES(EMP_ID)`

### HRMS.EMPLOYEES
- Columns (23): EMP_ID, EMP_NUMBER, FIRST_NAME, MIDDLE_NAME, DATE_OF_BIRTH, MARITAL_STATUS, SSN_ENCRYPTED, PHONE_WORK, ADDRESS_LINE1, CITY, POSTAL_CODE, HIRE_DATE, TERMINATION_DATE, DEPT_ID, JOB_ID
- Primary Key: EMP_ID
- FK `DEPT_ID` → `HRMS.DEPARTMENTS(DEPT_ID)`
- FK `JOB_ID` → `HRMS.JOB_TITLES(JOB_ID)`
- FK `MANAGER_EMP_ID` → `HRMS.EMPLOYEES(EMP_ID)`
- FK `LOCATION_CODE` → `HRMS.LOCATIONS(LOCATION_CODE)`
- CHECK: `EMPLOYMENT_STATUS IN ('ACTIVE', 'ON_LEAVE', 'SUSPENDED', 'TERMINATED'`
- CHECK: `EMPLOYMENT_TYPE IN ('FULL_TIME', 'PART_TIME', 'CONTRACT', 'INTERN'`
- CHECK: `GENDER IN ('M', 'F', 'O'`

### HRMS.EMPLOYEE_BANK_ACCOUNTS
- Columns (13): BANK_ACCT_ID, EMP_ID, BANK_NAME, ACCOUNT_NUMBER_ENC, ACCOUNT_TYPE, DEPOSIT_TYPE, DEPOSIT_AMOUNT, PRIORITY_ORDER, PRENOTE_SENT, PRENOTE_DATE, CREATED_BY, CREATED_DATE, MODIFIED_BY
- Primary Key: BANK_ACCT_ID
- FK `EMP_ID` → `HRMS.EMPLOYEES(EMP_ID)`
- CHECK: `ACCOUNT_TYPE IN ('CHECKING', 'SAVINGS'`
- CHECK: `DEPOSIT_TYPE IN ('FULL', 'PARTIAL_AMOUNT', 'PARTIAL_PERCENT', 'REMAINDER'`

### HRMS.EMPLOYEE_DEPENDENTS
- Columns (11): DEPENDENT_ID, EMP_ID, FIRST_NAME, LAST_NAME, RELATIONSHIP, DATE_OF_BIRTH, BENEFITS_ENROLLED, ACTIVE_FLAG, CREATED_BY, CREATED_DATE, MODIFIED_BY
- Primary Key: DEPENDENT_ID
- FK `EMP_ID` → `HRMS.EMPLOYEES(EMP_ID)`
- CHECK: `RELATIONSHIP IN ('SPOUSE', 'CHILD', 'PARENT', 'DOMESTIC_PARTNER', 'OTHER'`

### HRMS.EMPLOYEE_HISTORY
- Columns (12): HIST_ID, EMP_ID, CHANGE_TYPE, EFFECTIVE_DATE, OLD_DEPT_ID, OLD_JOB_ID, OLD_MANAGER_ID, OLD_SALARY, OLD_LOCATION, REASON_CODE, CREATED_BY, CREATED_DATE
- Primary Key: HIST_ID
- FK `EMP_ID` → `HRMS.EMPLOYEES(EMP_ID)`
- CHECK: `CHANGE_TYPE IN (
        'HIRE', 'TRANSFER', 'PROMOTION', 'DEMOTION', 'SALARY_CHANGE',
        'TERMINATION', 'REHIRE', 'LEAVE_START', 'LEAVE_END', 'STATUS_CHANGE'
    `

### HRMS.EMPLOYEE_PAY_ELEMENTS
- Columns (10): EMP_ELEMENT_ID, EMP_ID, ELEMENT_ID, EFFECTIVE_DATE, END_DATE, PERCENTAGE, ACTIVE_FLAG, CREATED_BY, CREATED_DATE, MODIFIED_BY
- Primary Key: EMP_ELEMENT_ID
- FK `EMP_ID` → `HRMS.EMPLOYEES(EMP_ID)`
- FK `ELEMENT_ID` → `HRMS.PAY_ELEMENTS(ELEMENT_ID)`

### HRMS.EMPLOYEE_TAX_INFO
- Columns (14): TAX_INFO_ID, EMP_ID, TAX_YEAR, FILING_STATUS, FEDERAL_ALLOWANCES, STATE_ALLOWANCES, ADDITIONAL_FED_WH, ADDITIONAL_STATE_WH, EXEMPT_FLAG, STATE_CODE, ACTIVE_FLAG, CREATED_BY, CREATED_DATE, MODIFIED_BY
- Primary Key: TAX_INFO_ID
- FK `EMP_ID` → `HRMS.EMPLOYEES(EMP_ID)`

### HRMS.HOLIDAYS
- Columns (7): HOLIDAY_ID, HOLIDAY_DATE, HOLIDAY_NAME, LOCATION_CODE, ACTIVE_FLAG, CREATED_BY, CREATED_DATE
- Primary Key: HOLIDAY_ID

### HRMS.JOB_GRADES
- Columns (10): GRADE_ID, GRADE_CODE, GRADE_NAME, MIN_SALARY, MAX_SALARY, OVERTIME_ELIGIBLE, ACTIVE_FLAG, CREATED_BY, CREATED_DATE, MODIFIED_BY
- Primary Key: GRADE_ID
- CHECK: `MAX_SALARY >= MIN_SALARY`

### HRMS.JOB_TITLES
- Columns (9): JOB_ID, JOB_CODE, JOB_TITLE, JOB_FAMILY, EEO_CATEGORY, ACTIVE_FLAG, CREATED_BY, CREATED_DATE, MODIFIED_BY
- Primary Key: JOB_ID
- FK `GRADE_ID` → `HRMS.JOB_GRADES(GRADE_ID)`

### HRMS.LEAVE_ACCRUAL_LOG
- Columns (8): ACCRUAL_ID, EMP_ID, LEAVE_TYPE_ID, ACCRUAL_DATE, ACCRUAL_AMOUNT, BALANCE_AFTER, CREATED_BY, CREATED_DATE
- Primary Key: ACCRUAL_ID
- FK `EMP_ID` → `HRMS.EMPLOYEES(EMP_ID)`
- FK `LEAVE_TYPE_ID` → `HRMS.LEAVE_TYPES(LEAVE_TYPE_ID)`

### HRMS.LEAVE_BALANCES
- Columns (14): BALANCE_ID, EMP_ID, LEAVE_TYPE_ID, CALENDAR_YEAR, OPENING_BALANCE, ACCRUED, USED, ADJUSTMENT, PENDING, AVAILABLE, CARRYOVER_FROM_PREV, CARRYOVER_EXPIRY_DT, CREATED_DATE, MODIFIED_BY
- Primary Key: BALANCE_ID
- FK `EMP_ID` → `HRMS.EMPLOYEES(EMP_ID)`
- FK `LEAVE_TYPE_ID` → `HRMS.LEAVE_TYPES(LEAVE_TYPE_ID)`

### HRMS.LEAVE_REQUESTS
- Columns (14): REQUEST_ID, EMP_ID, LEAVE_TYPE_ID, START_DATE, END_DATE, TOTAL_DAYS, HALF_DAY_FLAG, HALF_DAY_PERIOD, REASON, APPROVER_EMP_ID, APPROVAL_COMMENTS, CANCELLED_DATE, CREATED_DATE, MODIFIED_BY
- Primary Key: REQUEST_ID
- FK `EMP_ID` → `HRMS.EMPLOYEES(EMP_ID)`
- FK `LEAVE_TYPE_ID` → `HRMS.LEAVE_TYPES(LEAVE_TYPE_ID)`
- FK `APPROVER_EMP_ID` → `HRMS.EMPLOYEES(EMP_ID)`
- CHECK: `STATUS IN ('PENDING', 'APPROVED', 'REJECTED', 'CANCELLED', 'TAKEN'`
- CHECK: `END_DATE >= START_DATE`
- CHECK: `HALF_DAY_PERIOD IN ('AM', 'PM', NULL`

### HRMS.LEAVE_TYPES
- Columns (14): LEAVE_TYPE_ID, LEAVE_TYPE_CODE, LEAVE_TYPE_NAME, PAID_FLAG, ACCRUAL_FLAG, ACCRUAL_RATE, MAX_BALANCE, CARRYOVER_EXPIRY, REQUIRES_APPROVAL, REQUIRES_DOCUMENT, ACTIVE_FLAG, CREATED_BY, CREATED_DATE, MODIFIED_BY
- Primary Key: LEAVE_TYPE_ID
- CHECK: `ACCRUAL_FREQUENCY IN ('MONTHLY', 'BIWEEKLY', 'ANNUAL', NULL`

### HRMS.LOCATIONS
- Columns (10): LOCATION_CODE, LOCATION_NAME, ADDRESS_LINE1, CITY, POSTAL_CODE, PHONE_NUMBER, ACTIVE_FLAG, CREATED_BY, CREATED_DATE, MODIFIED_BY
- Primary Key: LOCATION_CODE

### HRMS.LOOKUP_VALUES
- Columns (8): LOOKUP_ID, LOOKUP_TYPE, LOOKUP_CODE, LOOKUP_VALUE, DISPLAY_ORDER, PARENT_LOOKUP_ID, CREATED_BY, CREATED_DATE
- Primary Key: LOOKUP_ID

### HRMS.NOTIFICATION_QUEUE
- Columns (12): NOTIFICATION_ID, RECIPIENT_EMP_ID, NOTIFICATION_TYPE, SUBJECT, BODY, STATUS, PRIORITY, SENT_DATE, RETRY_COUNT, REFERENCE_TABLE, CREATED_BY, CREATED_DATE
- Primary Key: NOTIFICATION_ID
- CHECK: `STATUS IN ('PENDING', 'SENT', 'FAILED', 'CANCELLED'`
- CHECK: `NOTIFICATION_TYPE IN ('EMAIL', 'IN_APP', 'SMS'`

### HRMS.PAYROLL_DETAILS
- Columns (10): DETAIL_ID, RUN_ID, EMP_ID, ELEMENT_ID, ELEMENT_TYPE, HOURS_WORKED, AMOUNT, YTD_AMOUNT, ERROR_MESSAGE, CREATED_DATE
- Primary Key: DETAIL_ID
- FK `RUN_ID` → `HRMS.PAYROLL_RUNS(RUN_ID)`
- FK `EMP_ID` → `HRMS.EMPLOYEES(EMP_ID)`
- FK `ELEMENT_ID` → `HRMS.PAY_ELEMENTS(ELEMENT_ID)`

### HRMS.PAYROLL_RUNS
- Columns (13): RUN_ID, PERIOD_ID, RUN_TYPE, RUN_DATE, STATUS, TOTAL_GROSS, TOTAL_NET, EMPLOYEE_COUNT, SUBMITTED_BY, APPROVED_BY, CREATED_BY, CREATED_DATE, MODIFIED_BY
- Primary Key: RUN_ID
- FK `PERIOD_ID` → `HRMS.PAY_PERIODS(PERIOD_ID)`
- CHECK: `RUN_TYPE IN ('REGULAR', 'SUPPLEMENTAL', 'BONUS', 'FINAL'`
- CHECK: `STATUS IN ('PENDING', 'CALCULATING', 'CALCULATED', 'APPROVED', 'PAID', 'REVERSED', 'ERROR'`

### HRMS.PAY_ELEMENTS
- Columns (14): ELEMENT_ID, ELEMENT_CODE, ELEMENT_NAME, ELEMENT_TYPE, CALCULATION_TYPE, DEFAULT_AMOUNT, TAXABLE_FLAG, PRETAX_FLAG, EMPLOYER_PAID, GL_ACCOUNT_CODE, ACTIVE_FLAG, CREATED_BY, CREATED_DATE, MODIFIED_BY
- Primary Key: ELEMENT_ID
- CHECK: `ELEMENT_TYPE IN ('EARNING', 'DEDUCTION', 'TAX', 'BENEFIT', 'REIMBURSEMENT'`
- CHECK: `CALCULATION_TYPE IN ('FLAT', 'PERCENTAGE', 'HOURS', 'FORMULA'`

### HRMS.PAY_PERIODS
- Columns (11): PERIOD_ID, PERIOD_NAME, PAY_FREQUENCY, PERIOD_START_DATE, PERIOD_END_DATE, PAY_DATE, STATUS, CLOSED_BY, CREATED_BY, CREATED_DATE, MODIFIED_BY
- Primary Key: PERIOD_ID
- CHECK: `STATUS IN ('OPEN', 'PROCESSING', 'CLOSED', 'REVERSED'`

### HRMS.PERFORMANCE_GOALS
- Columns (12): GOAL_ID, REVIEW_ID, EMP_ID, GOAL_TITLE, GOAL_DESCRIPTION, WEIGHT_PCT, TARGET_DATE, PROGRESS_PCT, SELF_RATING, COMMENTS, CREATED_DATE, MODIFIED_BY
- Primary Key: GOAL_ID
- FK `REVIEW_ID` → `HRMS.PERFORMANCE_REVIEWS(REVIEW_ID)`
- FK `EMP_ID` → `HRMS.EMPLOYEES(EMP_ID)`
- CHECK: `STATUS IN ('NOT_STARTED', 'IN_PROGRESS', 'COMPLETED', 'DEFERRED', 'CANCELLED'`
- CHECK: `GOAL_CATEGORY IN ('BUSINESS', 'DEVELOPMENT', 'LEADERSHIP', 'INNOVATION', 'COMPLIANCE'`

### HRMS.PERFORMANCE_REVIEWS
- Columns (14): REVIEW_ID, CYCLE_ID, EMP_ID, REVIEWER_EMP_ID, REVIEW_TYPE, STATUS, OVERALL_RATING, SELF_ASSESSMENT, STRENGTHS, DEVELOPMENT_PLAN, EMPLOYEE_ACK_DATE, CALIBRATION_NOTES, CREATED_DATE, MODIFIED_BY
- Primary Key: REVIEW_ID
- FK `CYCLE_ID` → `HRMS.REVIEW_CYCLES(CYCLE_ID)`
- FK `EMP_ID` → `HRMS.EMPLOYEES(EMP_ID)`
- FK `REVIEWER_EMP_ID` → `HRMS.EMPLOYEES(EMP_ID)`
- CHECK: `STATUS IN ('NOT_STARTED', 'SELF_REVIEW', 'MANAGER_REVIEW', 'MEETING_SCHEDULED', 'COMPLETED', 'ACKNOWLEDGED'`
- CHECK: `OVERALL_RATING BETWEEN 1.0 AND 5.0`

### HRMS.REVIEW_CYCLES
- Columns (10): CYCLE_ID, CYCLE_NAME, CYCLE_YEAR, START_DATE, END_DATE, SELF_REVIEW_DUE, CALIBRATION_DUE, CREATED_BY, CREATED_DATE, MODIFIED_BY
- Primary Key: CYCLE_ID
- CHECK: `STATUS IN ('DRAFT', 'OPEN', 'IN_PROGRESS', 'CALIBRATION', 'CLOSED'`

### HRMS.SALARY_RECORDS
- Columns (13): SALARY_ID, EMP_ID, EFFECTIVE_DATE, END_DATE, CURRENCY_CODE, PAY_FREQUENCY, SALARY_BASIS, CHANGE_REASON, APPROVED_BY, ACTIVE_FLAG, CREATED_BY, CREATED_DATE, MODIFIED_BY
- Primary Key: SALARY_ID
- FK `EMP_ID` → `HRMS.EMPLOYEES(EMP_ID)`
- CHECK: `PAY_FREQUENCY IN ('WEEKLY', 'BIWEEKLY', 'SEMIMONTHLY', 'MONTHLY'`
- CHECK: `SALARY_BASIS IN ('ANNUAL', 'HOURLY'`

### HRMS.SYSTEM_PARAMETERS
- Columns (9): PARAM_ID, PARAM_GROUP, PARAM_CODE, PARAM_VALUE, PARAM_DESCRIPTION, EDITABLE_FLAG, CREATED_BY, CREATED_DATE, MODIFIED_BY
- Primary Key: PARAM_ID

### HRMS.TAX_BRACKETS
- Columns (9): BRACKET_ID, TAX_YEAR, FILING_STATUS, BRACKET_MIN, BRACKET_MAX, BASE_TAX, STATE_CODE, CREATED_BY, CREATED_DATE
- Primary Key: BRACKET_ID
- CHECK: `FILING_STATUS IN ('SINGLE', 'MARRIED_JOINT', 'MARRIED_SEPARATE', 'HEAD_OF_HOUSEHOLD'`

### HRMS.USER_SESSIONS
- Columns (7): SESSION_ID, EMP_ID, USERNAME, LOGIN_TIME, LOGOUT_TIME, FORMS_MODULE, CREATED_DATE
- Primary Key: SESSION_ID
- FK `EMP_ID` → `HRMS.EMPLOYEES(EMP_ID)`

---

## Consolidated Business Rules

Total: 656 rules

| ID | Source | Type | Rule |
|---|---|---|---|
| BR-0001 | HRMS.PKG_AUDIT | validation_rule | Package uses PRAGMA AUTONOMOUS_TRANSACTION — audit/notification writes are independent of caller transactions |
| BR-0002 | HRMS.PKG_AUDIT | validation_rule | Captures client IP address for audit trail via SYS_CONTEXT |
| BR-0003 | HRMS.PKG_AUDIT | validation_rule | Captures Oracle session ID for audit trail via SYS_CONTEXT |
| BR-0004 | HRMS.PKG_AUDIT | known_bug | Exception swallowing: WHEN OTHERS THEN ROLLBACK/NULL — errors silently suppressed |
| BR-0005 | HRMS.PKG_AUDIT.log_action | validation_rule | log_action: Runs in autonomous transaction — changes committed independently of the caller |
| BR-0006 | HRMS.PKG_AUDIT.log_action | validation_rule | log_action: Captures client IP address via SYS_CONTEXT for audit trail |
| BR-0007 | HRMS.PKG_AUDIT.log_action | validation_rule | log_action: Captures Oracle session ID via SYS_CONTEXT for audit trail |
| BR-0008 | HRMS.PKG_AUDIT.log_action | validation_rule | log_action: Silently swallows exceptions — errors are suppressed to protect calling transaction |
| BR-0009 | HRMS.PKG_COMMON | business_rule | Only system parameters explicitly flagged as editable (EDITABLE_FLAG = 'Y') may be modified; parameters marked non-edita |
| BR-0010 | HRMS.PKG_COMMON | business_rule | _days_between |
| BR-0011 | HRMS.PKG_COMMON | validation_rule | A parameter update must match exactly one editable row; if zero rows are updated the parameter either does not exist in  |
| BR-0012 | HRMS.PKG_COMMON | validation_rule | Attempting to modify a non-existent or non-editable system parameter is a fatal error; callers must not silently ignore  |
| BR-0013 | HRMS.PKG_COMMON | validation_rule | Saturday and Sunday are not counted as business days; only Monday through Friday increment the business day counter |
| BR-0014 | HRMS.PKG_COMMON | validation_rule | Saturday and Sunday are skipped when advancing by business days; only weekdays (Monday through Friday) count toward the  |
| BR-0015 | HRMS.PKG_COMMON | validation_rule | A date falling in October or later belongs to the fiscal year of the following calendar year (e.g. October 2024 is in fi |
| BR-0016 | HRMS.PKG_COMMON | validation_rule | Fiscal quarters follow the October 1 fiscal year start: Q1 = October–December, Q2 = January–March, Q3 = April–June, Q4 = |
| BR-0017 | HRMS.PKG_COMMON | validation_rule | A 10-digit number is formatted as a US domestic number in (NXX) NXX-XXXX notation |
| BR-0018 | HRMS.PKG_COMMON | validation_rule | An 11-digit number starting with '1' is formatted as a US/Canada international number with a +1 prefix; all other length |
| BR-0019 | HRMS.PKG_COMMON | validation_rule | A null SSN or one with fewer than 4 characters cannot be partially unmasked; the entire value is replaced with the full  |
| BR-0020 | HRMS.PKG_COMMON | validation_rule | Format code 'LF' produces "Last, First" display order; any other value (including the default 'FL') produces "First Last |
| BR-0021 | HRMS.PKG_COMMON | validation_rule | Package uses PRAGMA AUTONOMOUS_TRANSACTION — audit/notification writes are independent of caller transactions |
| BR-0022 | HRMS.PKG_COMMON | constraint | The fiscal year boundary is month 10 (October); the organisation's fiscal year begins on October 1 |
| BR-0023 | HRMS.PKG_COMMON | constraint | A standard US domestic phone number must contain exactly 10 digits |
| BR-0024 | HRMS.PKG_COMMON | constraint | An 11-digit phone number is only recognised as a valid US/Canada international number if it begins with country code '1' |
| BR-0025 | HRMS.PKG_COMMON | constraint | An SSN must have at least 4 characters for the last-four-digit display to be meaningful |
| BR-0026 | HRMS.PKG_COMMON | known_bug | Exception swallowing: WHEN OTHERS THEN ROLLBACK/NULL — errors silently suppressed |
| BR-0027 | HRMS.PKG_COMMON.log_error | validation_rule | log_error: Runs in autonomous transaction — changes committed independently of the caller |
| BR-0028 | HRMS.PKG_COMMON.log_error | validation_rule | log_error: Silently swallows exceptions — errors are suppressed to protect calling transaction |
| BR-0029 | HRMS.PKG_COMMON.log_info | validation_rule | log_info: Runs in autonomous transaction — changes committed independently of the caller |
| BR-0030 | HRMS.PKG_COMMON.log_info | validation_rule | log_info: Silently swallows exceptions — errors are suppressed to protect calling transaction |
| BR-0031 | HRMS.PKG_COMMON.set_param | business_rule | Only system parameters explicitly flagged as editable (EDITABLE_FLAG = 'Y') may be modified; parameters marked non-edita |
| BR-0032 | HRMS.PKG_COMMON.set_param | business_rule | _days_between |
| BR-0033 | HRMS.PKG_COMMON.set_param | validation_rule | A parameter update must match exactly one editable row; if zero rows are updated the parameter either does not exist in  |
| BR-0034 | HRMS.PKG_COMMON.set_param | validation_rule | Attempting to modify a non-existent or non-editable system parameter is a fatal error; callers must not silently ignore  |
| BR-0035 | HRMS.PKG_COMMON.set_param | error_rule | Error -20900: Parameter not found or not editable:  |
| BR-0036 | HRMS.PKG_COMMON.business_days_between | validation_rule | Saturday and Sunday are not counted as business days; only Monday through Friday increment the business day counter |
| BR-0037 | HRMS.PKG_COMMON.add_business_days | validation_rule | Saturday and Sunday are skipped when advancing by business days; only weekdays (Monday through Friday) count toward the  |
| BR-0038 | HRMS.PKG_COMMON.get_fiscal_year | validation_rule | A date falling in October or later belongs to the fiscal year of the following calendar year (e.g. October 2024 is in fi |
| BR-0039 | HRMS.PKG_COMMON.get_fiscal_quarter | validation_rule | Fiscal quarters follow the October 1 fiscal year start: Q1 = October–December, Q2 = January–March, Q3 = April–June, Q4 = |
| BR-0040 | HRMS.PKG_COMMON.format_phone | validation_rule | A 10-digit number is formatted as a US domestic number in (NXX) NXX-XXXX notation |
| BR-0041 | HRMS.PKG_COMMON.format_phone | validation_rule | An 11-digit number starting with '1' is formatted as a US/Canada international number with a +1 prefix; all other length |
| BR-0042 | HRMS.PKG_COMMON.format_ssn_masked | validation_rule | A null SSN or one with fewer than 4 characters cannot be partially unmasked; the entire value is replaced with the full  |
| BR-0043 | HRMS.PKG_COMMON.format_name | validation_rule | Format code 'LF' produces "Last, First" display order; any other value (including the default 'FL') produces "First Last |
| BR-0044 | HRMS.PKG_EMPLOYEE | business_rule | Only departments flagged as active (ACTIVE_FLAG = 'Y') are considered valid for employee assignment |
| BR-0045 | HRMS.PKG_EMPLOYEE | business_rule | Only employees with EMPLOYMENT_STATUS = 'ACTIVE' are eligible to be assigned as a manager |
| BR-0046 | HRMS.PKG_EMPLOYEE | business_rule | Only job titles with ACTIVE_FLAG = 'Y' are valid for assignment to a new employee |
| BR-0047 | HRMS.PKG_EMPLOYEE | business_rule | The current salary is the active salary record that became effective on or before today and whose end date is either ope |
| BR-0048 | HRMS.PKG_EMPLOYEE | business_rule | When provided, the status filter restricts search results to employees with the specified EMPLOYMENT_STATUS value (e.g., |
| BR-0049 | HRMS.PKG_EMPLOYEE | business_rule | The most recent active salary record is used as the pre-promotion baseline for computing the percentage salary increase |
| BR-0050 | HRMS.PKG_EMPLOYEE | business_rule | Only leave requests in PENDING status are identified for automatic cancellation upon employee termination |
| BR-0051 | HRMS.PKG_EMPLOYEE | business_rule | Only currently active salary records (ACTIVE_FLAG = 'Y') are closed upon termination; previously ended records are not m |
| BR-0052 | HRMS.PKG_EMPLOYEE | business_rule | Only currently active pay elements (ACTIVE_FLAG = 'Y') are deactivated at termination; previously ended pay elements are |
| BR-0053 | HRMS.PKG_EMPLOYEE | business_rule | Only employees with EMPLOYMENT_STATUS = 'ACTIVE' are returned as direct reports; terminated or inactive employees are ex |
| BR-0054 | HRMS.PKG_EMPLOYEE | business_rule | The org chart hierarchy traversal includes only employees with EMPLOYMENT_STATUS = 'ACTIVE'; terminated employees are ex |
| BR-0055 | HRMS.PKG_EMPLOYEE | business_rule | Headcount counts only employees who were actively employed on the specified as-of date — hired on or before that date an |
| BR-0056 | HRMS.PKG_EMPLOYEE | validation_rule | Department must exist and be active before it can be assigned to an employee |
| BR-0057 | HRMS.PKG_EMPLOYEE | validation_rule | Assigning an inactive or non-existent department to an employee raises an application error |
| BR-0058 | HRMS.PKG_EMPLOYEE | validation_rule | A NULL manager assignment is valid and indicates the employee is at the top of the reporting hierarchy with no manager a |
| BR-0059 | HRMS.PKG_EMPLOYEE | validation_rule | The designated manager must exist in the system and have EMPLOYMENT_STATUS = 'ACTIVE' |
| BR-0060 | HRMS.PKG_EMPLOYEE | validation_rule | Specifying a manager who does not exist or is not currently active raises an application error |
| BR-0061 | HRMS.PKG_EMPLOYEE | validation_rule | When updating an existing employee, the new manager assignment must not create a circular reporting chain |
| BR-0062 | HRMS.PKG_EMPLOYEE | validation_rule | An employee cannot directly or indirectly report to themselves; circular reporting chains are prohibited |
| BR-0063 | HRMS.PKG_EMPLOYEE | validation_rule | Assigning a manager who already reports (directly or indirectly) to this employee creates a circular chain and raises an |
| BR-0064 | HRMS.PKG_EMPLOYEE | validation_rule | Both first name and last name are mandatory fields when creating a new employee record |
| BR-0065 | HRMS.PKG_EMPLOYEE | validation_rule | An employee cannot be created without both a first name and a last name |
| BR-0066 | HRMS.PKG_EMPLOYEE | validation_rule | The job title specified at hire must exist in the JOB_TITLES table and be currently active |
| BR-0067 | HRMS.PKG_EMPLOYEE | validation_rule | Employee starting salary must fall within the minimum and maximum range for their assigned job grade (soft warning — man |
| BR-0068 | HRMS.PKG_EMPLOYEE | validation_rule | A salary record is only created at hire when a starting salary is explicitly provided; employees may be hired without an |
| BR-0069 | HRMS.PKG_EMPLOYEE | validation_rule | Employee numbers must be unique; a duplicate generated during concurrent inserts requires the caller to retry the operat |
| BR-0070 | HRMS.PKG_EMPLOYEE | validation_rule | Employee must exist in the system before their contact or personal information can be updated |
| BR-0071 | HRMS.PKG_EMPLOYEE | validation_rule | Attempting to update a non-existent employee record raises an application error |
| BR-0072 | HRMS.PKG_EMPLOYEE | validation_rule | If the update affects zero rows, an error is raised to signal an unexpected data integrity failure |
| BR-0073 | HRMS.PKG_EMPLOYEE | validation_rule | Zero rows updated after a successful existence check indicates a concurrent deletion between the two operations |
| BR-0074 | HRMS.PKG_EMPLOYEE | validation_rule | Requesting an employee by ID that does not exist in the EMPLOYEES table raises an application error |
| BR-0075 | HRMS.PKG_EMPLOYEE | validation_rule | Requesting an employee by employee number that does not exist in the EMPLOYEES table raises an application error |
| BR-0076 | HRMS.PKG_EMPLOYEE | validation_rule | Only employees with EMPLOYMENT_STATUS = 'ACTIVE' may be transferred; transferring a non-active employee is prohibited |
| BR-0077 | HRMS.PKG_EMPLOYEE | validation_rule | Attempting to transfer an employee who is not in ACTIVE status raises an application error |
| BR-0078 | HRMS.PKG_EMPLOYEE | validation_rule | A new manager for the transfer is validated (including circular-chain detection) only when one is explicitly provided; o |
| BR-0079 | HRMS.PKG_EMPLOYEE | validation_rule | An employee who is already terminated cannot be terminated again; re-termination is blocked |
| BR-0080 | HRMS.PKG_EMPLOYEE | validation_rule | Attempting to terminate an already-terminated employee raises an application error |
| BR-0081 | HRMS.PKG_EMPLOYEE | validation_rule | All pending leave requests for a terminating employee are automatically cancelled; no manual action is required from the |
| BR-0082 | HRMS.PKG_EMPLOYEE | validation_rule | A termination notification is sent to the employee's direct manager only when a manager is assigned; top-level employees |
| BR-0083 | HRMS.PKG_EMPLOYEE | validation_rule | Rehiring an employee overwrites their hire date with the rehire date and clears all prior termination data; the employee |
| BR-0084 | HRMS.PKG_EMPLOYEE | validation_rule | Attempting to rehire an employee ID that does not exist in the EMPLOYEES table raises an application error |
| BR-0085 | HRMS.PKG_EMPLOYEE | validation_rule | An employee is considered active if and only if their EMPLOYMENT_STATUS column value equals 'ACTIVE' |
| BR-0086 | HRMS.PKG_EMPLOYEE | validation_rule | An employee record is considered invalid if either the first name or the last name is absent |
| BR-0087 | HRMS.PKG_EMPLOYEE | validation_rule | An employee record is considered invalid if no hire date has been recorded |
| BR-0088 | HRMS.PKG_EMPLOYEE | validation_rule | An employee record is considered inconsistent if EMPLOYMENT_STATUS is 'ACTIVE' but ACTIVE_FLAG is not 'Y'; both fields m |
| BR-0089 | HRMS.PKG_EMPLOYEE | validation_rule | Package uses PRAGMA AUTONOMOUS_TRANSACTION — audit/notification writes are independent of caller transactions |
| BR-0090 | HRMS.PKG_EMPLOYEE | constraint | The reporting hierarchy is limited to a maximum depth of 15 levels to prevent unbounded traversal during circular refere |
| BR-0091 | HRMS.PKG_EMPLOYEE | constraint | The default maximum depth for org chart traversal is 10 levels; callers may override this, but deeper traversal risks ti |
| BR-0092 | HRMS.PKG_EMPLOYEE | known_bug | race condition under concurrent inserts - no SELECT FOR UPDATE |
| BR-0093 | HRMS.PKG_EMPLOYEE | known_bug | SQL injection possible via p_last_name if called with unvalidated input |
| BR-0094 | HRMS.PKG_EMPLOYEE | known_bug | Exception swallowing: WHEN OTHERS THEN ROLLBACK/NULL — errors silently suppressed |
| BR-0095 | HRMS.PKG_EMPLOYEE.validate_dept | business_rule | Only departments flagged as active (ACTIVE_FLAG = 'Y') are considered valid for employee assignment |
| BR-0096 | HRMS.PKG_EMPLOYEE.validate_dept | validation_rule | Department must exist and be active before it can be assigned to an employee |
| BR-0097 | HRMS.PKG_EMPLOYEE.validate_dept | validation_rule | Assigning an inactive or non-existent department to an employee raises an application error |
| BR-0098 | HRMS.PKG_EMPLOYEE.validate_dept | error_rule | Error -20003: Invalid or inactive department:  |
| BR-0099 | HRMS.PKG_EMPLOYEE.validate_manager | business_rule | Only employees with EMPLOYMENT_STATUS = 'ACTIVE' are eligible to be assigned as a manager |
| BR-0100 | HRMS.PKG_EMPLOYEE.validate_manager | validation_rule | A NULL manager assignment is valid and indicates the employee is at the top of the reporting hierarchy with no manager a |
| BR-0101 | HRMS.PKG_EMPLOYEE.validate_manager | validation_rule | The designated manager must exist in the system and have EMPLOYMENT_STATUS = 'ACTIVE' |
| BR-0102 | HRMS.PKG_EMPLOYEE.validate_manager | validation_rule | Specifying a manager who does not exist or is not currently active raises an application error |
| BR-0103 | HRMS.PKG_EMPLOYEE.validate_manager | validation_rule | When updating an existing employee, the new manager assignment must not create a circular reporting chain |
| BR-0104 | HRMS.PKG_EMPLOYEE.validate_manager | validation_rule | An employee cannot directly or indirectly report to themselves; circular reporting chains are prohibited |
| BR-0105 | HRMS.PKG_EMPLOYEE.validate_manager | validation_rule | Assigning a manager who already reports (directly or indirectly) to this employee creates a circular chain and raises an |
| BR-0106 | HRMS.PKG_EMPLOYEE.validate_manager | error_rule | Error -20004: Invalid or inactive manager:  |
| BR-0107 | HRMS.PKG_EMPLOYEE.validate_manager | error_rule | Error -20004: Circular reporting chain detected: Employee  |
| BR-0108 | HRMS.PKG_EMPLOYEE.log_history | validation_rule | log_history: Runs in autonomous transaction — changes committed independently of the caller |
| BR-0109 | HRMS.PKG_EMPLOYEE.log_history | validation_rule | log_history: Silently swallows exceptions — errors are suppressed to protect calling transaction |
| BR-0110 | HRMS.PKG_EMPLOYEE.create_employee | business_rule | Only job titles with ACTIVE_FLAG = 'Y' are valid for assignment to a new employee |
| BR-0111 | HRMS.PKG_EMPLOYEE.create_employee | validation_rule | Both first name and last name are mandatory fields when creating a new employee record |
| BR-0112 | HRMS.PKG_EMPLOYEE.create_employee | validation_rule | An employee cannot be created without both a first name and a last name |
| BR-0113 | HRMS.PKG_EMPLOYEE.create_employee | validation_rule | The job title specified at hire must exist in the JOB_TITLES table and be currently active |
| BR-0114 | HRMS.PKG_EMPLOYEE.create_employee | validation_rule | Employee starting salary must fall within the minimum and maximum range for their assigned job grade (soft warning — man |
| BR-0115 | HRMS.PKG_EMPLOYEE.create_employee | validation_rule | A salary record is only created at hire when a starting salary is explicitly provided; employees may be hired without an |
| BR-0116 | HRMS.PKG_EMPLOYEE.create_employee | validation_rule | Employee numbers must be unique; a duplicate generated during concurrent inserts requires the caller to retry the operat |
| BR-0117 | HRMS.PKG_EMPLOYEE.create_employee | error_rule | Error -20010: First name and last name are required |
| BR-0118 | HRMS.PKG_EMPLOYEE.create_employee | error_rule | Error -20011: Invalid or inactive job:  |
| BR-0119 | HRMS.PKG_EMPLOYEE.create_employee | error_rule | Error -20002: Duplicate employee number generated. Please retry. |
| BR-0120 | HRMS.PKG_EMPLOYEE.update_employee | validation_rule | Employee must exist in the system before their contact or personal information can be updated |
| BR-0121 | HRMS.PKG_EMPLOYEE.update_employee | validation_rule | Attempting to update a non-existent employee record raises an application error |
| BR-0122 | HRMS.PKG_EMPLOYEE.update_employee | validation_rule | If the update affects zero rows, an error is raised to signal an unexpected data integrity failure |
| BR-0123 | HRMS.PKG_EMPLOYEE.update_employee | validation_rule | Zero rows updated after a successful existence check indicates a concurrent deletion between the two operations |
| BR-0124 | HRMS.PKG_EMPLOYEE.update_employee | error_rule | Error -20001: Employee not found:  |
| BR-0125 | HRMS.PKG_EMPLOYEE.update_employee | error_rule | Error -20001: Employee update failed:  |
| BR-0126 | HRMS.PKG_EMPLOYEE.get_employee | business_rule | The current salary is the active salary record that became effective on or before today and whose end date is either ope |
| BR-0127 | HRMS.PKG_EMPLOYEE.get_employee | validation_rule | Requesting an employee by ID that does not exist in the EMPLOYEES table raises an application error |
| BR-0128 | HRMS.PKG_EMPLOYEE.get_employee | error_rule | Error -20001: Employee not found:  |
| BR-0129 | HRMS.PKG_EMPLOYEE.get_employee_by_number | validation_rule | Requesting an employee by employee number that does not exist in the EMPLOYEES table raises an application error |
| BR-0130 | HRMS.PKG_EMPLOYEE.get_employee_by_number | error_rule | Error -20001: Employee not found:  |
| BR-0131 | HRMS.PKG_EMPLOYEE.search_employees | business_rule | When provided, the status filter restricts search results to employees with the specified EMPLOYMENT_STATUS value (e.g., |
| BR-0132 | HRMS.PKG_EMPLOYEE.search_employees | validation_rule | search_employees: BUG — uses dynamic SQL concatenation with user input; vulnerable to SQL injection |
| BR-0133 | HRMS.PKG_EMPLOYEE.transfer_employee | validation_rule | Only employees with EMPLOYMENT_STATUS = 'ACTIVE' may be transferred; transferring a non-active employee is prohibited |
| BR-0134 | HRMS.PKG_EMPLOYEE.transfer_employee | validation_rule | Attempting to transfer an employee who is not in ACTIVE status raises an application error |
| BR-0135 | HRMS.PKG_EMPLOYEE.transfer_employee | validation_rule | A new manager for the transfer is validated (including circular-chain detection) only when one is explicitly provided; o |
| BR-0136 | HRMS.PKG_EMPLOYEE.transfer_employee | error_rule | Error -20012: Cannot transfer non-active employee. Status:  |
| BR-0137 | HRMS.PKG_EMPLOYEE.promote_employee | business_rule | The most recent active salary record is used as the pre-promotion baseline for computing the percentage salary increase |
| BR-0138 | HRMS.PKG_EMPLOYEE.terminate_employee | business_rule | Only leave requests in PENDING status are identified for automatic cancellation upon employee termination |
| BR-0139 | HRMS.PKG_EMPLOYEE.terminate_employee | business_rule | Only currently active salary records (ACTIVE_FLAG = 'Y') are closed upon termination; previously ended records are not m |
| BR-0140 | HRMS.PKG_EMPLOYEE.terminate_employee | business_rule | Only currently active pay elements (ACTIVE_FLAG = 'Y') are deactivated at termination; previously ended pay elements are |
| BR-0141 | HRMS.PKG_EMPLOYEE.terminate_employee | validation_rule | An employee who is already terminated cannot be terminated again; re-termination is blocked |
| BR-0142 | HRMS.PKG_EMPLOYEE.terminate_employee | validation_rule | Attempting to terminate an already-terminated employee raises an application error |
| BR-0143 | HRMS.PKG_EMPLOYEE.terminate_employee | validation_rule | All pending leave requests for a terminating employee are automatically cancelled; no manual action is required from the |
| BR-0144 | HRMS.PKG_EMPLOYEE.terminate_employee | validation_rule | A termination notification is sent to the employee's direct manager only when a manager is assigned; top-level employees |
| BR-0145 | HRMS.PKG_EMPLOYEE.terminate_employee | validation_rule | terminate_employee: LEGACY/stub — marked as placeholder or not fully implemented |
| BR-0146 | HRMS.PKG_EMPLOYEE.terminate_employee | error_rule | Error -20005: Employee  |
| BR-0147 | HRMS.PKG_EMPLOYEE.rehire_employee | validation_rule | Rehiring an employee overwrites their hire date with the rehire date and clears all prior termination data; the employee |
| BR-0148 | HRMS.PKG_EMPLOYEE.rehire_employee | validation_rule | Attempting to rehire an employee ID that does not exist in the EMPLOYEES table raises an application error |
| BR-0149 | HRMS.PKG_EMPLOYEE.rehire_employee | error_rule | Error -20001: Employee not found for rehire:  |
| BR-0150 | HRMS.PKG_EMPLOYEE.get_headcount_by_dept | business_rule | Headcount counts only employees who were actively employed on the specified as-of date — hired on or before that date an |

*... and 506 more rules in business_rules.json*