-- ============================================================================
-- HRMS_VALIDATION_LIB - PL/SQL Library (PLL)
-- Client-side validation code shared across forms
--
-- This file represents the source of HRMS_VALIDATION_LIB.pll
-- In Oracle Forms, PLL files are compiled binary; this is the source export.
--
-- NOTE: Many of these validations duplicate server-side logic in PKG_VALIDATION.
-- This duplication is a common issue in Oracle Forms apps - validation runs
-- both client-side (for immediate feedback) and server-side (for security).
-- They can drift out of sync over time.
-- ============================================================================

-- -----------------------------------------------------------------------
-- validate_email
-- Client-side email validation
-- Known drift: Server-side (PKG_VALIDATION) uses REGEXP_LIKE with a
-- more permissive pattern. This version rejects valid emails with
-- subdomains (e.g., user@mail.company.com)
-- -----------------------------------------------------------------------
FUNCTION validate_email(p_email IN VARCHAR2) RETURN BOOLEAN IS
    v_at_pos  NUMBER;
    v_dot_pos NUMBER;
BEGIN
    -- RULE: Email address is not a required field; NULL is treated as valid and bypasses all format checks
    IF p_email IS NULL THEN
        RETURN TRUE;  -- NULL is valid (not required check)
    END IF;

    v_at_pos := INSTR(p_email, '@');
    -- RULE: Email must contain exactly one '@' symbol, which must not appear as the first or last character (both local-part and domain must be non-empty)
    IF v_at_pos = 0 OR v_at_pos = 1 OR v_at_pos = LENGTH(p_email) THEN
        RETURN FALSE;
    END IF;

    v_dot_pos := INSTR(p_email, '.', v_at_pos);
    -- RULE: The domain portion of an email must contain at least one dot, it must not immediately follow '@', and it must not be the final character (a valid TLD must follow)
    IF v_dot_pos = 0 OR v_dot_pos = v_at_pos + 1 OR v_dot_pos = LENGTH(p_email) THEN
        RETURN FALSE;
    END IF;

    -- BUG: Only checks for one dot after @, rejects valid subdomains
    RETURN TRUE;
END validate_email;

-- -----------------------------------------------------------------------
-- validate_phone
-- US phone format validation
-- -----------------------------------------------------------------------
FUNCTION validate_phone(p_phone IN VARCHAR2) RETURN BOOLEAN IS
    v_digits VARCHAR2(20);
BEGIN
    -- RULE: Phone number is not a required field; NULL is treated as valid
    IF p_phone IS NULL THEN
        RETURN TRUE;
    END IF;

    -- Strip non-digits
    v_digits := TRANSLATE(p_phone, '0123456789()-. +x', '0123456789');

    -- US phone: 10 or 11 digits
    -- CONSTRAINT: A valid US phone number must contain exactly 10 digits (local format, no country code) or 11 digits (including the leading country code digit); any other digit count is rejected
    IF LENGTH(v_digits) NOT IN (10, 11) THEN
        RETURN FALSE;
    END IF;

    RETURN TRUE;
END validate_phone;

-- -----------------------------------------------------------------------
-- validate_ssn
-- Social Security Number format validation
-- -----------------------------------------------------------------------
FUNCTION validate_ssn(p_ssn IN VARCHAR2) RETURN BOOLEAN IS
    v_digits VARCHAR2(20);
BEGIN
    -- RULE: SSN is not a required field; NULL is treated as valid
    IF p_ssn IS NULL THEN
        RETURN TRUE;
    END IF;

    v_digits := TRANSLATE(p_ssn, '0123456789-', '0123456789');

    -- CONSTRAINT: A valid SSN must consist of exactly 9 numeric digits after stripping formatting characters (dashes)
    IF LENGTH(v_digits) != 9 THEN
        RETURN FALSE;
    END IF;

    -- Cannot be all zeros in any group
    -- RULE: Each of the three SSN segments must contain at least one non-zero digit: the area number (digits 1-3), the group number (digits 4-5), and the serial number (digits 6-9) must never be all zeros, in accordance with SSA issuance rules
    IF SUBSTR(v_digits, 1, 3) = '000' OR
       SUBSTR(v_digits, 4, 2) = '00' OR
       SUBSTR(v_digits, 6, 4) = '0000' THEN
        RETURN FALSE;
    END IF;

    RETURN TRUE;
END validate_ssn;

-- -----------------------------------------------------------------------
-- validate_date_not_future
-- Ensures date is not in the future
-- -----------------------------------------------------------------------
FUNCTION validate_date_not_future(p_date IN DATE) RETURN BOOLEAN IS
BEGIN
    -- RULE: A date value must not be in the future; only today's date or any prior date is accepted; NULL bypasses the check
    RETURN p_date IS NULL OR TRUNC(p_date) <= TRUNC(SYSDATE);
END validate_date_not_future;

-- -----------------------------------------------------------------------
-- validate_salary_range
-- Checks salary against grade range using cached local data
-- BUG: Uses a hard-coded cache that's populated at form startup
-- and never refreshed. If grade ranges change mid-session, this
-- validation uses stale data.
-- -----------------------------------------------------------------------
FUNCTION validate_salary_range(
    p_salary   IN NUMBER,
    p_grade_id IN NUMBER
) RETURN VARCHAR2 IS
    -- Returns NULL if valid, error message if invalid
    v_min NUMBER;
    v_max NUMBER;
BEGIN
    -- RULE: Salary range validation is skipped when either the salary amount or the job grade identifier is absent; both values must be present for the range check to execute
    IF p_salary IS NULL OR p_grade_id IS NULL THEN
        RETURN NULL;
    END IF;

    -- Direct DB query (not cached - contradicts the comment above)
    -- This is another common pattern: optimistic comment/code mismatch
    -- BUSINESS: Salary boundaries are determined by the employee's assigned job grade; the allowable minimum and maximum pay are read from the JOB_GRADES reference table for the given grade
    SELECT MIN_SALARY, MAX_SALARY INTO v_min, v_max
    FROM JOB_GRADES WHERE GRADE_ID = p_grade_id;

    -- RULE: An employee's salary must not fall below the minimum pay threshold defined for their job grade
    IF p_salary < v_min THEN
        RETURN 'Below minimum (' || TO_CHAR(v_min, 'FM$999,999') || ')';
    -- RULE: An employee's salary must not exceed the maximum pay threshold defined for their job grade
    ELSIF p_salary > v_max THEN
        RETURN 'Exceeds maximum (' || TO_CHAR(v_max, 'FM$999,999') || ')';
    END IF;

    RETURN NULL;
EXCEPTION
    WHEN NO_DATA_FOUND THEN
        RETURN 'Invalid grade';
END validate_salary_range;
