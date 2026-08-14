CREATE OR REPLACE PACKAGE BODY HRMS.PKG_VALIDATION AS
-- ============================================================================
-- PKG_VALIDATION - Centralized Validation Package Body
-- ============================================================================

    FUNCTION validate_date_range(
        p_start_date IN DATE,
        p_end_date   IN DATE
    ) RETURN BOOLEAN IS
    BEGIN
        -- RULE: Both start date and end date must be provided; a null in either makes the range invalid
        IF p_start_date IS NULL OR p_end_date IS NULL THEN
            RETURN FALSE;
        END IF;
        -- RULE: End date must be on or after start date for a valid date range
        RETURN p_end_date >= p_start_date;
    END validate_date_range;

    FUNCTION validate_salary_for_grade(
        p_salary   IN NUMBER,
        p_grade_id IN NUMBER
    ) RETURN VARCHAR2 IS
        v_min NUMBER;
        v_max NUMBER;
        v_grade_name VARCHAR2(50);
    BEGIN
        -- RULE: Both salary amount and job grade must be supplied before salary validation can proceed
        IF p_salary IS NULL OR p_grade_id IS NULL THEN
            RETURN 'Salary and grade are required';
        END IF;

        -- BUSINESS: Look up the minimum and maximum salary boundaries defined for the specified job grade
        SELECT MIN_SALARY, MAX_SALARY, GRADE_NAME
        INTO v_min, v_max, v_grade_name
        FROM JOB_GRADES
        WHERE GRADE_ID = p_grade_id;

        -- RULE: Salary must not fall below the minimum pay band defined for the employee's job grade
        IF p_salary < v_min THEN
            RETURN 'Salary ' || TO_CHAR(p_salary, 'FM$999,999,990.00') ||
                   ' is below minimum for grade ' || v_grade_name ||
                   ' (' || TO_CHAR(v_min, 'FM$999,999,990.00') || ')';
        -- RULE: Salary must not exceed the maximum pay band defined for the employee's job grade
        ELSIF p_salary > v_max THEN
            RETURN 'Salary ' || TO_CHAR(p_salary, 'FM$999,999,990.00') ||
                   ' exceeds maximum for grade ' || v_grade_name ||
                   ' (' || TO_CHAR(v_max, 'FM$999,999,990.00') || ')';
        END IF;

        RETURN NULL;  -- Valid
    EXCEPTION
        WHEN NO_DATA_FOUND THEN
            RETURN 'Invalid grade ID: ' || p_grade_id;
    END validate_salary_for_grade;

    FUNCTION validate_email_format(
        p_email IN VARCHAR2
    ) RETURN BOOLEAN IS
    BEGIN
        RETURN PKG_COMMON.is_valid_email(p_email);
    END validate_email_format;

    FUNCTION validate_phone_format(
        p_phone IN VARCHAR2
    ) RETURN BOOLEAN IS
    BEGIN
        RETURN PKG_COMMON.is_valid_phone(p_phone);
    END validate_phone_format;

    FUNCTION validate_emp_number_format(
        p_emp_number IN VARCHAR2
    ) RETURN BOOLEAN IS
    BEGIN
        -- RULE: Employee number must follow the format EMP- followed by exactly 6 digits (e.g. EMP-001234)
        RETURN REGEXP_LIKE(p_emp_number, '^EMP-\d{6}$');
    END validate_emp_number_format;

    FUNCTION is_future_date(
        p_date IN DATE
    ) RETURN BOOLEAN IS
    BEGIN
        -- RULE: A date qualifies as a future date only if its calendar day is strictly after today; same-day dates are not considered future
        RETURN TRUNC(p_date) > TRUNC(SYSDATE);
    END is_future_date;

    FUNCTION is_business_day(
        p_date          IN DATE,
        p_location_code IN VARCHAR2 DEFAULT NULL
    ) RETURN BOOLEAN IS
        v_day VARCHAR2(3);
        v_holiday_count NUMBER;
    BEGIN
        v_day := TO_CHAR(p_date, 'DY', 'NLS_DATE_LANGUAGE=AMERICAN');
        -- RULE: Saturday and Sunday are never valid business days regardless of location or holiday configuration
        IF v_day IN ('SAT', 'SUN') THEN
            RETURN FALSE;
        END IF;

        -- BUSINESS: Only active holidays (ACTIVE_FLAG = 'Y') that apply globally (LOCATION_CODE IS NULL) or match the specific location block a date from being a business day
        SELECT COUNT(*) INTO v_holiday_count
        FROM HOLIDAYS
        WHERE HOLIDAY_DATE = TRUNC(p_date)
        AND ACTIVE_FLAG = 'Y'
        AND (LOCATION_CODE IS NULL OR LOCATION_CODE = p_location_code);

        -- RULE: A weekday is a valid business day only when no active holiday record exists for that date and location
        RETURN v_holiday_count = 0;
    END is_business_day;

    FUNCTION validate_required_fields(
        p_table_name IN VARCHAR2,
        p_record_id  IN NUMBER
    ) RETURN VARCHAR2 IS
    BEGIN
        -- Simplified validation - in production would use data dictionary
        -- to check NOT NULL columns
        -- RULE: Required-field validation is currently only implemented for the EMPLOYEES table; other tables pass through without checks
        IF p_table_name = 'EMPLOYEES' THEN
            DECLARE
                v_rec EMPLOYEES%ROWTYPE;
            BEGIN
                SELECT * INTO v_rec FROM EMPLOYEES WHERE EMP_ID = p_record_id;
                -- RULE: An employee record must have First Name, Last Name, Hire Date, Department, and Job Title populated before it is considered complete
                IF v_rec.FIRST_NAME IS NULL THEN RETURN 'First Name is required'; END IF;
                IF v_rec.LAST_NAME IS NULL THEN RETURN 'Last Name is required'; END IF;
                IF v_rec.HIRE_DATE IS NULL THEN RETURN 'Hire Date is required'; END IF;
                IF v_rec.DEPT_ID IS NULL THEN RETURN 'Department is required'; END IF;
                IF v_rec.JOB_ID IS NULL THEN RETURN 'Job Title is required'; END IF;
            EXCEPTION
                WHEN NO_DATA_FOUND THEN
                    RETURN 'Record not found';
            END;
        END IF;
        RETURN NULL;
    END validate_required_fields;

END PKG_VALIDATION;
/
