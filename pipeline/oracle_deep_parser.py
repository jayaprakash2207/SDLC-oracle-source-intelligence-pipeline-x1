"""
oracle_deep_parser.py — v2 (full coverage)
-------------------------------------------
Deep extraction of Oracle PL/SQL packages, Oracle Forms XML,
PLL libraries, menu modules, sequences, and seed data.

Output (02_oracle_parser_output/):
  plsql_deep.json       — all 11 packages deep extraction
  forms_deep.json       — all 6 Oracle Forms deep extraction
  pll_deep.json         — HRMS_COMMON_LIB + HRMS_VALIDATION_LIB procedures
  menu_deep.json        — HRMS_MENU structure (menus, items, security)
  schema_deep.json      — all 30 tables, views, triggers, sequences
  seed_deep.json        — all seed data rows (86 rows across 8 tables)
  business_rules.json   — all rules consolidated with IDs (BR-XXXX)
  DEEP_REPORT.md        — human-readable full report
"""

import re
import json
import xml.etree.ElementTree as ET
from pathlib import Path

SOURCE_DIR   = Path(__file__).parent.parent / "source"
OUTPUT_DIR   = Path(__file__).parent.parent / "output" / "02_oracle_parser_output"
PKG_DIR      = SOURCE_DIR / "plsql" / "packages"
FORMS_DIR    = SOURCE_DIR / "forms" / "xml-exports"
LIBS_DIR     = SOURCE_DIR / "forms" / "libraries"
MENUS_DIR    = SOURCE_DIR / "forms" / "menus"
TRIGGERS_DIR = SOURCE_DIR / "plsql" / "triggers"
SCHEMA_DIR   = SOURCE_DIR / "schema"
SEED_DIR     = SOURCE_DIR / "data" / "seed"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def read_file(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def extract_inline_comments(content: str, tag: str) -> list:
    pattern = re.compile(r"--\s*" + re.escape(tag) + r":?\s*(.+)", re.IGNORECASE)
    return [m.group(1).strip() for m in pattern.finditer(content)]


def extract_constants(content: str) -> list:
    results = []
    pattern = re.compile(
        r"--\s*(CONSTRAINT|NOTE|INFO)[:\s]+(.+?)\n\s*(\w+)\s+CONSTANT\s+(\w[\w\(\),\s]+?)\s*:=\s*([^;]+);",
        re.IGNORECASE
    )
    for m in pattern.finditer(content):
        results.append({
            "name": m.group(3).strip(),
            "type": m.group(4).strip(),
            "value": m.group(5).strip(),
            "meaning": m.group(2).strip(),
        })
    pattern2 = re.compile(
        r"(\w+)\s+CONSTANT\s+(\w[\w\(\),\s]+?)\s*:=\s*([^;]+);",
        re.IGNORECASE
    )
    existing_names = {r["name"] for r in results}
    for m in pattern2.finditer(content):
        name = m.group(1).strip()
        if name not in existing_names and not name.startswith("--"):
            results.append({
                "name": name,
                "type": m.group(2).strip(),
                "value": m.group(3).strip(),
                "meaning": "",
            })
            existing_names.add(name)
    return results


def extract_raise_application_errors(content: str) -> list:
    pattern = re.compile(
        r"RAISE_APPLICATION_ERROR\s*\(\s*(-\d+)\s*,\s*'([^']+)'",
        re.IGNORECASE
    )
    return [{"code": m.group(1), "message": m.group(2)} for m in pattern.finditer(content)]


def extract_sql_statements(content: str) -> dict:
    selects = list(set(re.findall(r"FROM\s+(HRMS\.)?(\w+)\b", content, re.IGNORECASE)))
    inserts = list(set(re.findall(r"INSERT\s+INTO\s+(HRMS\.)?(\w+)\b", content, re.IGNORECASE)))
    updates = list(set(re.findall(r"UPDATE\s+(HRMS\.)?(\w+)\b", content, re.IGNORECASE)))
    deletes = list(set(re.findall(r"DELETE\s+FROM\s+(HRMS\.)?(\w+)\b", content, re.IGNORECASE)))

    def clean(lst):
        skip = {"DUAL", "NULL", "SELECT", "WHERE", "SET", "FROM", "SYSDATE"}
        return sorted(set(
            ("HRMS." + t[1] if t[0] else t[1]).upper()
            for t in lst if t[1].upper() not in skip
        ))

    return {
        "selects_from": clean(selects),
        "inserts_into": clean(inserts),
        "updates": clean(updates),
        "deletes_from": clean(deletes),
    }


def infer_behavioral_rules_from_code(proc_name: str, body: str) -> list:
    """Infer implicit behavioral rules from PL/SQL code patterns."""
    rules = []
    if not body:
        return rules
    if re.search(r"PRAGMA\s+AUTONOMOUS_TRANSACTION", body, re.IGNORECASE):
        rules.append(f"{proc_name}: Runs in autonomous transaction — changes committed independently of the caller")
    if re.search(r"SYS_CONTEXT\s*\(\s*'USERENV'\s*,\s*'IP_ADDRESS'", body, re.IGNORECASE):
        rules.append(f"{proc_name}: Captures client IP address via SYS_CONTEXT for audit trail")
    if re.search(r"SYS_CONTEXT\s*\(\s*'USERENV'\s*,\s*'SESSIONID'", body, re.IGNORECASE):
        rules.append(f"{proc_name}: Captures Oracle session ID via SYS_CONTEXT for audit trail")
    if re.search(r"EXCEPTION\s+WHEN\s+OTHERS\s+THEN\s*\n\s*(?:--|ROLLBACK|NULL)", body, re.IGNORECASE):
        rules.append(f"{proc_name}: Silently swallows exceptions — errors are suppressed to protect calling transaction")
    # Dynamic SQL injection risk
    if re.search(r"v_sql\s*:=\s*v_sql\s*\|\|.*p_\w+", body, re.IGNORECASE):
        rules.append(f"{proc_name}: BUG — uses dynamic SQL concatenation with user input; vulnerable to SQL injection")
    # UTL_FILE file operations
    if re.search(r"UTL_FILE\.FOPEN", body, re.IGNORECASE):
        fname_m = re.search(r"v_filename\s*:=\s*'([^']+)'|v_filename\s*:=\s*([^;]+);", body, re.IGNORECASE)
        rules.append(f"{proc_name}: Writes output file to Oracle directory object via UTL_FILE")
    if re.search(r"UTL_FILE\.GET_LINE", body, re.IGNORECASE):
        rules.append(f"{proc_name}: Reads input file line-by-line via UTL_FILE")
    # LEGACY/stub markers
    if re.search(r"LEGACY|Placeholder|stub|not.yet.implemented|TODO", body, re.IGNORECASE):
        rules.append(f"{proc_name}: LEGACY/stub — marked as placeholder or not fully implemented")
    # Fixed-width format markers
    if re.search(r"fixed.width|RPAD|LPAD.*fixed", body, re.IGNORECASE):
        rules.append(f"{proc_name}: Generates fixed-width format file (vendor-specific format)")
    # SMTP email
    if re.search(r"UTL_SMTP\.", body, re.IGNORECASE):
        rules.append(f"{proc_name}: Sends email via UTL_SMTP (not UTL_MAIL)")
    # Default retention
    for m in re.finditer(r"DEFAULT\s+(\d+)\s*\).*(?:days|purge|retain|keep)", body, re.IGNORECASE):
        rules.append(f"{proc_name}: Default retention period is {m.group(1)} days")
    return rules


def extract_procedure_bodies(content: str) -> list:
    results = []
    pattern = re.compile(
        r"(?:PROCEDURE|FUNCTION)\s+(\w+)\s*\([^)]*\)[^IS]*(?:IS|AS)\s*\n(.*?)(?=\n\s{4}(?:PROCEDURE|FUNCTION)\s+\w|\Z)",
        re.DOTALL | re.IGNORECASE
    )
    for m in pattern.finditer(content):
        name = m.group(1)
        body = m.group(2)
        business_rules = extract_inline_comments(body, "BUSINESS")
        rules = extract_inline_comments(body, "RULE")
        bugs = extract_inline_comments(body, "BUG")
        raises = extract_raise_application_errors(body)
        sql = extract_sql_statements(body)
        pkg_calls = list(set(re.findall(r"(PKG_\w+)\.\w+", body, re.IGNORECASE)))
        if_conditions = re.findall(r"IF\s+(.+?)\s+THEN", body, re.IGNORECASE)
        # Merge inferred rules into the rules list
        inferred = infer_behavioral_rules_from_code(name, body)
        results.append({
            "name": name,
            "business_rules": business_rules,
            "rules": rules + inferred,
            "bugs": bugs,
            "raise_errors": raises,
            "sql": sql,
            "package_calls": pkg_calls,
            "if_conditions": if_conditions[:10],
        })
    return results


# ─────────────────────────────────────────────────────────────────────────────
# DEEP PL/SQL PARSER
# ─────────────────────────────────────────────────────────────────────────────

def deep_parse_pkb(filepath: Path) -> dict:
    content = read_file(filepath)
    pkg_match = re.search(r"CREATE\s+OR\s+REPLACE\s+PACKAGE\s+BODY\s+(\S+)\s+AS", content, re.IGNORECASE)
    pkg_name = pkg_match.group(1) if pkg_match else filepath.stem

    # Package-level inferred behavioral rules
    pkg_inferred_rules = []
    if re.search(r"PRAGMA\s+AUTONOMOUS_TRANSACTION", content, re.IGNORECASE):
        pkg_inferred_rules.append("Package uses PRAGMA AUTONOMOUS_TRANSACTION — audit/notification writes are independent of caller transactions")
    if re.search(r"SYS_CONTEXT\s*\(\s*'USERENV'\s*,\s*'IP_ADDRESS'", content, re.IGNORECASE):
        pkg_inferred_rules.append("Captures client IP address for audit trail via SYS_CONTEXT")
    if re.search(r"SYS_CONTEXT\s*\(\s*'USERENV'\s*,\s*'SESSIONID'", content, re.IGNORECASE):
        pkg_inferred_rules.append("Captures Oracle session ID for audit trail via SYS_CONTEXT")
    utl_pkgs = list(set(re.findall(r"(UTL_\w+)\.", content, re.IGNORECASE)))
    if "UTL_SMTP" in [u.upper() for u in utl_pkgs]:
        pkg_inferred_rules.append("Email delivery uses UTL_SMTP (not UTL_MAIL)")
    if "UTL_FILE" in [u.upper() for u in utl_pkgs]:
        pkg_inferred_rules.append("File I/O uses UTL_FILE with Oracle directory objects")
    if re.search(r"Hard.coded|should be in SYSTEM_PARAMETERS", content, re.IGNORECASE):
        pkg_inferred_rules.append("Contains hard-coded configuration values that should be in SYSTEM_PARAMETERS table")

    pkg_bugs = extract_inline_comments(content, "BUG")
    if re.search(r"EXCEPTION\s+WHEN\s+OTHERS\s+THEN\s*\n\s*(?:ROLLBACK\s*;?\s*\n\s*)?(?:NULL|--)", content, re.IGNORECASE):
        pkg_bugs.append("Exception swallowing: WHEN OTHERS THEN ROLLBACK/NULL — errors silently suppressed")

    return {
        "name": pkg_name,
        "file": filepath.name,
        "constants": extract_constants(content),
        "business_rules": extract_inline_comments(content, "BUSINESS"),
        "rules": extract_inline_comments(content, "RULE") + pkg_inferred_rules,
        "constraints": extract_inline_comments(content, "CONSTRAINT"),
        "bugs": pkg_bugs,
        "raise_errors": extract_raise_application_errors(content),
        "sql": extract_sql_statements(content),
        "procedures": extract_procedure_bodies(content),
        "package_calls": list(set(re.findall(r"(PKG_\w+)\.\w+", content, re.IGNORECASE))),
        "sequences_used": list(set(re.findall(r"(SEQ_\w+)\.NEXTVAL", content, re.IGNORECASE))),
        "pragma_autonomous": bool(re.search(r"PRAGMA\s+AUTONOMOUS_TRANSACTION", content, re.IGNORECASE)),
        "uses_sys_context": bool(re.search(r"SYS_CONTEXT\s*\(", content, re.IGNORECASE)),
        "utl_packages_used": utl_pkgs,
    }


def deep_parse_pks(filepath: Path) -> dict:
    content = read_file(filepath)
    pkg_match = re.search(r"CREATE\s+OR\s+REPLACE\s+PACKAGE\s+(\S+)\s+AS", content, re.IGNORECASE)
    pkg_name = pkg_match.group(1) if pkg_match else filepath.stem

    procedures = []
    for m in re.finditer(r"PROCEDURE\s+(\w+)\s*\(([^)]*)\)", content, re.IGNORECASE):
        params = [p.strip().split()[0] for p in m.group(2).split(",") if p.strip()]
        procedures.append({"name": m.group(1), "params": params})

    functions = []
    for m in re.finditer(r"FUNCTION\s+(\w+)\s*\(([^)]*)\)\s*RETURN\s+(\w+)", content, re.IGNORECASE):
        params = [p.strip().split()[0] for p in m.group(2).split(",") if p.strip()]
        functions.append({"name": m.group(1), "params": params, "returns": m.group(3)})

    # Capture ALL exceptions — both PRAGMA-linked and plain EXCEPTION declarations
    exceptions = []
    seen_exc = set()

    # Build a map of exception_name -> code from all PRAGMA EXCEPTION_INIT lines
    pragma_map = {}
    for pm in re.finditer(
        r"PRAGMA\s+EXCEPTION_INIT\s*\(\s*(e_\w+)\s*,\s*(-\d+)\s*\)",
        content, re.IGNORECASE
    ):
        pragma_map[pm.group(1).lower()] = pm.group(2)

    # Find all EXCEPTION declarations and look up code from pragma_map
    for m in re.finditer(r"(e_\w+)\s+EXCEPTION\s*;", content, re.IGNORECASE):
        name = m.group(1)
        if name.lower() not in seen_exc:
            exceptions.append({
                "name": name,
                "code": pragma_map.get(name.lower()),
            })
            seen_exc.add(name.lower())

    types = re.findall(r"TYPE\s+(\w+)\s+IS\s+(\w+)", content, re.IGNORECASE)

    deps_match = re.search(r"Dependencies:\s*(.+)", content)
    callers_match = re.search(r"Called by:\s*(.+)", content)
    issues_lines = []
    issues_block = re.search(r"Known issues:(.*?)(?=\n--\s*={5,}|\Z)", content, re.DOTALL)
    if issues_block:
        for line in issues_block.group(1).splitlines():
            line = line.strip().lstrip("-").strip()
            if line:
                issues_lines.append(line)

    return {
        "name": pkg_name,
        "file": filepath.name,
        "procedures": procedures,
        "functions": functions,
        "exceptions": exceptions,
        "types": [{"name": t[0], "kind": t[1]} for t in types],
        "dependencies": [d.strip() for d in deps_match.group(1).split(",")] if deps_match else [],
        "callers": [c.strip() for c in callers_match.group(1).split(",")] if callers_match else [],
        "known_issues": issues_lines,
    }


def deep_parse_all_packages() -> dict:
    packages = {}
    for pks in sorted(PKG_DIR.glob("*.pks")):
        data = deep_parse_pks(pks)
        packages[data["name"]] = {"spec": data, "body": None}
    for pkb in sorted(PKG_DIR.glob("*.pkb")):
        data = deep_parse_pkb(pkb)
        name = data["name"]
        if name in packages:
            packages[name]["body"] = data
        else:
            packages[name] = {"spec": None, "body": data}
    return packages


# ─────────────────────────────────────────────────────────────────────────────
# PLL LIBRARY PARSER
# ─────────────────────────────────────────────────────────────────────────────

def parse_pll_library(filepath: Path) -> dict:
    content = read_file(filepath)
    lib_name = filepath.stem.replace(".pll", "").upper()

    procedures = []
    for m in re.finditer(
        r"PROCEDURE\s+(\w+)\s*\(([^)]*)\)\s+IS\s*\n(.*?)(?=\n(?:PROCEDURE|FUNCTION)\s+\w|\Z)",
        content, re.DOTALL | re.IGNORECASE
    ):
        name = m.group(1)
        body = m.group(3)
        procedures.append({
            "name": name,
            "params": [p.strip().split()[0] for p in m.group(2).split(",") if p.strip()],
            "business_rules": extract_inline_comments(body, "BUSINESS"),
            "rules": extract_inline_comments(body, "RULE"),
            "bugs": extract_inline_comments(body, "BUG"),
            "pkg_calls": list(set(re.findall(r"(PKG_\w+\.\w+)", body, re.IGNORECASE))),
        })

    functions = []
    for m in re.finditer(
        r"FUNCTION\s+(\w+)\s*\(([^)]*)\)\s+RETURN\s+(\w+)\s+IS\s*\n(.*?)(?=\n(?:PROCEDURE|FUNCTION)\s+\w|\Z)",
        content, re.DOTALL | re.IGNORECASE
    ):
        name = m.group(1)
        body = m.group(4)
        functions.append({
            "name": name,
            "params": [p.strip().split()[0] for p in m.group(2).split(",") if p.strip()],
            "returns": m.group(3),
            "business_rules": extract_inline_comments(body, "BUSINESS"),
            "rules": extract_inline_comments(body, "RULE"),
            "bugs": extract_inline_comments(body, "BUG"),
            "pkg_calls": list(set(re.findall(r"(PKG_\w+\.\w+)", body, re.IGNORECASE))),
        })

    # Dependencies/metadata from header comments
    deps_match = re.search(r"Dependencies:\s*(.+)", content)
    attached_by_match = re.search(r"Attached by:\s*(.+)", content)

    return {
        "name": lib_name,
        "file": filepath.name,
        "dependencies": [d.strip() for d in deps_match.group(1).split(",")] if deps_match else [],
        "attached_by": attached_by_match.group(1).strip() if attached_by_match else "",
        "procedures": procedures,
        "functions": functions,
        "all_business_rules": extract_inline_comments(content, "BUSINESS"),
        "all_rules": extract_inline_comments(content, "RULE"),
        "all_bugs": extract_inline_comments(content, "BUG"),
        "pkg_calls": list(set(re.findall(r"(PKG_\w+\.\w+)", content, re.IGNORECASE))),
    }


def parse_all_pll_libraries() -> list:
    results = []
    for f in sorted(LIBS_DIR.glob("*.sql")):
        results.append(parse_pll_library(f))
    return results


# ─────────────────────────────────────────────────────────────────────────────
# MENU MODULE PARSER
# ─────────────────────────────────────────────────────────────────────────────

def parse_menu_module(filepath: Path) -> dict:
    content = read_file(filepath)

    menus = []
    # Extract top-level menu names from tree comment (├── MenuName)
    for m in re.finditer(r"├──\s+(\w[\w\s&]+?)\s*$", content, re.MULTILINE):
        name = m.group(1).strip()
        if name not in menus:
            menus.append(name)

    # Extract all menu items with their actions
    items = []
    for m in re.finditer(r"[├└]──\s+(.+?)\s+\(([^)]+)\)", content):
        items.append({
            "label": m.group(1).strip(),
            "action": m.group(2).strip(),
        })

    # Extract OPEN_FORM calls (module navigation)
    open_forms = list(set(re.findall(r"OPEN_FORM\(['\"]([^'\"]+)['\"]\)", content, re.IGNORECASE)))

    # Extract permission requirements
    permission_notes = re.findall(r"requires\s+(\w+)\s+permission", content, re.IGNORECASE)

    # Extract PKG_SECURITY references
    security_calls = list(set(re.findall(r"(PKG_SECURITY\.\w+)", content, re.IGNORECASE)))

    # Extract SHOW_WINDOW calls
    show_windows = list(set(re.findall(r"SHOW_WINDOW\(['\"]([^'\"]+)['\"]\)", content, re.IGNORECASE)))

    return {
        "name": "HRMS_MENU",
        "file": filepath.name,
        "menu_bar": "MAIN_MENUBAR",
        "menus": menus,
        "total_items": len(items),
        "items": items,
        "open_forms": open_forms,
        "show_windows": show_windows,
        "permission_requirements": permission_notes,
        "security_calls": security_calls,
        "notes": [
            "Menu items are enabled/disabled at runtime based on PKG_SECURITY.has_permission() checks in WHEN-NEW-FORM-INSTANCE",
            "Compiled binary: HRMS_MENU.mmb — this file is the source representation",
        ],
    }


def parse_all_menu_modules() -> list:
    results = []
    for f in sorted(MENUS_DIR.glob("*.sql")):
        results.append(parse_menu_module(f))
    return results


# ─────────────────────────────────────────────────────────────────────────────
# SEQUENCE PARSER
# ─────────────────────────────────────────────────────────────────────────────

def parse_sequences(filepath: Path) -> list:
    content = read_file(filepath)
    sequences = []
    pattern = re.compile(
        r"CREATE\s+SEQUENCE\s+(HRMS\.)?(\w+)\s+START\s+WITH\s+(\d+)\s+INCREMENT\s+BY\s+(\d+)"
        r"(?:\s+(NOCACHE|CACHE\s+\d+))?",
        re.IGNORECASE
    )
    # Also capture inline BUG/NOTE comments above each sequence
    lines = content.splitlines()
    for i, line in enumerate(lines):
        m = pattern.search(line)
        if m:
            name = ("HRMS." + m.group(2)).upper()
            cache_val = m.group(5) or "NOCACHE"
            # Look for comment on previous lines
            comment_lines = []
            for j in range(max(0, i-3), i):
                stripped = lines[j].strip().lstrip("-").strip()
                if stripped and not stripped.startswith("="):
                    comment_lines.append(stripped)
            bug_notes = [l for l in comment_lines if "BUG" in l.upper() or "NOTE" in l.upper()]
            sequences.append({
                "name": name,
                "start_with": int(m.group(3)),
                "increment_by": int(m.group(4)),
                "cache": cache_val.strip(),
                "notes": bug_notes,
            })
    return sequences


# ─────────────────────────────────────────────────────────────────────────────
# SEED DATA PARSER
# ─────────────────────────────────────────────────────────────────────────────

def parse_seed_file(filepath: Path) -> dict:
    content = read_file(filepath)
    tables = {}

    # Extract INSERT INTO statements
    pattern = re.compile(
        r"INSERT\s+INTO\s+(\w+)\s*\(([^)]+)\)\s*\n?\s*VALUES\s*\(([^;]+)\)\s*;",
        re.IGNORECASE | re.DOTALL
    )
    for m in pattern.finditer(content):
        table_name = m.group(1).upper()
        columns_raw = m.group(2)
        values_raw = m.group(3)

        columns = [c.strip() for c in columns_raw.split(",")]

        # Parse values — handle quoted strings, functions, NULLs
        values = []
        current = ""
        depth = 0
        in_quote = False
        for ch in values_raw:
            if ch == "'" and not in_quote:
                in_quote = True
                current += ch
            elif ch == "'" and in_quote:
                in_quote = False
                current += ch
            elif ch == "(" and not in_quote:
                depth += 1
                current += ch
            elif ch == ")" and not in_quote:
                depth -= 1
                current += ch
            elif ch == "," and not in_quote and depth == 0:
                values.append(current.strip().strip("'"))
                current = ""
            else:
                current += ch
        if current.strip():
            values.append(current.strip().strip("'"))

        row = {}
        for i, col in enumerate(columns):
            row[col] = values[i] if i < len(values) else ""

        if table_name not in tables:
            tables[table_name] = {"rows": [], "columns": columns}
        tables[table_name]["rows"].append(row)

    return {
        "file": filepath.name,
        "tables": tables,
        "total_rows": sum(len(t["rows"]) for t in tables.values()),
    }


def parse_all_seed_data() -> list:
    results = []
    for f in sorted(SEED_DIR.glob("*.sql")):
        results.append(parse_seed_file(f))
    return results


# ─────────────────────────────────────────────────────────────────────────────
# DEEP FORMS XML PARSER (fixed)
# ─────────────────────────────────────────────────────────────────────────────

def _infer_form_rules(trigger_name: str, body: str) -> list:
    """Infer implicit business rules from Oracle Forms trigger code patterns."""
    rules = []
    if not body:
        return rules
    # Session/permission checks
    if re.search(r"is_session_valid", body, re.IGNORECASE):
        rules.append(f"{trigger_name}: Session must be valid before form operations are permitted")
    if re.search(r"has_permission", body, re.IGNORECASE):
        perms = re.findall(r"has_permission\([^,]+,\s*'([^']+)',\s*'([^']+)'", body, re.IGNORECASE)
        for module, action in perms:
            rules.append(f"{trigger_name}: Requires {action} permission on {module}")
    # Block property restrictions set at runtime
    if re.search(r"INSERT_ALLOWED.*PROPERTY_FALSE|SET_BLOCK_PROPERTY.*INSERT", body, re.IGNORECASE):
        rules.append(f"{trigger_name}: Insert operations may be disabled based on user permissions")
    if re.search(r"UPDATE_ALLOWED.*PROPERTY_FALSE|SET_BLOCK_PROPERTY.*UPDATE", body, re.IGNORECASE):
        rules.append(f"{trigger_name}: Update operations may be disabled based on user permissions")
    if re.search(r"DELETE_ALLOWED.*PROPERTY_FALSE|SET_BLOCK_PROPERTY.*DELETE", body, re.IGNORECASE):
        rules.append(f"{trigger_name}: Delete operations may be disabled based on user permissions")
    # PKG_VALIDATION calls imply server-side validation
    for m in re.finditer(r"PKG_VALIDATION\.(\w+)", body, re.IGNORECASE):
        rules.append(f"{trigger_name}: Calls PKG_VALIDATION.{m.group(1)} for server-side validation")
    # Commit/rollback logic
    if re.search(r"COMMIT_FORM|ROLLBACK", body, re.IGNORECASE):
        rules.append(f"{trigger_name}: Manages transaction commit/rollback")
    return rules

def deep_parse_form(filepath: Path) -> dict:
    try:
        tree = ET.parse(filepath)
        root = tree.getroot()
    except ET.ParseError as e:
        return {"name": filepath.stem, "file": filepath.name, "error": str(e)}

    form_name = root.attrib.get("Name", filepath.stem)

    # Libraries
    libraries = [el.attrib.get("Name", "") for el in root.findall(".//AttachedLibrary")]

    # Form-level triggers with full body
    form_triggers = []
    for trig in root.findall("Trigger"):
        text_el = trig.find("TriggerText")
        body = text_el.text.strip() if text_el is not None and text_el.text else ""
        form_triggers.append({
            "name": trig.attrib.get("Name", ""),
            "style": trig.attrib.get("TriggerStyle", ""),
            "body": body,
            "pkg_calls": list(set(re.findall(r"(PKG_\w+\.\w+)", body, re.IGNORECASE))),
            "business_rules": extract_inline_comments(body, "BUSINESS"),
            "rules": extract_inline_comments(body, "RULE"),
            "raise_errors": extract_raise_application_errors(body),
        })

    # Blocks with full item detail
    blocks = []
    for block in root.findall(".//Block"):
        block_name = block.attrib.get("Name", "")
        table = block.attrib.get("DMLDataTargetName", "") or block.attrib.get("QueryDataSourceName", "")
        where = block.attrib.get("DefaultWhere", "")
        order = block.attrib.get("OrderByClause", "")
        insert_allowed = block.attrib.get("InsertAllowed", "")
        update_allowed = block.attrib.get("UpdateAllowed", "")
        delete_allowed = block.attrib.get("DeleteAllowed", "")
        query_allowed  = block.attrib.get("QueryAllowed", "")

        items = []
        for item in block.findall(".//Item"):
            i = {
                "name": item.attrib.get("Name", ""),
                "type": item.attrib.get("ItemType", ""),
                "data_type": item.attrib.get("DataType", ""),
                "max_length": item.attrib.get("MaximumLength", ""),
                "required": item.attrib.get("RequiredItem", ""),
                "column": item.attrib.get("ColumnName", ""),
                "canvas": item.attrib.get("CanvasName", ""),
                "tab_page": item.attrib.get("TabPageName", ""),
                "visible": item.attrib.get("Visible", ""),
                "database_item": item.attrib.get("DatabaseItem", ""),
                "primary_key": item.attrib.get("PrimaryKey", ""),
                "lov": item.attrib.get("LOV", ""),
                "insert_allowed": item.attrib.get("InsertAllowed", ""),
                "update_allowed": item.attrib.get("UpdateAllowed", ""),
                "query_allowed": item.attrib.get("QueryAllowed", ""),
            }
            # Remove empty keys
            i = {k: v for k, v in i.items() if v}
            items.append(i)

        block_triggers = []
        for trig in block.findall(".//Trigger"):
            text_el = trig.find("TriggerText")
            body = text_el.text.strip() if text_el is not None and text_el.text else ""
            block_triggers.append({
                "name": trig.attrib.get("Name", ""),
                "body": body,
                "pkg_calls": list(set(re.findall(r"(PKG_\w+\.\w+)", body, re.IGNORECASE))),
                "business_rules": extract_inline_comments(body, "BUSINESS"),
                "rules": extract_inline_comments(body, "RULE"),
                "raise_errors": extract_raise_application_errors(body),
            })

        blocks.append({
            "name": block_name,
            "table": table,
            "default_where": where,
            "order_by": order,
            "insert_allowed": insert_allowed,
            "update_allowed": update_allowed,
            "delete_allowed": delete_allowed,
            "query_allowed": query_allowed,
            "items": items,
            "triggers": block_triggers,
        })

    # LOVs — now also capturing column mappings
    lovs = []
    for lov in root.findall(".//LOV"):
        lov_name = lov.attrib.get("Name", "")
        lov_title = lov.attrib.get("Title", "")
        column_mappings = []
        for cm in lov.findall("ColumnMapping"):
            column_mappings.append({
                "lov_column": cm.attrib.get("LOVColumn", ""),
                "return_item": cm.attrib.get("ReturnItem", ""),
            })
        lovs.append({
            "name": lov_name,
            "title": lov_title,
            "record_group": lov.attrib.get("RecordGroup", ""),
            "column_mappings": column_mappings,
        })

    # Record groups — FIX: use QueryText attribute, not child element
    record_groups = []
    for rg in root.findall(".//RecordGroup"):
        # QueryText is an XML attribute in Oracle Forms XML exports
        query = rg.attrib.get("QueryText", "")
        # Fallback: try child element
        if not query:
            query_el = rg.find("RecordGroupQuery")
            if query_el is not None and query_el.text:
                query = query_el.text.strip()
        # Normalise whitespace
        query = re.sub(r"\s+", " ", query).strip()
        record_groups.append({
            "name": rg.attrib.get("Name", ""),
            "query": query,
            "tables": list(set(re.findall(r"FROM\s+(\w+)", query, re.IGNORECASE))),
        })

    # Relations (master-detail)
    relations = []
    for rel in root.findall(".//Relation"):
        relations.append({
            "name": rel.attrib.get("Name", ""),
            "detail_block": rel.attrib.get("DetailBlock", ""),
            "join_condition": rel.attrib.get("JoinCondition", ""),
            "delete_record": rel.attrib.get("DeleteRecord", ""),
            "deferred": rel.attrib.get("Deferred", ""),
            "automatic_query": rel.attrib.get("AutomaticQuery", ""),
        })

    # Canvases
    canvases = []
    for canvas in root.findall(".//Canvas"):
        canvases.append({
            "name": canvas.attrib.get("Name", ""),
            "type": canvas.attrib.get("CanvasType", ""),
            "width": canvas.attrib.get("Width", ""),
            "height": canvas.attrib.get("Height", ""),
        })

    # Windows
    windows = []
    for win in root.findall(".//Window"):
        windows.append({
            "name": win.attrib.get("Name", ""),
            "title": win.attrib.get("Title", ""),
            "width": win.attrib.get("Width", ""),
            "height": win.attrib.get("Height", ""),
        })

    # Alerts
    alerts = []
    for alert in root.findall(".//Alert"):
        alerts.append({
            "name": alert.attrib.get("Name", ""),
            "title": alert.attrib.get("AlertStyle", ""),
            "message": alert.attrib.get("Message", ""),
        })

    # All package calls and business rules across entire form XML
    full_xml = ET.tostring(root, encoding="unicode")
    all_pkg_calls = list(set(re.findall(r"(PKG_\w+\.\w+)", full_xml, re.IGNORECASE)))

    # Collect business rules from ALL trigger bodies (form + block)
    # Also infer implicit rules from trigger logic patterns
    all_business_rules = []
    all_rules = []
    for trig in form_triggers:
        all_business_rules.extend(trig.get("business_rules", []))
        all_rules.extend(trig.get("rules", []))
        # Infer rules from trigger body logic patterns
        body = trig.get("body", "")
        all_rules.extend(_infer_form_rules(trig["name"], body))
    for block in blocks:
        for trig in block.get("triggers", []):
            all_business_rules.extend(trig.get("business_rules", []))
            all_rules.extend(trig.get("rules", []))
            body = trig.get("body", "")
            all_rules.extend(_infer_form_rules(f"{block['name']}.{trig['name']}", body))

    return {
        "name": form_name,
        "file": filepath.name,
        "title": root.attrib.get("Title", ""),
        "first_block": root.attrib.get("FirstNavigationBlock", ""),
        "menu_module": root.attrib.get("MenuModule", ""),
        "libraries": libraries,
        "form_triggers": form_triggers,
        "blocks": blocks,
        "lovs": lovs,
        "record_groups": record_groups,
        "relations": relations,
        "canvases": canvases,
        "windows": windows,
        "alerts": alerts,
        "all_package_calls": all_pkg_calls,
        "all_business_rules": all_business_rules,
        "all_rules": all_rules,
    }


def deep_parse_all_forms() -> list:
    return [deep_parse_form(f) for f in sorted(FORMS_DIR.glob("*.xml"))]


# ─────────────────────────────────────────────────────────────────────────────
# SCHEMA / DDL DEEP PARSER (fixed: virtual columns, GRADE_LEVEL)
# ─────────────────────────────────────────────────────────────────────────────

def deep_parse_schema() -> dict:
    tables = {}
    for sql_file in sorted((SCHEMA_DIR / "tables").glob("*.sql")):
        content = read_file(sql_file)
        for m in re.finditer(
            r"CREATE\s+TABLE\s+(HRMS\.)?(\w+)\s*\((.*?)\);",
            content, re.DOTALL | re.IGNORECASE
        ):
            tbl_name = ("HRMS." + m.group(2)).upper()
            body = m.group(3)
            columns = []

            # Match regular columns AND virtual/generated columns
            # First pass: extract virtual/generated columns (full line match)
            virtual_cols = {}
            for virt_m in re.finditer(
                r"^\s{2,6}(\w+)\s+(\w[\w\(\),]+)\s+GENERATED\s+ALWAYS\s+AS\s*\(([^)]+)\)\s*VIRTUAL",
                body, re.MULTILINE | re.IGNORECASE
            ):
                virtual_cols[virt_m.group(1).upper()] = virt_m.group(3).strip()

            col_pattern = re.compile(
                r"^\s{2,6}(\w+)\s+([\w\(\),]+(?:\s+\w+)?)",
                re.MULTILINE | re.IGNORECASE
            )
            for col_m in col_pattern.finditer(body):
                col_name = col_m.group(1).upper()
                if col_name.upper() in ("CONSTRAINT", "PRIMARY", "FOREIGN", "UNIQUE", "CHECK",
                                         "GENERATED", "ALWAYS", "VIRTUAL", "DEFAULT"):
                    continue
                col_entry = {
                    "name": col_name,
                    "type": col_m.group(2).strip(),
                }
                if col_name in virtual_cols:
                    col_entry["virtual"] = True
                    col_entry["expression"] = virtual_cols[col_name]
                columns.append(col_entry)

            pks = re.findall(r"CONSTRAINT\s+\w+\s+PRIMARY\s+KEY\s*\(([^)]+)\)", body, re.IGNORECASE)
            fks = re.findall(
                r"CONSTRAINT\s+(\w+)\s+FOREIGN\s+KEY\s*\(([^)]+)\)\s*REFERENCES\s+(HRMS\.)?(\w+)\s*\(([^)]+)\)",
                body, re.IGNORECASE
            )
            checks = re.findall(r"CONSTRAINT\s+\w+\s+CHECK\s*\(([^)]+)\)", body, re.IGNORECASE)

            tables[tbl_name] = {
                "name": tbl_name,
                "file": sql_file.name,
                "columns": columns,
                "primary_keys": [pk.strip() for pks_entry in pks for pk in pks_entry.split(",")],
                "foreign_keys": [
                    {"constraint": fk[0], "columns": fk[1].strip(),
                     "references": ("HRMS." + fk[3]).upper(), "ref_columns": fk[4].strip()}
                    for fk in fks
                ],
                "check_constraints": checks,
            }

    views = {}
    views_file = SCHEMA_DIR / "views" / "hrms_views.sql"
    if views_file.exists():
        content = read_file(views_file)
        for m in re.finditer(
            r"CREATE\s+OR\s+REPLACE\s+VIEW\s+(HRMS\.)?(\w+)\s+AS\s*\n(.*?)(?=CREATE|\Z)",
            content, re.DOTALL | re.IGNORECASE
        ):
            view_name = ("HRMS." + m.group(2)).upper()
            body = m.group(3)
            tables_used = list(set(re.findall(r"FROM\s+(\w+)", body, re.IGNORECASE)))
            joins = list(set(re.findall(r"JOIN\s+(\w+)", body, re.IGNORECASE)))
            views[view_name] = {
                "name": view_name,
                "tables_used": tables_used,
                "joins": joins,
                "query_snippet": body.strip()[:300],
            }

    # Sequences
    seq_file = SCHEMA_DIR / "sequences" / "hrms_sequences.sql"
    sequences = parse_sequences(seq_file) if seq_file.exists() else []

    triggers = {}
    for trig_file in sorted(TRIGGERS_DIR.glob("*.sql")):
        content = read_file(trig_file)
        for m in re.finditer(
            r"CREATE\s+OR\s+REPLACE\s+TRIGGER\s+(?:HRMS\.)?(\w+)\s+"
            r"(BEFORE|AFTER|INSTEAD\s+OF)\s+(\w+(?:\s+OR\s+\w+)*)\s+ON\s+(HRMS\.)?(\w+)",
            content, re.IGNORECASE
        ):
            trig_name = m.group(1).upper()
            timing = m.group(2).upper()
            events = m.group(3).upper()

            # Extract rules per trigger — scope to the trigger body only
            # Find the trigger body start
            body_start = content.find("BEGIN", m.end())
            body = content[body_start:] if body_start != -1 else content[m.end():]

            triggers[trig_name] = {
                "name": trig_name,
                "file": trig_file.name,
                "timing": timing,
                "events": events,
                "table": ("HRMS." + m.group(5)).upper(),
                "business_rules": extract_inline_comments(body, "BUSINESS"),
                "rules": extract_inline_comments(body, "RULE"),
                "bugs": extract_inline_comments(body, "BUG"),
                "pkg_calls": list(set(re.findall(r"(PKG_\w+\.\w+)", body, re.IGNORECASE))),
                "pragma_autonomous": bool(re.search(r"PRAGMA\s+AUTONOMOUS_TRANSACTION", body, re.IGNORECASE)),
                "uses_sys_context": bool(re.search(r"SYS_CONTEXT\s*\(", body, re.IGNORECASE)),
            }

    return {"tables": tables, "views": views, "triggers": triggers, "sequences": sequences}


# ─────────────────────────────────────────────────────────────────────────────
# BUSINESS RULES CONSOLIDATOR
# ─────────────────────────────────────────────────────────────────────────────

def consolidate_business_rules(packages: dict, forms: list, schema: dict,
                                pll_libs: list, seed_data: list) -> list:
    rules = []
    rule_id = 1

    def add(source, source_type, category, text):
        nonlocal rule_id
        rules.append({
            "id": f"BR-{rule_id:04d}",
            "source": source,
            "source_type": source_type,
            "category": category,
            "rule": text,
        })
        rule_id += 1

    # PL/SQL packages
    for pkg_name, pkg in packages.items():
        body = pkg.get("body") or {}
        for r in body.get("business_rules", []):
            add(pkg_name, "plsql_package", "business_rule", r)
        for r in body.get("rules", []):
            add(pkg_name, "plsql_package", "validation_rule", r)
        for r in body.get("constraints", []):
            add(pkg_name, "plsql_package", "constraint", r)
        for r in body.get("bugs", []):
            add(pkg_name, "plsql_package", "known_bug", r)
        for proc in body.get("procedures", []):
            for r in proc.get("business_rules", []):
                add(f"{pkg_name}.{proc['name']}", "plsql_procedure", "business_rule", r)
            for r in proc.get("rules", []):
                add(f"{pkg_name}.{proc['name']}", "plsql_procedure", "validation_rule", r)
            for e in proc.get("raise_errors", []):
                add(f"{pkg_name}.{proc['name']}", "plsql_procedure", "error_rule",
                    f"Error {e['code']}: {e['message']}")

    # Oracle Forms
    for form in forms:
        if "error" in form:
            continue
        for r in form.get("all_business_rules", []):
            add(form["name"], "oracle_form", "business_rule", r)
        for r in form.get("all_rules", []):
            add(form["name"], "oracle_form", "validation_rule", r)
        for block in form.get("blocks", []):
            for trig in block.get("triggers", []):
                for e in trig.get("raise_errors", []):
                    add(f"{form['name']}.{block['name']}.{trig['name']}", "form_trigger", "error_rule",
                        f"Error {e['code']}: {e['message']}")

    # PLL Libraries
    for lib in pll_libs:
        for r in lib.get("all_business_rules", []):
            add(lib["name"], "pll_library", "business_rule", r)
        for r in lib.get("all_rules", []):
            add(lib["name"], "pll_library", "validation_rule", r)
        for r in lib.get("all_bugs", []):
            add(lib["name"], "pll_library", "known_bug", r)
        for proc in lib.get("procedures", []) + lib.get("functions", []):
            for r in proc.get("rules", []):
                add(f"{lib['name']}.{proc['name']}", "pll_procedure", "validation_rule", r)
            for r in proc.get("bugs", []):
                add(f"{lib['name']}.{proc['name']}", "pll_procedure", "known_bug", r)

    # DB Triggers
    for trig_name, trig in schema.get("triggers", {}).items():
        for r in trig.get("business_rules", []):
            add(trig_name, "db_trigger", "business_rule", r)
        for r in trig.get("rules", []):
            add(trig_name, "db_trigger", "validation_rule", r)
        for r in trig.get("bugs", []):
            add(trig_name, "db_trigger", "known_bug", r)

    # DDL check constraints
    for tbl_name, tbl in schema.get("tables", {}).items():
        for chk in tbl.get("check_constraints", []):
            add(tbl_name, "ddl_table", "check_constraint", chk)

    # Sequence bugs/notes
    for seq in schema.get("sequences", []):
        for note in seq.get("notes", []):
            if "BUG" in note.upper():
                add(seq["name"], "sequence", "known_bug", note)

    return rules


# ─────────────────────────────────────────────────────────────────────────────
# REPORT GENERATOR
# ─────────────────────────────────────────────────────────────────────────────

def generate_deep_report(packages, forms, schema, rules, pll_libs, menus, seed_data):
    lines = []
    lines.append("# Oracle Deep Parser Report — HRMS Source Code (v2 Full Coverage)\n")

    total_br  = sum(1 for r in rules if r["category"] == "business_rule")
    total_vr  = sum(1 for r in rules if r["category"] == "validation_rule")
    total_con = sum(1 for r in rules if r["category"] == "constraint")
    total_bug = sum(1 for r in rules if r["category"] == "known_bug")
    total_err = sum(1 for r in rules if r["category"] == "error_rule")
    total_chk = sum(1 for r in rules if r["category"] == "check_constraint")
    total_seed_rows = sum(
        sum(len(t["rows"]) for t in s["tables"].values())
        for s in seed_data
    )

    lines.append("## Summary\n")
    lines.append("| Category | Count |")
    lines.append("|---|---|")
    lines.append(f"| PL/SQL Packages parsed | {len(packages)} |")
    lines.append(f"| Oracle Forms parsed | {len(forms)} |")
    lines.append(f"| PLL Libraries parsed | {len(pll_libs)} |")
    lines.append(f"| Menu Modules parsed | {len(menus)} |")
    lines.append(f"| DDL Tables parsed | {len(schema['tables'])} |")
    lines.append(f"| Views parsed | {len(schema['views'])} |")
    lines.append(f"| DB Triggers parsed | {len(schema['triggers'])} |")
    lines.append(f"| Sequences parsed | {len(schema.get('sequences', []))} |")
    lines.append(f"| Seed data rows | {total_seed_rows} |")
    lines.append(f"| Business rules extracted | {total_br} |")
    lines.append(f"| Validation rules extracted | {total_vr} |")
    lines.append(f"| Constraints extracted | {total_con} |")
    lines.append(f"| Known bugs extracted | {total_bug} |")
    lines.append(f"| Error codes extracted | {total_err} |")
    lines.append(f"| Check constraints extracted | {total_chk} |")
    lines.append(f"| **Total rules** | **{len(rules)}** |\n")

    lines.append("---\n")
    lines.append("## PL/SQL Packages\n")
    for pkg_name, pkg in sorted(packages.items()):
        spec = pkg.get("spec") or {}
        body = pkg.get("body") or {}
        lines.append(f"### {pkg_name}")
        if spec.get("known_issues"):
            lines.append("**Known Issues:**")
            for issue in spec["known_issues"]:
                lines.append(f"- {issue}")
        if spec.get("exceptions"):
            lines.append(f"\n**Exceptions ({len(spec['exceptions'])}):**")
            for e in spec["exceptions"]:
                code_str = f" ({e['code']})" if e.get("code") else ""
                lines.append(f"- `{e['name']}`{code_str}")
        if body.get("pragma_autonomous"):
            lines.append("\n**PRAGMA AUTONOMOUS_TRANSACTION: YES**")
        if body.get("utl_packages_used"):
            lines.append(f"\n**UTL Packages used:** {', '.join(body['utl_packages_used'])}")
        if body.get("business_rules"):
            lines.append(f"\n**Business Rules ({len(body['business_rules'])}):**")
            for r in body["business_rules"]:
                lines.append(f"- {r}")
        if body.get("rules"):
            lines.append(f"\n**Validation Rules ({len(body['rules'])}):**")
            for r in body["rules"]:
                lines.append(f"- {r}")
        sql = body.get("sql", {})
        all_tables = list(set(
            sql.get("selects_from", []) + sql.get("inserts_into", []) +
            sql.get("updates", []) + sql.get("deletes_from", [])
        ))
        if all_tables:
            lines.append(f"\n**Tables accessed ({len(all_tables)}):** {', '.join(sorted(all_tables))}")
        if body.get("sequences_used"):
            lines.append(f"\n**Sequences used:** {', '.join(body['sequences_used'])}")
        lines.append("")

    lines.append("---\n")
    lines.append("## PLL Libraries\n")
    for lib in pll_libs:
        lines.append(f"### {lib['name']}")
        lines.append(f"- Attached by: {lib.get('attached_by', '')}")
        lines.append(f"- Procedures: {len(lib.get('procedures', []))}")
        lines.append(f"- Functions: {len(lib.get('functions', []))}")
        if lib.get("all_rules"):
            lines.append(f"\n**Validation Rules ({len(lib['all_rules'])}):**")
            for r in lib["all_rules"]:
                lines.append(f"- {r}")
        if lib.get("all_bugs"):
            lines.append(f"\n**Known Bugs ({len(lib['all_bugs'])}):**")
            for r in lib["all_bugs"]:
                lines.append(f"- {r}")
        lines.append("")

    lines.append("---\n")
    lines.append("## Menu Module\n")
    for menu in menus:
        lines.append(f"### {menu['name']}")
        lines.append(f"- Menu bar: {menu.get('menu_bar', '')}")
        lines.append(f"- Menus: {', '.join(menu.get('menus', []))}")
        lines.append(f"- Total items: {menu.get('total_items', 0)}")
        lines.append(f"- OPEN_FORM calls: {', '.join(menu.get('open_forms', []))}")
        lines.append(f"- Security calls: {', '.join(menu.get('security_calls', []))}")
        for note in menu.get("notes", []):
            lines.append(f"- NOTE: {note}")
        lines.append("")

    lines.append("---\n")
    lines.append("## Oracle Forms\n")
    for form in forms:
        if "error" in form:
            continue
        lines.append(f"### {form['name']} — {form.get('title', '')}")
        lines.append(f"- Libraries: {', '.join(form.get('libraries', []))}")
        lines.append(f"- Relations: {len(form.get('relations', []))}")
        lines.append(f"- Canvases: {len(form.get('canvases', []))}")
        lines.append(f"- Windows: {len(form.get('windows', []))}")
        lines.append(f"- Alerts: {len(form.get('alerts', []))}")
        if form.get("relations"):
            lines.append("\n**Relations:**")
            for rel in form["relations"]:
                lines.append(f"- `{rel['name']}` → detail block: `{rel['detail_block']}`")
        if form.get("record_groups"):
            lines.append(f"\n**Record Groups / LOV Queries ({len(form['record_groups'])}):**")
            for rg in form["record_groups"]:
                if rg.get("query"):
                    lines.append(f"- `{rg['name']}`: `{rg['query'][:120]}`")
        if form.get("all_business_rules"):
            lines.append(f"\n**Business Rules ({len(form['all_business_rules'])}):**")
            for r in form["all_business_rules"]:
                lines.append(f"- {r}")
        if form.get("all_rules"):
            lines.append(f"\n**Validation Rules ({len(form['all_rules'])}):**")
            for r in form["all_rules"]:
                lines.append(f"- {r}")
        lines.append("")

    lines.append("---\n")
    lines.append("## Sequences\n")
    lines.append(f"Total: {len(schema.get('sequences', []))} sequences\n")
    lines.append("| Name | Start | Increment | Cache |")
    lines.append("|---|---|---|---|")
    for seq in schema.get("sequences", []):
        lines.append(f"| {seq['name']} | {seq['start_with']} | {seq['increment_by']} | {seq['cache']} |")
    lines.append("")

    lines.append("---\n")
    lines.append("## Seed Data\n")
    for s in seed_data:
        lines.append(f"### {s['file']} ({s['total_rows']} rows)")
        for tbl_name, tbl in s["tables"].items():
            lines.append(f"- **{tbl_name}**: {len(tbl['rows'])} rows — columns: {', '.join(tbl['columns'][:8])}")
        lines.append("")

    lines.append("---\n")
    lines.append("## DDL Tables\n")
    for tbl_name, tbl in sorted(schema["tables"].items()):
        lines.append(f"### {tbl_name}")
        lines.append(f"- Columns ({len(tbl['columns'])}): {', '.join(c['name'] for c in tbl['columns'][:15])}")
        if tbl.get("primary_keys"):
            lines.append(f"- Primary Key: {', '.join(tbl['primary_keys'])}")
        for fk in tbl.get("foreign_keys", []):
            lines.append(f"- FK `{fk['columns']}` → `{fk['references']}({fk['ref_columns']})`")
        for chk in tbl.get("check_constraints", []):
            lines.append(f"- CHECK: `{chk}`")
        lines.append("")

    lines.append("---\n")
    lines.append("## Consolidated Business Rules\n")
    lines.append(f"Total: {len(rules)} rules\n")
    lines.append("| ID | Source | Type | Rule |")
    lines.append("|---|---|---|---|")
    for r in rules[:150]:
        rule_text = r["rule"][:120].replace("|", "/")
        lines.append(f"| {r['id']} | {r['source']} | {r['category']} | {rule_text} |")
    if len(rules) > 150:
        lines.append(f"\n*... and {len(rules) - 150} more rules in business_rules.json*")

    return "\n".join(lines)


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────

def main():
    print("Deep parsing PL/SQL packages...")
    packages = deep_parse_all_packages()
    print(f"  Parsed {len(packages)} packages")

    print("Deep parsing Oracle Forms XML...")
    forms = deep_parse_all_forms()
    print(f"  Parsed {len(forms)} forms")

    print("Parsing PLL libraries...")
    pll_libs = parse_all_pll_libraries()
    print(f"  Parsed {len(pll_libs)} libraries")

    print("Parsing menu modules...")
    menus = parse_all_menu_modules()
    print(f"  Parsed {len(menus)} menu modules")

    print("Deep parsing DDL schema + sequences...")
    schema = deep_parse_schema()
    print(f"  Parsed {len(schema['tables'])} tables, {len(schema['views'])} views, "
          f"{len(schema['triggers'])} triggers, {len(schema.get('sequences', []))} sequences")

    print("Parsing seed data...")
    seed_data = parse_all_seed_data()
    total_rows = sum(s["total_rows"] for s in seed_data)
    print(f"  Parsed {total_rows} seed rows across {len(seed_data)} files")

    print("Consolidating business rules...")
    rules = consolidate_business_rules(packages, forms, schema, pll_libs, seed_data)
    print(f"  Extracted {len(rules)} total rules")

    print("Writing output files...")
    (OUTPUT_DIR / "plsql_deep.json").write_text(json.dumps(packages, indent=2), encoding="utf-8")
    (OUTPUT_DIR / "forms_deep.json").write_text(json.dumps(forms, indent=2), encoding="utf-8")
    (OUTPUT_DIR / "pll_deep.json").write_text(json.dumps(pll_libs, indent=2), encoding="utf-8")
    (OUTPUT_DIR / "menu_deep.json").write_text(json.dumps(menus, indent=2), encoding="utf-8")
    (OUTPUT_DIR / "schema_deep.json").write_text(json.dumps(schema, indent=2), encoding="utf-8")
    (OUTPUT_DIR / "seed_deep.json").write_text(json.dumps(seed_data, indent=2), encoding="utf-8")
    (OUTPUT_DIR / "business_rules.json").write_text(json.dumps(rules, indent=2), encoding="utf-8")

    report = generate_deep_report(packages, forms, schema, rules, pll_libs, menus, seed_data)
    (OUTPUT_DIR / "DEEP_REPORT.md").write_text(report, encoding="utf-8")

    print(f"\n=== DONE ===")
    print(f"  Packages:           {len(packages)}")
    print(f"  Forms:              {len(forms)}")
    print(f"  PLL Libraries:      {len(pll_libs)}")
    print(f"  Menu Modules:       {len(menus)}")
    print(f"  Tables:             {len(schema['tables'])}")
    print(f"  Views:              {len(schema['views'])}")
    print(f"  DB Triggers:        {len(schema['triggers'])}")
    print(f"  Sequences:          {len(schema.get('sequences', []))}")
    print(f"  Seed rows:          {total_rows}")
    print(f"  Business rules:     {sum(1 for r in rules if r['category'] == 'business_rule')}")
    print(f"  Validation rules:   {sum(1 for r in rules if r['category'] == 'validation_rule')}")
    print(f"  Known bugs:         {sum(1 for r in rules if r['category'] == 'known_bug')}")
    print(f"  Error codes:        {sum(1 for r in rules if r['category'] == 'error_rule')}")
    print(f"  Check constraints:  {sum(1 for r in rules if r['category'] == 'check_constraint')}")
    print(f"  Total rules:        {len(rules)}")
    print(f"\nOutput files (02_oracle_parser_output/):")
    for f in ["plsql_deep.json", "forms_deep.json", "pll_deep.json", "menu_deep.json",
              "schema_deep.json", "seed_deep.json", "business_rules.json", "DEEP_REPORT.md"]:
        print(f"  {f}")


if __name__ == "__main__":
    main()
