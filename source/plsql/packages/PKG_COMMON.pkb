CREATE OR REPLACE PACKAGE BODY HRMS.PKG_COMMON AS
-- ============================================================================
-- PKG_COMMON - Shared Utility Package Body
-- ============================================================================

    -- -----------------------------------------------------------------------
    -- log_error
    -- Uses autonomous transaction so logging never rolls back main work
    -- -----------------------------------------------------------------------
    PROCEDURE log_error(
        p_package   IN VARCHAR2,
        p_procedure IN VARCHAR2,
        p_message   IN VARCHAR2,
        p_user      IN VARCHAR2 DEFAULT USER
    ) IS
        PRAGMA AUTONOMOUS_TRANSACTION;
    BEGIN
        INSERT INTO AUDIT_LOG (
            AUDIT_ID, TABLE_NAME, RECORD_ID, ACTION_TYPE,
            OLD_VALUES, NEW_VALUES, CHANGED_BY, CHANGED_DATE
        ) VALUES (
            SEQ_AUDIT.NEXTVAL, 'ERROR_LOG', 0, 'INSERT',
            NULL,
            '{"package":"' || p_package || '","procedure":"' || p_procedure ||
            '","message":"' || REPLACE(SUBSTR(p_message, 1, 3000), '"', '\"') || '"}',
            p_user, SYSDATE
        );
        COMMIT;
    EXCEPTION
        WHEN OTHERS THEN
            -- Last resort: write to DBMS_OUTPUT
            DBMS_OUTPUT.PUT_LINE('ERROR LOG FAILED: ' || p_package || '.' ||
                p_procedure || ': ' || p_message);
            ROLLBACK;
    END log_error;

    -- -----------------------------------------------------------------------
    -- log_info
    -- -----------------------------------------------------------------------
    PROCEDURE log_info(
        p_package   IN VARCHAR2,
        p_procedure IN VARCHAR2,
        p_message   IN VARCHAR2,
        p_user      IN VARCHAR2 DEFAULT USER
    ) IS
        PRAGMA AUTONOMOUS_TRANSACTION;
    BEGIN
        INSERT INTO AUDIT_LOG (
            AUDIT_ID, TABLE_NAME, RECORD_ID, ACTION_TYPE,
            NEW_VALUES, CHANGED_BY, CHANGED_DATE
        ) VALUES (
            SEQ_AUDIT.NEXTVAL, 'INFO_LOG', 0, 'INSERT',
            '{"package":"' || p_package || '","procedure":"' || p_procedure ||
            '","message":"' || SUBSTR(p_message, 1, 3000) || '"}',
            p_user, SYSDATE
        );
        COMMIT;
    EXCEPTION
        WHEN OTHERS THEN
            ROLLBACK;
    END log_info;

    -- -----------------------------------------------------------------------
    -- get_param / get_param_number / get_param_date
    -- -----------------------------------------------------------------------
    FUNCTION get_param(
        p_group IN VARCHAR2,
        p_code  IN VARCHAR2
    ) RETURN VARCHAR2 IS
        v_value VARCHAR2(4000);
    BEGIN
        SELECT PARAM_VALUE INTO v_value
        FROM SYSTEM_PARAMETERS
        WHERE PARAM_GROUP = p_group
        AND PARAM_CODE = p_code;

        RETURN v_value;
    EXCEPTION
        WHEN NO_DATA_FOUND THEN
            RETURN NULL;
    END get_param;

    FUNCTION get_param_number(
        p_group IN VARCHAR2,
        p_code  IN VARCHAR2
    ) RETURN NUMBER IS
    BEGIN
        RETURN TO_NUMBER(get_param(p_group, p_code));
    EXCEPTION
        WHEN VALUE_ERROR THEN
            RETURN NULL;
    END get_param_number;

    FUNCTION get_param_date(
        p_group IN VARCHAR2,
        p_code  IN VARCHAR2
    ) RETURN DATE IS
    BEGIN
        RETURN TO_DATE(get_param(p_group, p_code), 'YYYY-MM-DD');
    EXCEPTION
        WHEN OTHERS THEN
            RETURN NULL;
    END get_param_date;

    -- -----------------------------------------------------------------------
    -- set_param
    -- -----------------------------------------------------------------------
    PROCEDURE set_param(
        p_group IN VARCHAR2,
        p_code  IN VARCHAR2,
        p_value IN VARCHAR2,
        p_user  IN VARCHAR2 DEFAULT USER
    ) IS
    BEGIN
        UPDATE SYSTEM_PARAMETERS SET
            PARAM_VALUE = p_value,
            MODIFIED_BY = p_user,
            MODIFIED_DATE = SYSDATE
        WHERE PARAM_GROUP = p_group
        AND PARAM_CODE = p_code
        -- BUSINESS: Only system parameters explicitly flagged as editable (EDITABLE_FLAG = 'Y') may be modified; parameters marked non-editable are protected from update
        AND EDITABLE_FLAG = 'Y';

        -- RULE: A parameter update must match exactly one editable row; if zero rows are updated the parameter either does not exist in the given group/code or has been locked as non-editable
        IF SQL%ROWCOUNT = 0 THEN
            -- RULE: Attempting to modify a non-existent or non-editable system parameter is a fatal error; callers must not silently ignore this condition
            RAISE_APPLICATION_ERROR(-20900,
                'Parameter not found or not editable: ' || p_group || '.' || p_code);
        END IF;
    END set_param;

    -- -----------------------------------------------------------------------
    -- business_days_between
    -- -----------------------------------------------------------------------
    FUNCTION business_days_between(
        p_start_date IN DATE,
        p_end_date   IN DATE
    ) RETURN NUMBER IS
        v_count NUMBER := 0;
        v_date  DATE := TRUNC(p_start_date);
    BEGIN
        WHILE v_date <= TRUNC(p_end_date) LOOP
            -- RULE: Saturday and Sunday are not counted as business days; only Monday through Friday increment the business day counter
            IF TO_CHAR(v_date, 'DY', 'NLS_DATE_LANGUAGE=AMERICAN') NOT IN ('SAT', 'SUN') THEN
                v_count := v_count + 1;
            END IF;
            v_date := v_date + 1;
        END LOOP;
        RETURN v_count;
    END business_days_between;

    -- -----------------------------------------------------------------------
    -- add_business_days
    -- -----------------------------------------------------------------------
    FUNCTION add_business_days(
        p_date IN DATE,
        p_days IN NUMBER
    ) RETURN DATE IS
        v_result DATE := TRUNC(p_date);
        v_added  NUMBER := 0;
    BEGIN
        WHILE v_added < p_days LOOP
            v_result := v_result + 1;
            -- RULE: Saturday and Sunday are skipped when advancing by business days; only weekdays (Monday through Friday) count toward the requested number of days added
            IF TO_CHAR(v_result, 'DY', 'NLS_DATE_LANGUAGE=AMERICAN') NOT IN ('SAT', 'SUN') THEN
                v_added := v_added + 1;
            END IF;
        END LOOP;
        RETURN v_result;
    END add_business_days;

    -- -----------------------------------------------------------------------
    -- get_fiscal_year (fiscal year starts Oct 1)
    -- -----------------------------------------------------------------------
    FUNCTION get_fiscal_year(
        p_date IN DATE DEFAULT SYSDATE
    ) RETURN NUMBER IS
    BEGIN
        -- CONSTRAINT: The fiscal year boundary is month 10 (October); the organisation's fiscal year begins on October 1
        -- RULE: A date falling in October or later belongs to the fiscal year of the following calendar year (e.g. October 2024 is in fiscal year 2025)
        IF EXTRACT(MONTH FROM p_date) >= 10 THEN
            RETURN EXTRACT(YEAR FROM p_date) + 1;
        ELSE
            RETURN EXTRACT(YEAR FROM p_date);
        END IF;
    END get_fiscal_year;

    -- -----------------------------------------------------------------------
    -- get_fiscal_quarter
    -- -----------------------------------------------------------------------
    FUNCTION get_fiscal_quarter(
        p_date IN DATE DEFAULT SYSDATE
    ) RETURN NUMBER IS
        v_month NUMBER := EXTRACT(MONTH FROM p_date);
    BEGIN
        -- RULE: Fiscal quarters follow the October 1 fiscal year start: Q1 = October–December, Q2 = January–March, Q3 = April–June, Q4 = July–September
        RETURN CASE
            WHEN v_month IN (10, 11, 12) THEN 1
            WHEN v_month IN (1, 2, 3) THEN 2
            WHEN v_month IN (4, 5, 6) THEN 3
            WHEN v_month IN (7, 8, 9) THEN 4
        END;
    END get_fiscal_quarter;

    -- -----------------------------------------------------------------------
    -- format_phone
    -- -----------------------------------------------------------------------
    FUNCTION format_phone(
        p_phone IN VARCHAR2
    ) RETURN VARCHAR2 IS
        v_digits VARCHAR2(20);
    BEGIN
        v_digits := REGEXP_REPLACE(p_phone, '[^0-9]', '');
        -- CONSTRAINT: A standard US domestic phone number must contain exactly 10 digits
        -- RULE: A 10-digit number is formatted as a US domestic number in (NXX) NXX-XXXX notation
        IF LENGTH(v_digits) = 10 THEN
            RETURN '(' || SUBSTR(v_digits, 1, 3) || ') ' ||
                   SUBSTR(v_digits, 4, 3) || '-' || SUBSTR(v_digits, 7, 4);
        -- CONSTRAINT: An 11-digit phone number is only recognised as a valid US/Canada international number if it begins with country code '1'
        -- RULE: An 11-digit number starting with '1' is formatted as a US/Canada international number with a +1 prefix; all other lengths or leading digits are returned unmodified
        ELSIF LENGTH(v_digits) = 11 AND SUBSTR(v_digits, 1, 1) = '1' THEN
            RETURN '+1 (' || SUBSTR(v_digits, 2, 3) || ') ' ||
                   SUBSTR(v_digits, 5, 3) || '-' || SUBSTR(v_digits, 8, 4);
        ELSE
            RETURN p_phone;
        END IF;
    END format_phone;

    -- -----------------------------------------------------------------------
    -- format_ssn_masked
    -- -----------------------------------------------------------------------
    FUNCTION format_ssn_masked(
        p_ssn IN VARCHAR2
    ) RETURN VARCHAR2 IS
    BEGIN
        -- CONSTRAINT: An SSN must have at least 4 characters for the last-four-digit display to be meaningful
        -- RULE: A null SSN or one with fewer than 4 characters cannot be partially unmasked; the entire value is replaced with the full mask '***-**-****' to prevent partial PII exposure
        IF p_ssn IS NULL OR LENGTH(p_ssn) < 4 THEN
            RETURN '***-**-****';
        END IF;
        RETURN '***-**-' || SUBSTR(p_ssn, -4);
    END format_ssn_masked;

    -- -----------------------------------------------------------------------
    -- format_currency
    -- -----------------------------------------------------------------------
    FUNCTION format_currency(
        p_amount        IN NUMBER,
        p_currency_code IN VARCHAR2 DEFAULT 'USD'
    ) RETURN VARCHAR2 IS
    BEGIN
        -- VALIDATION: Currency symbol is resolved by ISO code: USD maps to '$', EUR maps to the euro sign (U+20AC), GBP maps to the pound sign (U+00A3); any unrecognised code is prepended as a plain text prefix
        RETURN CASE p_currency_code
            WHEN 'USD' THEN '$'
            WHEN 'EUR' THEN CHR(8364)
            WHEN 'GBP' THEN CHR(163)
            ELSE p_currency_code || ' '
        END || TO_CHAR(p_amount, 'FM999,999,990.00');
    END format_currency;

    -- -----------------------------------------------------------------------
    -- format_name
    -- -----------------------------------------------------------------------
    FUNCTION format_name(
        p_first_name IN VARCHAR2,
        p_last_name  IN VARCHAR2,
        p_format     IN VARCHAR2 DEFAULT 'FL'
    ) RETURN VARCHAR2 IS
    BEGIN
        -- RULE: Format code 'LF' produces "Last, First" display order; any other value (including the default 'FL') produces "First Last" display order
        IF p_format = 'LF' THEN
            RETURN INITCAP(p_last_name) || ', ' || INITCAP(p_first_name);
        ELSE
            RETURN INITCAP(p_first_name) || ' ' || INITCAP(p_last_name);
        END IF;
    END format_name;

    -- -----------------------------------------------------------------------
    -- Validations
    -- -----------------------------------------------------------------------
    FUNCTION is_valid_email(p_email IN VARCHAR2) RETURN BOOLEAN IS
    BEGIN
        -- VALIDATION: A valid email address must have a non-empty local part, an '@' symbol, a domain name, and a top-level domain of at least two alphabetic characters
        RETURN REGEXP_LIKE(p_email, '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$');
    END is_valid_email;

    FUNCTION is_valid_phone(p_phone IN VARCHAR2) RETURN BOOLEAN IS
        v_digits VARCHAR2(20);
    BEGIN
        v_digits := REGEXP_REPLACE(p_phone, '[^0-9]', '');
        -- VALIDATION: A valid phone number must contain exactly 10 digits (US domestic) or 11 digits (US/Canada with country code) after all non-numeric characters are stripped
        RETURN LENGTH(v_digits) BETWEEN 10 AND 11;
    END is_valid_phone;

    FUNCTION is_valid_ssn(p_ssn IN VARCHAR2) RETURN BOOLEAN IS
    BEGIN
        -- VALIDATION: A valid SSN must consist of exactly 9 digits after all non-numeric characters (dashes, spaces) are removed
        RETURN REGEXP_LIKE(REGEXP_REPLACE(p_ssn, '[^0-9]', ''), '^\d{9}$');
    END is_valid_ssn;

END PKG_COMMON;
/
