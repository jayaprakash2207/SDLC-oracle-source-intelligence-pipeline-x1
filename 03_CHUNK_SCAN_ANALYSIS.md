# Team Chunk Deep Scan — Analysis and Gaps

**Date:** 2026-08-18 | **Chunks:** 19 files covering 42 source files

---

## What the Chunk Scan Is

Claude AI read all 42 Oracle HRMS source files in 19 chunks and wrote prose markdown summaries.
Each procedure gets a narrative walkthrough (5–15 lines) with source line references like `[SOURCE: L40-56]`.

**Location:** `automated-reverse-engineering-pipeline-main/.../team's chunk deep scan results/results/Scan/`

---

## What Chunks Cover (Verified Correct)

| Area | Coverage | Verified Example |
|---|---|---|
| Procedure/function names | ✅ 115/115 | All named across chunks |
| Table names | ✅ 30/30 | All present |
| Sequence names + values | ✅ 29/29 | `SEQ_EMPLOYEE START WITH 10000` ✅ |
| Error codes (RAISE + PRAGMA) | ✅ 34/34 | Including `-20302`, `-20303`, `-20304` from PKG_SECURITY |
| View FROM/JOIN tables | ✅ All | As prose sentences with all table names |
| Form blocks/items/LOVs | ✅ All | All 6 forms, all blocks named |
| Business rule facts | ✅ Present | Same facts as OSIRIS — paraphrased |
| Param directions — spec chunks | ✅ Complete | Chunk_13/14 have full IN/OUT for all params |
| Architecture risks | ✅ Present | e.g. "VW_ORG_HIERARCHY times out for orgs >500 employees" |

**Verified example — `VW_ACTIVE_EMPLOYEES`:**
> *"joins EMPLOYEES to DEPARTMENTS, JOB_TITLES, JOB_GRADES, a self-join to EMPLOYEES for the
> manager's name, LOCATIONS, and the employee's active SALARY_RECORDS row"* — all tables present ✅

**Verified example — `validate_ssn`:**
> *"Area segment = SUBSTR(v_digits, 1, 3), invalid if equal to '000'. Group segment = SUBSTR(v_digits, 4, 2),
> invalid if equal to '00'. Serial segment = SUBSTR(v_digits, 6, 4), invalid if equal to '0000'."* ✅

---

## What Chunks Do That OSIRIS Does Not

| Strength | Detail |
|---|---|
| Procedure narrative | 5–15 line walkthrough per procedure — logic, conditions, what updates happen |
| Source line references | Every claim tagged `[SOURCE: L40-56]` |
| Deep code logic | Exact Oracle expressions with context |
| Architecture risks | Timeout risks, circular dependencies, stub detection |
| Cross-procedure context | Calls to other packages explained in narrative |
| Security observations | 3 critical bugs found only in chunks (see below) |

---

## 3 Critical Bugs in Chunks Only (Not in OSIRIS)

These must be reviewed before any forward engineering work:

| # | Bug | Location | Why Critical |
|---|---|---|---|
| 1 | `authenticate()` may not fully verify the password in all paths | PKG_SECURITY.pkb | Authentication bypass risk |
| 2 | `change_password()` does not verify the old password before updating | PKG_SECURITY.pkb | Any user can change any password |
| 3 | FTP credentials stored in cleartext in SYSTEM_PARAMETERS table | PKG_INTEGRATION.pkb | Credentials exposed in plain text |

---

## Known Gaps in the Chunk Scan

### Gap 1 — Body Chunks Drop `IN` Parameter Directions

**Affected chunks:** Chunk_05 through Chunk_12 (all package body chunks)

Body-file chunks preserve `OUT` directions but drop `IN` keywords from procedure signatures.

| | Spec chunk (Chunk_13) | Body chunk (Chunk_10) | OSIRIS |
|---|---|---|---|
| `get_payslip` | `p_cursor OUT, p_run_id IN NUMBER, p_emp_id IN NUMBER` ✅ | `p_cursor OUT, p_run_id NUMBER, p_emp_id NUMBER` ❌ | Full directions ✅ |

**Fix:** Use Chunk_13 and Chunk_14 (spec chunks) for all parameter directions — never body chunks.

---

### Gap 2 — INCOMPLETE Flags on 6 Chunks

| Chunk | File | Issue |
|---|---|---|
| Chunk_01 | HRMS_EMPLOYEE.xml | Pipeline status counters missing |
| Chunk_02 | HRMS_LEAVE/LOGIN/MENU/PAYROLL.xml | 4 forms — counts unreliable |
| Chunk_05 | PKG_COMMON.pkb | One counter missing |
| Chunk_10 | PKG_PAYROLL.pkb | Largest file (46K chars) — many counters missing |
| Chunk_12 | PKG_SECURITY.pkb | Counters missing |
| Chunk_15 | HRMS_VALIDATION_LIB.pll.sql | Still INCOMPLETE after max attempts |

Content is present and correct — but pipeline completeness counters are unreliable for these 6 chunks.

---

### Gap 3 — No Structured Format

All chunk output is free-text markdown prose. It cannot be consumed by code generators,
migration scripts, or any automated tool. A human must re-read every chunk.

---

### Gap 4 — No Verification

The chunk output has **zero audit checks**. OSIRIS has 3,715 verified checks.
Chunk accuracy is based on spot checks — not systematic verification.

---

### Gap 5 — Source Completeness

The README states 18 forms, 200+ triggers. Only 6 Oracle Forms XML exports exist in the
provided source. Neither OSIRIS nor chunks can cover the missing 12 forms.
This is a source gap — the full codebase is larger than what was provided.

---

## Chunk Map — What Each Chunk Covers

| Chunk | Files | Type |
|---|---|---|
| Chunk_01 | HRMS_EMPLOYEE.xml | Forms XML |
| Chunk_02 | HRMS_LEAVE.xml, HRMS_LOGIN.xml, HRMS_MENU.xml, HRMS_PAYROLL.xml | Forms XML |
| Chunk_03 | HRMS_PERFORMANCE.xml | Forms XML |
| Chunk_04 | README.md | Documentation only |
| Chunk_05 | PKG_AUDIT.pkb, PKG_COMMON.pkb | PL/SQL body |
| Chunk_06 | PKG_EMPLOYEE.pkb | PL/SQL body |
| Chunk_07 | PKG_INTEGRATION.pkb | PL/SQL body |
| Chunk_08 | PKG_LEAVE.pkb | PL/SQL body |
| Chunk_09 | PKG_NOTIFICATION.pkb | PL/SQL body |
| Chunk_10 | PKG_PAYROLL.pkb | PL/SQL body |
| Chunk_11 | PKG_PERFORMANCE.pkb, PKG_REPORTING.pkb | PL/SQL body |
| Chunk_12 | PKG_SECURITY.pkb, PKG_VALIDATION.pkb | PL/SQL body |
| Chunk_13 | PKG_AUDIT.pks → PKG_REPORTING.pks (9 specs) | PL/SQL spec — **use for param directions** |
| Chunk_14 | PKG_SECURITY.pks, PKG_VALIDATION.pks | PL/SQL spec — **use for param directions** |
| Chunk_15 | HRMS_COMMON_LIB.pll, HRMS_VALIDATION_LIB.pll, HRMS_MENU.mmb, triggers, sequences | Mixed |
| Chunk_16 | 01_core_tables.sql, 02_payroll_tables.sql, 03_leave_tables.sql | DDL tables |
| Chunk_17 | 04_performance_tables.sql, hrms_views.sql | DDL + Views |
| Chunk_18 | 01_reference_data.sql | Seed data |
| Chunk_19 | 02_employee_data.sql | Seed data |

---

## Quick Reference — Which Chunk to Read for What

| What you need | Read |
|---|---|
| What PKG_EMPLOYEE does step-by-step | Chunk_06 |
| Payroll calculation — tax brackets, rates, logic | Chunk_10 |
| Security vulnerabilities (critical bugs) | Chunk_12 + Chunk_14 |
| Integration with ADP / GL / FTP | Chunk_07 |
| Leave rules — accrual, carryover, backdating | Chunk_08 |
| All parameter directions (IN/OUT) | **Chunk_13 + Chunk_14 only** |
| All view definitions with logic | Chunk_17 |
| All sequence values | Chunk_15 |
| Seed data — employees | Chunk_19 |
| Seed data — reference data (departments, grades, etc.) | Chunk_18 |
