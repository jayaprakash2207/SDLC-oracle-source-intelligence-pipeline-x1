# OSIRIS Parser — Gap Report (Final)

> All gaps verified by direct reading of source files and OSIRIS output files.
> Date: 2026-08-17 (updated after fixes)

---

## Status: ALL GAPS CLOSED — 100% Verified

| Audit | Result |
|---|---|
| `audit.py` (structural) | ✅ **1195/1195 (100%)** |
| `audit_full.py` (content) | ✅ **2050/2050 (100%)** |

---

## Summary

| Area | Status | Detail |
|------|--------|--------|
| Package procedures/functions | ✅ 100% | All 117 (115 public + 2 private helpers) |
| Table columns | ✅ 100% | All 441 columns with types, defaults |
| Table constraints (PK/FK/UK) | ✅ 100% | All FKs with referenced tables |
| CHECK constraints | ✅ **29/29** | **All captured — FIXED (multi-line balanced-paren extractor)** |
| Sequences | ✅ 100% | All 29 with correct START WITH + INCREMENT BY |
| Triggers | ✅ 100% | All 6 triggers |
| RAISE_APPLICATION_ERROR codes | ✅ 100% | All 31 |
| PRAGMA EXCEPTION_INIT codes | ✅ **100%** | **All 21 across all packages — FIXED** |
| Param directions (IN/OUT) | ✅ 100% | All 336 structured with direction fields |
| Form blocks + items | ✅ 100% | All 6 forms, 14 blocks, 114 items |
| View FROM/JOIN tables | ✅ 100% | All 26 references in `joins[]` arrays |
| View `full_query` bodies | ✅ **100%** | **All 6 complete — FIXED** |
| PLL library procedures | ✅ 100% | HRMS_COMMON_LIB (17) + HRMS_VALIDATION_LIB (5) |
| Seed data rows | ✅ 100% | All 133 rows structured |
| BUSINESS tagged comments | ✅ 100% | All verbatim |
| RULE tagged comments | ✅ 100% | All verbatim |
| CONSTRAINT tagged comments | ✅ **100%** | **All captured — FIXED** |
| VALIDATION tagged comments | ✅ 100% | All verbatim |
| BUG tagged comments | ✅ **100%** | **All captured — FIXED** |
| NOTE tagged comments | ✅ **100%** | **All 10 captured — FIXED** |
| WARNING tagged comments | ✅ **100%** | **All 1 captured — FIXED** |

---

## What Was Fixed

### Fix 1 — PRAGMA EXCEPTION_INIT codes (was: 0/3 in PKG_SECURITY, missed across all packages)

**Root cause:** `consolidate_business_rules()` only read `body.raise_errors`. The PRAGMA codes
live in `spec.exceptions[].code` and were never promoted to `business_rules.json`.

**Fix:** Consolidator now iterates every `spec.exceptions[]` entry and emits an `error_rule`
for each one that has a `code` value.

**Result:** 21 PRAGMA entries now in `business_rules.json`, including:
- `PRAGMA EXCEPTION_INIT e_account_locked = -20302`
- `PRAGMA EXCEPTION_INIT e_session_expired = -20303`
- `PRAGMA EXCEPTION_INIT e_insufficient_priv = -20304`
- All PKG_EMPLOYEE, PKG_LEAVE, PKG_PAYROLL PRAGMA codes

---

### Fix 2 — View `full_query` bodies truncated (was: all 6 views cut short)

**Root cause:** The view body regex `(.*)`  with `re.DOTALL` captured everything from the `AS`
keyword to the next view's `CREATE` — including `COMMENT ON TABLE` lines and separator comments.

**Fix:** After extracting the raw body, trim at the first `;` — that's the end of the SELECT
statement. Everything after is noise.

**Result:** All 6 view `full_query` fields now end with `;` and contain only the SELECT body:
- `VW_ACTIVE_EMPLOYEES`: 1187 chars, ends `AND e.ACTIVE_FLAG = 'Y';` ✅
- `VW_ORG_HIERARCHY`: 398 chars, ends `ORDER SIBLINGS BY LAST_NAME;` ✅
- `VW_PENDING_APPROVALS`: 1015 chars, ends `STATUS = 'MANAGER_REVIEW';` ✅

---

### Fix 3 — CONSTRAINT comments not captured from PLL and triggers

**Root cause:** `parse_pll_library()` and the trigger parser only extracted `BUSINESS`, `RULE`,
`VALIDATION`, `BUG` tags. `CONSTRAINT` was not extracted.
`consolidate_business_rules()` also did not read constraints from PLL libs or triggers.

**Fix:**
- PLL parser: added `all_constraints` field
- Trigger parser: added `constraints` field
- Consolidator: wired both new fields as `"constraint"` category rules

**Result:** 36 constraint rules in output, including:
- `[pll_library]` A valid US phone number must contain exactly 10 digits
- `[pll_library]` A valid SSN must consist of exactly 9 numeric digits after stripping formatting characters
- `[db_trigger]` Maximum allowed future hire date is 180 days from the current date

---

### Fix 4 — Sequence BUG note prefix mismatch

**Root cause:** `parse_sequences()` captured comment lines verbatim, storing
`"BUG: NOCACHE means gaps..."`. The audit compared this against the source comment text
`"NOCACHE means gaps..."` (without the `BUG:` prefix) — mismatch.

**Fix:** Consolidator strips `BUG:` prefix from sequence notes before storing.

---

### Fix 5 — SOURCE_DIR path incorrect (parser could not find source files)

**Root cause:** `SOURCE_DIR` and `SRC` in all three scripts were hardcoded to a long
`automated-reverse-engineering-pipeline-main/.../ts-plsql-oracle-forms-hrms-main` path
that no longer exists in the repo.

**Fix:** All three scripts (`oracle_deep_parser.py`, `audit.py`, `audit_full.py`) now use
`Path(__file__).parent.parent / "source"` — the actual source location.

---

## Output — Current State

| File | Entries |
|---|---|
| `business_rules.json` | 807 rules (was 795) |
| `plsql_deep.json` | 11 packages, 117 procedures/functions |
| `schema_deep.json` | 30 tables, 6 views (complete), 6 triggers, 29 sequences |
| `pll_deep.json` | 2 PLL libraries, 22 procedures/functions |
| `forms_deep.json` | 6 forms, 14 blocks, 114 items |
| `seed_deep.json` | 133 rows across 10 tables |

---

## Remaining Known Limitation (not a gap — by design)

| Item | Detail |
|---|---|
| No procedure narrative | OSIRIS extracts structured facts — it does not write prose descriptions of what each procedure does. That is the role of the team chunk scan. |

---

## Fix 6 — Multi-line CHECK constraint (EMPLOYEE_HISTORY.CHANGE_TYPE)

**Root cause:** `_parse_ddl_columns()` used the regex `CHECK\s*\(([^)]+)\)` — `[^)]+` stops at the
first `)` it finds. The `CHANGE_TYPE IN (...)` list spans multiple lines with `)` characters inside
the values, so the regex closed early and discarded the whole constraint.

**Fix:** Replaced the per-line regex with `_extract_check_constraints()` — a balanced-parentheses
extractor that counts `(` and `)` depth to find the true end of each CHECK expression.

**Result:** 29/29 CHECK constraints captured. `EMPLOYEE_HISTORY.CHANGE_TYPE IN ('HIRE', 'TRANSFER',
'PROMOTION', 'DEMOTION', 'SALARY_CHANGE', 'TERMINATION', 'REHIRE', 'LEAVE_START', 'LEAVE_END',
'STATUS_CHANGE')` is now present verbatim.

---

## Fix 7 — NOTE and WARNING comments not extracted

**Root cause:** `extract_inline_comments()` was never called with `"NOTE"` or `"WARNING"` tags
anywhere in the parser. These tags existed in pkb files, PLL libraries, triggers, sequences, and
the views file — but were silently dropped.

**Fix:** Added NOTE + WARNING extraction in:
- `deep_parse_pkb()` — package body level
- `parse_pll_library()` — library level  
- Trigger extractor — trigger body level
- `parse_sequences()` — sequence preceding-comment block
- `deep_parse_schema()` views section — scans 10 lines before each `CREATE OR REPLACE VIEW`
- `consolidate_business_rules()` — wires all new fields into `business_rules.json`

**Result:** 10 `note` entries + 1 `warning` entry now in output:
- `[VW_ORG_HIERARCHY]` Performance degrades significantly with >500 employees
- `[TRG_EMP_BEFORE_UPDATE]` This trigger converts DELETE into an UPDATE, which is confusing but necessary
- `[HRMS_COMMON_LIB]` MESSAGE called twice intentionally — Oracle Forms requires two calls
- `[PKG_PAYROLL]` Hard-coded 2024 brackets — should read from TAX_BRACKETS table
- And 6 more NOTE entries across PKG_EMPLOYEE, PKG_SECURITY, HRMS_VALIDATION_LIB, sequences

---

*Both audits run after every parser change. 3,245 total checks. Zero misses.*
