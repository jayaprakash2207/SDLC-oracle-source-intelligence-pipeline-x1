# What We Did — Graphify + Oracle Parser
**Project:** Oracle HRMS Reverse Engineering — Source Code Extraction Phase  
**Date:** 2026-08-13  
**Folder:** `graphify + oracle parser/`

---

## The Goal

Before the AI pipeline can generate 25 enterprise documents, it needs to deeply understand
the legacy Oracle HRMS source code. The source has 42 files written in Oracle-specific
formats — DDL SQL, PL/SQL packages, database triggers, and Oracle Forms XML. No general-purpose
tool can fully read all of these. So we built a 3-layer extraction system to achieve 100%
file coverage and extract every business rule, validation, constraint, and structure from
every single file.

---

## The Source Code We Worked With

Located at:
```
source/ts-plsql-oracle-forms-hrms/ts-plsql-oracle-forms-hrms-main/
```

| Folder | Files | What They Contain |
|---|---|---|
| `schema/tables/` | 4 `.sql` files | DDL — CREATE TABLE statements for all 30 tables |
| `schema/views/` | 1 `.sql` file | 6 database views |
| `schema/sequences/` | 1 `.sql` file | Auto-increment sequences |
| `plsql/packages/` | 22 files (`.pks` + `.pkb`) | 11 PL/SQL packages — all business logic |
| `plsql/triggers/` | 2 `.sql` files | 5 database triggers |
| `forms/xml-exports/` | 6 `.xml` files | Oracle Forms — all screens and UI logic |
| `forms/libraries/` | 2 `.sql` files | Shared form libraries |
| `forms/menus/` | 1 `.sql` file | Menu definitions |
| `data/seed/` | 2 `.sql` files | Reference and employee seed data |
| `README.md` | 1 file | Project documentation |
| **Total** | **42 files** | |

---

## Step 1 — Graphify (Knowledge Graph from SQL Files)

### What is Graphify?
Graphify (`pip install graphifyy`) is an open-source tool that reads source code and builds
a **knowledge graph** — a network of nodes (things) and edges (relationships between them).
It is designed for AI coding assistants so they can understand a codebase structurally.

### What We Did
1. Installed `graphifyy` (v0.9.1 was already present — upgraded to v0.9.41)
2. Discovered that `.sql` files were being silently skipped — the SQL tree-sitter parser
   was a separate optional install (`graphifyy[sql]`)
3. Installed `pip install "graphifyy[sql]"` which added `tree-sitter-sql` (v0.3.11)
4. Had to copy source files to `C:\oracle-hrms-src` (no spaces in path) because
   Windows path-with-spaces caused graphify's temp file writer to crash
5. Ran `python -m graphify update . --force` from the clean path
6. Copied output to `graphify + oracle parser/graphify-out/`

### What Graphify Produced

| Metric | Result |
|---|---|
| Nodes | 74 |
| Edges | 71 |
| Communities | 15 |
| Files scanned | 14 (SQL + README) |
| Files skipped | 28 (`.pkb`, `.pks`, `.xml` — not supported) |

**Communities found:**
- Community 3 — Core Tables: `HRMS.EMPLOYEES`, `HRMS.DEPARTMENTS`, `HRMS.LOCATIONS`, `HRMS.JOB_GRADES`, `HRMS.JOB_TITLES` + 3 more
- Community 2 — Payroll Tables: `HRMS.PAYROLL_RUNS`, `HRMS.SALARY_RECORDS`, `HRMS.PAY_ELEMENTS` + 6 more
- Community 5 — Leave Tables: `HRMS.LEAVE_REQUESTS`, `HRMS.LEAVE_BALANCES`, `HRMS.LEAVE_TYPES` + 2 more
- Community 4 — Performance Tables: `HRMS.PERFORMANCE_REVIEWS`, `HRMS.AUDIT_LOG` + 6 more
- Community 6 — Views: `HRMS.VW_PAYROLL_LATEST`, `HRMS.VW_ACTIVE_EMPLOYEES` + 5 more

**Most connected nodes (core of the system):**
1. `HRMS.VW_ACTIVE_EMPLOYEES` — 7 edges
2. `HRMS.VW_EMPLOYEE_COMPENSATION` — 6 edges
3. `HRMS.VW_PENDING_APPROVALS` — 6 edges

**Surprising connection found:**
- `HRMS.VW_PAYROLL_LATEST` reads from `EMPLOYEES` — bridges payroll community to employee community

**Output files:**
- `graphify-out/graph.json` — full graph (nodes + edges)
- `graphify-out/graph.html` — interactive visual graph (open in browser)
- `graphify-out/GRAPH_REPORT.md` — human-readable summary
- `graphify-out/manifest.json` — list of every file scanned

### Why Graphify Didn't Work at First
Three problems were discovered and fixed:
1. **Old version (0.9.1)** — silently skipped all `.sql` files with no warning. Fixed by upgrading to 0.9.41
2. **Missing SQL plugin** — `tree-sitter-sql` was not installed. The new version warned us. Fixed by `pip install "graphifyy[sql]"`
3. **Windows path with spaces** — `c:\rev-eng1 test oracle new\...` caused temp file crash. Fixed by running from `C:\oracle-hrms-src`

---

## Step 2 — Oracle Parser (PL/SQL Packages + Oracle Forms)

### Why We Needed This
Graphify does not support `.pkb`, `.pks` (PL/SQL package) or Oracle Forms `.xml` files.
These 28 files contain **the most important content** — all the business logic, procedures,
functions, form screens, and validation rules. Without them the graph was only 33% complete.

### What We Built
`oracle_parser.py` — a custom Python parser using regex and Python's built-in XML parser (`xml.etree.ElementTree`).

### How It Works — PL/SQL Parser
For each `.pks` (package spec) file:
- Extracts the package name (`CREATE OR REPLACE PACKAGE HRMS.PKG_xxx AS`)
- Lists all `PROCEDURE` and `FUNCTION` signatures
- Reads `-- Dependencies:` and `-- Called by:` comment headers
- Reads `-- Known issues:` block
- Extracts custom exception definitions and `PRAGMA EXCEPTION_INIT` codes
- Extracts `TYPE` definitions (record types, cursor types, table types)

For each `.pkb` (package body) file:
- Extracts procedure/function implementations
- Finds all `FROM / JOIN / INTO / UPDATE` table references → which tables each package touches
- Finds all `PKG_xxx.procedure` cross-package calls
- Finds all `RAISE` statements

### How It Works — Oracle Forms XML Parser
For each `.xml` Oracle Forms export:
- Parses `<FormModule>` attributes (name, title, first block, menu module)
- Finds all `<AttachedLibrary>` — which shared libraries the form uses
- Finds all `<Block>` — data blocks with their `DMLDataTargetName` (which table they read/write)
- Finds all `<Item>` within each block — form fields
- Finds all `<Trigger>` — both form-level and block-level event handlers
- Finds all `<LOV>` — list of values (dropdowns)
- Finds all `<Canvas>` and `<Window>` definitions
- Extracts all `PKG_xxx.procedure` calls from trigger body text

### What It Produced

**PL/SQL Packages (11 packages, 235 nodes):**

| Package | Procedures | Functions | Tables Accessed | Dependencies |
|---|---|---|---|---|
| PKG_AUDIT | 2 | 1 | 1 | None (base) |
| PKG_COMMON | 3 | 14 | 6 | None (base) |
| PKG_EMPLOYEE | 7 | 10 | 19 | PKG_COMMON, PKG_AUDIT, PKG_NOTIFICATION, PKG_PAYROLL |
| PKG_INTEGRATION | 4 | 1 | 5 | PKG_COMMON, PKG_PAYROLL, PKG_EMPLOYEE |
| PKG_LEAVE | 10 | 3 | 14 | PKG_EMPLOYEE, PKG_COMMON, PKG_AUDIT, PKG_NOTIFICATION |
| PKG_NOTIFICATION | 4 | 0 | 3 | PKG_COMMON |
| PKG_PAYROLL | 9 | 7 | 17 | PKG_EMPLOYEE, PKG_COMMON, PKG_AUDIT, PKG_NOTIFICATION |
| PKG_PERFORMANCE | 8 | 4 | 6 | PKG_EMPLOYEE, PKG_COMMON, PKG_AUDIT, PKG_NOTIFICATION |
| PKG_REPORTING | 8 | 0 | 7 | PKG_EMPLOYEE, PKG_PAYROLL, PKG_COMMON |
| PKG_SECURITY | 2 | 6 | 4 | PKG_COMMON, PKG_AUDIT |
| PKG_VALIDATION | 0 | 8 | 4 | PKG_COMMON |

**Oracle Forms (6 forms, 45 nodes):**

| Form | Blocks | Items | Triggers | Package Calls |
|---|---|---|---|---|
| HRMS_EMPLOYEE | 2 | 38 | 3 | PKG_SECURITY, PKG_EMPLOYEE + 2 more |
| HRMS_LEAVE | 3 | 24 | 1 | PKG_SECURITY, PKG_LEAVE + 1 more |
| HRMS_LOGIN | 1 | 5 | 1 | PKG_SECURITY |
| HRMS_MENU | 1 | 8 | 1 | PKG_SECURITY, PKG_COMMON |
| HRMS_PAYROLL | 2 | 17 | 1 | PKG_SECURITY, PKG_PAYROLL + 3 more |
| HRMS_PERFORMANCE | 3 | 22 | 1 | PKG_PERFORMANCE |

**Combined graph after Step 2:**
- 74 (graphify) + 235 (PL/SQL) + 45 (Forms) = **338 total nodes**
- 71 (graphify) + 307 (PL/SQL) + 73 (Forms) = **451 total edges**

**Output files:**
- `graphify-out/oracle_plsql_graph.json`
- `graphify-out/oracle_forms_graph.json`
- `graphify-out/oracle_combined_graph.json`
- `graphify-out/ORACLE_PARSER_REPORT.md`

---

## Step 3 — Deep Parser (Full Business Logic Extraction)

### Why We Needed This
Step 2 told us **what exists** (package names, procedure names, form blocks).
Step 3 extracts **what the code actually does** — the business rules written inside
procedure bodies, the constraints embedded in comments, the validation logic,
the known bugs, the error codes, and the full trigger bodies.

### What We Built
`oracle_deep_parser.py` — a deep extraction engine using regex + sqlparse + XML parsing
that reads every line of every file and extracts structured intelligence.

### How It Works

**PL/SQL Deep Parser — Package Spec (`.pks`)**
- Extracts full procedure signatures with all parameter names and directions (IN/OUT)
- Extracts full function signatures with return types
- Extracts exception definitions with their `-20xxx` error codes via `PRAGMA EXCEPTION_INIT`
- Extracts `TYPE` definitions with their kind (RECORD, REF CURSOR, TABLE)
- Reads `-- Dependencies:`, `-- Called by:`, `-- Known issues:` comment blocks

**PL/SQL Deep Parser — Package Body (`.pkb`)**
- Reads every `-- BUSINESS:` comment → business rules
- Reads every `-- RULE:` comment → validation rules
- Reads every `-- CONSTRAINT:` comment → system constraints
- Reads every `-- BUG:` comment → known defects
- Extracts all `CONSTANT` declarations with their values and meanings
- Extracts all `RAISE_APPLICATION_ERROR(-20xxx, 'message')` calls → error catalogue
- Extracts per-procedure: SQL operations (SELECT FROM, INSERT INTO, UPDATE, DELETE FROM)
- Extracts per-procedure: IF conditions (validation logic)
- Extracts per-procedure: cross-package calls
- Extracts sequences used (`SEQ_xxx.NEXTVAL`)

**DDL Deep Parser — Schema Tables**
- Extracts every `CREATE TABLE` block
- For each table: all column names and data types
- PRIMARY KEY constraint columns
- FOREIGN KEY constraints with referenced table and columns
- CHECK constraints (embedded business rules at database level)

**DDL Deep Parser — Views**
- Extracts every `CREATE OR REPLACE VIEW` block
- Which tables each view reads from and joins
- Query snippet (first 300 chars) for context

**DDL Deep Parser — Database Triggers**
- Extracts trigger name, timing (BEFORE/AFTER/INSTEAD OF), events (INSERT/UPDATE/DELETE)
- Which table the trigger fires on
- All `-- BUSINESS:` and `-- RULE:` comments inside the trigger body
- All package calls made from the trigger

**Oracle Forms Deep Parser**
- Full trigger body text extracted (not just the trigger name)
- Per-block: `DEFAULT_WHERE` clause and `ORDER BY` clause
- Per-item: data type, max length, required flag, mapped column name
- Record groups with their full SQL query text (these power the LOV dropdowns)
- All `-- BUSINESS:` and `-- RULE:` comments inside trigger bodies
- All `RAISE_APPLICATION_ERROR` calls inside form triggers

**Business Rules Consolidator**
- Collects every rule from every source (packages, forms, triggers, DDL)
- Assigns a unique ID: `BR-0001` through `BR-0581`
- Tags each rule with source file, source type, and category

### What It Produced

| Category | Count |
|---|---|
| Business rules | 101 |
| Validation rules | 376 |
| Constraints | 33 |
| Known bugs | 5 |
| Error codes | 37 |
| Check constraints | 29 |
| **Total rules extracted** | **581** |

**Tables extracted:**
30 tables with full column definitions, PKs, FKs, and check constraints including:
`HRMS.EMPLOYEES`, `HRMS.DEPARTMENTS`, `HRMS.PAYROLL_RUNS`, `HRMS.SALARY_RECORDS`,
`HRMS.LEAVE_REQUESTS`, `HRMS.PERFORMANCE_REVIEWS`, `HRMS.AUDIT_LOG` and 23 more.

**Views extracted:**
`HRMS.VW_ACTIVE_EMPLOYEES`, `HRMS.VW_ORG_HIERARCHY`, `HRMS.VW_EMPLOYEE_COMPENSATION`,
`HRMS.VW_LEAVE_SUMMARY`, `HRMS.VW_PAYROLL_LATEST`, `HRMS.VW_PENDING_APPROVALS`

**DB Triggers extracted:**
`TRG_EMP_BEFORE_INSERT`, `TRG_EMP_BEFORE_UPDATE`, `TRG_EMP_INSTEAD_OF_DELETE`,
`TRG_SALARY_AUDIT`, `TRG_DEPARTMENT_AUDIT`

**Example business rules extracted:**
- `PKG_EMPLOYEE` — "Only departments flagged as active (ACTIVE_FLAG = 'Y') are valid for employee assignment"
- `PKG_PAYROLL` — "Social Security wage base 2024 is $168,600; earnings above this are exempt from SS tax"
- `PKG_PAYROLL` — "Employee Medicare tax rate is 1.45% on all wages with no cap"
- `PKG_PAYROLL` — "Additional 0.9% Medicare surtax applies to annual earnings above $200,000"
- `PKG_COMMON` — "Fiscal year begins October 1; dates in October or later belong to the following calendar year"
- `PKG_COMMON` — "Only system parameters with EDITABLE_FLAG = 'Y' may be modified"

**Example known bugs extracted:**
- `PKG_EMPLOYEE.generate_emp_number` — "Race condition under concurrent inserts — no SELECT FOR UPDATE"
- `PKG_EMPLOYEE.get_org_chart` — "Recursive SQL times out for deep hierarchies"

**Output files:**
- `graphify-out/deep/plsql_deep.json` — full PL/SQL extraction
- `graphify-out/deep/forms_deep.json` — full Oracle Forms extraction
- `graphify-out/deep/schema_deep.json` — full DDL extraction
- `graphify-out/deep/business_rules.json` — all 581 rules with IDs
- `graphify-out/deep/DEEP_REPORT.md` — full human-readable report

---

## Final Coverage Summary

| File Type | Files | Step | Status |
|---|---|---|---|
| DDL Tables (`.sql`) | 4 | Graphify + Deep Parser | 100% |
| Views (`.sql`) | 1 | Graphify + Deep Parser | 100% |
| Sequences (`.sql`) | 1 | Graphify | 100% |
| DB Triggers (`.sql`) | 2 | Deep Parser | 100% |
| PL/SQL Package Specs (`.pks`) | 11 | Oracle Parser + Deep Parser | 100% |
| PL/SQL Package Bodies (`.pkb`) | 11 | Oracle Parser + Deep Parser | 100% |
| Oracle Forms XML (`.xml`) | 6 | Oracle Parser + Deep Parser | 100% |
| Forms Libraries (`.sql`) | 2 | Graphify | 100% |
| Forms Menus (`.sql`) | 1 | Graphify | 100% |
| Seed Data (`.sql`) | 2 | Graphify | 100% |
| README (`.md`) | 1 | Graphify | 100% |
| **Total** | **42 files** | | **100%** |

---

## What This Enables

All output files in `graphify-out/` and `graphify-out/deep/` now contain the complete
structured intelligence of the Oracle HRMS system. This will be used to generate the
8 agent input files that feed into the main pipeline:

| Agent File | Source Data |
|---|---|
| `BA_Structural_Scout.md` | Business rules + package structure + form structure |
| `BA_Deep_Analyst.md` | Deep business rules (BR-0001 to BR-0581) + validation rules |
| `DA_Data_Extractor.md` | schema_deep.json — 30 tables, columns, PKs, FKs |
| `DA_Data_Reviewer.md` | Views, check constraints, FK relationships |
| `TA_Stack_Scout.md` | Package dependencies, sequences, trigger architecture |
| `TA_Deep_Analyst.md` | Error codes, known bugs, constants, technical constraints |
| `AA_App_Extractor.md` | forms_deep.json — 6 forms, blocks, items, LOVs |
| `AA_Quality_Review.md` | Known bugs, validation rules, error handling patterns |

Once these 8 files are generated, `python fresh_run_template.py` will produce all 25
enterprise forward-engineering documents from the Oracle HRMS source.

---

## Tools and Libraries Used

| Tool | Version | Purpose |
|---|---|---|
| `graphifyy` | 0.9.41 | Knowledge graph from SQL source files |
| `tree-sitter-sql` | 0.3.11 | SQL AST parser used by graphify |
| `tree-sitter` | 0.25.2 | Underlying AST parser engine |
| `sqlparse` | 0.5.5 | SQL parsing support |
| `antlr4-python3-runtime` | 4.13.2 | Grammar parser runtime |
| `xml.etree.ElementTree` | stdlib | Oracle Forms XML parsing |
| `re` (regex) | stdlib | PL/SQL pattern extraction |
| Python | 3.12 | Runtime |

---

## Files in This Folder

```
graphify + oracle parser/
  oracle_parser.py              — Step 2: Oracle PL/SQL + Forms parser
  oracle_deep_parser.py         — Step 3: Deep business logic extractor
  WHAT_WE_DID.md                — This document
  graphify-out/
    graph.json                  — Graphify knowledge graph
    graph.html                  — Interactive visual graph (open in browser)
    graph.manifest.json         — Files scanned by graphify
    GRAPH_REPORT.md             — Graphify summary report
    oracle_plsql_graph.json     — PL/SQL package graph nodes + edges
    oracle_forms_graph.json     — Oracle Forms graph nodes + edges
    oracle_combined_graph.json  — Everything merged into one graph
    ORACLE_PARSER_REPORT.md     — Oracle parser summary report
    deep/
      plsql_deep.json           — Full deep PL/SQL extraction
      forms_deep.json           — Full deep Oracle Forms extraction
      schema_deep.json          — Full DDL tables, views, triggers
      business_rules.json       — All 581 rules with IDs (BR-0001 to BR-0581)
      DEEP_REPORT.md            — Full human-readable deep report
```

---

*Generated: 2026-08-13 | Oracle HRMS Reverse Engineering Pipeline*
