-- ============================================================================
-- Database Triggers for EMPLOYEES table
-- These triggers enforce business rules at the database level,
-- duplicating logic that also exists in PKG_EMPLOYEE and Forms triggers.
-- This is a common anti-pattern in legacy Oracle Forms applications.
-- ============================================================================

-- -----------------------------------------------------------------------
-- TRG_EMP_BEFORE_INSERT
-- Sets audit columns and validates required fields before insert
-- -----------------------------------------------------------------------
CREATE OR REPLACE TRIGGER HRMS.TRG_EMP_BEFORE_INSERT
BEFORE INSERT ON HRMS.EMPLOYEES
FOR EACH ROW
BEGIN
    -- Set audit columns
    -- RULE: CREATED_BY must be populated; defaults to the current database session user if not supplied by the caller
    IF :NEW.CREATED_BY IS NULL THEN
        :NEW.CREATED_BY := USER;
    END IF;
    -- RULE: CREATED_DATE must be populated; defaults to the current system timestamp if not supplied by the caller
    IF :NEW.CREATED_DATE IS NULL THEN
        :NEW.CREATED_DATE := SYSDATE;
    END IF;

    -- Default active flag
    -- RULE: A new employee record is considered active by default unless ACTIVE_FLAG is explicitly set to a different value
    IF :NEW.ACTIVE_FLAG IS NULL THEN
        :NEW.ACTIVE_FLAG := 'Y';
    END IF;

    -- Default employment status
    -- RULE: A new employee record defaults to ACTIVE employment status unless an alternative status is explicitly provided on insert
    IF :NEW.EMPLOYMENT_STATUS IS NULL THEN
        :NEW.EMPLOYMENT_STATUS := 'ACTIVE';
    END IF;

    -- Validate hire date not too far in the future
    -- CONSTRAINT: Maximum allowed future hire date is 180 days from the current date
    -- RULE: Hire date cannot be more than 180 days in the future, preventing erroneous or speculative pre-dated hires beyond a 6-month planning horizon
    IF :NEW.HIRE_DATE > SYSDATE + 180 THEN
        -- RULE: Inserting an employee with a hire date more than 180 days in the future is not permitted
        RAISE_APPLICATION_ERROR(-20501,
            'Hire date cannot be more than 180 days in the future');
    END IF;

    -- Validate email uniqueness (also enforced by unique constraint, but
    -- this trigger provides a better error message)
    DECLARE
        v_count NUMBER;
    BEGIN
        -- BUSINESS: Only active employees (ACTIVE_FLAG = 'Y') are considered when checking email uniqueness; inactive or terminated employee records do not block reuse of an email address
        SELECT COUNT(*) INTO v_count
        FROM EMPLOYEES
        WHERE UPPER(EMAIL) = UPPER(:NEW.EMAIL)
        AND ACTIVE_FLAG = 'Y';

        -- RULE: An email address already assigned to an active employee cannot be reused for a new employee record
        IF v_count > 0 THEN
            -- RULE: Inserting an employee whose email is already in use by an active employee record is not permitted
            RAISE_APPLICATION_ERROR(-20502,
                'Email address already in use: ' || :NEW.EMAIL);
        END IF;
    END;
END TRG_EMP_BEFORE_INSERT;
/

-- -----------------------------------------------------------------------
-- TRG_EMP_BEFORE_UPDATE
-- Sets modification audit columns and validates state transitions
-- -----------------------------------------------------------------------
CREATE OR REPLACE TRIGGER HRMS.TRG_EMP_BEFORE_UPDATE
BEFORE UPDATE ON HRMS.EMPLOYEES
FOR EACH ROW
BEGIN
    -- VALIDATION: MODIFIED_BY defaults to the current database session user if not supplied, ensuring the audit trail is never blank
    :NEW.MODIFIED_BY := NVL(:NEW.MODIFIED_BY, USER);
    :NEW.MODIFIED_DATE := SYSDATE;

    -- Prevent reactivation of terminated employees via direct UPDATE
    -- (should go through PKG_EMPLOYEE.rehire_employee instead)
    -- RULE: A terminated employee cannot be directly reactivated by changing EMPLOYMENT_STATUS from TERMINATED to ACTIVE via a plain UPDATE; the formal rehire process (PKG_EMPLOYEE.rehire_employee) must be used instead
    IF :OLD.EMPLOYMENT_STATUS = 'TERMINATED' AND :NEW.EMPLOYMENT_STATUS = 'ACTIVE' THEN
        -- RULE: Bypassing the rehire process to reactivate a terminated employee is not permitted
        RAISE_APPLICATION_ERROR(-20503,
            'Cannot directly reactivate a terminated employee. Use the rehire process.');
    END IF;

    -- Log status changes to history
    -- RULE: Every change to an employee's EMPLOYMENT_STATUS must be recorded in the EMPLOYEE_HISTORY audit table with the old and new status values
    IF :OLD.EMPLOYMENT_STATUS != :NEW.EMPLOYMENT_STATUS THEN
        INSERT INTO EMPLOYEE_HISTORY (
            HISTORY_ID, EMP_ID, CHANGE_TYPE, CHANGE_DATE,
            OLD_VALUE, NEW_VALUE, CHANGED_BY, CHANGE_REASON
        ) VALUES (
            SEQ_EMP_HISTORY.NEXTVAL, :NEW.EMP_ID, 'STATUS_CHANGE', SYSDATE,
            :OLD.EMPLOYMENT_STATUS, :NEW.EMPLOYMENT_STATUS,
            NVL(:NEW.MODIFIED_BY, USER), 'Triggered by status update'
        );
    END IF;

    -- Log department transfers
    -- RULE: Every change to an employee's department assignment (DEPT_ID) must be recorded in the EMPLOYEE_HISTORY audit table as a DEPARTMENT_CHANGE event; NULL department is treated as a distinct value to catch assignments to or from an unassigned state
    IF NVL(:OLD.DEPT_ID, -1) != NVL(:NEW.DEPT_ID, -1) THEN
        INSERT INTO EMPLOYEE_HISTORY (
            HISTORY_ID, EMP_ID, CHANGE_TYPE, CHANGE_DATE,
            OLD_VALUE, NEW_VALUE, CHANGED_BY, CHANGE_REASON
        ) VALUES (
            SEQ_EMP_HISTORY.NEXTVAL, :NEW.EMP_ID, 'DEPARTMENT_CHANGE', SYSDATE,
            TO_CHAR(:OLD.DEPT_ID), TO_CHAR(:NEW.DEPT_ID),
            NVL(:NEW.MODIFIED_BY, USER), 'Department transfer'
        );
    END IF;

    -- Log job changes
    -- RULE: Every change to an employee's job assignment (JOB_ID) must be recorded in the EMPLOYEE_HISTORY audit table as a JOB_CHANGE event; NULL job is treated as a distinct value to catch assignments to or from an unassigned state
    IF NVL(:OLD.JOB_ID, -1) != NVL(:NEW.JOB_ID, -1) THEN
        INSERT INTO EMPLOYEE_HISTORY (
            HISTORY_ID, EMP_ID, CHANGE_TYPE, CHANGE_DATE,
            OLD_VALUE, NEW_VALUE, CHANGED_BY, CHANGE_REASON
        ) VALUES (
            SEQ_EMP_HISTORY.NEXTVAL, :NEW.EMP_ID, 'JOB_CHANGE', SYSDATE,
            TO_CHAR(:OLD.JOB_ID), TO_CHAR(:NEW.JOB_ID),
            NVL(:NEW.MODIFIED_BY, USER), 'Job title change'
        );
    END IF;
END TRG_EMP_BEFORE_UPDATE;
/

-- -----------------------------------------------------------------------
-- TRG_EMP_AFTER_DELETE
-- Soft delete: instead of actual deletion, marks record as inactive
-- NOTE: This trigger converts DELETE into an UPDATE, which is confusing
-- and a known maintenance issue
-- -----------------------------------------------------------------------
CREATE OR REPLACE TRIGGER HRMS.TRG_EMP_INSTEAD_OF_DELETE
BEFORE DELETE ON HRMS.EMPLOYEES
FOR EACH ROW
BEGIN
    -- Convert delete to soft delete
    -- BUG: This actually prevents deletion, but Forms expects DELETE to succeed.
    -- Workaround in Forms: set ACTIVE_FLAG = 'N' then CLEAR_RECORD instead of DELETE_RECORD.
    -- RULE: Physical deletion of employee records is never permitted; callers must deactivate a record by setting ACTIVE_FLAG to 'N' or by running the formal termination process
    RAISE_APPLICATION_ERROR(-20504,
        'Direct deletion not allowed. Use termination process or set ACTIVE_FLAG to N.');
END TRG_EMP_INSTEAD_OF_DELETE;
/
