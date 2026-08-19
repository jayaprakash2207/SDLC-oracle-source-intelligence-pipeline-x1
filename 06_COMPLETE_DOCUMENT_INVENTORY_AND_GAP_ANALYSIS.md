# Complete Document Inventory — What's Needed to Reach 100%
## Oracle HRMS Reverse Engineering → Forward Engineering Project

**Date:** 2026-08-19  
**Audience:** Team members + Manager  
**Purpose:** Full gap analysis across all 15 layers — what we have, what we need, and why

---

## Summary

```
Layer 1   Design (pipeline output)    20 docs  ✅ Done
Layer 2   Analysis Closure             2 docs  ❌ Missing
Layer 3   As-Is / Gap Analysis         2 docs  ❌ Missing
Layer 4   Design Gap                   1 doc   ❌ Missing
Layer 5   Project Management           4 docs  ❌ Missing
Layer 6   Testing                      2 docs  ❌ Missing
Layer 7   Data Governance              2 docs  ❌ Missing
Layer 8   Execution                    2 docs  ❌ Missing
Layer 9   Security Execution           1 doc   ❌ Missing
Layer 10  Training                     3 docs  ❌ Missing
Layer 11  Operations                   2 docs  ❌ Missing
Layer 12  Compliance                   1 doc   ❌ Missing
Layer 13  Decommission                 1 doc   ❌ Missing
Layer 14  Governance                   1 doc   ❌ Missing
Layer 15  Post-Migration               2 docs  ❌ Missing
──────────────────────────────────────────────────────────
TOTAL                                 46 docs  = true 100%
```

The 20 existing documents cover the **design layer** — requirements, data model,
API contracts, UI spec, security, and deployment. That is approximately **45% of
what a true production migration actually needs.**

The remaining 26 documents cover project management, testing, execution, operations,
training, compliance, governance, and decommission — the layers where most
migrations fail.

---

## Layer 1 — Design (20 Documents) ✅ Already Done

| # | Document | What It Covers |
|---|----------|----------------|
| 01 | BRD | Business requirements document |
| 02 | BRD Supplement | Extended requirements |
| 03 | Use Case Specification | All use cases with actors and flows |
| 04 | Business Process Model | End-to-end process flows |
| 05 | Domain Model | Business entities and relationships |
| 06 | Data Dictionary | Every table, column, type, default, constraint |
| 07 | Data Model Specification | Normalisation, relationships, design decisions |
| 08 | ERD | Entity relationship diagram |
| 09 | Data Flow Diagram | How data moves through the system |
| 10 | Service Catalog | Every package as a service domain |
| 11 | API Contract Specification | Every procedure as an endpoint with typed parameters |
| 12 | Technology Blueprint | Stack, architecture, dependencies |
| 13 | Security Architecture | Auth, session, vulnerabilities, fixes required |
| 14 | NFR Specification | Performance, scalability, availability requirements |
| 15 | Forward Engineering Specification | Risk register, requirement backlog |
| 16 | Generation Manifest | What was generated and how |
| 17 | FE Readiness Report | Readiness assessment |
| 18 | Deployment Architecture | Infrastructure and deployment design |
| 19 | Frontend Architecture | UI component architecture |
| 20 | UI/UX Specification | Every screen, field, form, navigation |

---

## Layer 2 — Analysis Closure (2 Documents) ❌ Missing

---

### Doc 21 — Traceability Matrix
**Priority:** High

#### How It Helps
Links every business rule → use case → test case → implementation component in one
place. Without this, you cannot prove the new system covers everything the old system
did. Auditors and project sponsors ask for this on day one. It is also the safety
net that prevents requirements from being silently dropped during development.

#### What It Contains
- Every business rule (BR-0001 to BR-0826) mapped to the use case it satisfies
- Every use case mapped to the test case that verifies it
- Every test case mapped to the component that implements it
- Coverage percentage — what % of rules have a test, what % have an implementation
- Gap column — rules with no test case or no implementation flagged explicitly
- Change impact analysis — if rule BR-0045 changes, which tests and components are affected
- Sign-off column — who confirmed each mapping is correct

#### Why It Is Generic
Every software project that must prove completeness needs a traceability matrix.
Standard deliverable in BABOK, IEEE 830, and any regulated environment.

---

### Doc 22 — Glossary / Business Terminology
**Priority:** Medium

#### How It Helps
HRMS has domain-specific terminology. "Pay Period", "Pay Element", "Leave Balance",
"Review Cycle", "Compa-Ratio" — these words appear in hundreds of business rules.
New developers, QA testers, and business stakeholders all need one agreed definition
per term. Without this, the same word gets interpreted differently by different people
and produces bugs.

#### What It Contains
- Every domain term with a precise business definition (not technical language)
- Where the term appears in source system — package, table, form
- Synonyms and aliases — e.g. "Employee Number" = "EMP_NUMBER" = "Staff ID"
- Terms that look similar but mean different things — e.g. "Pay Run" vs "Pay Period"
- Acronyms expanded — COBRA, HRMS, LOV, NFR, PKG, etc.
- Terms specific to this organisation vs industry-standard terms
- Deprecated terms from the old system that must not be used in the new one

---

## Layer 3 — As-Is / Gap Analysis (2 Documents) ❌ Missing

---

### Doc 23 — As-Is Process Documentation
**Priority:** High

#### How It Helps
The parser extracted machine-readable facts. But business stakeholders — HR managers,
payroll officers, finance directors — need to see what the current Oracle system does
in plain business language, not JSON. This document is their sign-off artifact. It
also becomes the baseline against which the new system is measured.

#### What It Contains
- Current business processes described in plain language — no technical jargon
- Who does what, when, using which part of the Oracle system
- Process flows for every major domain: hiring, payroll, leave, performance, reporting
- Current pain points, manual workarounds, and known limitations
- Screenshot inventory of current Oracle Forms screens
- Current integration points with external systems
- Stakeholder review and sign-off section

---

### Doc 24 — As-Is to To-Be Gap Analysis
**Priority:** High

#### How It Helps
Business stakeholders need to know explicitly what is changing, what is staying the
same, and what is being dropped. Without this, stakeholders discover missing features
during UAT and raise expensive late-stage change requests. This document prevents
surprises.

#### What It Contains
- Side-by-side comparison: current Oracle capability vs new system capability
- What is changing — with reason why
- What is staying the same — confirmed carried forward
- What is being dropped — with business justification and stakeholder sign-off
- What is being added that did not exist in Oracle (the 5 deferred TODOs)
- What is being fixed — the 20 known bugs and 4 vulnerabilities
- New capabilities introduced by the modern platform
- Impact assessment — which user groups are affected by each change

---

## Layer 4 — Design Gap (1 Document) ❌ Missing

---

### Doc 25 — Integration Specification
**Priority:** High

#### How It Helps
PKG_INTEGRATION exists with 5 incomplete integrations. The existing 20 documents
describe internal system design but nothing about how the new system communicates
with external systems. Without this, developers make assumptions about message
formats, retry logic, and error handling — and those assumptions are almost always
wrong. Every enterprise HRMS connects to external systems.

#### What It Contains
- List of all external systems the HRMS connects to or should connect to
- For each integration:
  - Direction — inbound, outbound, or bidirectional
  - Trigger — scheduled batch, real-time event, or manual
  - Data exchanged — exact fields, formats, and validation rules
  - Protocol — file transfer, API, message queue, database link
  - Error handling — what happens when the external system is unavailable
  - Retry logic — how many attempts, intervals, when to give up
  - Timeout behaviour — maximum wait time for a response
  - Monitoring — how to detect a broken integration
- Full specification for the 5 deferred TODOs from PKG_INTEGRATION:
  COBRA, access revoke on termination, final pay, tax brackets, time import
- Sequence diagrams for each integration flow

---

## Layer 5 — Project Management (4 Documents) ❌ Missing

---

### Doc 26 — Project Charter / Business Case
**Priority:** High

#### How It Helps
Without a project charter, there is no formal agreement on why the project exists,
what success looks like, who has authority to make decisions, and what the approved
budget is. This is the first document any sponsor or auditor asks for.

#### What It Contains
- Project purpose and objectives — why this migration is being done
- Business case — cost of staying on Oracle vs cost of migration
- Success criteria — measurable outcomes that define "done"
- Scope statement — what is in scope and explicitly what is not
- Approved budget and funding source
- Project sponsor name and authority level
- Project manager name and authority level
- Key stakeholders and their roles
- High-level timeline and major milestones
- Key constraints and assumptions
- Approval signatures

---

### Doc 27 — Risk Register
**Priority:** High

#### How It Helps
A risk register is a live document tracking everything that could go wrong, who owns
it, and what the mitigation plan is. Without it, risks are discovered too late to
mitigate. PMBOK and PRINCE2 both mandate this as a core project document.

#### What It Contains
- Risk ID, description, category (technical, business, resource, external)
- Probability rating (1–5) and impact rating (1–5)
- Risk score = probability × impact
- Risk owner — who is responsible for monitoring and mitigating
- Mitigation plan — what actions reduce the probability
- Contingency plan — what to do if the risk becomes an issue
- Current status — open, mitigated, closed, occurred

**Known risks already identified for this project:**
- 4 critical security vulnerabilities must be fixed before go-live
- Circular dependency between PKG_EMPLOYEE and PKG_PAYROLL
- 5 deferred TODOs are incomplete features — implementation scope unclear
- Oracle Forms to modern UI migration is complex — LOV behaviour must be replicated exactly
- Payroll calculation equivalence — new system must match Oracle to the cent
- Data quality in Oracle is unknown until assessed

---

### Doc 28 — Stakeholder Register and Communication Plan
**Priority:** Medium

#### How It Helps
Different stakeholders need different information at different times. Employees need
to know when the new system goes live. HR managers need to know what changes.
The finance director needs assurance that payroll will not be disrupted. Without a
communication plan, people find out the wrong things at the wrong time.

#### What It Contains

**Stakeholder Register:**
- Name, role, department
- Interest in the project — what they care about
- Influence level — high / medium / low
- Current attitude — supporter / neutral / resistant
- Engagement strategy — how to keep them informed and on-side

**Communication Plan:**
- What information is communicated, to whom, how often, by which channel
- Go-live communication timeline — what employees are told and when
- Escalation communications — who is notified if a milestone is missed
- Status report schedule — how frequently management is updated

---

### Doc 29 — Change Management Plan
**Priority:** Medium

#### How It Helps
Scope creep is the most common reason projects fail. Without a formal change
management process, every stakeholder adds requirements informally, the scope grows
uncontrolled, the timeline slips, and the budget is blown.

#### What It Contains
- How change requests are submitted — form, process, channel
- Change assessment process — who evaluates impact on scope, timeline, budget
- Approval authority — who can approve changes at each cost/impact threshold
- Change log — record of every change requested, assessed, approved or rejected
- Impact analysis template — how to assess schedule and budget impact of a change
- How approved changes flow into the requirements documents and traceability matrix

---

## Layer 6 — Testing (2 Documents) ❌ Missing

---

### Doc 30 — Test Strategy and Test Plan
**Priority:** High

#### How It Helps
Without a test strategy, QA is ad hoc. Different testers test different things
with no coordination. Test environments are undefined. Nobody knows when the system
is ready to ship. IEEE 829 defines the test plan as a mandatory artifact for any
enterprise software project.

#### What It Contains

**Test Strategy section:**
- Types of testing required: unit, integration, system, regression, performance,
  security, UAT, accessibility
- Who is responsible for each type — developers, QA, business users
- Test environment definitions — how many environments, what data each holds
- Entry and exit criteria for each phase
- Defect severity definitions — Critical / High / Medium / Low with examples
- Defect management process — how bugs are logged, triaged, resolved
- Regression strategy — which tests run on every code change

**Test Plan section:**
- Test scope — what is in scope vs explicitly out of scope
- Test schedule — which tests run in which sprint or phase
- Resource plan — who does what testing and when
- Risk log — what could go wrong with the testing effort
- Payroll-specific test requirements — month-end runs, leap years, mid-month changes
- Leave management tests — overlapping requests, carryover, type restrictions
- Security tests — the 4 vulnerabilities each have a test proving they are fixed
- Performance tests — response time requirements from the NFR Specification

---

### Doc 31 — Golden Test Suite / Behavioural Equivalence Specification
**Priority:** Critical

#### How It Helps
The new system must produce **identical outputs** to the Oracle system for the same
inputs. For payroll, a one-cent difference is a compliance problem. Golden tests are
the only way to prove behavioural equivalence. This document cannot be skipped for
any financial system.

#### What It Contains
- Methodology — how golden test data was extracted from Oracle
- Input/output pairs for every critical calculation:
  - Payroll: gross pay → deductions → net pay for every pay element type
  - Leave: accrual, carryover limit, balance deduction on approval
  - Performance: score calculation, rating boundaries
  - Security: session timeout, account lockout after N failures
- Edge cases that catch migration bugs:
  - Final pay on last day of month
  - Salary change mid pay period
  - Leap year leave accrual
  - Employee with multiple simultaneous leave requests
  - Payroll reversal and re-run
  - Employee transferred between departments mid-period
- Acceptance threshold — e.g. payroll must match to 2 decimal places, 100% of cases
- Bug regression tests — all 20 known bugs have a test proving they are fixed in new system
- How to run the suite — tool, command, expected output format
- Sign-off process — who reviews and approves results before go-live

---

## Layer 7 — Data Governance (2 Documents) ❌ Missing

---

### Doc 32 — Data Quality Assessment Report
**Priority:** High

#### How It Helps
Before any data migration, you must know what state the Oracle data is in. Duplicate
employee records, orphaned payroll entries, NULL values in required fields, invalid
foreign key references, and date format inconsistencies — all of these exist in every
legacy system that has been running for years. Migrating dirty data means the new
system inherits all the old problems plus new ones caused by the migration itself.

#### What It Contains
- Row counts per table — baseline before migration
- Duplicate analysis — duplicate employee numbers, duplicate payroll records
- Orphaned record analysis — FK references that point to deleted parent rows
- NULL analysis — columns with unexpected NULLs that violate business rules
- Referential integrity check — all FK relationships verified
- Date range validation — dates that are impossible or outside expected range
- Code value validation — status codes, type codes that are not in the reference tables
- Data cleansing rules — for each quality issue found, the rule that fixes it
- Cleansing ownership — who is responsible for fixing each category
- Re-assessment plan — after cleansing, re-run all checks to confirm clean

---

### Doc 33 — Data Lineage Document
**Priority:** Medium

#### How It Helps
Regulators and auditors ask: "where does this payroll figure come from?" Without
data lineage, the answer is "we are not sure." Data lineage maps every data element
from its origin through every transformation to its final destination. Required
for GDPR compliance, financial audit, and any data governance framework.

#### What It Contains
- Source of every critical data element — where it is first entered or generated
- Every transformation applied to the data as it flows through the system
- Every system or process that reads the data
- Every system or process that modifies the data
- Final resting place — which table, which report, which external system
- Lineage diagrams for payroll calculation chain, leave balance chain, employee record
- Retention mapping — how long each element is kept at each stage
- Access lineage — who can read or modify each element at each stage

---

## Layer 8 — Execution (2 Documents) ❌ Missing

---

### Doc 34 — Data Migration Plan
**Priority:** Critical

#### How It Helps
Data migration is the highest-risk activity in the entire migration. If it goes
wrong you lose live employee data, corrupt payroll history, or break audit trails.
The existing 20 documents describe what the new schema looks like but say nothing
about how data physically moves from Oracle to the new system.

#### What It Contains
- Source → target table and column mapping — every column explicitly mapped
- Data type transformation rules — Oracle to target platform type conversions
- Business transformation rules — status codes that changed, format changes
- NULL handling — where Oracle has NULL but new system requires a default value
- Sequence reset logic — all sequences start from current Oracle MAX + 1
- Data cleansing rules — applied during migration, based on quality assessment
- Migration sequence — reference tables first, then transactional (with dependency order)
- Row count validation — before and after for every table, must match
- Referential integrity validation — all FK relationships intact after migration
- Business rule validation — calculated fields re-verified post-migration
- Estimated data volume and migration window duration
- Rollback procedure — if migration fails at any step, exact steps to return to Oracle
- Post-migration smoke test — first checks to run on day 1 to confirm success

---

### Doc 35 — Cutover / Transition Plan
**Priority:** Critical

#### How It Helps
Without a cutover plan, go-live is chaotic. Nobody knows who does what, in what
order, at what time, and what the abort trigger is. A botched cutover during payroll
week means employees are not paid on time — a legal and HR crisis. Every migration
that has failed has either had no cutover plan or failed to follow it.

#### What It Contains
- Go / No-Go checklist — every item that must be confirmed true before go-live
  - All golden tests passing
  - Data migration validated
  - Rollback procedure tested in staging environment
  - Business stakeholder sign-off received
  - Support team briefed and on standby
- Parallel run period — how long both systems run, who validates, discrepancy threshold
- Cutover sequence — step by step with owner and time estimate per step:
  - Freeze Oracle (read-only)
  - Final data migration run
  - Validation checks
  - System switch
  - Smoke tests
  - User communication
- Rollback trigger — specific measurable conditions that mean abort and return to Oracle
- Phased rollout option — go live department by department as risk mitigation
- Communication plan — who is told what, when, by whom
- Post-cutover validation — first payroll run on new system, who approves, sign-off criteria
- Hypercare period — first 4 weeks post go-live, who is on standby, escalation path

---

## Layer 9 — Security Execution (1 Document) ❌ Missing

---

### Doc 36 — Vulnerability Remediation Plan
**Priority:** Critical

#### How It Helps
The Security Architecture document (Doc 13) lists the 4 critical vulnerabilities
and 1 weakness found in the Oracle source code. But it does not say who fixes each
one, how, by when, or how it is verified. Without a remediation plan, vulnerabilities
get acknowledged but never actually fixed. This has happened on every major breach.

#### What It Contains
For each of the 4 vulnerabilities and 1 weakness:
- Exact description of the vulnerability from the parser output
- Root cause — why the vulnerability exists in the old system
- Fix approach — the specific code or configuration change required
- Owner — who is responsible for implementing the fix
- Target completion date — before go-live is non-negotiable for Critical severity
- Verification method — how to prove the fix works (test case, code review, pen test)
- Status tracking — not started / in progress / fixed / verified

**The 5 items that must be in this plan:**
1. Hard-coded AES-256-CBC encryption key in PKG_SECURITY — replace with key management service
2. FTP credentials in cleartext in SYSTEM_PARAMETERS — replace with secrets management
3. Authentication bypass paths in PKG_SECURITY — fix all code paths to verify password
4. SQL injection in PKG_REPORTING — replace dynamic SQL concatenation with bind variables
5. MD5 password hashing in PKG_SECURITY — replace with bcrypt or scrypt

---

## Layer 10 — Training (3 Documents) ❌ Missing

---

### Doc 37 — Training Plan
**Priority:** High

#### How It Helps
New system adoption fails when users are not trained. HR staff, payroll officers,
and managers who cannot use the new system revert to manual workarounds — Excel
spreadsheets, email approvals, phone calls. This is how shadow systems are born
alongside the new system, defeating the entire purpose of the migration.

#### What It Contains
- Training needs analysis — which user groups need what level of training
- Training types — classroom, e-learning, one-on-one, hands-on practice
- Training schedule — who gets trained and when (before go-live)
- Training environment — separate instance with realistic test data
- Trainer identification — who delivers each training session
- Training materials to be produced — see Docs 38 and 39
- Assessment method — how to confirm users are competent before go-live
- Post-go-live support plan — help desk, floor walkers for first 2 weeks

---

### Doc 38 — End User Manual
**Priority:** High

#### How It Helps
When a payroll officer has a question about how to process a payroll reversal in
the new system, they need a manual — not a developer. This is the day-to-day
reference guide for all non-technical users of the system.

#### What It Contains
- Getting started — login, navigation, screen layout
- Step-by-step instructions for every major task:
  - How to create a new employee
  - How to process a monthly payroll run
  - How to approve or reject a leave request
  - How to submit a performance review
  - How to run a payroll report
  - How to change an employee's salary
- Screenshots for every step
- What to do when something goes wrong — common error messages and solutions
- Glossary of terms used in the system (links to Doc 22)
- FAQ — most common questions from UAT and training

---

### Doc 39 — System Administrator Guide
**Priority:** Medium

#### How It Helps
When the IT team needs to add a new user, reset a password, configure a new
department, or update a system parameter, they need an admin guide — not the
development team. This document makes the system operable without developer
involvement for routine tasks.

#### What It Contains
- System architecture overview — how the components fit together
- User management — how to create, modify, and deactivate user accounts
- Role and permission management — how to assign and revoke access
- System parameter configuration — which settings control which behaviour
- Reference data management — how to add new departments, job titles, leave types
- Scheduled job management — how to view, pause, and reschedule background jobs
- Log file locations and how to interpret them
- Database connection configuration
- Integration configuration — how to update FTP settings, API keys
- Backup configuration and verification
- How to apply system updates and patches

---

## Layer 11 — Operations (2 Documents) ❌ Missing

---

### Doc 40 — Operational Runbook
**Priority:** High

#### How It Helps
The developers who built the system will not always be available at 11pm on
month-end when payroll fails. The on-call engineer needs exact step-by-step
instructions — not tribal knowledge held by one person who may have left the company.

#### What It Contains
- Scheduled job calendar — what runs when, expected duration, success criteria
- Runbook procedures for each job:
  - Pre-run checks
  - Step-by-step execution
  - What success looks like
  - What failure looks like and immediate response
- Common failure scenarios with exact fix steps:
  - Payroll run fails mid-process — check state and restart safely
  - Employee account locked — unlock without bypassing audit log
  - Sequence mismatch after restore — reset procedure
  - Integration connection fails — retry and verify
  - Performance review stuck in pending — investigation steps
- Monitoring baselines — normal CPU, memory, DB connections, response time
- Alert definitions — what triggers a notification, who is notified, severity levels
- Escalation path — Level 1 → Level 2 → development team → vendor
- Backup and restore procedure — schedule, verification, full restore steps
- Emergency contacts — all relevant people with phone and email

---

### Doc 41 — Disaster Recovery / Business Continuity Plan
**Priority:** High

#### How It Helps
If the new system goes down during a payroll run, employees are not paid on time.
That is a legal liability in every jurisdiction. A DR plan defines exactly how the
system recovers, how quickly, and what happens to business operations during
the outage. Every enterprise system handling payroll must have this.

#### What It Contains
- Recovery Time Objective (RTO) — how quickly must the system be restored
- Recovery Point Objective (RPO) — how much data loss is acceptable
- Failure scenarios covered — database failure, application failure, infrastructure failure, data centre loss
- Recovery procedure for each scenario — step by step
- Failover procedure — how traffic switches to backup system
- Data backup strategy — frequency, location, retention, encryption
- Backup restoration testing schedule — how often DR is tested and by whom
- Business continuity during outage — manual fallback for payroll if system is down for >X hours
- Communication procedure during incident — who is notified, what they are told, when
- Post-incident review procedure — root cause analysis, prevention measures

---

## Layer 12 — Compliance (1 Document) ❌ Missing

---

### Doc 42 — Compliance and Audit Trail Specification
**Priority:** High

#### How It Helps
HRMS handles payroll (financial data) and employee personal information. In
virtually every country this is subject to data protection law, labour law,
and financial audit requirements. Without this specification, developers build
the system without knowing what must be logged, how long it must be kept, and
who is allowed to see it. This creates direct legal exposure for the organisation.

#### What It Contains
- Personal data inventory — every table and column containing personal data
- Data retention schedule — how long each data category must be kept by law
- Right to erasure handling — what can be deleted on request, what cannot
  (payroll records often have 7-year mandatory retention)
- Mandatory audit trail events — every event that must be permanently recorded:
  - Salary changes — who changed it, old value, new value, timestamp
  - Employee data changes — who, what, when
  - Login and logout — timestamp, IP address, success or failure
  - Payroll approval — who approved, when
  - Leave approval — who approved, when
  - Access to sensitive records — who viewed whose payroll data
- Password policy requirements — minimum length, complexity, expiry, history
- Session policy — maximum duration, inactivity timeout, concurrent session limit
- Data access controls — who can see salary data, who can see personal records
- Regulatory reporting — reports producible on demand for auditors
- Data residency — permitted geographies for employee data storage
- Breach notification procedure — what to do if data is exposed, timelines

---

## Layer 13 — Decommission (1 Document) ❌ Missing

---

### Doc 43 — Oracle Decommission Plan
**Priority:** Medium

#### How It Helps
Without a decommission plan, the old Oracle system runs indefinitely after go-live.
Costs double — both systems have infrastructure, licences, and support. Users get
confused about which system is authoritative. Data drift occurs between the two
systems. In practice, legacy systems without decommission plans have been found
still running 10 years after their replacement went live.

#### What It Contains
- Decommission trigger — the conditions that must be met before Oracle can be switched off
  (new system stable for N months, all golden tests passing in production, no active bugs)
- Data archival plan — historical Oracle data that cannot migrate but must be kept for compliance
- Archive access method — how archived Oracle data can be queried if needed
- Licence return procedure — Oracle licence termination process and timeline
- Infrastructure decommission — servers, storage, network to be decommissioned
- Oracle Forms client uninstall — procedure for removing Oracle client from user machines
- Decommission verification — checklist confirming nothing still depends on Oracle
- Final sign-off — who has authority to confirm Oracle is fully decommissioned
- Timeline — target decommission date (typically 3–6 months after go-live)

---

## Layer 14 — Governance (1 Document) ❌ Missing

---

### Doc 44 — Architecture Decision Records (ADRs)
**Priority:** Medium

#### How It Helps
Six months after go-live, a new developer joins and asks "why did we build it this
way?" Without ADRs, nobody knows. The original team has moved on, the decisions are
forgotten, and the same debates are rehashed every time someone new joins. ADRs
capture institutional knowledge permanently. They prevent the architecture being
dismantled by people who don't understand why it was built that way.

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
1. How to resolve PKG_EMPLOYEE ↔ PKG_PAYROLL circular dependency
2. Authentication approach — replacing PKG_SECURITY given the 4 critical vulnerabilities
3. How Oracle Forms blocks and items map to the new UI component model
4. How Oracle sequences are replaced in the new database
5. How RAISE_APPLICATION_ERROR codes map to the new error handling pattern
6. Whether PKG_COMMON (36 shared utilities) becomes a shared library or is split by domain
7. How Oracle Forms LOV pattern is implemented in the new UI
8. Strategy for the 5 deferred TODOs — phase 1 or phase 2 delivery
9. Audit trail implementation — database triggers vs application-layer logging
10. How the 826 business rules are enforced — DB constraints vs application logic

---

## Layer 15 — Post-Migration (2 Documents) ❌ Missing

---

### Doc 45 — Post-Implementation Review
**Priority:** Medium

#### How It Helps
Without a formal post-implementation review, nobody knows if the migration actually
succeeded against its original objectives. It also forces an honest assessment of
what went over budget, what took longer than planned, and whether the business
goals were achieved. PMBOK, PRINCE2, and TOGAF all mandate this as a project
closure deliverable.

#### What It Contains
- Review of original objectives — each one assessed: achieved / partially achieved / not achieved
- Budget vs actual — planned cost vs actual cost with variance explanation
- Timeline vs actual — planned dates vs actual dates with variance explanation
- Quality assessment — defect count by severity, golden test results in production
- Stakeholder satisfaction — feedback from HR, payroll, IT, management
- Outstanding issues — items not resolved at go-live, owner, resolution date
- Benefits realisation — measurable improvements over the old Oracle system
- What went well — practices to repeat on future projects
- What went badly — problems encountered and root causes
- Formal project closure — sponsor sign-off that the project is complete

---

### Doc 46 — Lessons Learned
**Priority:** Medium

#### How It Helps
Every migration hits unexpected problems. Without a lessons learned document,
the next project in the organisation repeats all the same mistakes. This is one
of the lowest-effort, highest-value documents in the entire project — it takes
one session with the team to produce and pays dividends on every future project.

#### What It Contains
- What went well — practices, tools, decisions that should be repeated
- What went badly — problems, delays, errors that should be avoided
- What was surprising — things nobody anticipated that significantly affected the project
- Root cause analysis for each major issue
- Specific recommendations for future migrations:
  - What to do earlier
  - What not to do
  - What to estimate differently
  - What tools worked and which did not
- Parser-specific learnings — what OSIRIS found that manual analysis would have missed
- Pipeline-specific learnings — which steps took longer than expected and why
- Stakeholder management learnings — what communication worked and what did not

---

## Complete Inventory — All 46 Documents

| # | Document | Layer | Priority | Status |
|---|----------|-------|----------|--------|
| 01 | BRD | Design | — | ✅ Done |
| 02 | BRD Supplement | Design | — | ✅ Done |
| 03 | Use Case Specification | Design | — | ✅ Done |
| 04 | Business Process Model | Design | — | ✅ Done |
| 05 | Domain Model | Design | — | ✅ Done |
| 06 | Data Dictionary | Design | — | ✅ Done |
| 07 | Data Model Specification | Design | — | ✅ Done |
| 08 | ERD | Design | — | ✅ Done |
| 09 | Data Flow Diagram | Design | — | ✅ Done |
| 10 | Service Catalog | Design | — | ✅ Done |
| 11 | API Contract Specification | Design | — | ✅ Done |
| 12 | Technology Blueprint | Design | — | ✅ Done |
| 13 | Security Architecture | Design | — | ✅ Done |
| 14 | NFR Specification | Design | — | ✅ Done |
| 15 | Forward Engineering Specification | Design | — | ✅ Done |
| 16 | Generation Manifest | Design | — | ✅ Done |
| 17 | FE Readiness Report | Design | — | ✅ Done |
| 18 | Deployment Architecture | Design | — | ✅ Done |
| 19 | Frontend Architecture | Design | — | ✅ Done |
| 20 | UI/UX Specification | Design | — | ✅ Done |
| 21 | Traceability Matrix | Analysis Closure | High | ❌ Missing |
| 22 | Glossary / Business Terminology | Analysis Closure | Medium | ❌ Missing |
| 23 | As-Is Process Documentation | As-Is / Gap | High | ❌ Missing |
| 24 | As-Is to To-Be Gap Analysis | As-Is / Gap | High | ❌ Missing |
| 25 | Integration Specification | Design Gap | High | ❌ Missing |
| 26 | Project Charter / Business Case | Project Mgmt | High | ❌ Missing |
| 27 | Risk Register | Project Mgmt | High | ❌ Missing |
| 28 | Stakeholder Register + Comms Plan | Project Mgmt | Medium | ❌ Missing |
| 29 | Change Management Plan | Project Mgmt | Medium | ❌ Missing |
| 30 | Test Strategy and Test Plan | Testing | High | ❌ Missing |
| 31 | Golden Test Suite Specification | Testing | Critical | ❌ Missing |
| 32 | Data Quality Assessment Report | Data Governance | High | ❌ Missing |
| 33 | Data Lineage Document | Data Governance | Medium | ❌ Missing |
| 34 | Data Migration Plan | Execution | Critical | ❌ Missing |
| 35 | Cutover / Transition Plan | Execution | Critical | ❌ Missing |
| 36 | Vulnerability Remediation Plan | Security Execution | Critical | ❌ Missing |
| 37 | Training Plan | Training | High | ❌ Missing |
| 38 | End User Manual | Training | High | ❌ Missing |
| 39 | System Administrator Guide | Training | Medium | ❌ Missing |
| 40 | Operational Runbook | Operations | High | ❌ Missing |
| 41 | DR / BCP Plan | Operations | High | ❌ Missing |
| 42 | Compliance and Audit Trail Spec | Compliance | High | ❌ Missing |
| 43 | Oracle Decommission Plan | Decommission | Medium | ❌ Missing |
| 44 | Architecture Decision Records | Governance | Medium | ❌ Missing |
| 45 | Post-Implementation Review | Post-Migration | Medium | ❌ Missing |
| 46 | Lessons Learned | Post-Migration | Medium | ❌ Missing |

---

## Priority Order to Complete

```
PHASE 1 — Before Development Starts (Blockers)
  26  Project Charter            ← formal project authority and budget
  27  Risk Register              ← know the risks before building anything
  23  As-Is Process Docs         ← business stakeholder baseline sign-off
  24  As-Is to To-Be Gap         ← no surprises in UAT
  21  Traceability Matrix        ← requirements coverage from day 1
  32  Data Quality Assessment    ← know the data state before migration design

PHASE 2 — During Design and Build
  25  Integration Specification  ← developers need this before building integrations
  29  Change Management Plan     ← control scope creep from the start
  28  Stakeholder Comms Plan     ← keep stakeholders informed throughout
  36  Vulnerability Remediation  ← fix the 4 critical bugs with clear ownership
  33  Data Lineage Document      ← define lineage while building, not after
  44  ADRs                       ← capture decisions as they are made

PHASE 3 — Before Testing Starts
  30  Test Strategy and Plan     ← QA needs this before writing a single test
  31  Golden Test Suite Spec     ← define expected outputs before testing begins
  22  Glossary                   ← finalise before UAT to prevent term confusion

PHASE 4 — Before Go-Live
  34  Data Migration Plan        ← highest risk activity
  35  Cutover Plan               ← go-live cannot happen without this
  42  Compliance Spec            ← legal requirements locked before launch
  37  Training Plan              ← users trained before go-live
  38  End User Manual            ← in users' hands before go-live
  39  System Admin Guide         ← IT team ready before go-live
  40  Operational Runbook        ← on-call team ready before go-live
  41  DR / BCP Plan              ← tested in staging before go-live
  43  Decommission Plan          ← agreed before go-live, executed after

PHASE 5 — After Go-Live
  45  Post-Implementation Review ← 1–3 months after go-live
  46  Lessons Learned            ← captured while memory is fresh
```

---

## The Layers Most Teams Skip (and Regret Most)

| Skipped Layer | What Goes Wrong |
|---|---|
| Training | Users reject the new system. Payroll team reverts to manual workarounds. |
| Decommission Plan | Oracle kept running for years. Double costs. Users confused about which is authoritative. |
| Data Quality Assessment | Dirty Oracle data migrates unchanged. New system inherits all old problems plus new ones. |
| DR / BCP Plan | First payroll outage — no recovery procedure. Employees not paid. Legal liability. |
| As-Is Gap Analysis | Business stakeholders find missing features in UAT. Expensive late change requests. |
| Vulnerability Remediation Plan | Vulnerabilities documented but never assigned or fixed. New system launches with the same security holes. |
| Lessons Learned | Next project repeats all the same mistakes. |

---

## Closing Point

> The 20 existing documents tell you **what to build.**  
> The 26 missing documents tell you **how to get there, how to prove it works,  
> how to train people to use it, how to keep it running, and how to shut down  
> the old system cleanly.**  
>
> Design is the easy part. Execution, testing, operations, and decommission  
> are where migrations succeed or fail.

---

*Oracle HRMS modernisation project*  
*GitHub: https://github.com/jayaprakash2207/SDLC-oracle-source-intelligence-pipeline-x1*
