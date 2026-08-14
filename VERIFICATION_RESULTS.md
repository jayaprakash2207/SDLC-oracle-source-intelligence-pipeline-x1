# Verification Results: Parser vs Teammate Chunk Deep Scans

**Date:** 2026-08-14  
**Method:** 8 parallel agents comparing 19 teammate chunk deep scan outputs against 4 Oracle parser JSON files  
**Runtime:** ~7 minutes | 9 agents | 720,675 tokens

---

## Overall Verdict: PARTIALLY ALIGNED

| Metric | Count |
|---|---|
| Matches | 153 |
| Parser missed | 158 |
| Chunk missed | 89 |
| Contradictions | 28 |
| **Overall Coverage** | **58%** |

---

## Per Group Coverage

| Group | Coverage | Parser Missed | Chunk Missed | Contradictions |
|---|---|---|---|---|
| Forms (Chunks 01-03) | 72% | 22 | 5 | 6 |
| PL/SQL Body A (Chunks 05-07) | 62% | 42 | 13 | 5 |
| PL/SQL Body B (Chunks 08-10) | 72% | 25 | 12 | 3 |
| PL/SQL Body C (Chunks 11-12) | 72% | 19 | 9 | 3 |
| PL/SQL Spec (Chunks 13-14) | 72% | 9 | 12 | 4 |
| Schema (Chunks 15-17) | 52% | 15 | 8 | 5 |
| Seed Data (Chunks 18-19) | 32% | 14 | 15 | 2 |
| Other/Libraries (Chunk 04) | 30% | 12 | 15 | 0 |

---

## What the Parser Does Well (Reliable)

- Table DDL (column names, data types, primary keys, foreign keys)
- PL/SQL procedure and function signatures
- Trigger names and basic structure
- Error codes (`RAISE_APPLICATION_ERROR` codes)
- Package names and dependencies

---

## Top 10 Gaps — What Parser Missed

1. **PLL library files entirely absent** — `HRMS_COMMON_LIB` (17 procedures) and `HRMS_VALIDATION_LIB` (5 functions) were never parsed — complete blind spot for Forms-layer utility code
2. **All 29 sequences missing** — `SEQ_EMPLOYEE` (START 10000), `SEQ_AUDIT` (CACHE 100), `SEQ_EMP_NUMBER` (START 1000) and all others absent from parser output
3. **Zero seed data** — all 86 seed rows across 8 tables (locations, grades, departments, job titles, leave types, pay elements, holidays, system parameters) are absent
4. **PKG_INTEGRATION business rules empty** — GL debit/credit posting logic, ADP fixed-width format specs, and stub/unimplemented status flags completely missing
5. **PKG_AUDIT behavioral rules absent** — `PRAGMA AUTONOMOUS_TRANSACTION` isolation, `SYS_CONTEXT` IP/session tracing, exception-swallowing behavior, and 365-day retention default all missing
6. **Form master-detail relations missing** — `EMP_SALARY_REL`, `PERIOD_RUN_REL`, `CYCLE_REVIEW_REL`, `REVIEW_GOAL_REL` undocumented; canvas/window/alert object definitions absent
7. **LOV SQL queries all empty strings** — `RG_DEPARTMENTS`, `RG_JOB_TITLES`, `RG_MANAGERS`, `RG_LOCATIONS` queries fully documented in chunks but blank in parser output
8. **Forms business rules arrays all empty** — chunks catalogue 15+ named business rules across HRMS_EMPLOYEE, HRMS_LEAVE, HRMS_PAYROLL, HRMS_PERFORMANCE; parser has zero
9. **HRMS_MENU entirely absent** — MAIN_MENUBAR with 7 menus, 22 menu items, OPEN_FORM calls, and `PKG_SECURITY.has_permission` guards not parsed at all
10. **Package spec exceptions incomplete** — parser captures only 1 exception per package; chunks document 4-5 per package; `get_leave_balance` and `generate_emp_number` functions missing from spec

---

## 5 Confirmed Contradictions (Factual Errors in Parser Output)

| # | Location | Parser Says | Truth (from Chunks) |
|---|---|---|---|
| 1 | `TRG_EMP_BEFORE_UPDATE` + `TRG_EMP_INSTEAD_OF_DELETE` | Has 14 rules copied from INSERT trigger | INSERT-only rules (CREATED_BY default, ACTIVE status default) don't apply to UPDATE/DELETE |
| 2 | `PKG_NOTIFICATION` | Uses `UTL_MAIL` | Actual implementation uses `UTL_SMTP` with `UTL_TCP.CRLF` |
| 3 | SQL injection bug | Attributed to `get_employee_by_number` | Actually in `search_employees` (where dynamic SQL concatenation exists) |
| 4 | `LEAVE_BALANCES.AVAILABLE` | Column absent from parser | Documented as `GENERATED ALWAYS AS (OPENING_BALANCE + ACCRUED - USED + ADJUSTMENT - PENDING) VIRTUAL` |
| 5 | `JOB_GRADES` table | Column named `GRADE_CODE` | Seed data shows column named `GRADE_LEVEL` (integer 1-10) |

---

## What to Do Next — Roadmap to 100% Coverage

### Phase 1: Fix Parser (target: 80% coverage)
- [ ] Add `.pll` file parser for `HRMS_COMMON_LIB` + `HRMS_VALIDATION_LIB`
- [ ] Add `.mmb` menu parser for `HRMS_MENU`
- [ ] Fix LOV SQL query extraction (currently writes empty strings)
- [ ] Fix Forms business rules extraction (currently empty arrays)
- [ ] Add sequence parser for `hrms_sequences.sql`
- [ ] Add seed data parser for all 8 seed SQL scripts
- [ ] Patch 5 factual errors (trigger rules, UTL_MAIL, bug misattribution, virtual column, GRADE_LEVEL)

### Phase 2: Combine Both Pipelines (target: 92-95% coverage)
- [ ] Use parser JSON for structural scaffold (DDL, signatures, error codes)
- [ ] Use old pipeline (Claude reads source directly) for behavioral rules and business logic
- [ ] Merge outputs before feeding the 8 agents

### Phase 3: Verification Pass (target: 97% coverage)
- [ ] Run verification workflow after every pipeline generation run
- [ ] Contradiction check is mandatory, not optional

### Phase 4: Human Review (target: 100%)
- [ ] Business intent behind design decisions
- [ ] Undocumented constraints
- [ ] Oracle Forms runtime behavior not visible in source

---

## Coverage Estimate by Approach

| Approach | Estimated Coverage |
|---|---|
| Old pipeline alone (Claude reads source) | ~85% |
| New parser alone (current state) | ~58% |
| New parser after Phase 1 fixes | ~80% |
| Old + fixed parser combined (Phase 2) | ~92-95% |
| All above + verification pass (Phase 3) | ~97% |
| All above + human review (Phase 4) | ~100% |

---

## Conclusion

The parser output is **reliable for structural inventory** (table DDL, PL/SQL signatures, trigger names, error codes) but **should not be used as a standalone source for behavioral analysis**.

For the next pipeline step (generating 25 documents via 8 agents):
- Use **teammate chunk files as authoritative reference** for behavioral analysis
- Use **parser JSON as structural scaffold** only
- Fix the 5 contradictions before any migration or test-generation use
