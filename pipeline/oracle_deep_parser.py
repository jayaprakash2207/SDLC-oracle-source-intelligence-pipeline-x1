"""
oracle_deep_parser.py — v4 (source-verified, maximum coverage)
---------------------------------------------------------------
Reads directly from the 42 Oracle HRMS source files.
Every extraction rule verified against actual source code.

Output -> ./output/
  plsql_deep.json, forms_deep.json, pll_deep.json, menu_deep.json,
  schema_deep.json, seed_deep.json, business_rules.json, DEEP_REPORT.md
"""

import re
import json
import xml.etree.ElementTree as ET
from pathlib import Path

SOURCE_DIR   = (Path(__file__).parent.parent
                / "automated-reverse-engineering-pipeline-main"
                / "automated-reverse-engineering-pipeline-main"
                / "source"
                / "ts-plsql-oracle-forms-hrms"
                / "ts-plsql-oracle-forms-hrms-main")

OUTPUT_DIR   = Path(__file__).parent / "parser-output"
PKG_DIR      = SOURCE_DIR / "plsql" / "packages"
FORMS_DIR    = SOURCE_DIR / "forms" / "xml-exports"
LIBS_DIR     = SOURCE_DIR / "forms" / "libraries"
MENUS_DIR    = SOURCE_DIR / "forms" / "menus"
TRIGGERS_DIR = SOURCE_DIR / "plsql" / "triggers"
SCHEMA_DIR   = SOURCE_DIR / "schema"
SEED_DIR     = SOURCE_DIR / "data" / "seed"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# ── SQL keywords that must never appear as table names ────────────────────────
_SQL_NOISE = {
    "A", "AN", "THE", "IN", "IS", "AS", "BY", "ON", "TO", "OF", "OR", "AND",
    "NOT", "IF", "AT", "BE", "DO", "IT", "NO", "SO", "UP", "ALL", "ARE",
    "SET", "GET", "FROM", "INTO", "WHERE", "JOIN", "LEFT", "RIGHT", "INNER",
    "OUTER", "CROSS", "FULL", "SELF", "WITH", "FOR", "NEW", "OLD", "NULL",
    "TRUE", "FALSE", "THEN", "ELSE", "WHEN", "CASE", "END", "BEGIN", "LOOP",
    "EXIT", "NEXT", "RETURN", "SELECT", "INSERT", "UPDATE", "DELETE",
    "CREATE", "ALTER", "DROP", "TABLE", "INDEX", "VIEW", "TRIGGER",
    "PROCEDURE", "FUNCTION", "PACKAGE", "BODY", "CURSOR", "TYPE", "RECORD",
    "EXCEPTION", "PRAGMA", "RAISE", "COMMIT", "ROLLBACK", "FETCH",
    "OPEN", "CLOSE", "EXECUTE", "IMMEDIATE", "USING", "INTO", "BULK",
    "COLLECT", "FORALL", "PIPE", "ROW", "ROWNUM", "ROWID", "SYSDATE",
    "USER", "DUAL", "SYSTIMESTAMP", "MUST", "AFFECTS", "FAILED",
    "DEPARTMENT", "AFFECT", "THE", "HAS", "HAVE",
    "UPDATING", "INSERTING", "DELETING", "BEFORE", "AFTER",
    "EACH", "STATEMENT", "REFERENCING", "DECLARE", "CONSTANT",
    "VARCHAR2", "NUMBER", "DATE", "CHAR", "CLOB", "BLOB", "RAW",
    "P_DATE", "V_SQL", "V_COUNT", "V_RESULT",
}


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def read_file(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")

def extract_inline_comments(content: str, tag: str) -> list:
    pattern = re.compile(r"--\s*" + re.escape(tag) + r":?\s*(.+)", re.IGNORECASE)
    return [m.group(1).strip() for m in pattern.finditer(content)]

def extract_all_tagged_comments(content: str) -> list:
    """Extract every tagged comment: BUSINESS, RULE, CONSTRAINT, BUG, VALIDATION, NOTE."""
    results = []
    for tag in ("BUSINESS", "RULE", "CONSTRAINT", "BUG", "VALIDATION", "NOTE"):
        for m in re.finditer(r"--\s*" + tag + r":?\s*(.+)", content, re.IGNORECASE):
            results.append({"tag": tag, "text": m.group(1).strip()})
    return results

def extract_raise_application_errors(content: str) -> list:
    results = []
    seen = set()
    # Single-line string literal messages (no newlines in message)
    for m in re.finditer(
        r"RAISE_APPLICATION_ERROR\s*\(\s*(-\d+)\s*,\s*'([^'\n]+)'",
        content, re.IGNORECASE
    ):
        code = m.group(1)
        msg = m.group(2).strip()
        if code not in seen:
            results.append({"code": code, "message": msg})
            seen.add(code)
    # Concatenated: 'static text ' || :NEW.xxx  or  || v_xxx
    for m in re.finditer(
        r"RAISE_APPLICATION_ERROR\s*\(\s*(-\d+)\s*,\s*'([^'\n]*)'\s*\|\|",
        content, re.IGNORECASE
    ):
        code = m.group(1)
        msg = m.group(2).strip() + " [+dynamic]"
        if code not in seen:
            results.append({"code": code, "message": msg})
            seen.add(code)
    # Multi-line: error code on one line, message on next line(s) indented
    for m in re.finditer(
        r"RAISE_APPLICATION_ERROR\s*\(\s*(-\d+)\s*,\s*\n\s*'([^'\n]+)'",
        content, re.IGNORECASE
    ):
        code = m.group(1)
        msg = m.group(2).strip()
        if code not in seen:
            results.append({"code": code, "message": msg})
            seen.add(code)
    return results

def extract_sql_tables(content: str) -> dict:
    def clean(matches):
        result = set()
        for schema, name in matches:
            n = name.upper().strip()
            if n in _SQL_NOISE or len(n) < 3 or n.startswith("V_") or n.startswith("P_") or n.startswith("C_") or n.startswith("L_"):
                continue
            result.add(("HRMS." + n) if schema else n)
        return sorted(result)
    return {
        "selects_from": clean(re.findall(r"\bFROM\s+(HRMS\.)?(\w+)\b", content, re.IGNORECASE)),
        "inserts_into": clean(re.findall(r"\bINSERT\s+INTO\s+(HRMS\.)?(\w+)\b", content, re.IGNORECASE)),
        "updates":      clean(re.findall(r"\bUPDATE\s+(HRMS\.)?(\w+)\b(?!\s+SET\s+\()", content, re.IGNORECASE)),
        "deletes_from": clean(re.findall(r"\bDELETE\s+FROM\s+(HRMS\.)?(\w+)\b", content, re.IGNORECASE)),
        "joins":        clean(re.findall(r"\bJOIN\s+(HRMS\.)?(\w+)\b", content, re.IGNORECASE)),
    }

def extract_constants(content: str) -> list:
    results = []
    seen = set()
    # CONSTANT declarations (any type incl VARCHAR2, NUMBER, RAW)
    for m in re.finditer(
        r"(\w+)\s+CONSTANT\s+([\w\(\)]+)\s*:=\s*([^;]+);",
        content, re.IGNORECASE
    ):
        name = m.group(1).strip()
        if name.upper() in _SQL_NOISE or name in seen:
            continue
        # Strip trailing comment
        val = re.sub(r"--.*$", "", m.group(3), flags=re.MULTILINE).strip()
        results.append({"name": name, "type": m.group(2).strip(), "value": val, "meaning": ""})
        seen.add(name)
    # RAW variable declarations (not CONSTANT keyword but behaves like one — e.g. c_encryption_key)
    for m in re.finditer(
        r"(\bc_\w+)\s+(RAW\s*\(\s*\d+\s*\))\s*:=\s*([^;]+);",
        content, re.IGNORECASE
    ):
        name = m.group(1).strip()
        if name in seen:
            continue
        val = re.sub(r"--.*$", "", m.group(3), flags=re.MULTILINE).strip()
        note = ""
        # Check if there's a VULNERABILITY comment before this line
        pos = m.start()
        preceding = content[max(0, pos-200):pos]
        vuln = re.search(r"--\s*(VULNERABILITY[^\n]*)", preceding)
        if vuln:
            note = vuln.group(1).strip()
        results.append({"name": name, "type": m.group(2).strip(), "value": val, "meaning": note})
        seen.add(name)
    return results

def infer_behavioral_rules(proc_name: str, body: str) -> list:
    rules = []
    if not body:
        return rules
    if re.search(r"PRAGMA\s+AUTONOMOUS_TRANSACTION", body, re.IGNORECASE):
        rules.append(f"{proc_name}: Runs in autonomous transaction — committed independently of caller")
    if re.search(r"SYS_CONTEXT\s*\(\s*'USERENV'\s*,\s*'IP_ADDRESS'", body, re.IGNORECASE):
        rules.append(f"{proc_name}: Captures client IP via SYS_CONTEXT('USERENV','IP_ADDRESS')")
    if re.search(r"SYS_CONTEXT\s*\(\s*'USERENV'\s*,\s*'SESSIONID'", body, re.IGNORECASE):
        rules.append(f"{proc_name}: Captures Oracle session ID via SYS_CONTEXT('USERENV','SESSIONID')")
    if re.search(r"EXCEPTION\s+WHEN\s+OTHERS\s+THEN\s*\n\s*(?:--|ROLLBACK|NULL\s*;)", body, re.IGNORECASE):
        rules.append(f"{proc_name}: WHEN OTHERS THEN NULL/ROLLBACK — exceptions silently swallowed")
    if re.search(r"v_sql\s*:=\s*v_sql\s*\|\|.*p_\w+", body, re.IGNORECASE):
        rules.append(f"{proc_name}: BUG — dynamic SQL built by concatenating user input (p_last_name etc.) — SQL injection risk")
    if re.search(r"UTL_FILE\.FOPEN.*'W'", body, re.IGNORECASE):
        fn = re.search(r"v_filename\s*:=\s*'([^']+)'", body, re.IGNORECASE)
        rules.append(f"{proc_name}: Writes file via UTL_FILE" + (f" (pattern: {fn.group(1)})" if fn else ""))
    if re.search(r"UTL_FILE\.FOPEN.*'R'|UTL_FILE\.GET_LINE", body, re.IGNORECASE):
        rules.append(f"{proc_name}: Reads file line-by-line via UTL_FILE")
    if re.search(r"UTL_SMTP\.", body, re.IGNORECASE):
        rules.append(f"{proc_name}: Sends email via UTL_SMTP (NOT UTL_MAIL)")
    # Stub detection — only when body is truly empty
    body_code = re.sub(r"--[^\n]*", "", body).strip()
    meaningful = [l.strip() for l in body_code.splitlines()
                  if l.strip() and l.strip() not in ("BEGIN", "END;", "/")]
    if re.search(r"Placeholder\s+for\s+\w+", body, re.IGNORECASE) and len(meaningful) <= 3:
        rules.append(f"{proc_name}: STUB — placeholder body, not yet implemented")
    if re.search(r"LEGACY.*[Ff]ixed.width|ADP.*vendor|fixed.width.*ADP", body, re.IGNORECASE):
        rules.append(f"{proc_name}: LEGACY fixed-width format for ADP vendor")
    if re.search(r"'H\|'|'T\|'", body, re.IGNORECASE):
        rules.append(f"{proc_name}: Pipe-delimited output — H| header row and T| trailer row")
    if re.search(r"EARNING.*debit|debit.*EARNING|credit.*DEDUCTION|DEDUCTION.*credit", body, re.IGNORECASE):
        rules.append(f"{proc_name}: GL: EARNING elements = debit; non-EARNING elements = credit")
    if re.search(r"FOR UPDATE", body, re.IGNORECASE):
        rules.append(f"{proc_name}: Uses SELECT FOR UPDATE to lock rows during processing")
    if re.search(r"STATUS\s*:=\s*'CALCULATING'", body, re.IGNORECASE):
        rules.append(f"{proc_name}: Sets STATUS='CALCULATING' at start before computing payroll")
    # Format mask extraction
    for fmt in re.findall(r"TO_CHAR\s*\([^,]+,\s*'([^']+)'", body, re.IGNORECASE):
        if any(c in fmt for c in ("Y", "M", "D", "H", "S", "9", "0", "$", "F")):
            rules.append(f"{proc_name}: Uses format mask '{fmt}'")
    # VARCHAR2 buffer sizes
    for m in re.finditer(r"(\w+)\s+VARCHAR2\s*\((\d+)\)", body, re.IGNORECASE):
        name, size = m.group(1), m.group(2)
        if name.lower().startswith(("v_", "l_")) and int(size) >= 60:
            rules.append(f"{proc_name}: Buffer {name} capped at VARCHAR2({size})")
    # NVL fallback
    if re.search(r"NVL\s*\(\s*:GLOBAL\.current_user\s*,\s*USER\s*\)", body, re.IGNORECASE):
        rules.append(f"{proc_name}: Falls back to DB USER when :GLOBAL.current_user not set")
    # Default retention
    for m in re.finditer(r"DEFAULT\s+(\d+).*?(?:days|purge|retain|keep)", body, re.IGNORECASE):
        rules.append(f"{proc_name}: Default retention {m.group(1)} days")
    return rules

def _parse_params(params_raw: str) -> list:
    """Parse parameter list — returns list of {name, direction, type} dicts.
    Strips inline comments before parsing. Handles IN/OUT/IN OUT directions."""
    cleaned = re.sub(r"--[^\n]*", "", params_raw)
    params = []
    for p in cleaned.split(","):
        p = p.strip()
        if not p:
            continue
        # Match:  param_name  [IN|OUT|IN OUT]  type  [DEFAULT ...]
        m = re.match(
            r"(\w+)\s+(IN\s+OUT|IN|OUT)\s+([\w%()]+)",
            p, re.IGNORECASE
        )
        if m:
            params.append({
                "name": m.group(1),
                "direction": re.sub(r"\s+", " ", m.group(2).upper()),
                "type": m.group(3).upper(),
            })
        else:
            # No direction keyword — just capture name
            tok = p.split()[0].strip()
            if tok and re.match(r"^\w+$", tok):
                params.append({"name": tok, "direction": "IN", "type": ""})
    return params


# ─────────────────────────────────────────────────────────────────────────────
# DEEP PL/SQL PARSER
# ─────────────────────────────────────────────────────────────────────────────

def deep_parse_pkb(filepath: Path) -> dict:
    content = read_file(filepath)
    pkg_match = re.search(r"CREATE\s+OR\s+REPLACE\s+PACKAGE\s+BODY\s+(\S+)\s+AS", content, re.IGNORECASE)
    pkg_name = pkg_match.group(1) if pkg_match else filepath.stem

    pkg_rules = []
    if re.search(r"PRAGMA\s+AUTONOMOUS_TRANSACTION", content, re.IGNORECASE):
        pkg_rules.append("Package uses PRAGMA AUTONOMOUS_TRANSACTION — writes independent of caller")
    if re.search(r"SYS_CONTEXT.*IP_ADDRESS", content, re.IGNORECASE):
        pkg_rules.append("Captures client IP via SYS_CONTEXT for audit trail")
    if re.search(r"SYS_CONTEXT.*SESSIONID", content, re.IGNORECASE):
        pkg_rules.append("Captures Oracle session ID via SYS_CONTEXT for audit trail")
    utl_pkgs = list(set(re.findall(r"(UTL_\w+)\.", content, re.IGNORECASE)))
    if any(u.upper() == "UTL_SMTP" for u in utl_pkgs):
        pkg_rules.append("Email delivery uses UTL_SMTP (NOT UTL_MAIL)")
    if any(u.upper() == "UTL_FILE" for u in utl_pkgs):
        pkg_rules.append("File I/O uses UTL_FILE with Oracle directory objects")
    if re.search(r"Hard.coded|should be in SYSTEM_PARAMETERS", content, re.IGNORECASE):
        pkg_rules.append("Contains hard-coded config values that should be in SYSTEM_PARAMETERS")

    pkg_bugs = extract_inline_comments(content, "BUG")
    if re.search(r"EXCEPTION\s+WHEN\s+OTHERS\s+THEN\s*\n\s*(?:ROLLBACK\s*;?\s*\n\s*)?(?:NULL|--)", content, re.IGNORECASE):
        pkg_bugs.append("Exception swallowing: WHEN OTHERS THEN ROLLBACK/NULL — errors silently suppressed")

    # Per-procedure extraction
    procedures = _extract_proc_bodies(content)

    return {
        "name": pkg_name,
        "file": filepath.name,
        "constants": extract_constants(content),
        "business_rules": extract_inline_comments(content, "BUSINESS"),
        "rules": extract_inline_comments(content, "RULE") + pkg_rules,
        "validation_notes": extract_inline_comments(content, "VALIDATION"),
        "constraints": extract_inline_comments(content, "CONSTRAINT"),
        "bugs": pkg_bugs,
        "raise_errors": extract_raise_application_errors(content),
        "sql": extract_sql_tables(content),
        "procedures": procedures,
        "package_calls": list(set(re.findall(r"(PKG_\w+)\.\w+", content, re.IGNORECASE))),
        "sequences_used": list(set(re.findall(r"(SEQ_\w+)\.NEXTVAL", content, re.IGNORECASE))),
        "pragma_autonomous": bool(re.search(r"PRAGMA\s+AUTONOMOUS_TRANSACTION", content, re.IGNORECASE)),
        "uses_sys_context": bool(re.search(r"SYS_CONTEXT\s*\(", content, re.IGNORECASE)),
        "utl_packages_used": utl_pkgs,
        "dbms_packages_used": list(set(re.findall(r"(DBMS_\w+)\.", content, re.IGNORECASE))),
    }


def _extract_proc_bodies(content: str) -> list:
    results = []
    # Find all PROCEDURE/FUNCTION start positions
    header_re = re.compile(
        r"(?m)^    (?:PROCEDURE|FUNCTION)\s+(\w+)\s*",
        re.IGNORECASE
    )
    positions = list(header_re.finditer(content))
    for i, m in enumerate(positions):
        name = m.group(1)
        start = m.start()
        end = positions[i+1].start() if i+1 < len(positions) else len(content)
        body = content[start:end]

        rules = extract_inline_comments(body, "RULE") + infer_behavioral_rules(name, body)
        results.append({
            "name": name,
            "business_rules": extract_inline_comments(body, "BUSINESS"),
            "rules": rules,
            "validation_notes": extract_inline_comments(body, "VALIDATION"),
            "bugs": extract_inline_comments(body, "BUG"),
            "raise_errors": extract_raise_application_errors(body),
            "sql": extract_sql_tables(body),
            "package_calls": list(set(re.findall(r"(PKG_\w+)\.\w+", body, re.IGNORECASE))),
            "if_conditions": re.findall(r"IF\s+(.+?)\s+THEN", body, re.IGNORECASE)[:8],
        })
    return results


def deep_parse_pks(filepath: Path) -> dict:
    content = read_file(filepath)
    pkg_match = re.search(r"CREATE\s+OR\s+REPLACE\s+PACKAGE\s+(\S+)\s+AS", content, re.IGNORECASE)
    pkg_name = pkg_match.group(1) if pkg_match else filepath.stem

    def _extract_param_block(text: str, start: int) -> str:
        """Extract balanced parentheses content starting from first '(' at or after start."""
        idx = text.find("(", start)
        if idx == -1:
            return ""
        depth, buf = 0, []
        for ch in text[idx:]:
            if ch == "(":
                depth += 1
                if depth > 1:
                    buf.append(ch)
            elif ch == ")":
                depth -= 1
                if depth == 0:
                    break
                buf.append(ch)
            else:
                buf.append(ch)
        return "".join(buf)

    procedures = []
    for m in re.finditer(r"PROCEDURE\s+(\w+)\s*", content, re.IGNORECASE):
        name = m.group(1)
        after = content[m.end():]
        # Has parameters?
        next_tok = after.lstrip()
        if next_tok.startswith("("):
            params_raw = _extract_param_block(content, m.end())
            params = _parse_params(params_raw)
        else:
            params = []
        procedures.append({"name": name, "params": params})

    functions = []
    for m in re.finditer(r"FUNCTION\s+(\w+)\s*", content, re.IGNORECASE):
        name = m.group(1)
        after = content[m.end():]
        next_tok = after.lstrip()
        if next_tok.startswith("("):
            params_raw = _extract_param_block(content, m.end())
            params = _parse_params(params_raw)
        else:
            params = []
        ret_m = re.search(r"\bRETURN\s+(\w+)", after[:400], re.IGNORECASE)
        returns = ret_m.group(1) if ret_m else ""
        functions.append({"name": name, "params": params, "returns": returns})

    # Exceptions with PRAGMA codes
    pragma_map = {}
    for pm in re.finditer(
        r"PRAGMA\s+EXCEPTION_INIT\s*\(\s*(e_\w+)\s*,\s*(-\d+)\s*\)",
        content, re.IGNORECASE
    ):
        pragma_map[pm.group(1).lower()] = pm.group(2)
    exceptions = []
    seen_exc = set()
    for m in re.finditer(r"(e_\w+)\s+EXCEPTION\s*;", content, re.IGNORECASE):
        name = m.group(1)
        if name.lower() not in seen_exc:
            exceptions.append({"name": name, "code": pragma_map.get(name.lower())})
            seen_exc.add(name.lower())

    types = [{"name": m.group(1), "kind": m.group(2)}
             for m in re.finditer(r"TYPE\s+(\w+)\s+IS\s+(\w+)", content, re.IGNORECASE)]

    deps_m = re.search(r"Dependencies:\s*(.+)", content)
    callers_m = re.search(r"Called by:\s*(.+)", content)
    issues_lines = []
    issues_block = re.search(r"Known issues:(.*?)(?=\n--\s*={5,}|\Z)", content, re.DOTALL)
    if issues_block:
        for line in issues_block.group(1).splitlines():
            line = line.strip().lstrip("-").strip()
            if line:
                issues_lines.append(line)

    globals_vars = []
    for m in re.finditer(
        r"^\s+(g_\w+)\s+(VARCHAR2|NUMBER|BOOLEAN|DATE|PLS_INTEGER)[\w\(\),\s]*(?::=\s*([^;]+))?;",
        content, re.MULTILINE | re.IGNORECASE
    ):
        globals_vars.append({
            "name": m.group(1),
            "type": m.group(2),
            "default": m.group(3).strip() if m.group(3) else None,
        })

    return {
        "name": pkg_name,
        "file": filepath.name,
        "procedures": procedures,
        "functions": functions,
        "exceptions": exceptions,
        "types": types,
        "global_variables": globals_vars,
        "noted_libraries": list(set(re.findall(r"(UTL_\w+|DBMS_\w+)", content, re.IGNORECASE))),
        "dependencies": [d.strip() for d in deps_m.group(1).split(",")] if deps_m else [],
        "callers": [c.strip() for c in callers_m.group(1).split(",")] if callers_m else [],
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

    sub_re = re.compile(
        r"^(?:PROCEDURE|FUNCTION)\s+(\w+)\s*(?:\(([^)]*)\))?\s*(?:RETURN\s+(\w+))?\s+IS",
        re.MULTILINE | re.IGNORECASE
    )
    sub_matches = list(sub_re.finditer(content))

    procedures = []
    functions = []
    for i, m in enumerate(sub_matches):
        name = m.group(1)
        params = _parse_params(m.group(2) or "")
        returns = m.group(3)
        body_start = m.end()
        body_end = sub_matches[i+1].start() if i+1 < len(sub_matches) else len(content)
        body = content[body_start:body_end]

        # Extract format masks used in this procedure
        format_masks = list(set(re.findall(r"TO_CHAR\s*\([^,]+,\s*'([^']+)'", body, re.IGNORECASE)))
        # Extract built-in Forms calls
        forms_calls = list(set(re.findall(
            r"\b(COMMIT_FORM|EXIT_FORM|CLEAR_FORM|CLEAR_RECORD|ENTER_QUERY|EXECUTE_QUERY|"
            r"FIRST_RECORD|LAST_RECORD|NEXT_RECORD|PREVIOUS_RECORD|CREATE_RECORD|"
            r"DELETE_RECORD|DUPLICATE_RECORD|GO_BLOCK|NEXT_BLOCK|PREVIOUS_BLOCK|"
            r"SET_BLOCK_PROPERTY|SET_ITEM_PROPERTY|MESSAGE|RAISE|SHOW_ALERT|"
            r"FORM_TRIGGER_FAILURE)\b",
            body, re.IGNORECASE
        )))
        # Buffer size caps
        buffer_caps = {}
        for bm in re.finditer(r"(\w+)\s+VARCHAR2\s*\(\s*(\d+)\s*\)", body, re.IGNORECASE):
            bname, bsize = bm.group(1), int(bm.group(2))
            if bname.lower().startswith(("v_", "l_")) and bsize >= 30:
                buffer_caps[bname] = bsize
        # NVL fallback detection
        nvl_fallback = bool(re.search(r"NVL\s*\(\s*:GLOBAL\.", body, re.IGNORECASE))
        # Exception handling details
        exc_details = []
        for em in re.finditer(r"WHEN\s+(\w+)\s+THEN\s+([^\n]+)", body, re.IGNORECASE):
            exc_details.append(f"{em.group(1)}: {em.group(2).strip()}")

        entry = {
            "name": name,
            "params": params,
            "business_rules": extract_inline_comments(body, "BUSINESS"),
            "rules": extract_inline_comments(body, "RULE") + infer_behavioral_rules(name, body),
            "bugs": extract_inline_comments(body, "BUG"),
            "pkg_calls": list(set(re.findall(r"(PKG_\w+\.\w+)", body, re.IGNORECASE))),
            "forms_calls": forms_calls,
            "format_masks": format_masks,
            "buffer_caps": buffer_caps,
            "nvl_fallback": nvl_fallback,
            "exception_handling": exc_details,
        }
        if returns:
            entry["returns"] = returns
            functions.append(entry)
        else:
            procedures.append(entry)

    deps_m = re.search(r"Dependencies:\s*(.+)", content)
    attached_m = re.search(r"Attached by:\s*(.+)", content)

    return {
        "name": lib_name,
        "file": filepath.name,
        "dependencies": [d.strip() for d in deps_m.group(1).split(",")] if deps_m else [],
        "attached_by": attached_m.group(1).strip() if attached_m else "",
        "procedures": procedures,
        "functions": functions,
        "all_business_rules": extract_inline_comments(content, "BUSINESS"),
        "all_rules": extract_inline_comments(content, "RULE"),
        "all_validation_notes": extract_inline_comments(content, "VALIDATION"),
        "all_bugs": extract_inline_comments(content, "BUG"),
        "pkg_calls": list(set(re.findall(r"(PKG_\w+\.\w+)", content, re.IGNORECASE))),
    }


def parse_all_pll_libraries() -> list:
    return [parse_pll_library(f) for f in sorted(LIBS_DIR.glob("*.sql"))]


# ─────────────────────────────────────────────────────────────────────────────
# MENU MODULE PARSER — full tree extraction
# ─────────────────────────────────────────────────────────────────────────────

def parse_menu_module(filepath: Path) -> dict:
    content = read_file(filepath)

    # The menu tree is encoded in SQL comment lines (-- prefix).
    # Strip the leading "-- " from each line before parsing.
    stripped_lines = []
    for raw in content.splitlines():
        # Remove leading "--" comment marker but preserve the rest of the line
        stripped = re.sub(r"^--\s?", "", raw)
        stripped_lines.append(stripped)
    tree_text = "\n".join(stripped_lines)

    menus = {}
    current_menu = None
    for line in stripped_lines:
        # Top-level menu header: "  ├── File" or "  └── File"  (no parentheses = no action)
        top_m = re.match(r"^\s+[├└]──\s+(\w[\w\s&]+?)\s*$", line)
        if top_m:
            current_menu = top_m.group(1).strip()
            menus[current_menu] = []
            continue
        # Menu item with action: "  │   ├── Save   (COMMIT_FORM)"
        # Also handles nested parens: (OPEN_FORM('HRMS_EMPLOYEE'))
        item_m = re.match(r"^\s*[│ ]*[├└]──\s+(.+?)\s{2,}\((.+)\)\s*$", line)
        if item_m and current_menu is not None:
            item_label = item_m.group(1).strip()
            item_action = item_m.group(2).strip()
            if item_label and not item_label.startswith("─"):  # ─
                if re.match(r"^requires\s+\w+\s+permission$", item_action, re.IGNORECASE):
                    perm = re.match(r"requires\s+(\w+)\s+permission", item_action, re.IGNORECASE)
                    menus[current_menu].append({
                        "label": item_label,
                        "action": f"requires {perm.group(1).upper()} permission",
                    })
                else:
                    menus[current_menu].append({"label": item_label, "action": item_action})
            continue
        # Separator lines are skipped implicitly (start with ─)

    all_items = [item for items in menus.values() for item in items]
    open_forms = list(set(re.findall(r"OPEN_FORM\s*\(\s*['\"]([^'\"]+)['\"]\s*\)", content, re.IGNORECASE)))
    show_windows = list(set(re.findall(r"SHOW_WINDOW\s*\(\s*['\"]([^'\"]+)['\"]\s*\)", content, re.IGNORECASE)))
    show_alerts = list(set(re.findall(r"SHOW_ALERT\s*\(\s*['\"]([^'\"]+)['\"]\s*\)", content, re.IGNORECASE)))
    web_docs = list(set(re.findall(r"WEB\.SHOW_DOCUMENT\s*\(\s*['\"]([^'\"]+)['\"]\s*\)", content, re.IGNORECASE)))
    security_calls = list(set(re.findall(r"(PKG_SECURITY\.\w+)", content, re.IGNORECASE)))
    perm_requirements = re.findall(r"requires\s+(\w+)\s+permission", content, re.IGNORECASE)

    return {
        "name": "HRMS_MENU",
        "file": filepath.name,
        "menu_bar": "MAIN_MENUBAR",
        "menus": menus,
        "total_menus": len(menus),
        "total_items": len(all_items),
        "all_items": all_items,
        "open_forms": open_forms,
        "show_windows": show_windows,
        "show_alerts": show_alerts,
        "web_documents": web_docs,
        "permission_requirements": list(set(perm_requirements)),
        "security_calls": security_calls,
        "notes": [
            "Menu items enabled/disabled at runtime via PKG_SECURITY.has_permission() in WHEN-NEW-FORM-INSTANCE",
            "Compiled binary: HRMS_MENU.mmb — this .sql file is the source representation",
        ],
    }


def parse_all_menu_modules() -> list:
    return [parse_menu_module(f) for f in sorted(MENUS_DIR.glob("*.sql"))]


# ─────────────────────────────────────────────────────────────────────────────
# SEQUENCE PARSER
# ─────────────────────────────────────────────────────────────────────────────

def parse_sequences(filepath: Path) -> list:
    content = read_file(filepath)
    sequences = []
    lines = content.splitlines()
    pattern = re.compile(
        r"CREATE\s+SEQUENCE\s+(HRMS\.)?(\w+)\s+START\s+WITH\s+(\d+)"
        r"\s+INCREMENT\s+BY\s+(\d+)(?:\s+(NOCACHE|CACHE\s+\d+))?",
        re.IGNORECASE
    )
    for i, line in enumerate(lines):
        m = pattern.search(line)
        if m:
            name = ("HRMS." + m.group(2)).upper()
            cache = m.group(5).strip() if m.group(5) else "NOCACHE"
            # Grab comments from up to 4 preceding lines
            notes = []
            for j in range(max(0, i-4), i):
                s = lines[j].strip().lstrip("-").strip()
                if s and not s.startswith("=") and not s.startswith("CREATE"):
                    notes.append(s)
            sequences.append({
                "name": name,
                "start_with": int(m.group(3)),
                "increment_by": int(m.group(4)),
                "cache": cache,
                "notes": notes,
            })
    return sequences


# ─────────────────────────────────────────────────────────────────────────────
# SEED DATA PARSER
# ─────────────────────────────────────────────────────────────────────────────

def parse_seed_file(filepath: Path) -> dict:
    content = read_file(filepath)
    tables = {}

    # UPDATE statements
    updates = []
    for m in re.finditer(
        r"UPDATE\s+(\w+)\s+SET\s+(.+?)\s+WHERE\s+(.+?)\s*;",
        content, re.IGNORECASE | re.DOTALL
    ):
        updates.append({
            "table": m.group(1).upper(),
            "set": re.sub(r"\s+", " ", m.group(2).strip()),
            "where": re.sub(r"\s+", " ", m.group(3).strip()),
        })

    # INSERT statements
    for m in re.finditer(
        r"INSERT\s+INTO\s+(\w+)\s*\(([^)]+)\)\s*\n?\s*VALUES\s*\(([^;]+)\)\s*;",
        content, re.IGNORECASE | re.DOTALL
    ):
        table_name = m.group(1).upper()
        columns = [c.strip() for c in m.group(2).split(",")]
        values_raw = m.group(3)

        # Parse values — handle quotes, nested parens
        values, current, depth, in_q = [], "", 0, False
        for ch in values_raw:
            if ch == "'" and not in_q:
                in_q = True; current += ch
            elif ch == "'" and in_q:
                in_q = False; current += ch
            elif ch == "(" and not in_q:
                depth += 1; current += ch
            elif ch == ")" and not in_q:
                depth -= 1; current += ch
            elif ch == "," and not in_q and depth == 0:
                values.append(current.strip().strip("'")); current = ""
            else:
                current += ch
        if current.strip():
            values.append(current.strip().strip("'"))

        row = {columns[i]: (values[i] if i < len(values) else "") for i in range(len(columns))}
        if table_name not in tables:
            tables[table_name] = {"rows": [], "columns": columns}
        tables[table_name]["rows"].append(row)

    return {
        "file": filepath.name,
        "tables": tables,
        "updates": updates,
        "total_rows": sum(len(t["rows"]) for t in tables.values()),
        "total_updates": len(updates),
    }


def parse_all_seed_data() -> list:
    return [parse_seed_file(f) for f in sorted(SEED_DIR.glob("*.sql"))]


# ─────────────────────────────────────────────────────────────────────────────
# ORACLE FORMS XML PARSER — full extraction
# ─────────────────────────────────────────────────────────────────────────────

def _infer_form_rules(trigger_name: str, body: str) -> list:
    rules = []
    if not body:
        return rules
    if re.search(r"is_session_valid", body, re.IGNORECASE):
        rules.append(f"{trigger_name}: Session must be valid before form operations permitted")
    if re.search(r"has_permission", body, re.IGNORECASE):
        for module, action in re.findall(
            r"has_permission\([^,]+,\s*'([^']+)',\s*'([^']+)'", body, re.IGNORECASE
        ):
            rules.append(f"{trigger_name}: Requires {action} permission on {module}")
    if re.search(r"INSERT_ALLOWED.*PROPERTY_FALSE|SET_BLOCK_PROPERTY.*INSERT", body, re.IGNORECASE):
        rules.append(f"{trigger_name}: Insert operations may be disabled by permissions at runtime")
    if re.search(r"UPDATE_ALLOWED.*PROPERTY_FALSE|SET_BLOCK_PROPERTY.*UPDATE", body, re.IGNORECASE):
        rules.append(f"{trigger_name}: Update operations may be disabled by permissions at runtime")
    if re.search(r"DELETE_ALLOWED.*PROPERTY_FALSE|SET_BLOCK_PROPERTY.*DELETE", body, re.IGNORECASE):
        rules.append(f"{trigger_name}: Delete operations may be disabled by permissions at runtime")
    for call in re.finditer(r"PKG_VALIDATION\.(\w+)", body, re.IGNORECASE):
        rules.append(f"{trigger_name}: Server-side validation via PKG_VALIDATION.{call.group(1)}")
    if re.search(r"COMMIT_FORM", body, re.IGNORECASE):
        rules.append(f"{trigger_name}: Issues COMMIT_FORM to persist changes")
    return rules


def deep_parse_form(filepath: Path) -> dict:
    try:
        tree = ET.parse(filepath)
        root = tree.getroot()
    except ET.ParseError as e:
        return {"name": filepath.stem, "file": filepath.name, "error": str(e)}

    form_name = root.attrib.get("Name", filepath.stem)
    libraries = [el.attrib.get("Name", "") for el in root.findall(".//AttachedLibrary")]

    # Form-level triggers
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

    # Canvases with Tab Pages
    canvases = []
    for canvas in root.findall(".//Canvas"):
        tab_pages = []
        for tp in canvas.findall("TabPage"):
            tab_pages.append({
                "name": tp.attrib.get("Name", ""),
                "label": tp.attrib.get("Label", ""),
            })
        canvases.append({
            "name": canvas.attrib.get("Name", ""),
            "type": canvas.attrib.get("CanvasType", ""),
            "width": canvas.attrib.get("Width", ""),
            "height": canvas.attrib.get("Height", ""),
            "tab_pages": tab_pages,
        })

    # Blocks
    blocks = []
    for block in root.findall(".//Block"):
        block_name = block.attrib.get("Name", "")
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
                "format_mask": item.attrib.get("FormatMask", ""),  # e.g. MM/DD/YYYY, $999,999,990.00
            }
            # Poplist values
            list_els = item.findall("ListItemElement")
            if list_els:
                i["poplist_values"] = [
                    {"label": el.attrib.get("Label", ""), "value": el.attrib.get("Value", "")}
                    for el in list_els
                ]
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
            "table": block.attrib.get("DMLDataTargetName", "") or block.attrib.get("QueryDataSourceName", ""),
            "default_where": block.attrib.get("DefaultWhere", ""),
            "order_by": block.attrib.get("OrderByClause", ""),
            "records_displayed": block.attrib.get("RecordsDisplayed", ""),
            "insert_allowed": block.attrib.get("InsertAllowed", ""),
            "update_allowed": block.attrib.get("UpdateAllowed", ""),
            "delete_allowed": block.attrib.get("DeleteAllowed", ""),
            "query_allowed": block.attrib.get("QueryAllowed", ""),
            "items": items,
            "triggers": block_triggers,
        })

    # LOVs
    lovs = []
    for lov in root.findall(".//LOV"):
        col_maps = [
            {"lov_column": cm.attrib.get("LOVColumn", ""), "return_item": cm.attrib.get("ReturnItem", "")}
            for cm in lov.findall("ColumnMapping")
        ]
        lovs.append({
            "name": lov.attrib.get("Name", ""),
            "title": lov.attrib.get("Title", ""),
            "record_group": lov.attrib.get("RecordGroup", ""),
            "column_mappings": col_maps,
        })

    # Record groups — QueryText is an XML attribute
    record_groups = []
    for rg in root.findall(".//RecordGroup"):
        query = rg.attrib.get("QueryText", "")
        if not query:
            qel = rg.find("RecordGroupQuery")
            if qel is not None and qel.text:
                query = qel.text.strip()
        query = re.sub(r"\s+", " ", query).strip()
        record_groups.append({
            "name": rg.attrib.get("Name", ""),
            "query": query,
            "tables": list(set(re.findall(r"FROM\s+(\w+)", query, re.IGNORECASE))),
        })

    # Relations
    relations = []
    for rel in root.findall(".//Relation"):
        relations.append({
            "name": rel.attrib.get("Name", ""),
            "detail_block": rel.attrib.get("DetailBlock", ""),
            "join_condition": rel.attrib.get("JoinCondition", ""),
            "delete_record_behavior": rel.attrib.get("DeleteRecordBehavior", ""),
            "auto_query": rel.attrib.get("AutoQuery", ""),
            "deferred": rel.attrib.get("Deferred", ""),
        })

    # Windows
    windows = [
        {"name": w.attrib.get("Name", ""), "title": w.attrib.get("Title", ""),
         "width": w.attrib.get("Width", ""), "height": w.attrib.get("Height", "")}
        for w in root.findall(".//Window")
    ]

    # Alerts — including button labels
    alerts = []
    for alert in root.findall(".//Alert"):
        alerts.append({
            "name": alert.attrib.get("Name", ""),
            "style": alert.attrib.get("AlertStyle", ""),
            "title": alert.attrib.get("Title", ""),
            "message": alert.attrib.get("Message", ""),
            "button1": alert.attrib.get("Button1Label", ""),
            "button2": alert.attrib.get("Button2Label", ""),
            "button3": alert.attrib.get("Button3Label", ""),
        })

    full_xml = ET.tostring(root, encoding="unicode")
    all_pkg_calls = list(set(re.findall(r"(PKG_\w+\.\w+)", full_xml, re.IGNORECASE)))

    all_business_rules, all_rules = [], []
    for trig in form_triggers:
        all_business_rules.extend(trig.get("business_rules", []))
        all_rules.extend(trig.get("rules", []))
        all_rules.extend(_infer_form_rules(trig["name"], trig.get("body", "")))
    for block in blocks:
        for trig in block.get("triggers", []):
            all_business_rules.extend(trig.get("business_rules", []))
            all_rules.extend(trig.get("rules", []))
            all_rules.extend(_infer_form_rules(f"{block['name']}.{trig['name']}", trig.get("body", "")))

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
# SCHEMA / DDL PARSER — line-by-line column extraction (fixes merge bug)
# ─────────────────────────────────────────────────────────────────────────────

# Known Oracle column type keywords to positively identify column lines
_COL_TYPES = re.compile(
    r"^(NUMBER|VARCHAR2|CHAR|DATE|TIMESTAMP|CLOB|BLOB|RAW|INTEGER|FLOAT|"
    r"PLS_INTEGER|BINARY_INTEGER|LONG|NVARCHAR2|NCHAR|INTERVAL)\b",
    re.IGNORECASE
)
_CONSTRAINT_KEYWORDS = {"CONSTRAINT", "PRIMARY", "FOREIGN", "UNIQUE", "CHECK",
                        "GENERATED", "ALWAYS", "VIRTUAL", "TABLESPACE"}


def _parse_ddl_columns(body: str) -> tuple:
    """
    Parse column definitions from a CREATE TABLE body.
    Returns (columns_list, pk_list, fk_list, uk_list, check_list).
    Line-by-line to avoid cross-line type merging.
    """
    columns = []
    pks, fks, uks, checks = [], [], [], []
    seen_names = set()

    # First pass: collect virtual column expressions
    virtual_cols = {}
    for vm in re.finditer(
        r"(\w+)\s+\w[\w\(\),]+\s+GENERATED\s+ALWAYS\s+AS\s*\(([^)]+)\)\s*VIRTUAL",
        body, re.IGNORECASE | re.MULTILINE
    ):
        virtual_cols[vm.group(1).upper()] = vm.group(2).strip()

    for line in body.splitlines():
        stripped = line.strip().rstrip(",")
        if not stripped or stripped.startswith("--"):
            continue

        upper = stripped.upper()
        first_word = upper.split()[0] if upper.split() else ""

        # Constraint lines
        if first_word == "CONSTRAINT":
            # PRIMARY KEY
            pk_m = re.search(r"PRIMARY\s+KEY\s*\(([^)]+)\)", stripped, re.IGNORECASE)
            if pk_m:
                pks.extend([c.strip() for c in pk_m.group(1).split(",")])
            # UNIQUE
            uk_m = re.search(r"UNIQUE\s*\(([^)]+)\)", stripped, re.IGNORECASE)
            if uk_m:
                name_m = re.match(r"CONSTRAINT\s+(\w+)", stripped, re.IGNORECASE)
                uks.append({
                    "name": name_m.group(1) if name_m else "",
                    "columns": [c.strip() for c in uk_m.group(1).split(",")],
                })
            # FOREIGN KEY
            fk_m = re.search(
                r"CONSTRAINT\s+(\w+)\s+FOREIGN\s+KEY\s*\(([^)]+)\)"
                r"\s+REFERENCES\s+(HRMS\.)?(\w+)\s*\(([^)]+)\)",
                stripped, re.IGNORECASE
            )
            if fk_m:
                fks.append({
                    "constraint": fk_m.group(1),
                    "columns": fk_m.group(2).strip(),
                    "references": ("HRMS." + fk_m.group(4)).upper(),
                    "ref_columns": fk_m.group(5).strip(),
                })
            # CHECK
            chk_m = re.search(r"CHECK\s*\((.+)\)", stripped, re.IGNORECASE)
            if chk_m:
                checks.append(chk_m.group(1).strip())
            continue

        # Skip lines that are clearly not column definitions
        if first_word in _CONSTRAINT_KEYWORDS:
            continue
        if first_word in (")", "(", "/"):
            continue
        # Multi-line CHECK constraint continuation (starts with quote or keyword)
        if re.match(r"^['\(]", stripped) or upper.startswith("CHECK"):
            continue

        # Try to match: COLUMN_NAME  TYPE_SPEC  [DEFAULT ...] [NOT NULL]
        col_m = re.match(
            r"^(\w+)\s+(NUMBER|VARCHAR2|CHAR|DATE|TIMESTAMP|CLOB|BLOB|RAW|"
            r"INTEGER|FLOAT|PLS_INTEGER|NVARCHAR2|NCHAR|LONG)\s*(?:\([^)]*\))?",
            stripped, re.IGNORECASE
        )
        if not col_m:
            continue

        col_name = col_m.group(1).upper()
        if col_name in _CONSTRAINT_KEYWORDS or col_name in seen_names:
            continue
        seen_names.add(col_name)

        # Extract type — just the type token + size, nothing after
        type_m = re.match(
            r"\w+\s+((NUMBER|VARCHAR2|CHAR|DATE|TIMESTAMP|CLOB|BLOB|RAW|"
            r"INTEGER|FLOAT|PLS_INTEGER|NVARCHAR2|NCHAR|LONG)\s*(?:\([^)]*\))?)",
            stripped, re.IGNORECASE
        )
        col_type = type_m.group(1).strip() if type_m else col_m.group(2).strip()

        # DEFAULT value
        default_m = re.search(r"\bDEFAULT\s+(SYSDATE|'[^']*'|[YN]|[0-9]+(?:\.[0-9]+)?)\b",
                               stripped, re.IGNORECASE)
        default_val = default_m.group(1) if default_m else None

        not_null = bool(re.search(r"\bNOT\s+NULL\b", stripped, re.IGNORECASE))

        col_entry = {"name": col_name, "type": col_type}
        if default_val:
            col_entry["default"] = default_val
        if not_null:
            col_entry["not_null"] = True
        if col_name in virtual_cols:
            col_entry["virtual"] = True
            col_entry["expression"] = virtual_cols[col_name]

        columns.append(col_entry)

    return columns, pks, fks, uks, checks


def deep_parse_schema() -> dict:
    tables = {}
    for sql_file in sorted((SCHEMA_DIR / "tables").glob("*.sql")):
        content = read_file(sql_file)
        for m in re.finditer(
            r"CREATE\s+TABLE\s+(HRMS\.)?(\w+)\s*\((.*?)\)\s*;",
            content, re.DOTALL | re.IGNORECASE
        ):
            tbl_name = ("HRMS." + m.group(2)).upper()
            body = m.group(3)
            columns, pks, fks, uks, checks = _parse_ddl_columns(body)
            tables[tbl_name] = {
                "name": tbl_name,
                "file": sql_file.name,
                "columns": columns,
                "primary_keys": pks,
                "foreign_keys": fks,
                "unique_constraints": uks,
                "check_constraints": checks,
            }

    views = {}
    views_file = SCHEMA_DIR / "views" / "hrms_views.sql"
    if views_file.exists():
        content = read_file(views_file)
        # Split on CREATE boundaries so greedy match captures each full view body
        view_blocks = re.split(r"(?=CREATE\s+OR\s+REPLACE\s+VIEW)", content, flags=re.IGNORECASE)
        for block in view_blocks:
            m_dummy = re.match(
                r"CREATE\s+OR\s+REPLACE\s+VIEW\s+(HRMS\.)?(\w+)\s+AS\s*\n(.*)",
                block, re.DOTALL | re.IGNORECASE
            )
            if not m_dummy:
                continue
            m = m_dummy
            view_name = ("HRMS." + m.group(2)).upper()
            body = m.group(3)
            # Filter noise from FROM/JOIN captures
            raw_from = re.findall(r"\bFROM\s+((?:HRMS\.)?(\w+))", body, re.IGNORECASE)
            raw_join = re.findall(r"\bJOIN\s+((?:HRMS\.)?(\w+))", body, re.IGNORECASE)
            tbl_noise = {"DUAL","WHERE","ON","AND","OR","SELECT","WITH","AS"}
            tables_used = sorted({t[1].upper() for t in raw_from if t[1].upper() not in tbl_noise})
            joins_used  = sorted({t[1].upper() for t in raw_join if t[1].upper() not in tbl_noise})
            views[view_name] = {
                "name": view_name,
                "tables_used": tables_used,
                "joins": joins_used,
                "query_snippet": body.strip()[:800],
                "full_query": body.strip(),
            }

    seq_file = SCHEMA_DIR / "sequences" / "hrms_sequences.sql"
    sequences = parse_sequences(seq_file) if seq_file.exists() else []

    triggers = {}
    for trig_file in sorted(TRIGGERS_DIR.glob("*.sql")):
        content = read_file(trig_file)
        trig_hdr = re.compile(
            r"CREATE\s+OR\s+REPLACE\s+TRIGGER\s+(?:HRMS\.)?(\w+)\s+"
            r"(BEFORE|AFTER|INSTEAD\s+OF)\s+([\w\s,]+?)\s+ON\s+(HRMS\.)?(\w+)",
            re.IGNORECASE
        )
        matches = list(trig_hdr.finditer(content))
        for i, m in enumerate(matches):
            trig_name = m.group(1).upper()
            body_start = m.end()
            body_end = matches[i+1].start() if i+1 < len(matches) else len(content)
            body = content[body_start:body_end]

            # Capture comments immediately before CREATE statement
            pre_lines = content[:m.start()].splitlines()
            header_lines = []
            for line in reversed(pre_lines):
                s = line.strip()
                if re.match(r"END\s+\w+\s*;|^/\s*$|^\s*BEGIN\b", s, re.IGNORECASE):
                    break
                if s.startswith("--") or s == "":
                    if s.startswith("--"):
                        header_lines.append(line)
                else:
                    break
            header_comment = "\n".join(reversed(header_lines))
            combined = header_comment + "\n" + body

            # Audit JSON patterns from trigger body
            audit_patterns = []
            for aj in re.finditer(r"'\{[^}]+\}'|\'\{.*?\}\'", body):
                p = aj.group(0).strip("'")
                if len(p) > 5:
                    audit_patterns.append(p)

            triggers[trig_name] = {
                "name": trig_name,
                "file": trig_file.name,
                "timing": m.group(2).upper(),
                "events": m.group(3).strip().upper(),
                "table": ("HRMS." + m.group(5)).upper(),
                "business_rules": extract_inline_comments(combined, "BUSINESS"),
                "rules": extract_inline_comments(combined, "RULE"),
                "validation_notes": extract_inline_comments(combined, "VALIDATION"),
                "bugs": extract_inline_comments(combined, "BUG"),
                "raise_errors": extract_raise_application_errors(body),
                "pkg_calls": list(set(re.findall(r"(PKG_\w+\.\w+)", body, re.IGNORECASE))),
                "pragma_autonomous": bool(re.search(r"PRAGMA\s+AUTONOMOUS_TRANSACTION", body, re.IGNORECASE)),
                "uses_sys_context": bool(re.search(r"SYS_CONTEXT\s*\(", body, re.IGNORECASE)),
                "audit_json_patterns": audit_patterns,
                "sql": extract_sql_tables(body),
            }

    return {"tables": tables, "views": views, "triggers": triggers, "sequences": sequences}


# ─────────────────────────────────────────────────────────────────────────────
# BUSINESS RULES CONSOLIDATOR
# ─────────────────────────────────────────────────────────────────────────────

def consolidate_business_rules(packages, forms, schema, pll_libs, seed_data) -> list:
    rules = []
    rule_id = 1

    def add(source, source_type, category, text):
        nonlocal rule_id
        rules.append({"id": f"BR-{rule_id:04d}", "source": source,
                      "source_type": source_type, "category": category, "rule": text})
        rule_id += 1

    for pkg_name, pkg in packages.items():
        body = pkg.get("body") or {}
        for r in body.get("business_rules", []):
            add(pkg_name, "plsql_package", "business_rule", r)
        for r in body.get("rules", []):
            add(pkg_name, "plsql_package", "validation_rule", r)
        for r in body.get("validation_notes", []):
            add(pkg_name, "plsql_package", "validation_note", r)
        for r in body.get("constraints", []):
            add(pkg_name, "plsql_package", "constraint", r)
        for r in body.get("bugs", []):
            add(pkg_name, "plsql_package", "known_bug", r)
        for proc in body.get("procedures", []):
            for r in proc.get("business_rules", []):
                add(f"{pkg_name}.{proc['name']}", "plsql_procedure", "business_rule", r)
            for r in proc.get("rules", []):
                add(f"{pkg_name}.{proc['name']}", "plsql_procedure", "validation_rule", r)
            for r in proc.get("validation_notes", []):
                add(f"{pkg_name}.{proc['name']}", "plsql_procedure", "validation_note", r)
            for e in proc.get("raise_errors", []):
                add(f"{pkg_name}.{proc['name']}", "plsql_procedure", "error_rule",
                    f"Error {e['code']}: {e['message']}")

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

    for lib in pll_libs:
        for r in lib.get("all_business_rules", []):
            add(lib["name"], "pll_library", "business_rule", r)
        for r in lib.get("all_rules", []):
            add(lib["name"], "pll_library", "validation_rule", r)
        for r in lib.get("all_validation_notes", []):
            add(lib["name"], "pll_library", "validation_note", r)
        for r in lib.get("all_bugs", []):
            add(lib["name"], "pll_library", "known_bug", r)
        for proc in lib.get("procedures", []) + lib.get("functions", []):
            for r in proc.get("rules", []):
                add(f"{lib['name']}.{proc['name']}", "pll_procedure", "validation_rule", r)
            for r in proc.get("bugs", []):
                add(f"{lib['name']}.{proc['name']}", "pll_procedure", "known_bug", r)

    for trig_name, trig in schema.get("triggers", {}).items():
        for r in trig.get("business_rules", []):
            add(trig_name, "db_trigger", "business_rule", r)
        for r in trig.get("rules", []):
            add(trig_name, "db_trigger", "validation_rule", r)
        for r in trig.get("validation_notes", []):
            add(trig_name, "db_trigger", "validation_note", r)
        for r in trig.get("bugs", []):
            add(trig_name, "db_trigger", "known_bug", r)
        for e in trig.get("raise_errors", []):
            add(trig_name, "db_trigger", "error_rule", f"Error {e['code']}: {e['message']}")

    for tbl_name, tbl in schema.get("tables", {}).items():
        for chk in tbl.get("check_constraints", []):
            add(tbl_name, "ddl_table", "check_constraint", chk)
        for uk in tbl.get("unique_constraints", []):
            add(tbl_name, "ddl_table", "unique_constraint",
                f"UNIQUE({', '.join(uk['columns'])}) — constraint: {uk['name']}")

    for seq in schema.get("sequences", []):
        for note in seq.get("notes", []):
            if "BUG" in note.upper():
                add(seq["name"], "sequence", "known_bug", note)

    return rules


# ─────────────────────────────────────────────────────────────────────────────
# REPORT GENERATOR
# ─────────────────────────────────────────────────────────────────────────────

def generate_deep_report(packages, forms, schema, rules, pll_libs, menus, seed_data):
    lines = ["# Oracle Deep Parser Report — HRMS Source Code\n"]

    total_seed = sum(sum(len(t["rows"]) for t in s["tables"].values()) for s in seed_data)

    lines += ["## Summary\n", "| Category | Count |", "|---|---|",
              f"| PL/SQL Packages | {len(packages)} |",
              f"| Oracle Forms | {len(forms)} |",
              f"| PLL Libraries | {len(pll_libs)} |",
              f"| Menu Modules | {len(menus)} |",
              f"| DDL Tables | {len(schema['tables'])} |",
              f"| Views | {len(schema['views'])} |",
              f"| DB Triggers | {len(schema['triggers'])} |",
              f"| Sequences | {len(schema.get('sequences', []))} |",
              f"| Seed rows | {total_seed} |",
              f"| Business rules | {sum(1 for r in rules if r['category']=='business_rule')} |",
              f"| Validation rules | {sum(1 for r in rules if r['category']=='validation_rule')} |",
              f"| Error codes | {sum(1 for r in rules if r['category']=='error_rule')} |",
              f"| Check constraints | {sum(1 for r in rules if r['category']=='check_constraint')} |",
              f"| Unique constraints | {sum(1 for r in rules if r['category']=='unique_constraint')} |",
              f"| Known bugs | {sum(1 for r in rules if r['category']=='known_bug')} |",
              f"| **Total rules** | **{len(rules)}** |\n",
              "---\n"]

    lines.append("## PL/SQL Packages\n")
    for pkg_name, pkg in sorted(packages.items()):
        spec = pkg.get("spec") or {}
        body = pkg.get("body") or {}
        lines.append(f"### {pkg_name}")
        if spec.get("known_issues"):
            lines += ["**Known Issues:**"] + [f"- {i}" for i in spec["known_issues"]]
        if spec.get("exceptions"):
            lines.append(f"\n**Exceptions ({len(spec['exceptions'])}):**")
            for e in spec["exceptions"]:
                lines.append(f"- `{e['name']}`" + (f" ({e['code']})" if e.get("code") else ""))
        if body.get("constants"):
            lines.append(f"\n**Constants ({len(body['constants'])}):**")
            for c in body["constants"][:10]:
                note = f" — {c['meaning']}" if c.get("meaning") else ""
                lines.append(f"- `{c['name']}` = {c['value']}{note}")
        if body.get("pragma_autonomous"):
            lines.append("\n**PRAGMA AUTONOMOUS_TRANSACTION: YES**")
        if body.get("utl_packages_used"):
            lines.append(f"\n**UTL Packages:** {', '.join(body['utl_packages_used'])}")
        if body.get("dbms_packages_used"):
            lines.append(f"\n**DBMS Packages:** {', '.join(body['dbms_packages_used'])}")
        if body.get("business_rules"):
            lines += [f"\n**Business Rules ({len(body['business_rules'])}):**"] + [f"- {r}" for r in body["business_rules"]]
        if body.get("rules"):
            lines += [f"\n**Validation Rules ({len(body['rules'])}):**"] + [f"- {r}" for r in body["rules"]]
        lines.append("")

    lines.append("---\n## PLL Libraries\n")
    for lib in pll_libs:
        lines.append(f"### {lib['name']}")
        lines.append(f"- Procedures: {len(lib.get('procedures', []))}, Functions: {len(lib.get('functions', []))}")
        for proc in lib.get("procedures", []) + lib.get("functions", []):
            detail = []
            if proc.get("forms_calls"):
                detail.append(f"calls: {', '.join(proc['forms_calls'][:3])}")
            if proc.get("format_masks"):
                detail.append(f"masks: {', '.join(proc['format_masks'][:2])}")
            if proc.get("buffer_caps"):
                caps = ", ".join(f"{k}=VARCHAR2({v})" for k, v in proc["buffer_caps"].items())
                detail.append(f"buffers: {caps}")
            if detail:
                lines.append(f"  - `{proc['name']}`: {'; '.join(detail)}")
        lines.append("")

    lines.append("---\n## Menu Modules\n")
    for menu in menus:
        lines.append(f"### {menu['name']} — {menu.get('total_menus', 0)} menus, {menu.get('total_items', 0)} items")
        for menu_name, items in menu.get("menus", {}).items():
            lines.append(f"\n**{menu_name}** ({len(items)} items):")
            for item in items:
                lines.append(f"  - {item['label']}: `{item['action']}`")
        lines.append(f"\n- OPEN_FORM targets: {', '.join(menu.get('open_forms', []))}")
        lines.append(f"- Security calls: {', '.join(menu.get('security_calls', []))}")
        lines.append("")

    lines.append("---\n## Oracle Forms\n")
    for form in forms:
        if "error" in form:
            continue
        lines.append(f"### {form['name']} — {form.get('title', '')}")
        lines.append(f"- Libraries: {', '.join(form.get('libraries', []))}")
        if form.get("canvases"):
            for canvas in form["canvases"]:
                if canvas.get("tab_pages"):
                    tps = ", ".join(f"{t['name']} ({t['label']})" for t in canvas["tab_pages"])
                    lines.append(f"- Canvas `{canvas['name']}` tab pages: {tps}")
        if form.get("relations"):
            lines += ["\n**Relations:**"] + [
                f"- `{r['name']}` → `{r['detail_block']}` (delete: {r.get('delete_record_behavior','')}, auto_query: {r.get('auto_query','')})"
                for r in form["relations"]
            ]
        if form.get("alerts"):
            lines += ["\n**Alerts:**"] + [
                f"- `{a['name']}` [{a.get('style','')}]: \"{a.get('message','')}\" Buttons: {a.get('button1','')} / {a.get('button2','')} / {a.get('button3','')}"
                for a in form["alerts"] if a.get("name")
            ]
        if form.get("record_groups"):
            lines.append(f"\n**LOV Queries ({len(form['record_groups'])}):**")
            for rg in form["record_groups"]:
                if rg.get("query"):
                    lines.append(f"- `{rg['name']}`: `{rg['query'][:150]}`")
        lines.append("")

    lines.append("---\n## Sequences\n")
    lines += ["| Name | Start | Inc | Cache |", "|---|---|---|---|"]
    for seq in schema.get("sequences", []):
        lines.append(f"| {seq['name']} | {seq['start_with']} | {seq['increment_by']} | {seq['cache']} |")

    lines.append("\n---\n## DDL Tables\n")
    for tbl_name, tbl in sorted(schema["tables"].items()):
        lines.append(f"### {tbl_name}")
        lines.append(f"- Columns ({len(tbl['columns'])}): " +
                     ", ".join(f"{c['name']}({c['type']})" + (" DEFAULT " + c.get("default", "") if c.get("default") else "") + (" [VIRTUAL]" if c.get("virtual") else "")
                               for c in tbl["columns"][:12]))
        if tbl.get("primary_keys"):
            lines.append(f"- PK: {', '.join(tbl['primary_keys'])}")
        for fk in tbl.get("foreign_keys", []):
            lines.append(f"- FK `{fk['columns']}` → `{fk['references']}({fk['ref_columns']})`")
        for uk in tbl.get("unique_constraints", []):
            lines.append(f"- UNIQUE({', '.join(uk['columns'])}) [{uk['name']}]")
        for chk in tbl.get("check_constraints", []):
            lines.append(f"- CHECK: `{chk}`")
        lines.append("")

    lines.append("---\n## Triggers\n")
    for trig_name, trig in sorted(schema["triggers"].items()):
        lines.append(f"### {trig_name} — {trig['timing']} {trig['events']} ON {trig['table']}")
        if trig.get("raise_errors"):
            for e in trig["raise_errors"]:
                lines.append(f"- Error {e['code']}: {e['message']}")
        if trig.get("rules"):
            for r in trig["rules"]:
                lines.append(f"- RULE: {r}")
        lines.append("")

    lines.append("---\n## Seed Data\n")
    for s in seed_data:
        lines.append(f"### {s['file']} — {s['total_rows']} rows")
        for tbl_name, tbl in s["tables"].items():
            lines.append(f"- **{tbl_name}**: {len(tbl['rows'])} rows")

    lines.append("\n---\n## Business Rules (first 200)\n")
    lines += ["| ID | Source | Category | Rule |", "|---|---|---|---|"]
    for r in rules[:200]:
        rule_text = r["rule"][:110].replace("|", "/")
        lines.append(f"| {r['id']} | {r['source']} | {r['category']} | {rule_text} |")
    if len(rules) > 200:
        lines.append(f"\n*... and {len(rules)-200} more in business_rules.json*")

    return "\n".join(lines)


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────

def main():
    print(f"Source: {SOURCE_DIR}")
    print(f"Output: {OUTPUT_DIR}\n")

    print("Parsing PL/SQL packages...")
    packages = deep_parse_all_packages()
    print(f"  {len(packages)} packages")

    print("Parsing Oracle Forms XML...")
    forms = deep_parse_all_forms()
    print(f"  {len(forms)} forms")

    print("Parsing PLL libraries...")
    pll_libs = parse_all_pll_libraries()
    print(f"  {len(pll_libs)} libraries")

    print("Parsing menu modules...")
    menus = parse_all_menu_modules()
    print(f"  {len(menus)} menus")

    print("Parsing DDL schema + sequences...")
    schema = deep_parse_schema()
    seq_count = len(schema.get("sequences", []))
    print(f"  {len(schema['tables'])} tables, {len(schema['views'])} views, "
          f"{len(schema['triggers'])} triggers, {seq_count} sequences")

    print("Parsing seed data...")
    seed_data = parse_all_seed_data()
    total_rows = sum(s["total_rows"] for s in seed_data)
    print(f"  {total_rows} rows across {len(seed_data)} files")

    print("Consolidating business rules...")
    rules = consolidate_business_rules(packages, forms, schema, pll_libs, seed_data)
    print(f"  {len(rules)} total rules")

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
    cats = {}
    for r in rules:
        cats[r["category"]] = cats.get(r["category"], 0) + 1
    for cat, cnt in sorted(cats.items(), key=lambda x: -x[1]):
        print(f"  {cat}: {cnt}")
    print(f"  TOTAL: {len(rules)}")
    print(f"\nOutput: {OUTPUT_DIR}")

if __name__ == "__main__":
    main()
