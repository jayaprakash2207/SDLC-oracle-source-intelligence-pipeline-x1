# Graph Report - oracle-hrms-src  (2026-08-13)

## Corpus Check
- 14 files · ~11,698 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 74 nodes · 71 edges · 15 communities
- Extraction: 100% EXTRACTED · 0% INFERRED · 0% AMBIGUOUS
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- Oracle Forms Legacy HR System
- HRMS.VW_ACTIVE_EMPLOYEES
- 02_payroll_tables.sql
- 01_core_tables.sql
- 04_performance_tables.sql
- 03_leave_tables.sql
- HRMS.VW_PAYROLL_LATEST

## God Nodes (most connected - your core abstractions)
1. `HRMS.VW_ACTIVE_EMPLOYEES` - 7 edges
2. `HRMS.VW_EMPLOYEE_COMPENSATION` - 6 edges
3. `HRMS.VW_PENDING_APPROVALS` - 6 edges
4. `Oracle Forms Legacy HR System` - 6 edges
5. `HRMS.VW_LEAVE_SUMMARY` - 5 edges
6. `HRMS.VW_PAYROLL_LATEST` - 5 edges
7. `Key Technical Characteristics` - 5 edges
8. `HRMS.VW_ORG_HIERARCHY` - 2 edges
9. `HRMS.DEPARTMENTS` - 1 edges
10. `HRMS.LOCATIONS` - 1 edges

## Surprising Connections (you probably didn't know these)
- `HRMS.VW_PAYROLL_LATEST` --reads_from--> `EMPLOYEES`  [EXTRACTED]
  schema/views/hrms_views.sql →   _Bridges community 1 → community 6_

## Import Cycles
- None detected.

## Communities (15 total, 0 thin omitted)

### Community 0 - "Oracle Forms Legacy HR System"
Cohesion: 0.18
Nodes (10): Application Overview, Architecture, Database Patterns, Directory Structure, Key Technical Characteristics, Known Technical Debt, License, Oracle Forms Legacy HR System (+2 more)

### Community 1 - "HRMS.VW_ACTIVE_EMPLOYEES"
Cohesion: 0.19
Nodes (16): DEPARTMENTS, EMPLOYEES, JOB_GRADES, JOB_TITLES, LEAVE_BALANCES, LEAVE_REQUESTS, LEAVE_TYPES, LOCATIONS (+8 more)

### Community 2 - "02_payroll_tables.sql"
Cohesion: 0.20
Nodes (9): HRMS.EMPLOYEE_BANK_ACCOUNTS, HRMS.EMPLOYEE_PAY_ELEMENTS, HRMS.EMPLOYEE_TAX_INFO, HRMS.PAY_ELEMENTS, HRMS.PAY_PERIODS, HRMS.PAYROLL_DETAILS, HRMS.PAYROLL_RUNS, HRMS.SALARY_RECORDS (+1 more)

### Community 3 - "01_core_tables.sql"
Cohesion: 0.22
Nodes (8): HRMS.DEPARTMENTS, HRMS.EMERGENCY_CONTACTS, HRMS.EMPLOYEE_DEPENDENTS, HRMS.EMPLOYEE_HISTORY, HRMS.EMPLOYEES, HRMS.JOB_GRADES, HRMS.JOB_TITLES, HRMS.LOCATIONS

### Community 4 - "04_performance_tables.sql"
Cohesion: 0.22
Nodes (8): HRMS.AUDIT_LOG, HRMS.LOOKUP_VALUES, HRMS.NOTIFICATION_QUEUE, HRMS.PERFORMANCE_GOALS, HRMS.PERFORMANCE_REVIEWS, HRMS.REVIEW_CYCLES, HRMS.SYSTEM_PARAMETERS, HRMS.USER_SESSIONS

### Community 5 - "03_leave_tables.sql"
Cohesion: 0.33
Nodes (5): HRMS.HOLIDAYS, HRMS.LEAVE_ACCRUAL_LOG, HRMS.LEAVE_BALANCES, HRMS.LEAVE_REQUESTS, HRMS.LEAVE_TYPES

### Community 6 - "HRMS.VW_PAYROLL_LATEST"
Cohesion: 0.50
Nodes (4): PAY_PERIODS, PAYROLL_DETAILS, PAYROLL_RUNS, HRMS.VW_PAYROLL_LATEST

## Knowledge Gaps
- **38 isolated node(s):** `HRMS.DEPARTMENTS`, `HRMS.LOCATIONS`, `HRMS.JOB_GRADES`, `HRMS.JOB_TITLES`, `HRMS.EMPLOYEES` (+33 more)
  These have ≤1 connection - possible missing edges or undocumented components.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `HRMS.VW_PAYROLL_LATEST` connect `HRMS.VW_PAYROLL_LATEST` to `HRMS.VW_ACTIVE_EMPLOYEES`?**
  _High betweenness centrality (0.021) - this node is a cross-community bridge._
- **What connects `HRMS.DEPARTMENTS`, `HRMS.LOCATIONS`, `HRMS.JOB_GRADES` to the rest of the system?**
  _38 weakly-connected nodes found - possible documentation gaps or missing edges._