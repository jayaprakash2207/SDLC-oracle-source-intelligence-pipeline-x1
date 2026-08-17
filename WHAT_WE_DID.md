# What We Did — Oracle HRMS Deep Parser
**Project:** Oracle HRMS Reverse Engineering — Source Code Extraction Phase  
**Date:** 2026-08-17  
**GitHub:** https://github.com/jayaprakash2207/SDLC-oracle-source-intelligence-pipeline-x1

---

## The Goal

Extract 100% of every business rule, validation, constraint, structure, and fact
from 42 Oracle HRMS source files so that AI agents can generate 25 accurate
forward-engineering documents without missing anything.

---

## Source Files — What We Worked With

```
source/ts-plsql-oracle-forms-hrms/ts-plsql-oracle-forms-hrms-main/
```

| Folder | Files | Content |
|---|---|---|
| `schema/tables/` | 4 `.sql` | CREATE TABLE — 30 tables |
| `schema/views/` | 1 `.sql` | 6 database views |
| `schema/sequences/` | 1 `.sql` | 29 sequences |
| `plsql/packages/` | 22 `.pks`+`.pkb` | 11 PL/SQL packages |
| `plsql/triggers/` | 2 `.sql` | 6 database triggers |
| `forms/xml-exports/` | 6 `.xml` | Oracle Forms screens |
| `forms/libraries/` | 2 `.sql` | PLL shared libraries |
| `forms/menus/` | 1 `.sql` | HRMS_MENU module |
| `data/seed/` | 2 `.sql` | 133 seed data rows |
| `README.md` | 1 | Project docs |
| **Total** | **42 files** | |

---

## What We Built

`oracle_deep_parser.py` — a single Python script that reads every line of every
source file and extracts structured intelligence. No external dependencies —
runs on Python stdlib only (`re`, `xml.etree.ElementTree`, `json`, `pathlib`).

Two audit scripts verify the output is 100% accurate:
- `audit.py` — structural audit (names, types, directions, constraints)
- `audit_full.py` — content audit (rule text, values, queries, properties)

---

## How the Parser Works — Step by Step

The parser has 8 independent extraction engines, one per file type.
Every engine reads its source files directly and writes structured JSON.
Nothing is inferred — every fact comes from a literal line in the source.

```
oracle_deep_parser.py
│
├── 1. PL/SQL Package Spec Parser   (.pks files)
├── 2. PL/SQL Package Body Parser   (.pkb files)
├── 3. DDL Schema Parser            (tables, views, sequences)
├── 4. Trigger Parser               (.sql trigger files)
├── 5. Oracle Forms XML Parser      (.xml files)
├── 6. PLL Library Parser           (.pll.sql files)
├── 7. Menu Module Parser           (.mmb.sql file)
├── 8. Seed Data Parser             (.sql seed files)
│
└── Business Rules Consolidator     (collects from all 8 above)
```

---

### Engine 1 — PL/SQL Package Spec Parser (`.pks`)

**Input:** 11 `.pks` files (package specifications)  
**What it reads:** The public contract of each package — what procedures and
functions exist, what parameters they take, what they return.

**How it works:**
1. Finds `CREATE OR REPLACE PACKAGE HRMS.PKG_xxx AS` to get the package name
2. For each `PROCEDURE name(...)` — uses a **balanced-parentheses extractor**
   to capture the full parameter block even when params span multiple lines or
   contain nested function calls like `DEFAULT EXTRACT(YEAR FROM SYSDATE)`
3. For each parameter — strips inline `-- comments` first, then splits on `,`
   and matches `param_name  IN|OUT|IN OUT  TYPE` to get name + direction + type
4. For each `FUNCTION name(...) RETURN type` — same param extraction + return type
5. Finds `e_xxx EXCEPTION` declarations and maps them to their
   `PRAGMA EXCEPTION_INIT(e_xxx, -20xxx)` error codes
6. Finds `TYPE xxx IS RECORD|REF CURSOR|TABLE` definitions
7. Finds `g_xxx` global variable declarations
8. Reads `-- Dependencies:`, `-- Called by:`, `-- Known issues:` header comments

**Output fields:** `procedures[]`, `functions[]`, `exceptions[]`, `types[]`,
`global_variables[]`, `dependencies`, `callers`, `known_issues`

---

### Engine 2 — PL/SQL Package Body Parser (`.pkb`)

**Input:** 11 `.pkb` files (package body implementations)  
**What it reads:** The actual logic — business rules buried in comments,
constants, error codes, SQL operations, cross-package calls.

**How it works:**
1. Finds `CREATE OR REPLACE PACKAGE BODY HRMS.PKG_xxx AS`
2. Splits the file into per-procedure body sections by finding all
   `PROCEDURE name` and `FUNCTION name` positions and slicing between them
3. For each tagged comment in the body — extracts verbatim text:
   - `-- BUSINESS:` → business rules
   - `-- RULE:` → validation rules
   - `-- VALIDATION:` → validation notes
   - `-- CONSTRAINT:` → system constraints
   - `-- BUG:` → known defects
4. For constants — two regex patterns:
   - `name CONSTANT TYPE := value` (standard)
   - `c_name RAW(N) := value` (no CONSTANT keyword, e.g. `c_encryption_key`)
5. For RAISE errors — three patterns to avoid message bleed:
   - Single-line: `RAISE_APPLICATION_ERROR(-20xxx, 'message')`
   - Concatenated: `RAISE_APPLICATION_ERROR(-20xxx, 'text' ||`
   - Multi-line: error code on one line, message on next indented line
6. For SQL operations — `FROM`, `JOIN`, `INSERT INTO`, `UPDATE`, `DELETE FROM`
   all filtered through `_SQL_NOISE` set to remove keyword false positives
7. Infers behavioral rules from code patterns:
   - `PRAGMA AUTONOMOUS_TRANSACTION` → audit isolation rule
   - `SYS_CONTEXT('USERENV','IP_ADDRESS')` → IP capture rule
   - `UTL_SMTP.` → email delivery rule
   - Dynamic SQL + user input → SQL injection bug
   - `EXCEPTION WHEN OTHERS THEN NULL` → silent swallow bug
8. Detects `DBMS_CRYPTO`, `UTL_FILE`, `UTL_SMTP`, `DBMS_OUTPUT` usage
9. Finds all `SEQ_xxx.NEXTVAL` sequence usage
10. Finds all `PKG_xxx.procedure` cross-package calls

**Output fields:** `constants[]`, `business_rules[]`, `rules[]`,
`validation_notes[]`, `constraints[]`, `bugs[]`, `raise_errors[]`,
`sql{}`, `procedures[]` (each with own rules/SQL/raises), `pragma_autonomous`,
`utl_packages_used[]`, `dbms_packages_used[]`

---

### Engine 3 — DDL Schema Parser

**Input:** `schema/tables/*.sql`, `schema/views/hrms_views.sql`,
`schema/sequences/hrms_sequences.sql`

**Tables — how it works:**
1. Finds each `CREATE TABLE HRMS.tablename (...)` block
2. Parses the body **line by line** (not with a single regex) to avoid the
   column absorption bug — each line is matched independently
3. For each non-constraint line — matches `COLUMN_NAME TYPE(size)` pattern
   using a whitelist of known Oracle types (NUMBER, VARCHAR2, CHAR, DATE, etc.)
4. Captures `DEFAULT value` and `NOT NULL` flags per column
5. Detects `GENERATED ALWAYS AS (...) VIRTUAL` columns
6. On `CONSTRAINT` lines — routes to the right handler:
   - `PRIMARY KEY (cols)` → pk list
   - `UNIQUE (cols)` → unique constraint with name
   - `FOREIGN KEY (col) REFERENCES table(col)` → FK with constraint name + referenced table
   - `CHECK (expression)` → check constraint expression verbatim

**Views — how it works:**
1. Splits file on `CREATE OR REPLACE VIEW` boundaries (not lazy regex)
   so each view gets its **complete body** including UNION ALL sections
2. From each view body — extracts all `FROM table` and `JOIN table` references
   using a noise filter to skip aliases and keywords

**Sequences — how it works:**
1. Scans for `CREATE SEQUENCE name START WITH n INCREMENT BY n [CACHE n|NOCACHE]`
2. Captures all three numeric values
3. Reads up to 4 comment lines above each sequence as notes

---

### Engine 4 — Trigger Parser

**Input:** `plsql/triggers/trg_employees.sql`, `trg_audit.sql`

**How it works:**
1. Finds each `CREATE OR REPLACE TRIGGER name BEFORE|AFTER|INSTEAD OF event ON table`
2. Slices body between consecutive trigger headers
3. Collects header comments (lines above CREATE) and appends to body for rule extraction
4. Extracts BUSINESS/RULE/VALIDATION/BUG tagged comments from combined text
5. Applies same RAISE error extractor as package bodies
6. Detects `PRAGMA AUTONOMOUS_TRANSACTION` and `SYS_CONTEXT` usage
7. Extracts inline JSON construction patterns from audit trigger bodies
8. Finds all `PKG_xxx.procedure` calls

---

### Engine 5 — Oracle Forms XML Parser

**Input:** 6 `.xml` Oracle Forms export files

**How it works:**
Python's `xml.etree.ElementTree` parses the XML tree. Then:

1. **Form level** — reads `Name`, `Title`, `FirstNavigationBlock`, `MenuModule`
2. **Libraries** — finds all `<AttachedLibrary Name="..."/>` elements
3. **Canvases** — for each `<Canvas>` finds all `<TabPage Name="" Label=""/>`
4. **Blocks** — for each `<Block>` reads:
   - `DMLDataTargetName` (which table it reads/writes)
   - `DefaultWhere`, `OrderByClause`
   - `RecordsDisplayed`, insert/update/delete/query permissions
5. **Items** — for each `<Item>` reads all key attributes:
   - `ItemType`, `DataType`, `MaximumLength`, `RequiredItem`
   - `ColumnName`, `CanvasName`, `TabPageName`
   - `FormatMask` (e.g. `$999,999,990.00`, `MM/DD/YYYY`, `990.00%`)
   - `PrimaryKey`, `DatabaseItem`, `LOV`
   - `ListItemElement` children → poplist label/value pairs
6. **Triggers** — for each `<Trigger>` reads `TriggerText` element body,
   then extracts PKG calls, BUSINESS/RULE comments, RAISE errors
7. **LOVs** — `<LOV>` with `Name`, `Title`, `RecordGroup`,
   and all `<ColumnMapping ReturnItem="..."/>` children
8. **Record Groups** — `QueryText` attribute or `<RecordGroupQuery>` child text
9. **Relations** — `DeleteRecordBehavior`, `AutoQuery`, `Deferred`, `JoinCondition`
10. **Windows** — `Name`, `Title`, `Width`, `Height`
11. **Alerts** — `Name`, `AlertStyle`, `Message`, `Button1Label`, `Button2Label`, `Button3Label`

---

### Engine 6 — PLL Library Parser

**Input:** `forms/libraries/HRMS_COMMON_LIB.pll.sql`,
`forms/libraries/HRMS_VALIDATION_LIB.pll.sql`

**How it works:**
1. Finds each `PROCEDURE name(...) IS` or `FUNCTION name(...) RETURN type IS`
   using multiline regex anchored at start of line
2. Slices body between consecutive procedure/function positions
3. From each body — extracts:
   - BUSINESS/RULE/VALIDATION/BUG tagged comments
   - Oracle Forms built-in calls (COMMIT_FORM, EXIT_FORM, GO_BLOCK, etc.)
   - `TO_CHAR(value, 'mask')` format mask patterns
   - `v_xxx VARCHAR2(N)` buffer size declarations
   - `NVL(:GLOBAL.current_user, USER)` fallback patterns
   - `WHEN exception THEN action` exception handling
   - Cross-package calls `PKG_xxx.procedure`
4. Reads `-- Dependencies:` and `-- Attached by:` header metadata

---

### Engine 7 — Menu Module Parser

**Input:** `forms/menus/HRMS_MENU.mmb.sql`

**How it works:**
The entire menu structure is encoded in SQL comment lines (`--` prefix).
The actual compiled `.mmb` binary cannot be read as text.

1. Strips `--` prefix from every line to reveal the tree structure:
   ```
     ├── File
     │   ├── Save                 (COMMIT_FORM)
     │   └── Exit                 (EXIT_FORM)
     ├── Modules
     │   ├── Employee Management  (OPEN_FORM('HRMS_EMPLOYEE'))
   ```
2. Lines matching `^\s+[├└]──\s+word$` with no `(action)` = top-level menu header
3. Lines matching `[├└]──  label  (action)` with 2+ spaces before `(` = menu item
   — greedy `.+` captures action including nested parens like `OPEN_FORM('...')`
4. Lines matching `(requires WORD permission)` = permission-guarded item
5. Extracts all `OPEN_FORM('...')` targets, `SHOW_WINDOW('...')` calls,
   `SHOW_ALERT('...')` calls, `WEB.SHOW_DOCUMENT('...')` calls
6. Finds `PKG_SECURITY.has_permission` guard calls

---

### Engine 8 — Seed Data Parser

**Input:** `data/seed/reference_data.sql`, `data/seed/employee_data.sql`

**How it works:**
1. Finds each `INSERT INTO table (col1, col2, ...) VALUES (val1, val2, ...);`
2. Parses the VALUES list with a **character-by-character state machine**
   that tracks quote depth and parenthesis depth — this correctly handles:
   - Quoted strings with embedded commas: `'Smith, John'`
   - Oracle function calls: `TO_DATE('2024-01-01', 'YYYY-MM-DD')`
   - Nested expressions: `NVL(value, default)`
3. Maps each value to its column name
4. Groups rows by table name
5. Finds `UPDATE table SET ... WHERE ...` statements (e.g. manager assignments
   in DEPARTMENTS that can only be set after all employees are inserted)

---

### Business Rules Consolidator

After all 8 engines run, the consolidator:
1. Collects every rule from every source
2. Assigns a unique ID: `BR-0001` through `BR-0775`
3. Tags each with: `source` (e.g. `HRMS.PKG_EMPLOYEE`),
   `source_type` (e.g. `plsql_procedure`), `category` (e.g. `business_rule`)
4. Writes `business_rules.json` — the single file that feeds all document agents

**Categories captured:**
`business_rule`, `validation_rule`, `validation_note`, `error_rule`,
`constraint`, `check_constraint`, `unique_constraint`, `known_bug`

---

## The Journey — Problems Faced and How We Fixed Them

### Problem 1: Wrong ground truth
**What happened:** Initial verification compared parser output against 19 teammate-generated
chunk scan files — not the actual Oracle source code.  
**Result:** False 79.3% coverage number. The chunks themselves had errors.  
**Fix:** Threw out the chunk comparison entirely. Rewrote verification to compare
directly against the 42 source files line by line. This is the only correct approach.

---

### Problem 2: Column-type boundary bug (adjacent column absorbed)
**What happened:** Regex `(\w+)\s+(TYPE[^,]+)` was greedy — when parsing column
definitions like:
```sql
DEPT_ID    NUMBER(10)    NOT NULL,
DEPT_CODE  VARCHAR2(20)  NOT NULL,
```
The type for `DEPT_ID` would absorb `DEPT_CODE` into its type string.  
**Fix:** Switched to line-by-line parsing. Each line is parsed independently.
Type regex stops at end of line, never crosses the comma boundary.

---

### Problem 3: SQL keywords injected as fake table names
**What happened:** `FROM\s+(\w+)` regex matched SQL keywords like `IN`, `IS`,
`UPDATE`, `THE`, `P_DATE` and added them to `selects_from` lists.  
**Fix:** Added `_SQL_NOISE` set of ~80 known SQL keywords and short tokens.
Any captured table name is filtered against this set before being stored.

---

### Problem 4: Inline comments parsed as parameter names
**What happened:** `format_name` in PKG_COMMON has this signature:
```sql
FUNCTION format_name(
    p_first_name IN VARCHAR2,
    p_last_name  IN VARCHAR2,
    p_format     IN VARCHAR2 DEFAULT 'FL'  -- FL=First Last, LF=Last, First
) RETURN VARCHAR2;
```
The `-- FL=First Last, LF=Last, First` comment was being split on commas,
making `LF=Last` and `First` appear as parameter names.  
**Fix:** `_parse_params()` now strips `--[^\n]*` before splitting on commas.

---

### Problem 5: UNIQUE constraints not extracted
**What happened:** DDL parser only looked for PRIMARY KEY and FOREIGN KEY.
`CONSTRAINT UK_DEPT_CODE UNIQUE (DEPT_CODE)` was completely missed.  
**Fix:** Added `UNIQUE\s*\(([^)]+)\)` regex inside the constraint-line handler.
Now extracts all 10 unique constraints with their names and column lists.

---

### Problem 6: Trigger RAISE_APPLICATION_ERROR codes not captured
**What happened:** RAISE error extraction was applied to package bodies but
not to trigger files. Errors -20501 to -20504 in `trg_employees.sql` were missed.  
**Fix:** Applied `extract_raise_application_errors()` to trigger body text.
All 4 trigger errors now captured alongside 34 package errors (38 total).

---

### Problem 7: `leave_utilization_report` missing from PKG_REPORTING
**What happened:** The procedure has a parameter with a nested function call:
```sql
PROCEDURE leave_utilization_report(
    p_year IN NUMBER DEFAULT EXTRACT(YEAR FROM SYSDATE),
    ...
);
```
The regex `([^)]*)` stopped at the `)` inside `EXTRACT(...)`,
so the outer `)` never matched and the whole procedure was skipped.  
**Fix:** Replaced simple `([^)]*)` regex with a balanced-parentheses parser
(`_extract_param_block`) that counts depth and stops only at the matching
outer `)`.

---

### Problem 8: `c_encryption_key` not captured (no CONSTANT keyword)
**What happened:** Standard constant extraction looks for `CONSTANT` keyword:
```sql
c_session_timeout_min CONSTANT NUMBER := 30;          -- captured
c_encryption_key RAW(32) := UTL_RAW.CAST_TO_RAW(...)  -- missed
```
**Fix:** Added a second regex for `c_` prefixed `RAW(N)` variables without
the CONSTANT keyword. Also captures the preceding `-- VULNERABILITY:` comment.

---

### Problem 9: XML FormatMask, TabPage, RecordsDisplayed, Alert buttons not extracted
**What happened:** Oracle Forms XML parser was not reading these attributes:
```xml
<Item Name="BASE_SALARY" FormatMask="$999,999,990.00"/>
<TabPage Name="TP_PERSONAL" Label="Personal Information"/>
<Block Name="EMPLOYEE" RecordsDisplayed="1"/>
<Alert Name="ALT_CONFIRM_EXIT" Button1Label="Save" Button2Label="Discard"/>
```
**Fix:** Added explicit attribute reads for all four. Result:
28 format masks, 16 tab pages, 12 RecordsDisplayed values, 3 alerts with buttons.

---

### Problem 10: Menu parser captured 0 items
**What happened:** The entire menu structure in `HRMS_MENU.mmb.sql` is inside
SQL comment lines (all lines start with `--`). The regex matched against raw
lines and never found the `├──` tree characters.  
**Fix:** Strip `--` prefix from every line before tree-parsing.
Result: 7 menus, 31 items all captured.

---

### Problem 11: Modules menu still 0 items (nested parentheses)
**What happened:** After the `--` fix, items like:
```
├── Employee Management  (OPEN_FORM('HRMS_EMPLOYEE'))
```
still didn't match because `([^)]+)` stops at the first `)` inside
`OPEN_FORM('HRMS_EMPLOYEE')`, leaving the outer `)` unmatched.  
**Fix:** Changed action capture to greedy `.+` anchored at end-of-line.
All 6 Modules items now captured.

---

### Problem 12: RAISE error message bleed (multi-line regex)
**What happened:** `re.DOTALL` in RAISE error extraction caused the message
string to bleed across hundreds of lines of surrounding code.  
**Fix:** Removed `re.DOTALL`. Three separate patterns: single-line literals,
concatenated messages, and multi-line where code and message are on separate lines.

---

### Problem 13: Parameter directions (IN/OUT/IN OUT) not captured
**What happened:** `_parse_params()` only returned names, not directions or types.  
**Fix:** Upgraded to return `{name, direction, type}` dicts.
Regex `(\w+)\s+(IN\s+OUT|IN|OUT)\s+([\w%()]+)` captures all three fields.

---

### Problem 14: FK constraints not verified for accuracy
**What happened:** FK names existed in output but referenced table names
were not verified against source.  
**Fix:** Added FK accuracy check to `audit.py`: every constraint name AND
referenced table must match exactly.

---

### Problem 15: `VW_PENDING_APPROVALS` body truncated (UNION ALL missed)
**What happened:** View body regex `(.*?)(?=CREATE|\Z)` with lazy `.*?`
stopped at only 226 characters — before the `FROM` clause. The entire
UNION ALL second SELECT was missed (LEAVE_REQUESTS, PERFORMANCE_REVIEWS,
LEAVE_TYPES, REVIEW_CYCLES, EMPLOYEES all missing).  
**Fix:** Split view file on `CREATE` boundaries first, then match each block
greedily — capturing full body including UNION ALL sections.

---

### Problem 16: `-- VALIDATION:` comments not captured (27 missed)
**What happened:** Parser extracted BUSINESS/RULE/BUG/CONSTRAINT tags
but not VALIDATION. 27 comments across 8 packages, 2 trigger files,
and 1 PLL library were completely missed.  
**Fix:** Added VALIDATION to every tag extraction call and to the
business rules consolidator as `validation_note` category.
Rules count: 721 → **775**.

---

## Final Output — `parser-output/`

| File | Contents |
|---|---|
| `plsql_deep.json` | 11 packages — procedures, functions, params with IN/OUT, constants, raise errors, rules |
| `forms_deep.json` | 6 forms — blocks, items, format masks, tab pages, alerts, LOVs, relations |
| `pll_deep.json` | 2 PLL libraries — HRMS_COMMON_LIB + HRMS_VALIDATION_LIB |
| `menu_deep.json` | HRMS_MENU — 7 menus, 31 items, OPEN_FORM calls |
| `schema_deep.json` | 30 tables, 6 views (full SQL incl UNION ALL), 6 triggers, 29 sequences |
| `seed_deep.json` | 133 seed rows with all column values |
| `business_rules.json` | 775 rules BR-0001 to BR-0775 |
| `DEEP_REPORT.md` | Human-readable full summary |

---

## Verification — How We Proved 100%

| Audit | Checks | Result |
|---|---|---|
| `audit.py` — structural | 1,195 | 100% |
| `audit_full.py` — content | 2,050 | 100% |
| **Combined** | **3,245** | **100%** |

**`audit.py` checks:** package/procedure/function names, parameter names+directions+types,
table+column names, FK names+referenced tables, CHECK expressions word-for-word,
UNIQUE constraint names, sequences, triggers, RAISE error codes, form blocks/alerts/tab pages/
format masks, menu items, PLL procedures, seed row count.

**`audit_full.py` checks:** BUSINESS/RULE/VALIDATION/BUG comment text verbatim,
constant values, view FROM+JOIN tables including UNION ALL, seed row column values,
form item properties (data_type, max_length, required, format_mask, column mapping),
poplist values, block relation attributes, LOV column mappings, record group query tables,
sequence START WITH + INCREMENT BY values, form trigger PKG calls.

---

## Rule Breakdown (775 total)

| Category | Count | Description |
|---|---|---|
| validation_rule | 491 | Inferred from code patterns + RULE comments |
| business_rule | 106 | BUSINESS comments verbatim |
| validation_note | 54 | VALIDATION comments verbatim |
| error_rule | 38 | RAISE_APPLICATION_ERROR codes + messages |
| constraint | 33 | CONSTRAINT comments |
| check_constraint | 28 | Database-level CHECK expressions |
| known_bug | 15 | BUG comments |
| unique_constraint | 10 | UNIQUE constraint definitions |
| **Total** | **775** | |

---

## Tools Used

| Tool | Purpose |
|---|---|
| `xml.etree.ElementTree` (stdlib) | Oracle Forms XML parsing |
| `re` regex (stdlib) | PL/SQL / DDL pattern extraction |
| Python 3.12 | Runtime — zero external dependencies |

---

*Last updated: 2026-08-17 | Oracle HRMS Reverse Engineering Pipeline*
