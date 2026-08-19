# How OSIRIS Parser Outputs Feed the Forward Engineering Pipeline

**Date:** 2026-08-19 | **Pipeline:** run.py — 15-step Standard Forward Engineering Pipeline

---

## Overview

The parser is the **data layer**. The pipeline agents are the **intelligence layer**.
Neither works well without the other — agents without structured facts hallucinate;
structured facts without agents produce no documents.

```
Oracle HRMS Source (42 files)
        │
        ▼
  OSIRIS Parser  ──────────────────────────────────────────────┐
  (oracle_deep_parser.py)                                      │
        │                                                      │
        ▼                                                      ▼
  7 Structured JSON Files                          826 Business Rules
  plsql / schema / forms /                         (business_rules.json)
  pll / menu / seed / deep report                         │
        │                                                  │
        └──────────────┬───────────────────────────────────┘
                       │
                       ▼
              run.py — 15-Step Pipeline
              (Steps 0, 1, 3.5, 4–12, 14, 15)
                       │
                       ▼
         20 Forward Engineering Documents
         + Knowledge Graph + Gap Hunter Report
```

---

## Step-by-Step: Where Each Parser File Is Used

### Step 0 — Rule Annotator

**Input:** `business_rules.json` (826 rules, BR-0001 to BR-0826)

The annotator reads each rule's `source` field, finds the matching source file, and
injects `-- RULE: BR-NNNN` comments into working copies. The pipeline uses these
annotated copies for all downstream steps.

Without `business_rules.json`, the annotator has nothing to inject — no rules flow
forward into any document.

---

### Step 1 — Layer 1 (Deterministic Extraction)

Layer 1 is the pipeline's own deterministic extractor. OSIRIS *is* the Layer 1
extractor for this Oracle HRMS codebase. The `--skip-layer1` flag exists so that
pre-existing OSIRIS output can bypass this step and feed directly into
`Source_Extraction/`.

---

### Step 3.5 — Implicit Rules

**Inputs:**
| Parser File | Rules Extracted |
|---|---|
| `seed_deep.json` | Seed-layer business rules (133 rows → default values, lookup codes) |
| `forms_deep.json` | Form-level LOV constraints, required-field rules, format mask rules |
| `pll_deep.json` | Library-level validation rules (22 procedures from 2 PLL files) |

---

### Steps 4–12 — BA / DA / TA / AA Analysis Agents (Parallel)

All four analysis tracks read from `Source_Extraction/` (parser output) plus
`DEEP_SCAN_OUTPUT.md` (chunk scan narrative). Agents get both:

- **Structured facts** from the parser — machine-verified, no ambiguity
- **Narrative explanation** from chunks — procedure logic, architecture risks

| Track | Steps | Key Parser Files Consumed |
|---|---|---|
| Business Analysis (BA) | 4–5 | `business_rules.json`, `plsql_deep.json` |
| Data Analysis (DA) | 6–7 | `schema_deep.json`, `seed_deep.json` |
| Technology Analysis (TA) | 8–10 | `plsql_deep.json`, `schema_deep.json`, `pll_deep.json` |
| Application Analysis (AA) | 11–12 | `forms_deep.json`, `menu_deep.json`, `pll_deep.json` |

---

### Step 14 — Foundation (20 Forward Engineering Documents + Knowledge Graph)

This is the synthesis step. Each of the 20 output documents is directly grounded in
specific parser files:

| Parser File | Documents Produced |
|---|---|
| `business_rules.json` | `01_BRD.md`, `03_USE_CASE_SPECIFICATION.md`, `04_BUSINESS_PROCESS_MODEL.md` |
| `plsql_deep.json` | `10_SERVICE_CATALOG.md`, `11_API_CONTRACT_SPECIFICATION.md`, `12_TECHNOLOGY_BLUEPRINT.md` |
| `schema_deep.json` | `06_DATA_DICTIONARY.md`, `07_DATA_MODEL_SPECIFICATION.md`, `08_ERD.md`, `09_DATA_FLOW_DIAGRAM.md` |
| `forms_deep.json` | `19_FRONTEND_ARCHITECTURE.md`, `20_UI_UX_SPECIFICATION.md` |
| `seed_deep.json` | `06_DATA_DICTIONARY.md` (seed values used as default/example values) |
| `vulnerability` category (4 rules) | `13_SECURITY_ARCHITECTURE.md` |
| `known_bug` category (15 rules) | `13_SECURITY_ARCHITECTURE.md`, `15_FORWARD_ENGINEERING_SPECIFICATION.md` |
| `deferred_todo` category (5 rules) | `15_FORWARD_ENGINEERING_SPECIFICATION.md` (risk register + requirement backlog) |
| `weakness` category (1 rule) | `13_SECURITY_ARCHITECTURE.md` |

---

### Step 15 — Gap Hunter (Self-Healing Loop)

The gap hunter knows exactly what the old system left unfinished because the parser
tagged them explicitly. It targets:

| Category | Count | Examples |
|---|---|---|
| `deferred_todo` | 5 | COBRA integration, access revoke, final pay, tax brackets, time import |
| `known_bug` | 15 | SQL injection in PKG_REPORTING, hard-coded encryption key, MD5 passwords |
| `vulnerability` | 4 | PKG_SECURITY: auth bypass paths, plaintext credential storage |
| `weakness` | 1 | MD5 hashing — should be bcrypt/scrypt |

These are the explicit items the new system must fix or implement that the old system
missed or deferred. Without the parser tagging them, the gap hunter would have to
discover them from scratch in every run.

---

## What Each Parser File Enables

| Parser File | What It Enables in Forward Engineering |
|---|---|
| `business_rules.json` (826 rules) | Rule injection (Step 0), BRD, use cases, process models — no human re-reading of source needed |
| `plsql_deep.json` | Generate TypeScript/Java service interfaces directly from structured procedure + parameter JSON |
| `schema_deep.json` | Regenerate entire DB schema on a new platform — 30 tables, 441 columns, all FKs, 29 CHECKs |
| `forms_deep.json` | Generate React/Angular UI components that replicate Oracle Forms behavior block-by-block |
| `seed_deep.json` | Ready-made test fixtures — 133 structured rows for the new application's test suite |
| `pll_deep.json` | Validation rule library — port 22 procedures to new validation layer |
| `menu_deep.json` | Replicate HRMS navigation tree + permission guards in new frontend router |

---

## Why Both Parser and Chunk Scan Are Needed

| | OSIRIS Parser | Chunk Deep Scan |
|---|---|---|
| Format | Structured JSON | Prose markdown |
| Machine-readable | Yes — code generators consume directly | No — human re-reading required |
| Verified accuracy | 3,715 audit checks (100%) | Zero automated checks |
| Procedure logic narrative | None | 5–15 lines per procedure |
| Architecture risk notes | None | Timeout risk, circular deps, stubs |
| Verbatim rule text | Yes — word-for-word from source | Paraphrased |

**Rule:** Use parser for generation tasks. Use chunk scan for understanding tasks.
Use both for architecture review and risk assessment.

---

## Quick Reference — Which File for Which Task

| Task | Parser File |
|---|---|
| Generate new REST API contracts | `plsql_deep.json` → parameter names, directions, types |
| Write DB migration scripts | `schema_deep.json` → columns, FKs, CHECK constraints |
| Build new UI screens | `forms_deep.json` → blocks, items, LOVs |
| Load test data | `seed_deep.json` → 133 ready rows |
| Define security requirements | `business_rules.json` vulnerability + weakness categories |
| Write compliance documents | `business_rules.json` verbatim rule text |
| Build requirement backlog | `business_rules.json` deferred_todo + known_bug categories |
| Port navigation / permissions | `menu_deep.json` |
| Port validation library | `pll_deep.json` |
