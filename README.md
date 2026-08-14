# Oracle Source Intelligence Pipeline

A 3-layer extraction pipeline for legacy Oracle HRMS systems.  
Combines Graphify knowledge graphs, custom PL/SQL package parsing, and deep Oracle Forms XML extraction  
to produce structured business rules, schema definitions, and dependency graphs from raw Oracle source code.

---

## What This Does

Takes 42 Oracle source files (PL/SQL packages, DDL tables, Oracle Forms XML, triggers)  
and extracts **581 business rules, 30 tables, 11 packages, 6 forms** into structured JSON + Markdown —  
ready to feed into an AI forward-engineering pipeline.

---

## Folder Structure

```
oracle-source-intelligence-pipeline/
  source/                        — 42 Oracle HRMS source files (input)
    schema/tables/               — DDL: 30 tables
    schema/views/                — 6 views
    schema/sequences/            — sequences
    plsql/packages/              — 11 PL/SQL packages (.pks + .pkb)
    plsql/triggers/              — 5 database triggers
    forms/xml-exports/           — 6 Oracle Forms XML exports
    forms/libraries/             — shared form libraries
    forms/menus/                 — menu definitions
    data/seed/                   — seed data

  pipeline/                      — extraction scripts (run these)
    oracle_parser.py             — Step 2: PL/SQL + Forms structure parser
    oracle_deep_parser.py        — Step 3: Deep business logic extractor

  output/                        — all extraction results (generated)
    graphify-out/
      graph.json                 — Graphify knowledge graph (74 nodes, 71 edges)
      graph.html                 — Interactive visual graph (open in browser)
      GRAPH_REPORT.md            — Graphify summary
      ORACLE_PARSER_REPORT.md    — Oracle parser summary
      oracle_plsql_graph.json    — PL/SQL package graph
      oracle_forms_graph.json    — Oracle Forms graph
      oracle_combined_graph.json — Everything merged (338 nodes, 451 edges)
      deep/
        plsql_deep.json          — Full PL/SQL deep extraction
        forms_deep.json          — Full Oracle Forms deep extraction
        schema_deep.json         — All tables, views, triggers
        business_rules.json      — 581 rules with IDs (BR-0001 to BR-0581)
        DEEP_REPORT.md           — Full human-readable deep report

  WHAT_WE_DID.md                 — Full explanation of approach and results
  requirements.txt               — Python dependencies
```

---

## How to Run

### 1. Install dependencies
```bash
pip install -r requirements.txt
```

### 2. Run Graphify on the source (Step 1)
```bash
# Copy source to a path without spaces first (Windows requirement)
cp -r source/ C:/oracle-hrms-src/
cd C:/oracle-hrms-src
python -m graphify update . --force
# Copy output back
cp -r C:/oracle-hrms-src/graphify-out/ output/graphify-out/
```

### 3. Run Oracle Parser (Step 2)
```bash
cd pipeline/
python oracle_parser.py
```

### 4. Run Deep Parser (Step 3)
```bash
cd pipeline/
python oracle_deep_parser.py
```

---

## Results

| Layer | Tool | Files Covered | Output |
|---|---|---|---|
| Step 1 — Knowledge Graph | Graphify | 14 `.sql` files | 74 nodes, 71 edges, 15 communities |
| Step 2 — Structure Parser | `oracle_parser.py` | 28 `.pkb`/`.pks` + 6 `.xml` | 338 nodes, 451 edges total |
| Step 3 — Deep Parser | `oracle_deep_parser.py` | All 42 files | 581 rules extracted |

**Total coverage: 42/42 files — 100%**

| Category | Count |
|---|---|
| Business rules | 101 |
| Validation rules | 376 |
| Constraints | 33 |
| Known bugs | 5 |
| Error codes | 37 |
| Check constraints | 29 |
| **Total rules** | **581** |

---

## Source System

- **Oracle Forms** 12c (12.2.1.4)
- **Oracle Database** 19c
- **Domain:** HRMS (Human Resource Management System)
- **Modules:** Employee, Payroll, Leave, Performance, Security, Audit, Reporting

---

## Next Step

The output from this pipeline feeds into the
[HRMS Reverse Engineering Pipeline](https://github.com/jayaprakash2207/HRMS-Reverse-Engineering-Pipeline---25-DOC-TEST)
as the 8 agent input files, which then generates 25 enterprise forward-engineering documents.
