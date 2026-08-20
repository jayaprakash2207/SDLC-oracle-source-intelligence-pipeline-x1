"""
Foundation Runner — Multi-Agent Self-Healing (Upgraded)
=========================================================
Replaces the sequential 4-call foundation_runner_template.py with a
3-phase Claude multi-agent architecture:

  Phase 1 — Parallel Generation
    Subagent A : Docs 01–10  + KG docs 21–25   (concurrent thread)
    Subagent B : Docs 11–20                     (concurrent thread)
    Both run simultaneously — wall-clock = slowest single agent

  Phase 2 — Self-Healing Loop (NEW)
    Iteration:
      Gap Hunter agent — reads all 25 docs, produces gap report
      If gaps > 0:
        Team Lead assigns gaps to domain agents by type:
          BA Agent  → business/use-case gaps
          DA Agent  → data/API/schema gaps
          SEC Agent → security/NFR gaps
        Domain agents claim, fix, communicate via shared gap list
        Fixes merged back to disk
        Gap Hunter re-reads — loops again
      Stop when: gap count = 0 | no progress | max 3 iterations
      Remaining unresolved → flagged HUMAN-DECISION-REQUIRED

  Phase 3 — Final Quality Gate
    Single final agent — reads all 25 docs, sets YES/CONDITIONAL/NO-GO

All existing infrastructure is reused:
  - base_runner.call_claude()
  - _split_documents(), _split_documents_updates(), _clean_document()
  - _run_coverage_pass(), _run_self_correction(), _run_second_opinion()
  - Population rules, all prompts, template appendix builder

Run via:
    python pipeline/foundation_runner_multiagent.py --output results/
"""

import argparse
import sys
import threading
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from base_runner import call_claude, save_output, extract_deep_scan_sections, supplement_from_cache

# ── Re-use everything from the template runner ────────────────────────────────
# Import prompts, helpers, constants directly — no duplication
from foundation_runner_template import (
    _POPULATION_RULES,
    CALL1_PROMPT,
    CALL2_PROMPT,
    CALL3_PROMPT,
    CALL4_PROMPT,
    _COVERAGE_CALL3_INSTRUCTION,
    _SELF_CORRECT_PROMPT,
    _FOUNDATION_FILES,
    _PART1_TEMPLATES,
    _PART2_TEMPLATES,
    _TEMPLATE_DIR,
    _load_layer_outputs,
    _build_template_appendix,
    _split_documents,
    _split_documents_updates,
    _save_docs,
    _reload_docs,
    _clean_document,
    _build_fallback_supplement,
    _run_coverage_pass,
    _run_self_correction,
    _run_second_opinion,
    _write_coverage_summary,
)

# ── Gap Hunter prompt ─────────────────────────────────────────────────────────

_GAP_HUNTER_PROMPT = """
# Gap Hunter Agent — Self-Healing Loop

You are the Gap Hunter. Read ALL 25 documents below and find every gap,
defect, or quality failure. Produce a structured gap report.

## What to Check

1. MANDATORY SECTIONS — every [M] section must be present and populated
   (not just a heading — actual content). NOT_AVAILABLE is acceptable if
   it follows the exact format.

2. REFERENCE INTEGRITY
   - Every BR-xxx cited anywhere must be defined in 01_BRD.md
   - Every BR-SEC-xxx cited anywhere must be in 13_SECURITY_ARCHITECTURE.md
   - Every UC-xxx cited anywhere must be in 03_USE_CASE_SPECIFICATION.md
   - Every table name (UPPER_CASE_TABLE) referenced must be in 07_DATA_MODEL_SPECIFICATION.md
   - Every PKG_xxx.procedure referenced must be in 11_API_CONTRACT_SPECIFICATION.md

3. EVIDENCE CLASSIFICATION — every material statement must carry one of:
   OBSERVED | DERIVED | INFERRED | ASSUMED | UNKNOWN | CONTRADICTED

4. TECHNOLOGY NEUTRALITY — flag any prescribed technology names:
   React, Angular, Vue, Node.js, Spring Boot, Kubernetes, Docker,
   AWS, Azure, GCP, PostgreSQL (as target), JWT (prescribed),
   bcrypt/Argon2/scrypt (prescribed), Nginx, Kafka, RabbitMQ

5. AI ARTIFACT TEXT — flag any lines containing:
   "Let me check", "I'll now", "I need to", "Based on the above",
   "I can see that", "Here is the updated", "I've removed", "I've added"

6. DUPLICATE SECTIONS — same ## or ### heading appearing more than once
   in the same document

7. ORACLE FORMS COVERAGE — all 6 modules must appear in
   19_FRONTEND_ARCHITECTURE.md or 20_UI_UX_SPECIFICATION.md:
   HRMS_EMPLOYEE, HRMS_PAYROLL, HRMS_LEAVE, HRMS_PERFORMANCE,
   HRMS_LOGIN, HRMS_MENU

8. NUMERIC CONTRADICTIONS — same fact (session timeout, tax rates,
   rating ranges) stated differently in two or more documents

9. QUALITY GATE CHECKLIST — must be present and filled in every document

## Output Format

Produce a gap report in this EXACT format:

=== GAP_REPORT ===
TOTAL_GAPS: {N}

=== GAP: {GAP_ID} ===
Document: {filename}
Section: {section heading or "cross-document"}
Type: MISSING_SECTION | BROKEN_REFERENCE | NO_EVIDENCE | TECH_VIOLATION | AI_ARTIFACT | DUPLICATE | CONTRADICTION | MISSING_QUALITY_GATE
Domain: BUSINESS | DATA | SECURITY | APPLICATION | CROSS
Description: {one sentence describing exactly what is wrong}
Fix: {one sentence describing exactly what must be done}
Priority: CRITICAL | HIGH | MEDIUM
=== END GAP ===

... one block per gap ...

=== END GAP_REPORT ===

If no gaps found, write:
=== GAP_REPORT ===
TOTAL_GAPS: 0
=== END GAP_REPORT ===

IMPORTANT: Be precise. Every gap must have a document name and section.
Do not flag NOT_AVAILABLE sections as gaps — they are correct when evidence
is genuinely absent. Only flag them if the format is wrong.
"""

# ── Domain fix agent prompts ──────────────────────────────────────────────────

_BA_FIX_PROMPT = """
# BA Domain Fix Agent — Self-Healing Loop

You are the Business Analysis domain fix agent. Below is:
1. A list of gaps assigned to you (BUSINESS domain gaps)
2. The current content of the affected documents
3. The original source evidence

Fix each assigned gap. For each document that needs changes, output:

=== UPDATE: {filename} ===
{COMPLETE document content — every line from start to finish}

RULES:
- Output the FULL document, not a diff
- Do not invent content — mark gaps with NOT_AVAILABLE if no evidence exists
- Technology neutral — no React, AWS, Spring Boot etc.
- Every material statement needs evidence class + confidence score
- BR-xxx = requirements only, BR-SEC-xxx = security defects only
- Begin content directly — no preamble
- Only output UPDATE blocks for documents you actually changed
"""

_DA_FIX_PROMPT = """
# DA/TA Domain Fix Agent — Self-Healing Loop

You are the Data and Technology domain fix agent. Below is:
1. A list of gaps assigned to you (DATA domain gaps)
2. The current content of the affected documents
3. The original source evidence

Fix each assigned gap. For each document that needs changes, output:

=== UPDATE: {filename} ===
{COMPLETE document content — every line from start to finish}

RULES:
- Output the FULL document, not a diff
- Do not invent data — mark gaps with NOT_AVAILABLE if no evidence
- Technology neutral for target stack — Oracle source facts are kept as-is
- Every table/column/FK must be sourced from schema_deep.json or DDL evidence
- Every procedure must be sourced from plsql_deep.json or PKB evidence
- Begin content directly — no preamble
- Only output UPDATE blocks for documents you actually changed
"""

_SEC_FIX_PROMPT = """
# Security/NFR Domain Fix Agent — Self-Healing Loop

You are the Security and NFR domain fix agent. Below is:
1. A list of gaps assigned to you (SECURITY domain gaps)
2. The current content of the affected documents
3. The original source evidence

Fix each assigned gap. For each document that needs changes, output:

=== UPDATE: {filename} ===
{COMPLETE document content — every line from start to finish}

RULES:
- Output the FULL document, not a diff
- The 4 VULNERABILITY findings and 1 WEAKNESS from PKG_SECURITY are source facts
- BR-SEC-xxx IDs for all security defects — never share numbers with BR-xxx
- Technology neutral — "industry-standard password hashing", not "bcrypt"
- Every security claim needs evidence class + source reference
- Begin content directly — no preamble
- Only output UPDATE blocks for documents you actually changed
"""

# ── Final quality gate prompt ─────────────────────────────────────────────────

_FINAL_GATE_PROMPT = """
# Final Quality Gate Agent

You are the final quality gate. Read all 25 documents and produce a
readiness verdict for each one.

For each document set one of:
  YES         — all mandatory sections populated, no blockers
  CONDITIONAL — usable with caveats (some NOT_AVAILABLE sections but
                no critical blockers)
  NO-GO       — critical mandatory section empty or critical blocker exists

Output format:

=== QUALITY_GATE_REPORT ===

| Document | Verdict | Reason |
|---|---|---|
| 01_BRD.md | YES/CONDITIONAL/NO-GO | one-line reason |
... one row per document ...

## Summary
- YES: {N}
- CONDITIONAL: {N}
- NO-GO: {N}

## Remaining HUMAN-DECISION-REQUIRED Items
List any items flagged across the loop that could not be resolved
automatically. Each needs a business stakeholder decision before
forward engineering can proceed.

=== END QUALITY_GATE_REPORT ===
"""

# ── Gap report parser ─────────────────────────────────────────────────────────

import re as _re


def _parse_gap_report(text: str) -> list:
    """Parse gap report from Gap Hunter output. Returns list of gap dicts."""
    total_match = _re.search(r'TOTAL_GAPS:\s*(\d+)', text)
    if not total_match or int(total_match.group(1)) == 0:
        return []

    gap_pattern = _re.compile(
        r'=== GAP:\s*([^=]+?)\s*===\s*(.*?)\s*=== END GAP ===',
        _re.DOTALL
    )
    gaps = []
    for gap_id, body in gap_pattern.findall(text):
        gap = {"id": gap_id.strip()}
        for field in ["Document", "Section", "Type", "Domain", "Description", "Fix", "Priority"]:
            m = _re.search(rf'{field}:\s*(.+)', body)
            gap[field.lower()] = m.group(1).strip() if m else ""
        gaps.append(gap)
    return gaps


def _assign_gaps_to_domains(gaps: list) -> dict:
    """Assign gaps to domain agents by Domain field."""
    assignments = {"BUSINESS": [], "DATA": [], "SECURITY": [], "APPLICATION": [], "CROSS": []}
    for gap in gaps:
        domain = gap.get("domain", "CROSS").upper()
        if domain not in assignments:
            domain = "CROSS"
        assignments[domain].append(gap)
    return assignments


def _build_gap_context(assigned_gaps: list, all_docs: dict, layers: dict) -> str:
    """Build the prompt context for a domain fix agent."""
    gap_lines = "\n".join(
        f"GAP {g['id']}: [{g['document']}] {g['section']} — {g['description']} FIX: {g['fix']}"
        for g in assigned_gaps
    )

    affected_docs = {g["document"] for g in assigned_gaps if g.get("document")}
    doc_context = "\n\n---\n\n".join(
        f"## {fname}\n\n{content}"
        for fname, content in all_docs.items()
        if fname in affected_docs and content
    )

    source_context = "\n\n".join(
        f"## {key}\n\n{content[:4000]}"
        for key, content in layers.items()
        if content
    )

    return (
        f"# Gaps Assigned to You\n\n{gap_lines}\n\n"
        f"# Current Document Content\n\n{doc_context}\n\n"
        f"# Source Evidence\n\n{source_context}\n\n"
        f"Fix the gaps now. Output one UPDATE block per changed document."
    )


# ── Phase 1 — Parallel generation ────────────────────────────────────────────

def _phase1_generate(
    output_dir: str,
    all_layer_text: str,
    layers: dict,
    foundation_dir: Path,
    fwd_eng_dir: Path,
) -> dict:
    """
    Run Call 1 (docs 01-10 + KG) and Call 2 (docs 11-20) in parallel threads.
    Returns merged dict of all 25 documents.
    """
    part1_raw = Path(output_dir) / "Foundation_Raw_Output_Part1.md"
    part2_raw = Path(output_dir) / "Foundation_Raw_Output_Part2.md"

    docs1 = {}
    docs2 = {}
    errors = []
    lock = threading.Lock()

    # ── Thread A: Call 1 ──────────────────────────────────────────────────────
    def run_call1():
        nonlocal docs1
        try:
            if part1_raw.exists() and part1_raw.stat().st_size > 0:
                print("\n[Phase 1 | Subagent A] Already done — loading Part1 from disk...")
                output = part1_raw.read_text(encoding="utf-8")
            else:
                print("\n[Phase 1 | Subagent A] Generating docs 01-10 + KG (21-25)...")
                template_appendix = _build_template_appendix(_PART1_TEMPLATES)
                prompt = (
                    f"{CALL1_PROMPT}"
                    f"{template_appendix}\n\n"
                    f"---\n\n"
                    f"# All Layer Outputs (Oracle Source Evidence)\n\n"
                    f"{all_layer_text}\n\n"
                    f"Begin Part 1 now. Populate each template from the evidence above."
                )
                output = call_claude(
                    prompt,
                    label="[Phase 1] Subagent A — docs 01-10 + KG",
                    timeout=5400,
                    allow_tools=False,
                )
                save_output(output_dir, "Foundation_Raw_Output_Part1.md", output)

            with lock:
                docs1 = _split_documents(output)
                saved = _save_docs(docs1, foundation_dir, fwd_eng_dir)
                print(f"[Phase 1 | Subagent A] Complete — {len(saved)} documents saved.")
        except Exception as exc:
            with lock:
                errors.append(f"Subagent A failed: {exc}")
            print(f"[Phase 1 | Subagent A] ERROR: {exc}")

    # ── Thread B: Call 2 ──────────────────────────────────────────────────────
    def run_call2():
        nonlocal docs2
        try:
            if part2_raw.exists() and part2_raw.stat().st_size > 0:
                print("\n[Phase 1 | Subagent B] Already done — loading Part2 from disk...")
                output = part2_raw.read_text(encoding="utf-8")
                with lock:
                    docs2 = _split_documents(output)
                    saved = _save_docs(docs2, foundation_dir, fwd_eng_dir)
                    print(f"[Phase 1 | Subagent B] Complete — {len(saved)} documents saved.")
                return

            # Call 2 needs Call 1 context — wait for docs1 to be ready
            # (thread-safe: we wait for part1_raw to exist on disk)
            import time as _time
            wait_secs = 0
            while not (part1_raw.exists() and part1_raw.stat().st_size > 0) and wait_secs < 600:
                _time.sleep(5)
                wait_secs += 5

            with lock:
                docs1_filled = _reload_docs(docs1, foundation_dir, fwd_eng_dir)

            kg_json = docs1_filled.get("ENTERPRISE_KNOWLEDGE_GRAPH.json", "")
            kg_context_parts = []
            if kg_json:
                kg_context_parts.append(f"## Enterprise Knowledge Graph\n\n```json\n{kg_json}\n```")
            doc_order = [
                "CANONICAL_ENTERPRISE_MODEL.md", "ARCHITECTURE_INVENTORY.md",
                "TRACEABILITY_MATRIX.md", "FORWARD_ENGINEERING_INPUT_MAP.md",
                "01_BRD.md", "02_BUSINESS_CAPABILITY_MODEL.md", "03_USE_CASE_SPECIFICATION.md",
                "04_BUSINESS_PROCESS_MODEL.md", "05_DOMAIN_MODEL.md", "06_DATA_DICTIONARY.md",
                "07_DATA_MODEL_SPECIFICATION.md", "08_ERD.md", "09_DATA_FLOW_DIAGRAM.md",
                "10_SERVICE_CATALOG.md",
            ]
            for doc_name in doc_order:
                if doc_name in docs1_filled and docs1_filled[doc_name]:
                    kg_context_parts.append(f"## {doc_name}\n\n{docs1_filled[doc_name]}")
            kg_context = "\n\n---\n\n".join(kg_context_parts)

            print("\n[Phase 1 | Subagent B] Generating docs 11-20...")
            template_appendix = _build_template_appendix(_PART2_TEMPLATES)
            prompt = (
                f"{CALL2_PROMPT}"
                f"{template_appendix}\n\n"
                f"---\n\n"
                f"# Part 1 Documents (context — do not regenerate)\n\n"
                f"{kg_context}\n\n"
                f"Begin Part 2 now. Populate each template from the evidence above."
            )
            output = call_claude(
                prompt,
                label="[Phase 1] Subagent B — docs 11-20",
                timeout=5400,
                allow_tools=False,
            )
            save_output(output_dir, "Foundation_Raw_Output_Part2.md", output)

            with lock:
                docs2 = _split_documents(output)
                saved = _save_docs(docs2, foundation_dir, fwd_eng_dir)
                print(f"[Phase 1 | Subagent B] Complete — {len(saved)} documents saved.")
        except Exception as exc:
            with lock:
                errors.append(f"Subagent B failed: {exc}")
            print(f"[Phase 1 | Subagent B] ERROR: {exc}")

    # ── Launch both threads ───────────────────────────────────────────────────
    print("\n" + "═" * 64)
    print("[Phase 1] PARALLEL GENERATION — Subagent A + B running simultaneously")
    print("═" * 64)

    thread_a = threading.Thread(target=run_call1, daemon=True)
    thread_b = threading.Thread(target=run_call2, daemon=True)
    thread_a.start()
    thread_b.start()
    thread_a.join()
    thread_b.join()

    if errors:
        for e in errors:
            print(f"  ERROR: {e}")
        raise RuntimeError(f"Phase 1 generation failed: {errors}")

    # Merge all 25 docs — reload from disk to get freshest content
    all_docs = {}
    all_docs.update(_reload_docs(docs1, foundation_dir, fwd_eng_dir))
    all_docs.update(_reload_docs(docs2, foundation_dir, fwd_eng_dir))
    print(f"\n[Phase 1] Complete — {len(all_docs)} documents generated.")
    return all_docs


# ── Phase 2 — Self-healing loop ───────────────────────────────────────────────

def _reload_all_from_disk(foundation_dir: Path, fwd_eng_dir: Path) -> dict:
    """Read all .md and .json files from both output directories."""
    docs = {}
    for directory in [foundation_dir, fwd_eng_dir]:
        for path in sorted(directory.glob("*")):
            if path.suffix in (".md", ".json") and path.stat().st_size > 0:
                docs[path.name] = path.read_text(encoding="utf-8")
    return docs


def _apply_updates(updates: dict, foundation_dir: Path, fwd_eng_dir: Path) -> int:
    """Write UPDATE blocks to disk. Returns count of files updated."""
    count = 0
    for filename, content in updates.items():
        if not content.strip():
            continue
        content = _clean_document(filename, content)
        if filename in _FOUNDATION_FILES:
            path = foundation_dir / filename
        else:
            path = fwd_eng_dir / filename
        path.write_text(content, encoding="utf-8")
        count += 1
        print(f"  Updated → {path.name}")
    return count


def _phase2_self_healing(
    output_dir: str,
    layers: dict,
    foundation_dir: Path,
    fwd_eng_dir: Path,
    max_iterations: int = 3,
) -> None:
    """
    Self-healing loop:
      1. Gap Hunter reads all 25 docs → gap report
      2. If gaps > 0: domain agents fix their domains in parallel
      3. Reload docs from disk
      4. Repeat until gap count = 0 or no progress or max iterations
    """
    print("\n" + "═" * 64)
    print("[Phase 2] SELF-HEALING LOOP starting...")
    print("═" * 64)

    prev_gap_count = None

    for iteration in range(1, max_iterations + 1):
        print(f"\n[Phase 2 | Iteration {iteration}/{max_iterations}]")

        # ── Gap Hunter ────────────────────────────────────────────────────────
        all_docs = _reload_all_from_disk(foundation_dir, fwd_eng_dir)
        docs_text = "\n\n---\n\n".join(
            f"## {fname}\n\n{content[:10000]}"
            for fname, content in all_docs.items()
            if content
        )

        gap_hunter_prompt = (
            f"{_GAP_HUNTER_PROMPT}\n\n"
            f"# All 25 Documents\n\n"
            f"{docs_text}\n\n"
            f"Produce the gap report now."
        )

        print(f"  Running Gap Hunter (iteration {iteration})...")
        gap_output = call_claude(
            gap_hunter_prompt,
            label=f"[Phase 2] Gap Hunter — iteration {iteration}",
            timeout=3600,
            allow_tools=False,
        )
        save_output(output_dir, f"Gap_Hunter_Iteration_{iteration}.md", gap_output)

        gaps = _parse_gap_report(gap_output)
        gap_count = len(gaps)
        print(f"  Gap Hunter found {gap_count} gap(s).")

        # ── Stop conditions ───────────────────────────────────────────────────
        if gap_count == 0:
            print(f"  [Phase 2] All gaps resolved. Exiting loop. ✅")
            break

        if prev_gap_count is not None and gap_count >= prev_gap_count:
            print(f"  [Phase 2] No progress (gaps: {prev_gap_count} → {gap_count}).")
            print(f"  Flagging remaining {gap_count} gap(s) as HUMAN-DECISION-REQUIRED.")
            _flag_human_decisions(gaps, output_dir, iteration)
            break

        prev_gap_count = gap_count

        if iteration == max_iterations:
            print(f"  [Phase 2] Max iterations reached. Flagging {gap_count} remaining gap(s).")
            _flag_human_decisions(gaps, output_dir, iteration)
            break

        # ── Assign to domain agents ───────────────────────────────────────────
        assignments = _assign_gaps_to_domains(gaps)
        active_domains = {d: g for d, g in assignments.items() if g}
        print(f"  Assigning gaps: " + ", ".join(f"{d}={len(g)}" for d, g in active_domains.items()))

        fix_results = {}
        fix_lock = threading.Lock()

        def run_domain_fix(domain, domain_gaps, fix_prompt_template):
            try:
                context = _build_gap_context(domain_gaps, all_docs, layers)
                prompt = fix_prompt_template + "\n\n" + context
                label = f"[Phase 2] {domain} Fix Agent — iteration {iteration}"
                output = call_claude(prompt, label=label, timeout=3600, allow_tools=False)
                save_output(output_dir, f"Fix_{domain}_Iteration_{iteration}.md", output)
                updates = _split_documents_updates(output)
                with fix_lock:
                    fix_results[domain] = updates
                    print(f"  [{domain} Fix Agent] {len(updates)} document(s) to update.")
            except Exception as exc:
                print(f"  [{domain} Fix Agent] ERROR: {exc}")

        fix_threads = []
        domain_prompt_map = {
            "BUSINESS": _BA_FIX_PROMPT,
            "APPLICATION": _BA_FIX_PROMPT,
            "DATA": _DA_FIX_PROMPT,
            "SECURITY": _SEC_FIX_PROMPT,
            "CROSS": _DA_FIX_PROMPT,
        }

        for domain, domain_gaps in active_domains.items():
            if domain_gaps:
                prompt_template = domain_prompt_map.get(domain, _DA_FIX_PROMPT)
                t = threading.Thread(
                    target=run_domain_fix,
                    args=(domain, domain_gaps, prompt_template),
                    daemon=True,
                )
                fix_threads.append(t)

        for t in fix_threads:
            t.start()
        for t in fix_threads:
            t.join()

        # ── Apply all fixes to disk ───────────────────────────────────────────
        total_updated = 0
        for domain, updates in fix_results.items():
            updated = _apply_updates(updates, foundation_dir, fwd_eng_dir)
            total_updated += updated
        print(f"  Iteration {iteration} complete — {total_updated} document(s) updated on disk.")

    print(f"\n[Phase 2] Self-healing loop complete.")


def _flag_human_decisions(gaps: list, output_dir: str, iteration: int) -> None:
    """Write unresolved gaps to a HUMAN_DECISION_REQUIRED report."""
    lines = [
        "# HUMAN-DECISION-REQUIRED — Unresolved Gaps",
        "",
        "The self-healing loop could not automatically resolve the following gaps.",
        "Each item requires a business stakeholder decision before forward engineering.",
        "",
        f"Unresolved after {iteration} iteration(s): {len(gaps)} gap(s)",
        "",
        "| Gap ID | Document | Section | Description | Fix Required |",
        "|---|---|---|---|---|",
    ]
    for g in gaps:
        lines.append(
            f"| {g['id']} | {g.get('document','')} | {g.get('section','')} "
            f"| {g.get('description','')} | {g.get('fix','')} |"
        )
    save_output(output_dir, "HUMAN_DECISION_REQUIRED.md", "\n".join(lines))
    print(f"  Written: HUMAN_DECISION_REQUIRED.md ({len(gaps)} item(s))")


# ── Phase 3 — Final quality gate ──────────────────────────────────────────────

def _phase3_quality_gate(
    output_dir: str,
    foundation_dir: Path,
    fwd_eng_dir: Path,
) -> None:
    """Run final quality gate — sets YES/CONDITIONAL/NO-GO per document."""
    print("\n" + "═" * 64)
    print("[Phase 3] FINAL QUALITY GATE")
    print("═" * 64)

    all_docs = _reload_all_from_disk(foundation_dir, fwd_eng_dir)
    docs_text = "\n\n---\n\n".join(
        f"## {fname}\n\n{content[:10000]}"
        for fname, content in all_docs.items()
        if content
    )

    gate_prompt = (
        f"{_FINAL_GATE_PROMPT}\n\n"
        f"# All 25 Documents\n\n"
        f"{docs_text}\n\n"
        f"Produce the quality gate report now."
    )

    print("  Running Final Quality Gate agent...")
    gate_output = call_claude(
        gate_prompt,
        label="[Phase 3] Final Quality Gate",
        timeout=3600,
        allow_tools=False,
    )
    save_output(output_dir, "FINAL_QUALITY_GATE_REPORT.md", gate_output)
    print("  Written: FINAL_QUALITY_GATE_REPORT.md")

    # Print summary from gate report
    yes_count = gate_output.upper().count("| YES")
    cond_count = gate_output.upper().count("| CONDITIONAL")
    nogo_count = gate_output.upper().count("| NO-GO")
    print(f"\n  Quality Gate Summary: YES={yes_count}  CONDITIONAL={cond_count}  NO-GO={nogo_count}")

    if nogo_count > 0:
        print(f"  ⚠  {nogo_count} document(s) are NO-GO — review FINAL_QUALITY_GATE_REPORT.md")
    else:
        print(f"  ✅ All documents are YES or CONDITIONAL — ready for downstream use.")


# ── Main orchestrator ─────────────────────────────────────────────────────────

def run(output_dir: str) -> None:
    print("\n[Foundation MultiAgent] Loading all layer outputs...")
    layers = _load_layer_outputs(output_dir)

    all_layer_text = "\n\n".join(
        f"## {key}\n\n{content}"
        for key, content in layers.items()
        if content
    )

    missing_agents = [k for k, v in layers.items() if not v]
    if missing_agents:
        print(f"\n  WARNING: {len(missing_agents)} agent output(s) missing: {missing_agents}")
        fallback_text = _build_fallback_supplement(output_dir)
        if fallback_text:
            all_layer_text = all_layer_text + "\n\n" + fallback_text

    if not _TEMPLATE_DIR.exists():
        print(f"\n  ERROR: Template directory not found: {_TEMPLATE_DIR}")
        sys.exit(1)

    foundation_dir = Path(output_dir) / "Foundation_KnowledgeGraph"
    fwd_eng_dir    = Path(output_dir) / "ForwardEngineering_Docs"
    foundation_dir.mkdir(parents=True, exist_ok=True)
    fwd_eng_dir.mkdir(parents=True, exist_ok=True)

    # ── Phase 1 — Parallel generation ────────────────────────────────────────
    _phase1_generate(output_dir, all_layer_text, layers, foundation_dir, fwd_eng_dir)

    # ── Existing passes preserved — run after Phase 1 ────────────────────────
    # Call 3 (template compliance + cleaning) still runs before the loop —
    # it removes AI artifacts and fixes obvious issues before the gap hunter
    part3_raw = Path(output_dir) / "Foundation_Raw_Output_Part3.md"
    if not (part3_raw.exists() and part3_raw.stat().st_size > 0):
        print("\n[Pre-Loop] Running Call 3 — template compliance verification...")
        all_docs_pre = _reload_all_from_disk(foundation_dir, fwd_eng_dir)
        generated_text = "\n\n---\n\n".join(
            f"## {fname}\n\n{content[:8000]}"
            for fname, content in all_docs_pre.items() if content
        )
        agent_text = "\n\n---\n\n".join(
            f"## {key}\n\n{content[:6000]}"
            for key, content in layers.items() if content
        )
        call3_prompt = (
            f"{CALL3_PROMPT}\n\n"
            f"{_COVERAGE_CALL3_INSTRUCTION}\n\n"
            f"# All 25 Generated Documents\n\n{generated_text}\n\n"
            f"# Original 8 Agent Outputs\n\n{agent_text}\n\n"
            f"Begin verification pass now."
        )
        call3_output = call_claude(
            call3_prompt,
            label="[Pre-Loop] Call 3 — template compliance",
            timeout=5400,
            allow_tools=False,
        )
        save_output(output_dir, "Foundation_Raw_Output_Part3.md", call3_output)
        docs3 = _split_documents_updates(call3_output)
        _apply_updates(docs3, foundation_dir, fwd_eng_dir)
        print(f"  Call 3 complete — {len(docs3)} update(s) applied.")

    # ── Phase 2 — Self-healing loop ───────────────────────────────────────────
    _phase2_self_healing(output_dir, layers, foundation_dir, fwd_eng_dir)

    # ── Call 5 — Self-correction of LOW confidence sections ───────────────────
    all_docs_post = _reload_all_from_disk(foundation_dir, fwd_eng_dir)
    _run_self_correction(output_dir, layers, foundation_dir, fwd_eng_dir)

    # ── Call 6 — Second-opinion scoring of HIGH confidence claims ─────────────
    downgrades = _run_second_opinion(output_dir, layers, foundation_dir, fwd_eng_dir)

    # ── Coverage pass — Python-verified evidence counts ───────────────────────
    source_dir = None
    try:
        import json as _json
        cache_path = Path(output_dir) / "file_cache.json"
        if cache_path.exists():
            source_dir = Path(output_dir)
    except Exception:
        pass

    _run_coverage_pass(
        foundation_dir, fwd_eng_dir, output_dir,
        source_dir=source_dir,
        second_opinion_downgrades=downgrades,
    )

    # ── Phase 3 — Final quality gate ──────────────────────────────────────────
    _phase3_quality_gate(output_dir, foundation_dir, fwd_eng_dir)

    print("\n" + "═" * 64)
    print("[Foundation MultiAgent] COMPLETE")
    print(f"  Output: {foundation_dir}")
    print(f"  Output: {fwd_eng_dir}")
    print(f"  Quality gate: {Path(output_dir) / 'FINAL_QUALITY_GATE_REPORT.md'}")
    if (Path(output_dir) / "HUMAN_DECISION_REQUIRED.md").exists():
        print(f"  Human decisions needed: {Path(output_dir) / 'HUMAN_DECISION_REQUIRED.md'}")
    print("═" * 64 + "\n")


# ── Entry point ───────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        prog="foundation_runner_multiagent.py",
        description="Foundation Runner — Multi-Agent Self-Healing (Upgraded)",
    )
    parser.add_argument(
        "--output", required=True,
        help="Pipeline output directory (same --output as run.py)"
    )
    args = parser.parse_args()
    run(args.output)


if __name__ == "__main__":
    main()
