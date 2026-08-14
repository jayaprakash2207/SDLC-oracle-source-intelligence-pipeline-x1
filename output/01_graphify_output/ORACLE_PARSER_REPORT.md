# Oracle Parser Report — HRMS Source Code

**Total nodes in combined graph:** 338
**Total edges in combined graph:** 451

---

## PL/SQL Packages

**Packages parsed:** 11

### HRMS.PKG_AUDIT
- **Procedures (2):** log_action, purge_old_records
- **Functions (1):** get_change_history
- **Dependencies:** None (base package)
- **Tables used (1):** AUDIT_LOG
- **Package calls:** none

### HRMS.PKG_COMMON
- **Procedures (3):** log_error, log_info, set_param
- **Functions (14):** get_param, get_param_number, get_param_date, business_days_between, add_business_days, get_fiscal_year, get_fiscal_quarter, format_phone, format_ssn_masked, format_currency, format_name, is_valid_email, is_valid_phone, is_valid_ssn
- **Dependencies:** None (base package - no cross-package dependencies)
- **Tables used (6):** P_DATE, SYSTEM_PARAMETERS, UPDATE, AUDIT_LOG, MUST, V_VALUE
- **Package calls:** none

### HRMS.PKG_EMPLOYEE
- **Procedures (7):** update_employee, search_employees, transfer_employee, promote_employee, terminate_employee, rehire_employee, set_session_context
- **Functions (10):** create_employee, get_employee, get_employee_by_number, get_direct_reports, get_org_chart, get_headcount_by_dept, get_tenure_years, is_active, validate_employee, emp_exists
- **Dependencies:** PKG_COMMON, PKG_AUDIT, PKG_NOTIFICATION, PKG_PAYROLL
- **Tables used (36):** SALARY_RECORDS, NOWAIT, EMPLOYEE_HISTORY, V_OLD_REC, V_GRADE_ID, EMPLOYEE_PAY_ELEMENTS, DEPARTMENT, V_ID, V_EMP_ID, V_HIRE_DATE, V_OLD_JOB_ID, PATTERN, EMPLOYEES, JOB_TITLES, LEAVE_REQUESTS, IS, DEPARTMENTS, V_MIN, AFFECTS, THE, V_STATUS, V_MAX_NUM, V_REC, V_PENDING_LEAVE, V_EMP, G_CURRENT_DEPT_ID, V_COUNT, JOB, V_CURRENT_MGR, A, V_OLD_SALARY, EMPLOYEE, JOB_GRADES, V_LOCATION, IN, FAILED
- **Package calls:** PKG_PAYROLL, PKG_NOTIFICATION, PKG_AUDIT, PKG_COMMON, PKG_EMPLOYEE
- **Known issues:**
  - - Circular dependency with PKG_PAYROLL (salary validation)
  - - get_org_chart uses recursive SQL that times out for deep hierarchies

### HRMS.PKG_INTEGRATION
- **Procedures (4):** generate_gl_journal, export_benefits_feed, import_time_attendance, sync_org_structure
- **Functions (1):** get_integration_status
- **Dependencies:** PKG_COMMON, PKG_PAYROLL, PKG_EMPLOYEE
- **Tables used (10):** DEPARTMENTS, PAYROLL, PAY_ELEMENTS, EMPLOYEE_DEPENDENTS, PAYROLL_RUNS, PAYROLL_DETAILS, EMPLOYEES, PAY_PERIODS, CSV, V_IMPORTED
- **Package calls:** PKG_COMMON
- **Known issues:**
  - - GL posting uses flat file exchange (UTL_FILE) instead of API
  - - Benefits feed format is vendor-specific (ADP format)
  - - No retry logic for failed file transfers
  - - FTP credentials stored in SYSTEM_PARAMETERS table (cleartext)

### HRMS.PKG_LEAVE
- **Procedures (10):** approve_leave_request, reject_leave_request, cancel_leave_request, adjust_leave_balance, initialize_balances, run_monthly_accrual, process_carryover, expire_carryover, get_pending_requests, get_team_calendar
- **Functions (4):** submit_leave_request, get_leave_balance, calculate_business_days, check_leave_overlap
- **Dependencies:** PKG_EMPLOYEE, PKG_COMMON, PKG_AUDIT, PKG_NOTIFICATION
- **Tables used (21):** V_EMP_REC, P_START_DATE, HOLIDAYS, LEAVE_BALANCES, LEAVE_TYPES, V_REQUEST_ID, REQUEST, LEAVE_ACCRUAL_LOG, APPROVED, EMPLOYEES, LEAVE_REQUESTS, V_HOLIDAY_COUNT, THE, V_LEAVE_TYPE, BALANCE, BUSINESS, V_COUNT, PENDING, P_ACCRUAL_DATE, V_REQUEST, V_BALANCE
- **Package calls:** PKG_AUDIT, PKG_NOTIFICATION
- **Known issues:**
  - - Overlapping leave detection does not account for half-day requests
  - - Carryover expiry job sometimes double-expires if run twice on same day
  - - Holiday detection only checks exact date match, not observed dates

### HRMS.PKG_NOTIFICATION
- **Procedures (4):** send_notification, process_queue, retry_failed, cancel_notification
- **Functions (0):** none
- **Dependencies:** PKG_COMMON
- **Tables used (4):** V_EMAIL, NOTIFICATION_QUEUE, EMPLOYEES, EMPLOYEE
- **Package calls:** PKG_COMMON
- **Known issues:**
  - - UTL_MAIL configuration hard-coded to legacy SMTP server
  - - No rate limiting - bulk operations can flood the queue
  - - HTML email templates stored as string constants (maintenance nightmare)

### HRMS.PKG_PAYROLL
- **Procedures (9):** create_salary_record, create_pay_periods, close_pay_period, calculate_payroll, calculate_employee_pay, approve_payroll, reverse_payroll, get_payslip, generate_pay_register
- **Functions (8):** get_current_salary, get_salary_as_of, create_payroll_run, calculate_federal_tax, calculate_state_tax, calculate_fica, calculate_medicare, get_ytd_earnings
- **Dependencies:** PKG_EMPLOYEE, PKG_COMMON, PKG_AUDIT, PKG_NOTIFICATION
- **Tables used (27):** SALARY_RECORDS, PP, PAY_ELEMENTS, V_END_DATE, EMPLOYEE_PAY_ELEMENTS, V_PERIOD_ID, V_PERIOD_START, V_START_DATE, V_SALARY, GET_SALARY_AS_OF, V_PERIOD_END, PAYROLL_RUNS, PAYROLL_DETAILS, EMPLOYEES, SS, DEPARTMENTS, STATUS, V_FILING_STATUS, V_PERIOD, THE, V_STATUS, TAX_BRACKETS, EMPLOYEE_TAX_INFO, PAY_PERIODS, RUN, V_YTD, V_RUN_ID
- **Package calls:** PKG_AUDIT, PKG_COMMON
- **Known issues:**
  - - Circular dependency with PKG_EMPLOYEE (is_active check)
  - - Tax calculation uses hard-coded 2024 brackets in some paths
  - - Overtime calculation does not account for holidays correctly
  - - YTD accumulation resets incorrectly for mid-year hires in some edge cases

### HRMS.PKG_PERFORMANCE
- **Procedures (8):** open_review_cycle, close_review_cycle, submit_self_assessment, submit_manager_review, acknowledge_review, update_goal_progress, get_team_reviews, generate_reviews_for_cycle
- **Functions (4):** create_review_cycle, create_review, add_goal, get_rating_distribution
- **Dependencies:** PKG_EMPLOYEE, PKG_COMMON, PKG_AUDIT, PKG_NOTIFICATION
- **Tables used (13):** DEPARTMENTS, V_MANAGER_ID, V_EMP_ID, REVIEW_CYCLES, BULK, THE, V_REVIEW_ID, V_GOAL_ID, PERFORMANCE_REVIEWS, EMPLOYEES, JOB_TITLES, PERFORMANCE_GOALS, V_CYCLE_ID
- **Package calls:** PKG_AUDIT, PKG_NOTIFICATION

### HRMS.PKG_REPORTING
- **Procedures (8):** headcount_report, compensation_summary, turnover_report, new_hires_report, leave_utilization_report, payroll_summary_report, eeo_compliance_report, refresh_reporting_tables
- **Functions (0):** none
- **Dependencies:** PKG_EMPLOYEE, PKG_PAYROLL, PKG_COMMON
- **Tables used (15):** SALARY_RECORDS, DEPARTMENTS, ALL, LEAVE_TYPES, UTILISATION, THE, PAYROLL_DETAILS, LOCATIONS, PAYROLL_RUNS, JOB_TITLES, EMPLOYEES, THREE, LEAVE_BALANCES, JOB_GRADES, DIFFERENT
- **Package calls:** PKG_COMMON
- **Known issues:**
  - - Denormalized reporting tables refreshed nightly; stale during business hours
  - - Some reports use hard-coded fiscal year start (Oct 1)

### HRMS.PKG_SECURITY
- **Procedures (2):** logout, change_password
- **Functions (6):** authenticate, is_session_valid, has_permission, encrypt_ssn, decrypt_ssn, hash_password
- **Dependencies:** PKG_COMMON, PKG_AUDIT
- **Tables used (9):** V_SESSION_ID, V_EMP_ID, USER_SESSIONS, V_STATUS, V_DEPT_ID, WOULD, EMPLOYEES, JOB_TITLES, IS
- **Package calls:** PKG_AUDIT, PKG_EMPLOYEE
- **Known issues:**
  - - Password stored as MD5 hash (should be bcrypt/scrypt)
  - - Session timeout check uses DB server time, not app server time
  - - No account lockout after failed attempts
  - - DBMS_CRYPTO key hard-coded in package body

### HRMS.PKG_VALIDATION
- **Procedures (0):** none
- **Functions (8):** validate_date_range, validate_salary_for_grade, validate_email_format, validate_phone_format, validate_emp_number_format, is_future_date, is_business_day, validate_required_fields
- **Dependencies:** PKG_COMMON
- **Tables used (7):** V_HOLIDAY_COUNT, V_MIN, BEING, V_REC, HOLIDAYS, EMPLOYEES, JOB_GRADES
- **Package calls:** PKG_COMMON

---

## Oracle Forms

**Forms parsed:** 6

### HRMS_EMPLOYEE
- **Title:** HRMS - Employee Maintenance
- **First Block:** EMPLOYEE
- **Blocks (2):** EMPLOYEE, SALARY
- **Triggers (7):** WHEN-NEW-FORM-INSTANCE, ON-ERROR, KEY-EXIT, PRE-INSERT, PRE-UPDATE, POST-QUERY, WHEN-VALIDATE-ITEM
- **LOVs (4):** LOV_DEPARTMENTS, LOV_JOB_TITLES, LOV_MANAGERS, LOV_LOCATIONS
- **Canvases:** CVS_MAIN, CVS_TOOLBAR
- **Libraries:** HRMS_COMMON_LIB, HRMS_VALIDATION_LIB
- **Package calls:** PKG_SECURITY, PKG_VALIDATION, PKG_EMPLOYEE

### HRMS_LEAVE
- **Title:** HRMS - Leave Management
- **First Block:** LEAVE_REQUEST
- **Blocks (3):** LEAVE_REQUEST, NEW_REQUEST, LEAVE_BALANCE
- **Triggers (4):** WHEN-NEW-FORM-INSTANCE, WHEN-BUTTON-PRESSED, POST-QUERY, WHEN-BUTTON-PRESSED
- **LOVs (1):** LOV_LEAVE_TYPES
- **Canvases:** CVS_MAIN
- **Libraries:** HRMS_COMMON_LIB
- **Package calls:** PKG_SECURITY, PKG_LEAVE

### HRMS_LOGIN
- **Title:** HRMS - Login
- **First Block:** LOGIN
- **Blocks (1):** LOGIN
- **Triggers (3):** WHEN-NEW-FORM-INSTANCE, WHEN-BUTTON-PRESSED, KEY-NEXT-ITEM
- **LOVs (0):** 
- **Canvases:** CVS_LOGIN
- **Libraries:** 
- **Package calls:** PKG_SECURITY

### HRMS_MENU
- **Title:** HRMS - Main Menu
- **First Block:** MENU_CONTROL
- **Blocks (1):** MENU_CONTROL
- **Triggers (7):** WHEN-NEW-FORM-INSTANCE, WHEN-BUTTON-PRESSED, WHEN-BUTTON-PRESSED, WHEN-BUTTON-PRESSED, WHEN-BUTTON-PRESSED, WHEN-BUTTON-PRESSED, WHEN-BUTTON-PRESSED
- **LOVs (0):** 
- **Canvases:** CVS_MAIN
- **Libraries:** HRMS_COMMON_LIB
- **Package calls:** PKG_SECURITY

### HRMS_PAYROLL
- **Title:** HRMS - Payroll Processing
- **First Block:** PAY_PERIOD
- **Blocks (2):** PAY_PERIOD, PAYROLL_RUN
- **Triggers (4):** WHEN-NEW-FORM-INSTANCE, WHEN-BUTTON-PRESSED, WHEN-BUTTON-PRESSED, WHEN-BUTTON-PRESSED
- **LOVs (0):** 
- **Canvases:** CVS_MAIN
- **Libraries:** HRMS_COMMON_LIB
- **Package calls:** PKG_SECURITY, PKG_PAYROLL

### HRMS_PERFORMANCE
- **Title:** HRMS - Performance Management
- **First Block:** REVIEW_CYCLE
- **Blocks (3):** REVIEW_CYCLE, PERFORMANCE_REVIEW, PERFORMANCE_GOAL
- **Triggers (2):** WHEN-NEW-FORM-INSTANCE, POST-QUERY
- **LOVs (0):** 
- **Canvases:** CVS_MAIN
- **Libraries:** HRMS_COMMON_LIB
- **Package calls:** PKG_SECURITY

---

## Coverage Summary

| Category | Files | Nodes Extracted |
|---|---|---|
| PL/SQL Packages | 22 (.pks + .pkb) | 21 |
| Procedures | — | 57 |
| Functions | — | 56 |
| Oracle Forms | 6 (.xml) | 6 |
| Form Blocks | — | 12 |
| Form Triggers | — | 19 |
| Tables (referenced) | — | 91 |
| **TOTAL** | **34 files** | **338** |