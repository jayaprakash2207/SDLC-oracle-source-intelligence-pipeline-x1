-- ============================================================================
-- Generic Audit Triggers
-- Applied to key tables for change tracking
-- ============================================================================

-- -----------------------------------------------------------------------
-- TRG_SALARY_AUDIT
-- Tracks all salary record changes for compliance
-- -----------------------------------------------------------------------
CREATE OR REPLACE TRIGGER HRMS.TRG_SALARY_AUDIT
AFTER INSERT OR UPDATE OR DELETE ON HRMS.SALARY_RECORDS
FOR EACH ROW
DECLARE
    v_action VARCHAR2(10);
    v_old_json CLOB;
    v_new_json CLOB;
BEGIN
    -- RULE: When a new salary record is inserted, the audit log must capture employee ID, base salary, and effective date to establish the initial compensation record
    IF INSERTING THEN
        v_action := 'INSERT';
        v_new_json := '{"emp_id":' || :NEW.EMP_ID ||
                      ',"salary":' || :NEW.BASE_SALARY ||
                      ',"effective":"' || TO_CHAR(:NEW.EFFECTIVE_DATE, 'YYYY-MM-DD') || '"}';
    -- RULE: When a salary record is updated, both the previous and new base salary and active status must be preserved in the audit trail to support compensation change reviews
    ELSIF UPDATING THEN
        v_action := 'UPDATE';
        v_old_json := '{"salary":' || :OLD.BASE_SALARY || ',"active":"' || :OLD.ACTIVE_FLAG || '"}';
        v_new_json := '{"salary":' || :NEW.BASE_SALARY || ',"active":"' || :NEW.ACTIVE_FLAG || '"}';
    -- RULE: When a salary record is deleted, the employee identity and last known salary must be preserved in the audit log to maintain a complete compensation history
    ELSIF DELETING THEN
        v_action := 'DELETE';
        v_old_json := '{"emp_id":' || :OLD.EMP_ID || ',"salary":' || :OLD.BASE_SALARY || '}';
    END IF;

    PKG_AUDIT.log_action(
        'SALARY_RECORDS',
        -- VALIDATION: Salary record identifier is resolved from NEW on insert/update and from OLD on delete, ensuring the audit entry is always linked to the correct record regardless of DML operation
        NVL(:NEW.SALARY_ID, :OLD.SALARY_ID),
        v_action,
        -- VALIDATION: If MODIFIED_BY is not explicitly populated on the salary row, the current database session user is recorded as the responsible actor so the audit trail always identifies who made the change
        NVL(:NEW.MODIFIED_BY, USER),
        v_old_json,
        v_new_json
    );
END TRG_SALARY_AUDIT;
/

-- -----------------------------------------------------------------------
-- TRG_LEAVE_REQUEST_AUDIT
-- Tracks leave request status changes
-- -----------------------------------------------------------------------
-- RULE: Only STATUS column changes on leave requests are subject to audit tracking; updates to other fields (e.g. comments, dates) do not generate an audit record
CREATE OR REPLACE TRIGGER HRMS.TRG_LEAVE_REQUEST_AUDIT
AFTER UPDATE OF STATUS ON HRMS.LEAVE_REQUESTS
FOR EACH ROW
BEGIN
    PKG_AUDIT.log_action(
        'LEAVE_REQUESTS',
        :NEW.REQUEST_ID,
        'STATUS_CHANGE',
        -- VALIDATION: If MODIFIED_BY is not populated on the leave request row, the current database session user is recorded as the responsible actor so workflow approval history is always attributable
        NVL(:NEW.MODIFIED_BY, USER),
        '{"status":"' || :OLD.STATUS || '"}',
        '{"status":"' || :NEW.STATUS || '"}'
    );
END TRG_LEAVE_REQUEST_AUDIT;
/

-- -----------------------------------------------------------------------
-- TRG_DEPARTMENT_AUDIT
-- Tracks department structure changes
-- -----------------------------------------------------------------------
CREATE OR REPLACE TRIGGER HRMS.TRG_DEPARTMENT_AUDIT
AFTER INSERT OR UPDATE OR DELETE ON HRMS.DEPARTMENTS
FOR EACH ROW
DECLARE
    v_action VARCHAR2(10);
BEGIN
    -- RULE: Every structural change to a department record (creation, modification, or removal) must be captured in the audit log to support organisational governance and accountability
    IF INSERTING THEN v_action := 'INSERT';
    ELSIF UPDATING THEN v_action := 'UPDATE';
    ELSIF DELETING THEN v_action := 'DELETE';
    END IF;

    PKG_AUDIT.log_action(
        'DEPARTMENTS',
        -- VALIDATION: Department identifier is resolved from NEW on insert/update and from OLD on delete, ensuring the audit entry is always linked to the correct department record regardless of DML operation
        NVL(:NEW.DEPT_ID, :OLD.DEPT_ID),
        v_action,
        -- RULE: For department changes, the database session user (USER) is always recorded as the actor; there is no application-supplied MODIFIED_BY column on this table
        USER
    );
END TRG_DEPARTMENT_AUDIT;
/
