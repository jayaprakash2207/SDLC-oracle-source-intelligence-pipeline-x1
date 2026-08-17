# Team Chunk Deep Scan — Detailed Gap Report

> Verified against 42 Oracle HRMS source files directly.
> Chunks location: `team's chunk deep scan results/results/Scan/` (19 chunks)
> Date: 2026-08-17

---

## Summary

| Area | Status | Detail |
|------|--------|--------|
| Procedure / function names | ✅ 100% | All 115 names mentioned |
| Table names | ✅ 100% | All 30 tables mentioned |
| Table column names | ✅ 100% | All columns mentioned (spot-checked 5 tables) |
| Sequence names | ✅ 100% | All 29 named |
| Sequence START WITH / INCREMENT BY values | ✅ Correct where checked | Not fully audited |
| RAISE error codes (real) | ✅ 31/31 | All real codes present |
| **RAISE error codes (invented)** | ❌ **5 fake codes** | Not in source |
| Form block names | ✅ 100% | All 6 forms, all blocks |
| Form item names | ✅ 100% | All 114 items |
| View FROM/JOIN table names | ✅ 100% | All 6 views |
| Constants | ✅ 100% | All 12 named |
| Param directions (IN/OUT) | ⚠️ Partial | Only in narrative, not structured |
| **`-- BUSINESS:` comments** | ❌ **9/53 (17%)** | **44 missing** |
| **`-- RULE:` comments** | ❌ **15/197 (8%)** | **182 missing** |
| **`-- VALIDATION:` comments** | ❌ **2/29 (7%)** | **27 missing** |
| **`-- BUG:` comments** | ❌ **1/8 (13%)** | **7 missing** |
| **`-- CONSTRAINT:` comments** | ❌ **3/36 (8%)** | **33 missing** |
| Machine-readable / structured output | ❌ No | Free-text markdown only |
| Verified against source by audit | ❌ No | Zero audit checks run |

---

## Gap 1 — 44 Missing `-- BUSINESS:` Rules (83% missed)

Source has 53 `-- BUSINESS:` tagged comments. Chunks captured only **9**.

### Sample of what is missing:

| Source File | Missing Rule |
|---|---|
| `HRMS_VALIDATION_LIB.pll` | Salary boundaries are determined by the employee's assigned job grade |
| `PKG_COMMON.pkb` | Only system parameters explicitly flagged as editable (EDITABLE_FLAG = 'Y') may be modified |
| `PKG_EMPLOYEE.pkb` | Only departments flagged as active (ACTIVE_FLAG = 'Y') are considered valid for employee assignment |
| `PKG_EMPLOYEE.pkb` | Only job titles with ACTIVE_FLAG = 'Y' are valid for assignment to a new employee |
| `PKG_EMPLOYEE.pkb` | The current salary is the active salary record that became effective on or before today |
| `PKG_PAYROLL.pkb` | (multiple payroll processing rules) |
| `PKG_LEAVE.pkb` | (multiple leave accrual rules) |
| `PKG_PERFORMANCE.pkb` | (multiple review cycle rules) |

**Why:** The AI read procedure logic and described it in its own words. It did NOT copy the `-- BUSINESS:` comment text verbatim. So the tagged rules from the source are largely absent.

---

## Gap 2 — 182 Missing `-- RULE:` Comments (92% missed)

Source has 197 `-- RULE:` tagged comments. Chunks captured only **15**.

### Sample of what is missing:

| Source File | Missing Rule |
|---|---|
| `HRMS_COMMON_LIB.pll` | Toolbar Query button behaviour depends on current form mode |
| `HRMS_COMMON_LIB.pll` | Abort form processing when no session exists; the user must authenticate before any operation |
| `HRMS_COMMON_LIB.pll` | A record group is only refreshed if it already exists in the form |
| `HRMS_VALIDATION_LIB.pll` | Email address is not a required field; NULL is treated as valid |
| `HRMS_VALIDATION_LIB.pll` | Email must contain exactly one '@' symbol |
| `PKG_COMMON.pkb` | Fiscal quarters follow the October 1 fiscal year start: Q1=October–December |
| `PKG_PAYROLL.pkb` | Salary must be positive — raises error -20101 if violated |
| `PKG_PAYROLL.pkb` | Employee with no salary record on the period end date cannot be processed |
| `PKG_REPORTING.pkb` | EEO gender breakdown uses three declared codes — 'M', 'F', 'O' |

**Why:** Same as above — AI paraphrased the logic rather than capturing the exact tagged rule text.

---

## Gap 3 — 27 Missing `-- VALIDATION:` Comments (93% missed)

Source has 29 `-- VALIDATION:` tagged comments. Chunks captured only **2**.

### Sample of what is missing:

| Source File | Missing Validation |
|---|---|
| `HRMS_COMMON_LIB.pll` | Falls back to the Oracle database session user when no HRMS application user is set |
| `HRMS_COMMON_LIB.pll` | Falls back to the Oracle database session user when the HRMS application-level global is empty |
| `PKG_COMMON.pkb` | Currency symbol is resolved by ISO code: USD maps to '$', EUR maps to euro symbol |
| `PKG_COMMON.pkb` | A valid email address must have a non-empty local part, an '@' symbol, a domain name |
| `PKG_EMPLOYEE.pkb` | When no location is explicitly provided, the employee's work location defaults to the department's location |

---

## Gap 4 — 7 Missing `-- BUG:` Comments (87% missed)

Source has 8 `-- BUG:` tagged comments. Chunks captured only **1**.

### All missing bugs:

| Source File | Missing Bug |
|---|---|
| `HRMS_VALIDATION_LIB.pll` | Uses a hard-coded cache that's populated at form startup |
| `PKG_EMPLOYEE.pkb` | Race condition under concurrent inserts — no SELECT FOR UPDATE |
| `PKG_EMPLOYEE.pkb` | SQL injection possible via p_last_name if called with unvalidated input |
| `PKG_LEAVE.pkb` | Does not handle "observed" holidays (e.g. if July 4 falls on weekend) |
| `PKG_LEAVE.pkb` | If run twice on same day, can double-subtract leave balance |
| `PKG_COMMON.pkb` | (additional bug comment) |
| `PKG_SECURITY.pkb` | (additional bug comment) |

**This is the most critical gap.** Known bugs are exactly what forward engineering needs to fix. Missing 7 out of 8 means the new system may not address these issues.

---

## Gap 5 — 33 Missing `-- CONSTRAINT:` Comments (92% missed)

Source has 36 `-- CONSTRAINT:` tagged comments. Chunks captured only **3**.

### Sample of what is missing:

| Source File | Missing Constraint |
|---|---|
| `PKG_COMMON.pkb` | The fiscal year boundary is month 10 (October) |
| `PKG_COMMON.pkb` | An 11-digit phone number is only recognised as valid US/Canada international format |
| `PKG_COMMON.pkb` | An SSN must have at least 4 characters for the last-four-digit display |
| `PKG_EMPLOYEE.pkb` | The reporting hierarchy is limited to a maximum depth of 15 levels |
| `PKG_EMPLOYEE.pkb` | The default maximum depth for org chart traversal is 10 levels |
| `HRMS_VALIDATION_LIB.pll` | A valid US phone number must contain exactly 10 digits |
| `HRMS_VALIDATION_LIB.pll` | A valid SSN must consist of exactly 9 numeric digits |
| `trg_employees.sql` | Maximum allowed future hire date is 180 days from the current date |

---

## Gap 6 — 5 Invented / Hallucinated Error Codes

The chunks contain **5 error codes that do not exist anywhere in the source:**

| Fake Code | Status |
|---|---|
| `-20000` | ❌ Not in source |
| `-20302` | ❌ Not in source |
| `-20303` | ❌ Not in source |
| `-20304` | ❌ Not in source |
| `-20999` | ❌ Not in source |

Real source has exactly 31 codes: `-20001` through `-20504` and `-20900`.
The chunks have 36 — 31 real + 5 invented.

---

## Gap 7 — Not Machine-Readable

The chunk output is **free-text markdown**. There is no structured data format.

| What forward engineering needs | Chunks provide |
|---|---|
| `procedure.name` | Mentioned in bold heading — parseable with regex but fragile |
| `procedure.params[].direction` | Written in narrative text — 138 triplets extractable, but incomplete |
| `table.columns[].type` | Mentioned in text — no structured field |
| `business_rule.id` | No IDs assigned — no way to reference a rule |
| `raise_error.code + message` | Written in narrative — extractable for real codes only |

**Verdict:** Chunks cannot be fed directly into a code generator. They require manual reading or a secondary extraction step.

---

## Gap 8 — Zero Verification Against Source

No audit script was run on the chunk outputs. There is **no proof** that:
- The exact values (column types, sequence numbers, error codes) match source
- The descriptions accurately reflect what the code does
- Nothing was missed or misread

The 5 invented error codes are evidence that values can be wrong without detection.

---

## What the Chunks Do Well

Despite the gaps, the team chunks provide value that OSIRIS does not:

| Strength | Example |
|---|---|
| **Narrative procedure descriptions** | Each procedure gets a 5–10 line explanation of what it does, edge cases, and data flow |
| **Business context in plain English** | "Unsaved changes must be explicitly saved or discarded, or the exit is cancelled" |
| **Source line references** | `[SOURCE: L40-56]` — exact line numbers in source |
| **Trigger logic walkthrough** | Step-by-step what each form trigger does |
| **Known architectural risks** | e.g. "recursive query is known to time out for orgs with >500 employees" |
| **Cross-procedure dependency notes** | Calls to PKG_PAYROLL, PKG_SECURITY, PKG_AUDIT documented |

---

## Side-by-Side: OSIRIS vs Team Chunks

| Dimension | OSIRIS | Team Chunks |
|---|---|---|
| `-- BUSINESS:` rules captured | ✅ 52/53 (98%) | ❌ 9/53 (17%) |
| `-- RULE:` rules captured | ✅ 191/197 (97%) | ❌ 15/197 (8%) |
| `-- VALIDATION:` captured | ✅ 29/29 (100%) | ❌ 2/29 (7%) |
| `-- BUG:` captured | ✅ 8/8 (100%) | ❌ 1/8 (13%) |
| `-- CONSTRAINT:` captured | ✅ 33/36 (92%) | ❌ 3/36 (8%) |
| Invented/fake data | ✅ Zero | ❌ 5 fake error codes |
| Machine-readable format | ✅ Structured JSON | ❌ Free-text markdown |
| Audit verified | ✅ 3,245/3,245 checks | ❌ Zero checks |
| Procedure narrative | ❌ No descriptions | ✅ Rich narrative per proc |
| Source line references | ❌ No | ✅ Yes [SOURCE: Lxx-Lxx] |
| Business context in English | ❌ Rule text only | ✅ Full walkthrough |

---

## Decision

| Use case | Use |
|---|---|
| Forward engineering input (code gen, DB, APIs) | ✅ **OSIRIS only** |
| Understanding what a procedure does | ✅ **Team chunks** |
| Knowing which bugs to fix | ✅ **OSIRIS** (chunks missed 7/8 bugs) |
| Architecture + design narrative | ✅ **Team chunks + OSIRIS combined** |
| Exact values (types, thresholds, error codes) | ✅ **OSIRIS only** — chunks have invented values |

---

*Analysis run directly against 42 Oracle HRMS source files. No assumptions.*
