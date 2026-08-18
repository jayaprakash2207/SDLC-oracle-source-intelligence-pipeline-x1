# OSIRIS Parser — Full Technical Details

**Date:** 2026-08-18 | **Audits: 3,715/3,715 (100%)**

---

## What the Parser Extracts — Dimension by Dimension

### PL/SQL Packages (11 packages)

| Package | Procs/Funcs | Exceptions | Constants | Known Bugs |
|---|---|---|---|---|
| PKG_AUDIT | 3 | 0 | 0 | 1 |
| PKG_COMMON | 19 | 0 | 0 | 1 |
| PKG_EMPLOYEE | 18 | 5 | 2 | 3 |
| PKG_INTEGRATION | 5 | 0 | 3 | 0 |
| PKG_LEAVE | 14 | 4 | 0 | 2 |
| PKG_NOTIFICATION | 4 | 0 | 4 | 1 |
| PKG_PAYROLL | 18 | 4 | 8 | 1 |
| PKG_PERFORMANCE | 12 | 0 | 0 | 0 |
| PKG_REPORTING | 8 | 0 | 0 | 0 |
| PKG_SECURITY | 8 | 4 | 2 | 0 |
| PKG_VALIDATION | 8 | 0 | 0 | 0 |
| **TOTAL** | **117** | **17** | **19** | **9** |

Every procedure has all parameters with `name`, `direction` (IN/OUT/IN OUT), and `type`.

---

### DDL Schema

| | Count | Notes |
|---|---|---|
| Tables | 30 | All with complete column definitions |
| Columns | 441 | With type, size, DEFAULT, NOT NULL flags |
| Foreign Keys | 30 | With constraint name + referenced table + referenced column |
| CHECK constraints | 29 | Verbatim expressions — incl. multi-line IN() lists |
| UNIQUE constraints | 10 | With constraint name + columns |
| Views | 6 | Complete full SQL body including UNION ALL sections |
| Sequences | 29 | START WITH, INCREMENT BY, CACHE setting |
| Triggers | 6 | Timing, events, table, rules, RAISE codes |

---

### Oracle Forms (6 forms)

| Form | Blocks | Items | LOVs | Purpose |
|---|---|---|---|---|
| HRMS_EMPLOYEE | 2 | 38 | 4 | Employee master record |
| HRMS_LEAVE | 3 | 24 | 1 | Leave requests + approval |
| HRMS_LOGIN | 1 | 5 | 0 | Authentication |
| HRMS_MENU | 1 | 8 | 0 | Navigation |
| HRMS_PAYROLL | 2 | 17 | 0 | Payroll run management |
| HRMS_PERFORMANCE | 3 | 22 | 0 | Performance reviews + goals |

Every item has: DataType, MaxLength, Required, FormatMask, ColumnName — all structured.

---

### Error Codes (55 error rules, 34 unique codes)

| Range | Package | Exceptions |
|---|---|---|
| -20001 to -20005 | PKG_EMPLOYEE | not_found, dup_emp_number, invalid_dept, invalid_mgr, termination_error |
| -20101 to -20104 | PKG_PAYROLL | invalid_salary, period_closed, run_already_paid, calculation_error |
| -20201 to -20212 | PKG_LEAVE | insufficient_balance, overlapping_leave, invalid_type, approval_error + 3 more |
| -20301 to -20312 | PKG_SECURITY | invalid_credentials, account_locked, session_expired, insufficient_priv + 3 more |

All 21 PRAGMA EXCEPTION_INIT codes also captured across all packages.

---

### Views (6 views — complete SQL bodies)

| View | Tables Used | Purpose |
|---|---|---|
| VW_ACTIVE_EMPLOYEES | EMPLOYEES, DEPARTMENTS, JOB_TITLES, JOB_GRADES, LOCATIONS, SALARY_RECORDS | Active employees with full profile |
| VW_EMPLOYEE_COMPENSATION | EMPLOYEES, DEPARTMENTS, JOB_GRADES, JOB_TITLES, SALARY_RECORDS | Salary vs grade range, compa-ratio |
| VW_LEAVE_SUMMARY | LEAVE_BALANCES, EMPLOYEES, DEPARTMENTS, LEAVE_TYPES | Leave balances + utilisation % |
| VW_ORG_HIERARCHY | EMPLOYEES (CONNECT BY) | Hierarchical org chart |
| VW_PAYROLL_LATEST | PAYROLL_DETAILS, PAYROLL_RUNS, EMPLOYEES, PAY_PERIODS | Latest approved payroll per employee |
| VW_PENDING_APPROVALS | LEAVE_REQUESTS, PERFORMANCE_REVIEWS, EMPLOYEES, LEAVE_TYPES, REVIEW_CYCLES | UNION ALL — pending leave + performance |

> **WARNING on VW_ORG_HIERARCHY:** Performance degrades significantly with >500 employees

---

## Known Bugs Found in Source Code

| # | Bug | Location | Severity |
|---|---|---|---|
| 1 | SQL injection — dynamic SQL concatenates user input `p_last_name` | PKG_REPORTING | Critical |
| 2 | Hard-coded AES-256-CBC encryption key in package body | PKG_SECURITY | Critical |
| 3 | FTP credentials stored in cleartext in SYSTEM_PARAMETERS | PKG_INTEGRATION | Critical |
| 4 | `authenticate()` may not verify password in all paths | PKG_SECURITY | Critical |
| 5 | MD5 password hashing (should be bcrypt/scrypt) | PKG_SECURITY | High |
| 6 | Race condition — `generate_emp_number` uses MAX()+1, not sequence | PKG_EMPLOYEE | High |
| 7 | Exception swallowing — WHEN OTHERS THEN NULL/ROLLBACK | Multiple | High |
| 8 | Hard-coded 2024 tax brackets (should read from TAX_BRACKETS table) | PKG_PAYROLL | Medium |
| 9 | Email validator rejects valid subdomains | HRMS_VALIDATION_LIB | Medium |
| 10 | `change_password()` does not verify old password before updating | PKG_SECURITY | Medium |
| 11 | `p_reason` in `reverse_payroll` never persisted — audit gap | PKG_PAYROLL | Medium |
| 12 | `expire_carryover` double-run risk | PKG_LEAVE | Medium |
| 13 | SMTP host/port hard-coded (should be in SYSTEM_PARAMETERS) | PKG_NOTIFICATION | Low |
| 14 | No account lockout after failed login attempts | PKG_SECURITY | Low |
| 15 | Circular dependency: PKG_EMPLOYEE ↔ PKG_PAYROLL | Both | Info |

> Bugs 1–4 must be addressed before forward engineering begins.

---

## OSIRIS vs Team Chunk Scan — Side by Side

| Dimension | OSIRIS | Team Chunk Scan |
|---|---|---|
| Format | ✅ Structured JSON | ❌ Prose markdown |
| Machine-readable | ✅ Yes — code generators can consume directly | ❌ No — human re-reading required |
| Param directions | ✅ All 336 — IN/OUT/IN OUT structured | ⚠️ Spec chunks: full. Body chunks: IN dropped |
| Rule text | ✅ Verbatim word-for-word from source | Paraphrased — same facts, different words |
| CHECK constraints | ✅ 29/29 verbatim including multi-line | Prose descriptions |
| All error codes | ✅ 34/34 + 21 PRAGMA across all packages | ✅ 34/34 (PKG_SECURITY PRAGMA only) |
| NOTE + WARNING comments | ✅ All 11 captured | ✅ In narrative |
| Verified accuracy | ✅ 3,715 audit checks | ❌ Zero checks |
| Procedure narrative | ❌ None | ✅ 5–15 lines per procedure with logic + edge cases |
| Source line references | ❌ None | ✅ Every claim tagged [SOURCE: Lxx] |
| Architecture risk notes | ❌ None | ✅ e.g. timeout risk, circular deps, stubs |

**Both are accurate. Neither invents data. They are complementary — use both.**

---

## How the Parser Works — 8 Engines

```
oracle_deep_parser.py
│
├── Engine 1 — PL/SQL Spec Parser     (.pks)   → procedures, params, exceptions, types
├── Engine 2 — PL/SQL Body Parser     (.pkb)   → rules, constants, raise errors, bugs
├── Engine 3 — DDL Schema Parser      (tables) → columns, PKs, FKs, CHECKs, UNIQUEs
├── Engine 4 — Trigger Parser         (trg)    → trigger rules, RAISE codes
├── Engine 5 — Oracle Forms XML       (.xml)   → blocks, items, LOVs, relations, alerts
├── Engine 6 — PLL Library Parser     (.pll)   → procedures, validation rules
├── Engine 7 — Menu Module Parser     (.mmb)   → tree, actions, permissions
├── Engine 8 — Seed Data Parser       (.sql)   → 133 rows, {column: value} per row
│
└── Business Rules Consolidator       → BR-0001..BR-0807 with source + category
```

**Key techniques:**
- Balanced-parenthesis extractor — handles multi-line CHECK constraints and nested function calls
- Line-by-line DDL parser — prevents column-type boundary merging bugs
- Character-by-character seed parser — correctly handles `'Smith, John'` vs separator commas
- `_SQL_NOISE` filter (80 tokens) — stops SQL keywords being captured as table names

---

## Problems Fixed During Development (18 total)

| # | Problem | Fix |
|---|---|---|
| 1 | Wrong SOURCE_DIR path | Set to `Path(__file__).parent / correct / path` |
| 2 | Column-type boundary bug — adjacent column absorbed into type | Line-by-line DDL parser |
| 3 | SQL keywords captured as table names | `_SQL_NOISE` filter set |
| 4 | Inline comments parsed as parameter names | Strip `-- comments` before param splitting |
| 5 | UNIQUE constraints not extracted | Added UNIQUE handler in constraint parser |
| 6 | Trigger RAISE errors not captured | Applied RAISE extractor to trigger files |
| 7 | Nested function in param default broke extractor | Balanced-paren `_extract_param_block()` |
| 8 | `c_encryption_key` not captured (no CONSTANT keyword) | Added `c_` RAW variable pattern |
| 9 | XML FormatMask, TabPage, Alerts not extracted | Added explicit XML attribute reads |
| 10 | Menu parser captured 0 items | Strip `--` prefix before tree-parsing |
| 11 | Modules menu items missed (nested parens in action) | Changed action capture to greedy `.+` |
| 12 | RAISE message bleed across hundreds of lines | Removed DOTALL, split into 3 patterns |
| 13 | Parameter directions (IN/OUT) not captured | Added `{name, direction, type}` dict parsing |
| 14 | FK referenced table names not verified | Added FK accuracy check to audit.py |
| 15 | View body truncated — UNION ALL missed | Split on CREATE boundaries, match greedily |
| 16 | VALIDATION comments not captured (27 missed) | Added VALIDATION to all tag extraction calls |
| 17 | Multi-line CHECK constraint missed (EMPLOYEE_HISTORY) | Balanced-paren `_extract_check_constraints()` |
| 18 | NOTE + WARNING comments not extracted | Added NOTE/WARNING extraction in all engines |
