# What's Still Missing to Reach 100% — Complete Document Inventory
## Oracle HRMS Reverse Engineering → Forward Engineering Project

**Date:** 2026-08-19  
**Audience:** Team members + Manager  
**Purpose:** Gap analysis — what we have, what we need, and why each piece matters

---

## Current Status

```
20 documents produced by the Forward Engineering Pipeline  →  Design Layer  ~70%
10 documents still missing                                 →  Gaps          ~30%
─────────────────────────────────────────────────────────────────────────────────
30 documents total                                         →  100% complete
```

The 20 existing documents cover the **design layer** well — requirements, data model,
API contracts, UI spec, security, and deployment architecture are all covered.

What is missing is everything else — **analysis closure, testing, execution, and
operations.** This is where most migrations fail. Design is the easy part. Getting
from old system to new system without breaking production payroll is the hard part.

---

## What We Already Have (20 Documents)

| # | Document | Layer | What It Covers |
|---|----------|-------|----------------|
| 01 | BRD | Business | Business requirements document |
| 02 | BRD Supplement | Business | Extended requirements |
| 03 | Use Case Specification | Business | All use cases with actors and flows |
| 04 | Business Process Model | Business | End-to-end process flows |
| 05 | Domain Model | Business | Business entities and relationships |
| 06 | Data Dictionary | Data | Every table, column, type, default, constraint |
| 07 | Data Model Specification | Data | Normalisation, relationships, design decisions |
| 08 | ERD | Data | Entity relationship diagram |
| 09 | Data Flow Diagram | Data | How data moves through the system |
| 10 | Service Catalog | Technology | Every package as a service domain |
| 11 | API Contract Specification | Technology | Every procedure as an endpoint |
| 12 | Technology Blueprint | Technology | Stack, architecture, dependencies |
| 13 | Security Architecture | Technology | Auth, session, vulnerabilities, fixes required |
| 14 | NFR Specification | Technology | Performance, scalability, availability requirements |
| 15 | Forward Engineering Specification | Technology | Risk register, requirement backlog |
| 16 | Generation Manifest | Technology | What was generated and how |
| 17 | FE Readiness Report | Technology | Readiness assessment |
| 18 | Deployment Architecture | Technology | Infrastructure and deployment design |
| 19 | Frontend Architecture | Application | UI component architecture |
| 20 | UI/UX Specification | Application | Every screen, field, form, navigation |

---

## What Is Still Missing (10 Documents)

---

### GAP 1 — Traceability Matrix
**Layer:** Analysis Closure  
**Priority:** High

#### How It Helps
Links every business rule → use case → test case → implementation component in one
place. Without this, you cannot prove the new system covers everything the old system
did. Auditors and project sponsors ask for this. It is also the safety net that
prevents requirements from being dropped silently during development.

#### What It Contains
- Every business rule (BR-0001 to BR-0826) mapped to the use case it satisfies
- Every use case mapped to the test case that verifies it
- Every test case mapped to the component that implements it
- Coverage percentage — what % of rules have a test, what % have an implementation
- Gap column — rules with no test case or no implementation flagged in red
- Change impact analysis — if rule BR-0045 changes, which test cases and components are affected
- Sign-off column — who confirmed each mapping is correct

#### Why It Is Generic
Every software project that must prove completeness needs a traceability matrix.
It is a standard deliverable in any regulated or enterprise environment.

---

### GAP 2 — Glossary / Business Terminology
**Layer:** Analysis Closure  
**Priority:** Medium

#### How It Helps
HRMS has domain-specific terminology that means different things to different people.
"Pay Period", "Pay Element", "Leave Balance", "Review Cycle", "Compa-Ratio" — these
words appear in hundreds of business rules and documents. New developers joining the
project, QA testers writing test cases, and business stakeholders reviewing documents
all need a single agreed definition for every term. Without this, the same word gets
interpreted differently by different people and causes bugs.

#### What It Contains
- Every domain term with a precise business definition (not technical)
- Where the term appears in the source system (which package, which table, which form)
- Synonyms and aliases — e.g. "Employee Number" = "EMP_NUMBER" = "Staff ID"
- Terms that look similar but mean different things — e.g. "Pay Run" vs "Pay Period"
- Acronyms expanded — e.g. COBRA, HRMS, LOV, PKG
- Terms specific to this organisation vs industry-standard terms
- Deprecated terms from the old system that should not be used in the new one

#### Why It Is Generic
Every enterprise system with business domain complexity needs a glossary. It is
the reference document that prevents miscommunication across business, development,
and QA teams throughout the project lifecycle.

---

### GAP 3 — Integration Specification
**Layer:** Design  
**Priority:** High

#### How It Helps
PKG_INTEGRATION exists in the old system with 5 incomplete integrations (COBRA,
time import, and others). The 20 existing documents describe the internal system
but do not cover how the new system communicates with external systems. Every
enterprise HRMS connects to payroll processors, benefits providers, time tracking
systems, and directory services. Without an integration spec, developers make
assumptions about message formats, retry logic, and error handling — and those
assumptions are almost always wrong.

#### What It Contains
- List of all external systems the HRMS connects to or should connect to
- For each integration:
  - Direction — inbound, outbound, or bidirectional
  - Trigger — scheduled batch, real-time event, or manual
  - Data exchanged — exact fields, formats, and validation rules
  - Protocol — file transfer, REST API, message queue, database link
  - Error handling — what happens when the external system is unavailable
  - Retry logic — how many times, how long to wait, when to give up
  - Timeout behaviour — how long to wait for a response
  - Monitoring — how to know if an integration is broken
- The 5 deferred TODOs from PKG_INTEGRATION fully specified as integration designs
- Sequence diagrams for each integration flow

#### Why It Is Generic
Every enterprise system has external integrations. This document is standard in
any system design for any industry.

---

### GAP 4 — Test Strategy and Test Plan
**Layer:** Testing  
**Priority:** High

#### How It Helps
Without a test strategy, QA is ad hoc — different testers test different things
differently, test environments are not defined, and nobody knows when the system
is ready to ship. A test strategy defines the overall approach; a test plan defines
the specifics for this project.

#### What It Contains

**Test Strategy section:**
- Types of testing required — unit, integration, system, regression, performance, security, UAT
- Who is responsible for each type — developers, QA team, business users
- Test environment requirements — how many environments, what data each has
- Entry criteria — what must be true before testing starts each phase
- Exit criteria — what must be true before testing is declared complete
- Defect severity definitions — what is Critical vs High vs Medium vs Low
- Defect management process — how bugs are logged, prioritised, and resolved
- Regression strategy — which tests run on every code change

**Test Plan section:**
- Test scope — what is in scope and explicitly what is out of scope
- Test schedule — which tests run in which sprint or phase
- Resource plan — who does what testing and when
- Risk log — what could go wrong with testing and mitigation
- Payroll-specific test requirements — end-of-month runs, leap years, mid-month changes
- Leave management test requirements — overlapping requests, carryover, type restrictions
- Security test requirements — the 4 vulnerabilities must each have a test proving they are fixed
- Performance test requirements — response time SLAs from NFR Specification

#### Why It Is Generic
Every software project needs a test strategy and test plan. This is not optional
for any system handling payroll or personal employee data.

---

### GAP 5 — Golden Test Suite / Behavioural Equivalence Specification
**Layer:** Testing  
**Priority:** Critical

#### How It Helps
This is the most important missing document for a payroll system. The new system
must produce **identical outputs** to the old system for the same inputs. If payroll
calculations differ by even one cent, it is a legal and compliance problem. Golden
tests are the only way to prove behavioural equivalence between old and new systems.

#### What It Contains
- Methodology — how golden test data was extracted from the old system
- Input/output pairs for every critical calculation:
  - Payroll: gross pay → deductions → net pay for each pay element type
  - Leave: accrual calculation, carryover limits, balance deduction on approval
  - Performance: review score calculation, rating boundaries
  - Security: session timeout logic, account lockout after N failures
- Edge case test cases (these are the ones that catch migration bugs):
  - Final pay on last day of month
  - Salary change mid pay period
  - Leap year leave accrual
  - Employee with multiple active leave requests
  - Payroll reversal and re-run
  - Employee with zero salary (intern/contractor)
- Acceptance threshold — e.g. payroll must match to 2 decimal places, 100% of cases
- Regression pack — the 20 known bugs each have a test proving they are fixed
- How to run the golden test suite — tool, command, expected output
- Sign-off process — who reviews and approves golden test results before go-live

#### Why It Is Generic
Any migration from one system to another that handles financial calculations or
legally binding data requires a behavioural equivalence test suite. This is
non-negotiable for payroll systems in any industry.

---

### GAP 6 — Data Migration Plan
**Layer:** Execution  
**Priority:** Critical

#### How It Helps
Data migration is the highest-risk activity in any system migration. If it goes
wrong, you lose live employee data, corrupt payroll history, or invalidate audit
trails. The 20 existing documents describe what the new schema looks like but say
nothing about how data physically moves from the old system to the new one.

#### What It Contains
- Source to target table and column mapping — every column mapped explicitly
- Data type transformation rules — e.g. Oracle VARCHAR2 → target VARCHAR, Oracle DATE → target TIMESTAMP
- Business transformation rules — e.g. status codes that changed meaning, format changes
- NULL handling — where Oracle has NULL but the new system requires a default value
- Sequence reset logic — all sequences must start from current MAX + 1 in Oracle, not from 1
- Data cleansing rules — fix known dirty data before migration, not after
- Migration sequence — which tables must be migrated before others (reference data first, then transactional)
- Row count validation — before and after counts for every table, must match
- Data integrity validation — FK relationships intact after migration
- Business rule validation — calculated fields re-verified after migration
- Estimated data volume — how many rows in each table, how long migration will take
- Migration window — how many hours of downtime required
- Rollback procedure — if migration fails at any step, exact steps to return to the old system
- Post-migration smoke test — the first checks to run on day 1 to confirm success

#### Why It Is Generic
Every system migration needs a data migration plan. This is universally required
regardless of technology stack or industry.

---

### GAP 7 — Cutover / Transition Plan
**Layer:** Execution  
**Priority:** Critical

#### How It Helps
Without a cutover plan, go-live is chaos. People do not know who does what, in
what order, at what time, and what the abort condition is. Every failed migration
in history either had no cutover plan or did not follow it. This is especially
critical for payroll — a botched cutover during a pay period means employees do
not get paid on time.

#### What It Contains
- Go / No-Go checklist — every item that must be confirmed true before go-live starts
  - All golden tests passing
  - Data migration validated
  - Rollback procedure tested in staging
  - Business stakeholder sign-off received
  - Support team briefed and on standby
- Parallel run period definition:
  - How long both old and new systems run simultaneously
  - Who compares outputs between systems
  - What discrepancy threshold triggers a stop
- Cutover sequence — step by step, with owner name and time estimate per step:
  - Freeze old system (read-only)
  - Final data migration run
  - Validation checks
  - DNS / URL switch
  - Smoke tests on new system
  - Communication to users
- Rollback trigger conditions — specific measurable conditions that mean abort and go back
- Feature flag / phased rollout strategy — option to go live department by department
- Communication plan:
  - What employees are told and when
  - What HR and payroll teams are told
  - What management is told
  - Who sends each communication
- Post-cutover validation — first payroll run on new system, who approves it, sign-off criteria
- Hypercare period — first 2–4 weeks post go-live, who is on standby, escalation path

#### Why It Is Generic
Every go-live needs a cutover plan. Standard deliverable for any enterprise project.

---

### GAP 8 — Operational Runbook
**Layer:** Operations  
**Priority:** High

#### How It Helps
The developers who built the system will not always be available. When payroll
fails at 11pm on month-end, the on-call engineer needs exact step-by-step
instructions — not tribal knowledge held by one person. A runbook is the
operations manual for the live system.

#### What It Contains
- Scheduled job calendar — what runs when, expected duration, success criteria
  - Monthly payroll run procedure
  - Leave carryover expiry job (end of year)
  - Performance review cycle open/close
  - Audit log archival job
- Runbook procedures — for each scheduled job:
  - Pre-run checks
  - Step by step execution
  - What success looks like
  - What failure looks like and first response steps
- Common failure scenarios with exact fix steps:
  - Payroll run fails mid-process — how to check state and restart safely
  - Employee account locked — how to unlock without bypassing audit log
  - Sequence mismatch after database restore — how to reset
  - Integration FTP connection fails — how to retry and verify
  - Performance review stuck in pending — how to investigate
- Monitoring baselines — what is normal response time, CPU, DB connections
- Alert definitions — what triggers a page, who gets paged, severity
- Escalation path — Level 1 support → Level 2 → development team → vendor
- Backup and restore procedure — schedule, location, how to verify, restore steps
- Contact list — all relevant people with phone and email

#### Why It Is Generic
Every production system needs a runbook. Operations cannot rely on having the
original developers available 24/7.

---

### GAP 9 — Compliance and Audit Trail Specification
**Layer:** Compliance  
**Priority:** High

#### How It Helps
HRMS handles payroll (financial data) and employee personal information. This makes
it subject to data protection law, labour law, and financial audit requirements in
virtually every country. Without a compliance specification, developers build the
system without knowing what must be logged, how long data must be retained, and
who is allowed to see what. This creates legal exposure.

#### What It Contains
- Personal data inventory — which tables and columns contain personal data
- Data retention schedule — how long each category of data must be kept
- Right to erasure handling — which data can be deleted on request, which cannot
  (payroll records often have mandatory minimum retention periods)
- Audit trail requirements — every event that must be recorded:
  - Salary changes — who changed it, what it was before, what it is now, when
  - Employee personal data changes — same pattern
  - Login and logout — timestamp, IP address, success or failure
  - Payroll run approval — who approved, when
  - Leave approval — who approved, when
  - Access to sensitive records — who viewed whose payroll data
- Password policy requirements — especially given the MD5 weakness found in PKG_SECURITY
- Session policy — max session duration, inactivity timeout, concurrent session rules
- Data access controls — who can see salary data, who can see personal data
- Regulatory reporting — what reports must be producible on demand for auditors
- Data residency — where employee data is permitted to be stored geographically
- Breach notification procedure — what to do if data is exposed

#### Why It Is Generic
Any system handling employee personal data and payroll is subject to regulatory
requirements. This document is required regardless of the technology stack or
the country of operation.

---

### GAP 10 — Architecture Decision Records (ADRs)
**Layer:** Governance  
**Priority:** Medium

#### How It Helps
Six months after go-live, a new developer joins and asks "why did we build it this
way?" Without ADRs, nobody knows — the original team has moved on, the decisions
are forgotten, and the same debates get rehashed every time someone new joins.
ADRs capture institutional knowledge permanently.

#### What It Contains
One ADR per major architectural decision. Each ADR has the same structure:
- **Title** — the decision in one line
- **Status** — Proposed / Accepted / Superseded
- **Context** — what situation forced this decision, what constraints existed
- **Options considered** — what alternatives were evaluated
- **Decision** — what was chosen
- **Reasoning** — why this option over the others
- **Consequences** — what this makes easier, what it makes harder, what debt it creates

**Likely ADRs for this project:**
1. How to resolve the PKG_EMPLOYEE ↔ PKG_PAYROLL circular dependency
2. Authentication approach — given PKG_SECURITY vulnerabilities found, what replaces it
3. How Oracle Forms blocks and items map to the new UI component model
4. How Oracle sequences are replaced in the new database platform
5. How RAISE_APPLICATION_ERROR codes map to the new error handling pattern
6. Whether PKG_COMMON (36 shared utilities) becomes a shared library or is split
7. How the Oracle Forms LOV pattern is implemented in the new UI
8. Strategy for the 5 deferred TODOs — implement in phase 1 or phase 2
9. Audit trail implementation — database triggers vs application layer logging
10. How the 826 business rules are enforced — database constraints vs application logic

#### Why It Is Generic
Every software project with architectural decisions needs ADRs. They are the
institutional memory of the project and prevent the same decisions being
relitigated every time team membership changes.

---

## Complete Document Inventory — All 30

### Design Layer (existing 20)

| # | Document | Status |
|---|----------|--------|
| 01 | BRD | ✅ Done |
| 02 | BRD Supplement | ✅ Done |
| 03 | Use Case Specification | ✅ Done |
| 04 | Business Process Model | ✅ Done |
| 05 | Domain Model | ✅ Done |
| 06 | Data Dictionary | ✅ Done |
| 07 | Data Model Specification | ✅ Done |
| 08 | ERD | ✅ Done |
| 09 | Data Flow Diagram | ✅ Done |
| 10 | Service Catalog | ✅ Done |
| 11 | API Contract Specification | ✅ Done |
| 12 | Technology Blueprint | ✅ Done |
| 13 | Security Architecture | ✅ Done |
| 14 | NFR Specification | ✅ Done |
| 15 | Forward Engineering Specification | ✅ Done |
| 16 | Generation Manifest | ✅ Done |
| 17 | FE Readiness Report | ✅ Done |
| 18 | Deployment Architecture | ✅ Done |
| 19 | Frontend Architecture | ✅ Done |
| 20 | UI/UX Specification | ✅ Done |

### Missing 10 Documents

| # | Document | Layer | Priority | Status |
|---|----------|-------|----------|--------|
| 21 | Traceability Matrix | Analysis Closure | High | ❌ Missing |
| 22 | Glossary / Business Terminology | Analysis Closure | Medium | ❌ Missing |
| 23 | Integration Specification | Design | High | ❌ Missing |
| 24 | Test Strategy and Test Plan | Testing | High | ❌ Missing |
| 25 | Golden Test Suite Specification | Testing | Critical | ❌ Missing |
| 26 | Data Migration Plan | Execution | Critical | ❌ Missing |
| 27 | Cutover / Transition Plan | Execution | Critical | ❌ Missing |
| 28 | Operational Runbook | Operations | High | ❌ Missing |
| 29 | Compliance and Audit Trail Specification | Compliance | High | ❌ Missing |
| 30 | Architecture Decision Records | Governance | Medium | ❌ Missing |

---

## Priority Order to Complete

```
Phase 1 — Do These First (Blockers)
  26  Data Migration Plan           ← highest risk activity in the whole project
  27  Cutover / Transition Plan     ← go-live cannot happen without this
  25  Golden Test Suite Spec        ← payroll correctness proof

Phase 2 — Do Before Development Starts
  21  Traceability Matrix           ← proves requirements coverage
  24  Test Strategy and Test Plan   ← QA needs this before writing a single test
  23  Integration Specification     ← developers need this before building integrations
  29  Compliance Spec               ← legal requirements must be known before building

Phase 3 — Do During Development
  30  Architecture Decision Records ← capture decisions as they are made, not after
  28  Operational Runbook           ← write as the system is built

Phase 4 — Finalise Before Go-Live
  22  Glossary                      ← useful throughout, finalise before UAT
```

---

## Summary

The 20 existing documents tell you **what to build.**
The 10 missing documents tell you **how to get there without breaking production.**

Design is 70% of the paper but 30% of the risk.
Execution, testing, and operations are 30% of the paper but 70% of the risk.

---

*Oracle HRMS modernisation project*  
*GitHub: https://github.com/jayaprakash2207/SDLC-oracle-source-intelligence-pipeline-x1*
