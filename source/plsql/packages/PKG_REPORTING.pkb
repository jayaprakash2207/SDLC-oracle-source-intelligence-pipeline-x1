CREATE OR REPLACE PACKAGE BODY HRMS.PKG_REPORTING AS
-- ============================================================================
-- PKG_REPORTING - Report Generation Package Body
-- ============================================================================

    PROCEDURE headcount_report(
        p_cursor     OUT t_report_cursor,
        p_as_of_date IN DATE DEFAULT SYSDATE,
        p_dept_id    IN NUMBER DEFAULT NULL,
        p_location   IN VARCHAR2 DEFAULT NULL
    ) IS
    BEGIN
        OPEN p_cursor FOR
            SELECT d.DEPT_NAME, d.COST_CENTER,
                   l.LOCATION_NAME, l.CITY, l.STATE_PROVINCE,
                   COUNT(*) AS HEADCOUNT,
                   -- RULE: Headcount is segmented into three mutually exclusive employment classifications: FULL_TIME, PART_TIME, and CONTRACT
                   SUM(CASE WHEN e.EMPLOYMENT_TYPE = 'FULL_TIME' THEN 1 ELSE 0 END) AS FT_COUNT,
                   SUM(CASE WHEN e.EMPLOYMENT_TYPE = 'PART_TIME' THEN 1 ELSE 0 END) AS PT_COUNT,
                   SUM(CASE WHEN e.EMPLOYMENT_TYPE = 'CONTRACT' THEN 1 ELSE 0 END) AS CONTRACT_COUNT,
                   -- RULE: Gender breakdown uses codes 'M' (male) and 'F' (female); employees with any other gender code are not counted in either gender total
                   SUM(CASE WHEN e.GENDER = 'M' THEN 1 ELSE 0 END) AS MALE_COUNT,
                   SUM(CASE WHEN e.GENDER = 'F' THEN 1 ELSE 0 END) AS FEMALE_COUNT,
                   -- VALIDATION: Average tenure is computed in years by dividing MONTHS_BETWEEN the snapshot date and hire date by 12, rounded to one decimal place
                   ROUND(AVG(MONTHS_BETWEEN(p_as_of_date, e.HIRE_DATE) / 12), 1) AS AVG_TENURE_YEARS
            FROM EMPLOYEES e
            JOIN DEPARTMENTS d ON e.DEPT_ID = d.DEPT_ID
            LEFT JOIN LOCATIONS l ON e.LOCATION_CODE = l.LOCATION_CODE
            -- BUSINESS: Only employees with EMPLOYMENT_STATUS = 'ACTIVE' are included in headcount; inactive, suspended, or terminated records are excluded
            WHERE e.EMPLOYMENT_STATUS = 'ACTIVE'
            -- RULE: Employee must have been hired on or before the reporting snapshot date to be counted in headcount
            AND e.HIRE_DATE <= p_as_of_date
            -- RULE: Employee must not be terminated as of the snapshot date; a NULL termination date or a future termination date both satisfy this requirement
            AND (e.TERMINATION_DATE IS NULL OR e.TERMINATION_DATE > p_as_of_date)
            AND (p_dept_id IS NULL OR e.DEPT_ID = p_dept_id)
            AND (p_location IS NULL OR e.LOCATION_CODE = p_location)
            GROUP BY d.DEPT_NAME, d.COST_CENTER,
                     l.LOCATION_NAME, l.CITY, l.STATE_PROVINCE
            ORDER BY d.DEPT_NAME;
    END headcount_report;

    PROCEDURE compensation_summary(
        p_cursor   OUT t_report_cursor,
        p_dept_id  IN NUMBER DEFAULT NULL,
        p_grade_id IN NUMBER DEFAULT NULL
    ) IS
    BEGIN
        OPEN p_cursor FOR
            SELECT d.DEPT_NAME, g.GRADE_NAME, j.JOB_TITLE,
                   COUNT(*) AS EMP_COUNT,
                   g.MIN_SALARY AS GRADE_MIN,
                   g.MAX_SALARY AS GRADE_MAX,
                   MIN(sr.BASE_SALARY) AS ACTUAL_MIN,
                   MAX(sr.BASE_SALARY) AS ACTUAL_MAX,
                   ROUND(AVG(sr.BASE_SALARY), 2) AS AVG_SALARY,
                   ROUND(MEDIAN(sr.BASE_SALARY), 2) AS MEDIAN_SALARY,
                   -- VALIDATION: Compa-ratio expresses average base salary as a percentage of the grade midpoint ((MIN + MAX) / 2); a value of 100 means pay is exactly at the midpoint
                   ROUND(AVG(sr.BASE_SALARY / ((g.MIN_SALARY + g.MAX_SALARY) / 2)) * 100, 1) AS COMPA_RATIO
            FROM EMPLOYEES e
            JOIN DEPARTMENTS d ON e.DEPT_ID = d.DEPT_ID
            JOIN JOB_TITLES j ON e.JOB_ID = j.JOB_ID
            JOIN JOB_GRADES g ON j.GRADE_ID = g.GRADE_ID
            -- BUSINESS: Only the currently active salary record (ACTIVE_FLAG = 'Y') is used for compensation analysis; historical salary rows are excluded
            JOIN SALARY_RECORDS sr ON e.EMP_ID = sr.EMP_ID AND sr.ACTIVE_FLAG = 'Y'
            -- BUSINESS: Compensation analysis is restricted to employees with EMPLOYMENT_STATUS = 'ACTIVE'
            WHERE e.EMPLOYMENT_STATUS = 'ACTIVE'
            AND (p_dept_id IS NULL OR e.DEPT_ID = p_dept_id)
            AND (p_grade_id IS NULL OR g.GRADE_ID = p_grade_id)
            GROUP BY d.DEPT_NAME, g.GRADE_NAME, j.JOB_TITLE,
                     g.MIN_SALARY, g.MAX_SALARY
            ORDER BY d.DEPT_NAME, g.GRADE_NAME;
    END compensation_summary;

    PROCEDURE turnover_report(
        p_cursor     OUT t_report_cursor,
        p_start_date IN DATE,
        p_end_date   IN DATE,
        p_dept_id    IN NUMBER DEFAULT NULL
    ) IS
    BEGIN
        OPEN p_cursor FOR
            SELECT d.DEPT_NAME,
                   -- RULE: A departure is counted as a termination only when TERMINATION_DATE falls within the specified reporting window (inclusive on both boundaries)
                   COUNT(CASE WHEN e.TERMINATION_DATE BETWEEN p_start_date AND p_end_date
                              THEN 1 END) AS TERMINATIONS,
                   -- RULE: Current headcount reflects employees whose EMPLOYMENT_STATUS is 'ACTIVE' at query time, not as of a historical snapshot date
                   COUNT(CASE WHEN e.EMPLOYMENT_STATUS = 'ACTIVE' THEN 1 END) AS CURRENT_HC,
                   -- VALIDATION: Turnover percentage is terminations divided by total employees hired on or before the period end date; NULLIF guards against division by zero for departments with no eligible employee history
                   ROUND(COUNT(CASE WHEN e.TERMINATION_DATE BETWEEN p_start_date AND p_end_date
                                    THEN 1 END) * 100.0 /
                         NULLIF(COUNT(CASE WHEN e.HIRE_DATE <= p_end_date THEN 1 END), 0), 1) AS TURNOVER_PCT,
                   -- RULE: A departure is classified as voluntary when TERMINATION_REASON = 'VOLUNTARY', indicating the employee resigned or chose to leave
                   COUNT(CASE WHEN e.TERMINATION_REASON = 'VOLUNTARY'
                              AND e.TERMINATION_DATE BETWEEN p_start_date AND p_end_date
                              THEN 1 END) AS VOLUNTARY,
                   -- RULE: A departure is classified as involuntary when TERMINATION_REASON is any value other than 'VOLUNTARY', covering layoffs, dismissals, and other employer-initiated separations
                   COUNT(CASE WHEN e.TERMINATION_REASON != 'VOLUNTARY'
                              AND e.TERMINATION_DATE BETWEEN p_start_date AND p_end_date
                              THEN 1 END) AS INVOLUNTARY,
                   ROUND(AVG(CASE WHEN e.TERMINATION_DATE BETWEEN p_start_date AND p_end_date
                                  THEN MONTHS_BETWEEN(e.TERMINATION_DATE, e.HIRE_DATE) / 12 END), 1)
                       AS AVG_TENURE_AT_EXIT
            FROM EMPLOYEES e
            JOIN DEPARTMENTS d ON e.DEPT_ID = d.DEPT_ID
            WHERE (p_dept_id IS NULL OR e.DEPT_ID = p_dept_id)
            AND e.HIRE_DATE <= p_end_date
            GROUP BY d.DEPT_NAME
            -- RULE: Only departments that had at least one employee hired on or before the period end date are shown; departments with no historical headcount are suppressed from the report
            HAVING COUNT(CASE WHEN e.HIRE_DATE <= p_end_date THEN 1 END) > 0
            ORDER BY TURNOVER_PCT DESC NULLS LAST;
    END turnover_report;

    PROCEDURE new_hires_report(
        p_cursor     OUT t_report_cursor,
        p_start_date IN DATE,
        p_end_date   IN DATE,
        p_dept_id    IN NUMBER DEFAULT NULL
    ) IS
    BEGIN
        OPEN p_cursor FOR
            SELECT e.EMP_NUMBER, e.FIRST_NAME || ' ' || e.LAST_NAME AS EMP_NAME,
                   e.HIRE_DATE, d.DEPT_NAME, j.JOB_TITLE,
                   l.LOCATION_NAME, e.EMPLOYMENT_TYPE,
                   sr.BASE_SALARY,
                   e.MANAGER_EMP_ID,
                   m.FIRST_NAME || ' ' || m.LAST_NAME AS MANAGER_NAME
            FROM EMPLOYEES e
            JOIN DEPARTMENTS d ON e.DEPT_ID = d.DEPT_ID
            JOIN JOB_TITLES j ON e.JOB_ID = j.JOB_ID
            LEFT JOIN LOCATIONS l ON e.LOCATION_CODE = l.LOCATION_CODE
            LEFT JOIN EMPLOYEES m ON e.MANAGER_EMP_ID = m.EMP_ID
            -- BUSINESS: Only the currently active salary record (ACTIVE_FLAG = 'Y') is retrieved; a new hire without an active salary record still appears in the report with a NULL base salary
            LEFT JOIN SALARY_RECORDS sr ON e.EMP_ID = sr.EMP_ID AND sr.ACTIVE_FLAG = 'Y'
            -- BUSINESS: Report is scoped to employees whose hire date falls within the specified date range, capturing all starters in the period
            WHERE e.HIRE_DATE BETWEEN p_start_date AND p_end_date
            AND (p_dept_id IS NULL OR e.DEPT_ID = p_dept_id)
            ORDER BY e.HIRE_DATE DESC;
    END new_hires_report;

    PROCEDURE leave_utilization_report(
        p_cursor  OUT t_report_cursor,
        p_year    IN NUMBER DEFAULT EXTRACT(YEAR FROM SYSDATE),
        p_dept_id IN NUMBER DEFAULT NULL
    ) IS
    BEGIN
        OPEN p_cursor FOR
            SELECT d.DEPT_NAME, lt.LEAVE_TYPE_NAME,
                   COUNT(DISTINCT lb.EMP_ID) AS EMP_COUNT,
                   ROUND(AVG(lb.OPENING_BALANCE + lb.ACCRUED), 1) AS AVG_ENTITLED,
                   ROUND(AVG(lb.USED), 1) AS AVG_USED,
                   -- VALIDATION: Remaining leave balance is computed as opening balance plus accruals minus days used plus manual adjustments; all four components must be combined to reflect the true balance
                   ROUND(AVG(lb.OPENING_BALANCE + lb.ACCRUED - lb.USED + lb.ADJUSTMENT), 1) AS AVG_REMAINING,
                   -- VALIDATION: Utilisation percentage is average days used divided by average days entitled; NULLIF prevents division by zero for leave types where no entitlement balance exists
                   ROUND(AVG(lb.USED) * 100.0 /
                         NULLIF(AVG(lb.OPENING_BALANCE + lb.ACCRUED), 0), 1) AS UTILIZATION_PCT
            FROM LEAVE_BALANCES lb
            JOIN EMPLOYEES e ON lb.EMP_ID = e.EMP_ID
            JOIN DEPARTMENTS d ON e.DEPT_ID = d.DEPT_ID
            JOIN LEAVE_TYPES lt ON lb.LEAVE_TYPE_ID = lt.LEAVE_TYPE_ID
            -- BUSINESS: Leave utilisation data is scoped to a single calendar year; balances from different years are not combined
            WHERE lb.CALENDAR_YEAR = p_year
            -- BUSINESS: Only currently active employees are included; departed employees' unused leave balances are excluded from utilisation analysis
            AND e.EMPLOYMENT_STATUS = 'ACTIVE'
            AND (p_dept_id IS NULL OR e.DEPT_ID = p_dept_id)
            GROUP BY d.DEPT_NAME, lt.LEAVE_TYPE_NAME
            ORDER BY d.DEPT_NAME, lt.LEAVE_TYPE_NAME;
    END leave_utilization_report;

    PROCEDURE payroll_summary_report(
        p_cursor    OUT t_report_cursor,
        p_period_id IN NUMBER
    ) IS
    BEGIN
        OPEN p_cursor FOR
            SELECT d.DEPT_NAME,
                   COUNT(DISTINCT pd.EMP_ID) AS EMP_COUNT,
                   -- RULE: Gross pay is the sum of all payroll lines with ELEMENT_TYPE = 'EARNING'; deduction, benefit, and tax lines are excluded from the gross total
                   SUM(CASE WHEN pd.ELEMENT_TYPE = 'EARNING' THEN pd.AMOUNT ELSE 0 END) AS TOTAL_GROSS,
                   -- CONSTRAINT: Payroll element ID 100 is the hard-coded identifier for Federal Income Tax withholding
                   SUM(CASE WHEN pd.ELEMENT_ID = 100 THEN ABS(pd.AMOUNT) ELSE 0 END) AS TOTAL_FED_TAX,
                   -- CONSTRAINT: Payroll element ID 101 is the hard-coded identifier for State Income Tax withholding
                   SUM(CASE WHEN pd.ELEMENT_ID = 101 THEN ABS(pd.AMOUNT) ELSE 0 END) AS TOTAL_STATE_TAX,
                   -- CONSTRAINT: Payroll element ID 102 is the hard-coded identifier for Social Security (FICA) withholding
                   SUM(CASE WHEN pd.ELEMENT_ID = 102 THEN ABS(pd.AMOUNT) ELSE 0 END) AS TOTAL_SS,
                   -- CONSTRAINT: Payroll element ID 103 is the hard-coded identifier for Medicare withholding
                   SUM(CASE WHEN pd.ELEMENT_ID = 103 THEN ABS(pd.AMOUNT) ELSE 0 END) AS TOTAL_MEDICARE,
                   -- RULE: Total deductions aggregates all lines classified as ELEMENT_TYPE 'DEDUCTION' or 'BENEFIT'; ABS() is applied because these amounts are stored as negative values in PAYROLL_DETAILS
                   SUM(CASE WHEN pd.ELEMENT_TYPE IN ('DEDUCTION','BENEFIT')
                            THEN ABS(pd.AMOUNT) ELSE 0 END) AS TOTAL_DEDUCTIONS,
                   SUM(pd.AMOUNT) AS TOTAL_NET
            FROM PAYROLL_DETAILS pd
            JOIN PAYROLL_RUNS pr ON pd.RUN_ID = pr.RUN_ID
            JOIN EMPLOYEES e ON pd.EMP_ID = e.EMP_ID
            JOIN DEPARTMENTS d ON e.DEPT_ID = d.DEPT_ID
            WHERE pr.PERIOD_ID = p_period_id
            -- RULE: Payroll lines with STATUS = 'ERROR' are excluded from all totals; only successfully processed lines contribute to departmental payroll figures
            AND pd.STATUS != 'ERROR'
            GROUP BY d.DEPT_NAME
            ORDER BY d.DEPT_NAME;
    END payroll_summary_report;

    PROCEDURE eeo_compliance_report(
        p_cursor     OUT t_report_cursor,
        p_as_of_date IN DATE DEFAULT SYSDATE
    ) IS
    BEGIN
        OPEN p_cursor FOR
            SELECT j.EEO_CATEGORY,
                   COUNT(*) AS TOTAL,
                   -- RULE: EEO gender breakdown uses three declared codes — 'M' (male), 'F' (female), 'O' (other/non-binary) — plus a separate count for employees who have not disclosed gender
                   SUM(CASE WHEN e.GENDER = 'M' THEN 1 ELSE 0 END) AS MALE,
                   SUM(CASE WHEN e.GENDER = 'F' THEN 1 ELSE 0 END) AS FEMALE,
                   SUM(CASE WHEN e.GENDER = 'O' THEN 1 ELSE 0 END) AS OTHER_GENDER,
                   -- RULE: Employees with a NULL gender value are counted separately as 'not disclosed' and are not rolled into the male, female, or other gender totals
                   SUM(CASE WHEN e.GENDER IS NULL THEN 1 ELSE 0 END) AS NOT_DISCLOSED,
                   -- VALIDATION: Female representation percentage is female count divided by total active headcount; multiplying by 100.0 ensures decimal precision when dividing integer counts
                   ROUND(SUM(CASE WHEN e.GENDER = 'F' THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 1)
                       AS FEMALE_PCT
            FROM EMPLOYEES e
            JOIN JOB_TITLES j ON e.JOB_ID = j.JOB_ID
            -- BUSINESS: EEO compliance report covers only employees with EMPLOYMENT_STATUS = 'ACTIVE'; former employees are excluded from all compliance headcount figures
            WHERE e.EMPLOYMENT_STATUS = 'ACTIVE'
            -- RULE: Only employees hired on or before the reporting snapshot date are counted; future-dated hires are excluded from the compliance figures
            AND e.HIRE_DATE <= p_as_of_date
            GROUP BY j.EEO_CATEGORY
            ORDER BY j.EEO_CATEGORY;
    END eeo_compliance_report;

    PROCEDURE refresh_reporting_tables(
        p_user IN VARCHAR2 DEFAULT USER
    ) IS
    BEGIN
        -- Placeholder for nightly refresh of denormalized reporting tables
        -- In production, this truncates and repopulates RPT_* tables
        PKG_COMMON.log_info('PKG_REPORTING', 'refresh_reporting_tables',
            'Reporting tables refreshed', p_user);
    END refresh_reporting_tables;

END PKG_REPORTING;
/
