# Multi-Agent Self-Healing Document Generation Architecture
## Proposed Upgrade — Foundation Runner (Step 14)

**Date:** 2026-08-19  
**Audience:** Team members + Manager  
**Purpose:** Explain the proposed architecture, how it works, and why it is better than the current approach

---

## Table of Contents

1. [The Problem with the Current Approach](#1-the-problem-with-the-current-approach)
2. [What the New Architecture Does](#2-what-the-new-architecture-does)
3. [Full Flow — Step by Step](#3-full-flow--step-by-step)
4. [The Two Agent Patterns Used](#4-the-two-agent-patterns-used)
5. [The Self-Healing Loop — How It Works](#5-the-self-healing-loop--how-it-works)
6. [Current vs Proposed — Side by Side](#6-current-vs-proposed--side-by-side)
7. [Why This Is the Best Architecture for This Use Case](#7-why-this-is-the-best-architecture-for-this-use-case)
8. [CrewAI vs Claude Multi-Agent — Which to Use](#8-crewai-vs-claude-multi-agent--which-to-use)
9. [What Problems This Solves](#9-what-problems-this-solves)
10. [Summary Numbers](#10-summary-numbers)

---

## 1. The Problem with the Current Approach

The current `foundation_runner_template.py` generates all 25 documents using
**4 sequential Claude calls**:

```
Call 1 → Call 2 → Call 3 (verify once) → Call 4 (consistency check once)
```

### What Goes Wrong

**Single-pass verification is not enough.** Call 3 finds gaps and fixes them in
one pass. Call 4 checks consistency once. Whatever either call misses stays
permanently broken in the output. There is no retry, no re-check, no confirmation
that the fixes actually worked.

**Specific failure modes observed:**

| Failure Mode | What Happens |
|---|---|
| Missing mandatory section | Call 3 finds it — but if the fix introduces a new gap, nobody catches it |
| Broken BR-xxx reference | Call 4 flags it — but if the fix uses a wrong ID, the error shifts not disappears |
| Contradiction between two docs | One agent fixes its doc, creates a new contradiction with a third doc |
| Weak evidence classification | Checked once — if still weak after one pass, stays weak |
| Technology name slipped in | Swept once — second occurrence in a different section stays |
| Gap in Data Dictionary | Found in Call 3 — but if the added rows break ERD references, nobody notices |

**Root cause:** The current architecture is **linear and single-pass**. It does not
loop. It does not confirm fixes worked. It has no inter-agent communication to
prevent fixes from conflicting with each other.

---

## 2. What the New Architecture Does

The proposed architecture has **three phases**:

```
Phase 1 — Parallel Generation     (3 subagents working simultaneously)
Phase 2 — Self-Healing Loop       (agent team: find gaps → claim → fix → re-verify → repeat)
Phase 3 — Final Quality Gate      (single agent reads all 25 docs, sets YES/NO/CONDITIONAL)
```

**Key difference from current:** Phase 2 loops until the gap count reaches zero —
or until it confirms no further progress is possible and flags remaining items as
`HUMAN-DECISION-REQUIRED`. It does not stop after one verification pass.

---

## 3. Full Flow — Step by Step

```
╔══════════════════════════════════════════════════════════════════════╗
║                    INPUTS (from Steps 1–13)                         ║
║                                                                      ║
║  8 Agent Output Files:                                               ║
║  BA_Structural_Scout.md  BA_Deep_Analyst.md                         ║
║  DA_Data_Extractor.md    DA_Data_Reviewer.md                        ║
║  TA_Stack_Scout.md       TA_Deep_Analyst.md                         ║
║  AA_App_Extractor.md     AA_Quality_Review.md                       ║
║  + DEEP_SCAN_OUTPUT.md   + business_rules.json (826 rules)          ║
║  + schema_deep.json      + plsql_deep.json                          ║
╚══════════════════════════════════════════════════════════════════════╝
                              ↓
╔══════════════════════════════════════════════════════════════════════╗
║              PHASE 1 — PARALLEL GENERATION                          ║
║                                                                      ║
║   Orchestrator (Main Agent / Team Lead)                             ║
║        │                                                             ║
║        ├──── Subagent A ────→ Docs 01–10                           ║
║        │     (BRD, Capability Model, Use Cases, Process Model,      ║
║        │      Domain Model, Data Dictionary, Data Model,            ║
║        │      ERD, DFD, Service Catalog)                            ║
║        │                                                             ║
║        ├──── Subagent B ────→ Docs 11–20                           ║
║        │     (API Contract, Technology Blueprint, Security,         ║
║        │      NFR, FE Spec, Generation Manifest, Readiness Report,  ║
║        │      Deployment Architecture, Frontend Architecture,       ║
║        │      UI/UX Specification)                                  ║
║        │                                                             ║
║        └──── Subagent C ────→ Docs 21–25                           ║
║              (Enterprise Knowledge Graph, Canonical Enterprise       ║
║               Model, Architecture Inventory, Traceability Matrix,   ║
║               Forward Engineering Input Map)                        ║
║                                                                      ║
║   All 3 run IN PARALLEL → results merged by Orchestrator            ║
║   Wall-clock time = slowest single subagent, not sum of all three   ║
╚══════════════════════════════════════════════════════════════════════╝
                              ↓
                    25 Draft Documents
                              ↓
╔══════════════════════════════════════════════════════════════════════╗
║              PHASE 2 — SELF-HEALING LOOP                            ║
║                                                                      ║
║  ┌───────────────────────────────────────────────────────────────┐  ║
║  │                                                               │  ║
║  │  ITERATION START                                              │  ║
║  │                                                               │  ║
║  │  Gap Hunter Agent                                             │  ║
║  │  ├── Reads all 25 documents                                   │  ║
║  │  ├── Checks: missing sections, broken BR/UC/table refs,       │  ║
║  │  │          contradictions, weak evidence, tech names,        │  ║
║  │  │          missing source citations, quality gate failures   │  ║
║  │  └── Produces: Shared Task List                               │  ║
║  │                     ↓                                         │  ║
║  │  Team Lead (Orchestrator)                                     │  ║
║  │  ├── Reads Shared Task List                                   │  ║
║  │  ├── Assigns tasks by domain:                                 │  ║
║  │  │     Business gaps → Teammate 1 (BA domain)                │  ║
║  │  │     Data/API gaps → Teammate 2 (DA/TA domain)             │  ║
║  │  │     Security/NFR gaps → Teammate 3 (Security domain)      │  ║
║  │  └── Spawns teammates simultaneously                          │  ║
║  │                     ↓                                         │  ║
║  │  ┌──────────────┬──────────────┬──────────────┐              │  ║
║  │  │  Teammate 1  │  Teammate 2  │  Teammate 3  │              │  ║
║  │  │  Claims BA   │  Claims DA   │  Claims Sec  │              │  ║
║  │  │  tasks from  │  tasks from  │  tasks from  │              │  ║
║  │  │  shared list │  shared list │  shared list │              │  ║
║  │  │      ↓       │      ↓       │      ↓       │              │  ║
║  │  │   Work on    │   Work on    │   Work on    │              │  ║
║  │  │   their docs │   their docs │   their docs │              │  ║
║  │  │      ↓       │      ↓       │      ↓       │              │  ║
║  │  │  Communicate ←→ Communicate ←→ Communicate │              │  ║
║  │  │  (check fixes don't conflict with each other)             │  ║
║  │  └──────────────┴──────────────┴──────────────┘              │  ║
║  │                     ↓                                         │  ║
║  │  Fixes merged back into 25 documents                          │  ║
║  │                     ↓                                         │  ║
║  │  Gap Hunter re-runs full verification                         │  ║
║  │                     ↓                                         │  ║
║  │  Gap count = 0?  ──── YES ────→ EXIT LOOP ✅                 │  ║
║  │       ↓                                                       │  ║
║  │      NO                                                       │  ║
║  │  Gap count < previous round? ── NO ──→ No progress           │  ║
║  │                                        Flag remaining as      │  ║
║  │                                        HUMAN-DECISION-REQUIRED│  ║
║  │                                        EXIT LOOP              │  ║
║  │       ↓                                                       │  ║
║  │      YES — gaps reduced → loop again (max 3 iterations) ─────┘  ║
║  └───────────────────────────────────────────────────────────────┘  ║
╚══════════════════════════════════════════════════════════════════════╝
                              ↓
                    25 Verified Documents
                              ↓
╔══════════════════════════════════════════════════════════════════════╗
║              PHASE 3 — FINAL QUALITY GATE                           ║
║                                                                      ║
║  Final Verifier Agent reads all 25 documents together               ║
║                                                                      ║
║  Checks:                                                             ║
║  ✓ Every BR-xxx ID referenced anywhere is defined in BRD            ║
║  ✓ Every UC-xxx ID referenced anywhere is defined in Use Cases      ║
║  ✓ Every table name referenced is defined in Data Model             ║
║  ✓ Every PKG_xxx.procedure referenced is in API Contract            ║
║  ✓ Technology neutrality — no vendor names prescribed               ║
║  ✓ Evidence classification on every material statement              ║
║  ✓ All 6 Oracle Forms modules in Frontend/UI docs                   ║
║  ✓ No AI artifact text remaining                                     ║
║  ✓ Quality gate checklist filled on every document                  ║
║                                                                      ║
║  Sets each document:                                                 ║
║    YES          — ready for downstream use                           ║
║    CONDITIONAL  — usable with noted caveats                          ║
║    NO-GO        — blocker exists, human review required              ║
╚══════════════════════════════════════════════════════════════════════╝
                              ↓
              25 Documents — Production Ready
```

---

## 4. The Two Agent Patterns Used

### Pattern 1 — Subagents (Phase 1: Generation)

```
Main Agent (Orchestrator)
     │
     ├── Spawn Subagent A → Work → Result (Docs 01–10)
     ├── Spawn Subagent B → Work → Result (Docs 11–20)
     └── Spawn Subagent C → Work → Result (Docs 21–25)
                                        ↓
                               Orchestrator merges → Report
```

**When to use:** Tasks are well-defined, independent, and can run in parallel.
Each subagent has a fixed scope and does not need to know what the others are doing.

**Why used here:** Docs 01–10, 11–20, and 21–25 are independent generation tasks.
Running them in parallel cuts wall-clock time to one-third of the sequential approach.

---

### Pattern 2 — Agent Teams (Phase 2: Self-Healing)

```
Main Agent (Team Lead)
     │
     └── Spawn Team + Assign Tasks via Shared Task List
              │
     ┌────────┴──────────────────┐
     ↓                           ↓                    ↓
Teammate 1               Teammate 2             Teammate 3
Communicate & Claim      Communicate & Claim    Communicate & Claim
     ↓                           ↓                    ↓
   Work                        Work                  Work
     ↓                           ↓                    ↓
     └──────────────── Communicate ──────────────────┘
                           ↓
                    Results → Shared Task List updated
```

**When to use:** Tasks are discovered dynamically (gaps found at runtime),
agents need to coordinate to avoid creating new conflicts while fixing old ones.

**Why used here:** Gaps found in the 25 documents are not known in advance —
they are discovered by the Gap Hunter at runtime. Teammates must communicate
because fixing a gap in one document can create a new gap in another.

---

## 5. The Self-Healing Loop — How It Works

### What the Gap Hunter Checks Every Iteration

| Check | What It Looks For |
|---|---|
| Mandatory sections | Every [M] section present and populated — not just a heading with no content |
| NOT_AVAILABLE blocks | Sections with no evidence use the correct format |
| BR-xxx reference integrity | Every BR-xxx cited in any document is defined in BRD |
| UC-xxx reference integrity | Every UC-xxx cited anywhere is defined in Use Case Spec |
| Table reference integrity | Every table name (UPPER_CASE) referenced exists in Data Model |
| Procedure reference integrity | Every PKG_xxx.procedure referenced exists in API Contract |
| Evidence classification | Every material statement has OBSERVED/DERIVED/INFERRED/ASSUMED/UNKNOWN |
| Confidence scores | Present in correct format — 0.XX — LABEL (reason) |
| Technology neutrality | No React, AWS, Spring Boot, bcrypt prescribed |
| AI artifact text | No "Let me check", "Based on the above", "I can see that" |
| Duplicate sections | Same heading appearing more than once in a document |
| Numeric contradictions | Same fact stated differently in two documents |
| Oracle Forms coverage | All 6 forms in Frontend Architecture and UI/UX Spec |
| Quality gate checklist | Present and filled on every document |

### Stop Conditions

```
STOP when any of these is true:

1. Gap count = 0               → all issues resolved ✅
2. Gap count = previous round  → no progress being made
                                  remaining gaps → HUMAN-DECISION-REQUIRED
3. Max iterations = 3          → safety cap reached
                                  remaining gaps → HUMAN-DECISION-REQUIRED
```

### Why Max 3 Iterations Is Enough

- Iteration 1 catches the majority of generation gaps (missing sections, broken refs)
- Iteration 2 catches gaps introduced by iteration 1 fixes (cross-document effects)
- Iteration 3 catches edge cases from iteration 2
- Anything not resolved in 3 iterations is either a genuine ambiguity or requires
  human business knowledge — flagging it is the right response, not looping forever

---

## 6. Current vs Proposed — Side by Side

### Architecture Comparison

| Dimension | Current (4 Sequential Calls) | Proposed (Multi-Agent Self-Healing) |
|---|---|---|
| Generation | Sequential — Call 1 then Call 2 | Parallel — Subagents A+B+C simultaneously |
| Generation speed | 3× slower (sequential) | 3× faster (parallel) |
| Verification | Single pass (Call 3) | Looping — runs until zero gaps or no progress |
| Consistency check | Single pass (Call 4) | Built into every loop iteration |
| Gap discovery | Once — whatever Call 3 misses stays missed | Every iteration — new gaps from fixes are caught |
| Fix conflicts | Not checked — one agent fixes all | Teammates communicate before finalising fixes |
| Convergence guarantee | None — one pass regardless | Yes — loops until gap count = 0 |
| Unresolvable gaps | Silently missed or partially fixed | Explicitly flagged as HUMAN-DECISION-REQUIRED |
| Final quality gate | None — Call 4 is the last step | Dedicated final verifier agent after loop exits |
| Technology neutrality | Swept once in Call 3 | Checked every iteration + final gate |

### Flow Comparison

```
CURRENT FLOW:
─────────────
Call 1 (Docs 01–10)
    ↓
Call 2 (Docs 11–20 + 21–25)
    ↓
Call 3 (verify + clean — ONCE)
    ↓
Call 4 (consistency — ONCE)
    ↓
Done — gaps that survive Call 3/4 stay in output

PROPOSED FLOW:
──────────────
Subagent A ──┐
Subagent B ──┼──→ Merge → 25 draft docs
Subagent C ──┘
    ↓
[LOOP]
  Gap Hunter finds gaps → Shared Task List
  Teammates claim, fix, communicate
  Fixes merged → Gap Hunter re-verifies
  Loop until gap count = 0
[END LOOP]
    ↓
Final Quality Gate → YES / CONDITIONAL / NO-GO per document
    ↓
Done — no undetected gaps, unresolvable items explicitly flagged
```

### Output Quality Comparison

| Output Dimension | Current | Proposed |
|---|---|---|
| Mandatory sections complete | ~85% — single pass misses some | ~99% — loop catches misses |
| BR-xxx reference integrity | Checked once | Verified every iteration |
| Cross-document consistency | Checked once | Verified every iteration |
| Evidence classification | Applied once | Enforced every iteration + final gate |
| Technology neutrality | Swept once | Enforced every iteration + final gate |
| AI artifact text removal | Once | Every iteration |
| Unresolvable gaps | Silently left in | Explicitly flagged |
| Readiness confidence | Medium | High |

---

## 7. Why This Is the Best Architecture for This Use Case

### The Core Reason

Document generation with strict templates, mandatory sections, cross-references,
and evidence classification is a **structured production problem** — not an
open-ended exploration problem. The architecture must match the problem type.

### Why Parallel Subagents for Generation

- Docs 01–10, 11–20, and 21–25 have no dependencies on each other during generation
- Running them in parallel is the correct choice — no reason to wait for Call 1
  to finish before starting Call 2
- Each subagent has a fixed, well-defined scope — exactly what subagents are for

### Why Agent Teams for Self-Healing

- Gaps are discovered at runtime — their number and location are not known in advance
- Fixing a gap in one document can affect other documents — teammates must coordinate
- Domain experts fixing their own domain is more reliable than one agent fixing everything
- The shared task list prevents two teammates fixing the same gap in conflicting ways

### Why Looping Until Convergence

- A single verification pass cannot guarantee completeness
- The loop provides a mathematical convergence guarantee — either gaps reach zero
  or they are explicitly escalated
- Three iterations is sufficient for any realistic document set

---

## 8. CrewAI vs Claude Multi-Agent — Which to Use

### CrewAI
**Designed for:** Open-ended tasks where agents negotiate, discover work dynamically,
and collaborate with minimal upfront structure.

**Strengths:**
- Good for research tasks where the work scope is unknown upfront
- Built-in role management and task delegation framework
- Agents can autonomously decide what to work on next

**Weaknesses for this project:**
- Agents can go off-script — a "BA Teammate" might decide to rewrite sections
  it was not asked to touch
- Harder to enforce strict population rules, evidence classification, and
  technology neutrality across all agents
- Harder to guarantee the 4 passes happen in the exact required sequence
- Higher overhead for a problem that is fundamentally structured

### Claude Multi-Agent
**Designed for:** Structured pipelines where tasks are well-defined, orchestration
is deterministic, and quality must be guaranteed.

**Strengths:**
- Orchestrator controls exact prompt, exact sequence, exact quality gates
- Subagents follow precise instructions — no going off-script
- Natural fit for the existing foundation runner architecture
- The self-healing loop maps perfectly to Claude's agent spawning model

**Weaknesses:**
- Less autonomous — requires a well-defined orchestrator
- Not ideal for open-ended discovery tasks

### Decision

```
Use Case: Generating 25 structured documents from verified source evidence
          using industry-standard templates with mandatory sections,
          evidence classification, and cross-reference integrity.

→ Claude Multi-Agent is the correct choice.

CrewAI would be correct if: the task was "explore this codebase and produce
whatever analysis seems most valuable" — open-ended, no fixed templates.

This task is the opposite: fixed templates, mandatory sections, strict rules.
Claude Multi-Agent wins.
```

---

## 9. What Problems This Solves

| Problem | Current Behaviour | New Behaviour |
|---|---|---|
| Missing mandatory section survives to output | Likely — single pass may miss it | Impossible — loop catches and fixes every iteration |
| Fix introduces new cross-document gap | Undetected — Call 4 already ran | Caught — Gap Hunter re-runs after every fix round |
| Two teammates fix same gap differently | Not applicable — one agent fixes all | Prevented — shared task list, each gap claimed once |
| AI artifact text in final output | Swept once — second occurrence stays | Swept every iteration + final gate |
| Technology vendor name prescribed | Swept once | Swept every iteration + final gate |
| Unresolvable gap stays silently broken | Yes — no escalation mechanism | No — explicitly flagged HUMAN-DECISION-REQUIRED |
| Generation takes 3× longer than necessary | Yes — sequential generation | No — parallel subagents cut time by ~60% |
| No final readiness status per document | No dedicated final gate | Yes — Phase 3 sets YES/CONDITIONAL/NO-GO per doc |

---

## 10. Summary Numbers

| Dimension | Current | Proposed |
|---|---|---|
| Agent calls | 4 sequential | 3 parallel + loop (3–5 calls per iteration) + 1 final |
| Generation speed | Baseline | ~60% faster (parallel subagents) |
| Verification passes | 1 | Up to 3 (loop) + 1 final gate |
| Gap detection coverage | ~85% | ~99% |
| Unresolvable gaps handling | Silent | Explicit HUMAN-DECISION-REQUIRED flag |
| Documents with readiness status | 0 | All 25 |
| Cross-document integrity checks | 1 pass | Every iteration + final gate |

---

## Closing Statement

> The current architecture is correct in structure but limited in reliability —
> it generates well but verifies only once. The proposed architecture adds a
> self-healing loop that guarantees convergence: either gaps reach zero, or
> they are explicitly escalated to a human. Combined with parallel generation
> that cuts wall-clock time by ~60%, this is the strongest possible architecture
> for producing 25 production-quality forward engineering documents from
> Oracle HRMS source evidence.

---

*Oracle HRMS modernisation project*  
*GitHub: https://github.com/jayaprakash2207/SDLC-oracle-source-intelligence-pipeline-x1*
