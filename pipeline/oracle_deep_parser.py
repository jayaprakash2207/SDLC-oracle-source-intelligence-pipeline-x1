"""
oracle_deep_parser.py
---------------------
Deep extraction of Oracle PL/SQL package bodies and Oracle Forms XML.
Extracts:
  - Business rules (-- BUSINESS: / -- RULE: comments)
  - Constraints (-- CONSTRAINT: comments)
  - Known bugs (-- BUG: comments)
  - Constants with their meaning
  - Per-procedure: parameters, SQL statements, exception handlers, table refs
  - Validation logic (IF conditions + RAISE_APPLICATION_ERROR calls)
  - Cross-package call graph (which proc calls which pkg.proc)
  - Oracle Forms: every block, item, trigger body, LOV, validation
  - Oracle Forms: full trigger PL/SQL body text extracted

Output:
  graphify-out/deep/plsql_deep.json       — full deep PL/SQL extraction
  graphify-out/deep/forms_deep.json       — full deep Forms extraction
  graphify-out/deep/business_rules.json   — all business rules consolidated
  graphify-out/deep/DEEP_REPORT.md        — human-readable full report
"""

import re
import json
import xml.etree.ElementTree as ET
from pathlib import Path

SOURCE_DIR   = Path(__file__).parent.parent / "source"
OUTPUT_DIR   = Path(__file__).parent.parent / "output" / "graphify-out" / "deep"
PKG_DIR      = SOURCE_DIR / "plsql" / "packages"
FORMS_DIR    = SOURCE_DIR / "forms" / "xml-exports"
TRIGGERS_DIR = SOURCE_DIR / "plsql" / "triggers"
SCHEMA_DIR   = SOURCE_DIR / "schema"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def read_file(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def extract_inline_comments(content: str, tag: str) -> list:
    """Extract -- TAG: comment lines from PL/SQL source."""
    pattern = re.compile(r"--\s*" + re.escape(tag) + r":?\s*(.+)", re.IGNORECASE)
    return [m.group(1).strip() for m in pattern.finditer(content)]


def extract_constants(content: str) -> list:
    """Extract CONSTANT declarations with their comment explanation."""
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
    # Also catch constants without preceding comment
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
    """Extract all RAISE_APPLICATION_ERROR calls with error code and message."""
    pattern = re.compile(
        r"RAISE_APPLICATION_ERROR\s*\(\s*(-\d+)\s*,\s*'([^']+)'",
        re.IGNORECASE
    )
    return [{"code": m.group(1), "message": m.group(2)} for m in pattern.finditer(content)]


def extract_sql_statements(content: str) -> dict:
    """Extract SELECT/INSERT/UPDATE/DELETE operations with target tables."""
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


def extract_procedure_bodies(content: str) -> list:
    """Extract each procedure/function with its full body."""
    results = []
    # Match PROCEDURE or FUNCTION name followed by body
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

        results.append({
            "name": name,
            "business_rules": business_rules,
            "rules": rules,
            "bugs": bugs,
            "raise_errors": raises,
            "sql": sql,
            "package_calls": pkg_calls,
            "if_conditions": if_conditions[:10],  # cap at 10
        })
    return results


# ─────────────────────────────────────────────────────────────────────────────
# DEEP PL/SQL PARSER
# ─────────────────────────────────────────────────────────────────────────────

def deep_parse_pkb(filepath: Path) -> dict:
    content = read_file(filepath)
    pkg_match = re.search(r"CREATE\s+OR\s+REPLACE\s+PACKAGE\s+BODY\s+(\S+)\s+AS", content, re.IGNORECASE)
    pkg_name = pkg_match.group(1) if pkg_match else filepath.stem

    return {
        "name": pkg_name,
        "file": filepath.name,
        "constants": extract_constants(content),
        "business_rules": extract_inline_comments(content, "BUSINESS"),
        "rules": extract_inline_comments(content, "RULE"),
        "constraints": extract_inline_comments(content, "CONSTRAINT"),
        "bugs": extract_inline_comments(content, "BUG"),
        "raise_errors": extract_raise_application_errors(content),
        "sql": extract_sql_statements(content),
        "procedures": extract_procedure_bodies(content),
        "package_calls": list(set(re.findall(r"(PKG_\w+)\.\w+", content, re.IGNORECASE))),
        "sequences_used": list(set(re.findall(r"(SEQ_\w+)\.NEXTVAL", content, re.IGNORECASE))),
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

    exceptions = []
    for m in re.finditer(r"(e_\w+)\s+EXCEPTION;\s*\n.*?PRAGMA EXCEPTION_INIT\(\s*\w+\s*,\s*(-\d+)\s*\)", content, re.IGNORECASE | re.DOTALL):
        exceptions.append({"name": m.group(1), "code": m.group(2)})

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
# DEEP FORMS XML PARSER
# ─────────────────────────────────────────────────────────────────────────────

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
        table = block.attrib.get("DMLDataTargetName", "")
        where = block.attrib.get("DefaultWhere", "")
        order = block.attrib.get("OrderByClause", "")

        items = []
        for item in block.findall(".//Item"):
            i = {
                "name": item.attrib.get("Name", ""),
                "type": item.attrib.get("ItemType", ""),
                "data_type": item.attrib.get("DataType", ""),
                "max_length": item.attrib.get("MaximumLength", ""),
                "required": item.attrib.get("RequiredItem", ""),
                "column": item.attrib.get("ColumnName", ""),
            }
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
                "raise_errors": extract_raise_application_errors(body),
            })

        blocks.append({
            "name": block_name,
            "table": table,
            "default_where": where,
            "order_by": order,
            "items": items,
            "triggers": block_triggers,
        })

    # LOVs
    lovs = []
    for lov in root.findall(".//LOV"):
        lovs.append({
            "name": lov.attrib.get("Name", ""),
            "record_group": lov.attrib.get("RecordGroup", ""),
        })

    # Record groups (SQL queries behind LOVs)
    record_groups = []
    for rg in root.findall(".//RecordGroup"):
        query_el = rg.find("RecordGroupQuery")
        query = query_el.text.strip() if query_el is not None and query_el.text else ""
        record_groups.append({
            "name": rg.attrib.get("Name", ""),
            "query": query,
            "tables": list(set(re.findall(r"FROM\s+(\w+)", query, re.IGNORECASE))),
        })

    # All package calls in entire form
    full_xml = ET.tostring(root, encoding="unicode")
    all_pkg_calls = list(set(re.findall(r"(PKG_\w+\.\w+)", full_xml, re.IGNORECASE)))
    all_business_rules = extract_inline_comments(full_xml, "BUSINESS")
    all_rules = extract_inline_comments(full_xml, "RULE")

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
        "all_package_calls": all_pkg_calls,
        "all_business_rules": all_business_rules,
        "all_rules": all_rules,
    }


def deep_parse_all_forms() -> list:
    return [deep_parse_form(f) for f in sorted(FORMS_DIR.glob("*.xml"))]


# ─────────────────────────────────────────────────────────────────────────────
# SCHEMA / DDL DEEP PARSER
# ─────────────────────────────────────────────────────────────────────────────

def deep_parse_schema() -> dict:
    tables = {}
    for sql_file in sorted((SCHEMA_DIR / "tables").glob("*.sql")):
        content = read_file(sql_file)
        # Extract CREATE TABLE blocks
        for m in re.finditer(
            r"CREATE\s+TABLE\s+(HRMS\.)?(\w+)\s*\((.*?)\);",
            content, re.DOTALL | re.IGNORECASE
        ):
            tbl_name = ("HRMS." + m.group(2)).upper()
            body = m.group(3)
            columns = []
            for col_m in re.finditer(
                r"^\s{4}(\w+)\s+([\w\(\),]+(?:\s+\w+)?)\s*(?:DEFAULT\s+\S+\s*)?(?:NOT NULL|NULL)?(?:\s*,)?$",
                body, re.MULTILINE | re.IGNORECASE
            ):
                col_name = col_m.group(1).upper()
                if col_name.upper() in ("CONSTRAINT", "PRIMARY", "FOREIGN", "UNIQUE", "CHECK"):
                    continue
                columns.append({
                    "name": col_name,
                    "type": col_m.group(2).strip(),
                })

            # Extract constraints
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

    triggers = {}
    for trig_file in sorted(TRIGGERS_DIR.glob("*.sql")):
        content = read_file(trig_file)
        for m in re.finditer(
            r"CREATE\s+OR\s+REPLACE\s+TRIGGER\s+(?:HRMS\.)?(\w+)\s+(BEFORE|AFTER|INSTEAD\s+OF)\s+(\w+(?:\s+OR\s+\w+)*)\s+ON\s+(HRMS\.)?(\w+)",
            content, re.IGNORECASE
        ):
            trig_name = m.group(1).upper()
            triggers[trig_name] = {
                "name": trig_name,
                "file": trig_file.name,
                "timing": m.group(2).upper(),
                "events": m.group(3).upper(),
                "table": ("HRMS." + m.group(5)).upper(),
                "business_rules": extract_inline_comments(content, "BUSINESS"),
                "rules": extract_inline_comments(content, "RULE"),
                "pkg_calls": list(set(re.findall(r"(PKG_\w+\.\w+)", content, re.IGNORECASE))),
            }

    return {"tables": tables, "views": views, "triggers": triggers}


# ─────────────────────────────────────────────────────────────────────────────
# BUSINESS RULES CONSOLIDATOR
# ─────────────────────────────────────────────────────────────────────────────

def consolidate_business_rules(packages: dict, forms: list, schema: dict) -> list:
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

    for form in forms:
        if "error" in form:
            continue
        for r in form.get("all_business_rules", []):
            add(form["name"], "oracle_form", "business_rule", r)
        for r in form.get("all_rules", []):
            add(form["name"], "oracle_form", "validation_rule", r)
        for block in form.get("blocks", []):
            for trig in block.get("triggers", []):
                for r in trig.get("business_rules", []):
                    add(f"{form['name']}.{block['name']}.{trig['name']}", "form_trigger", "business_rule", r)
                for e in trig.get("raise_errors", []):
                    add(f"{form['name']}.{block['name']}.{trig['name']}", "form_trigger", "error_rule",
                        f"Error {e['code']}: {e['message']}")

    for trig_name, trig in schema.get("triggers", {}).items():
        for r in trig.get("business_rules", []):
            add(trig_name, "db_trigger", "business_rule", r)
        for r in trig.get("rules", []):
            add(trig_name, "db_trigger", "validation_rule", r)

    for tbl_name, tbl in schema.get("tables", {}).items():
        for chk in tbl.get("check_constraints", []):
            add(tbl_name, "ddl_table", "check_constraint", chk)

    return rules


# ─────────────────────────────────────────────────────────────────────────────
# REPORT GENERATOR
# ─────────────────────────────────────────────────────────────────────────────

def generate_deep_report(packages: dict, forms: list, schema: dict, rules: list) -> str:
    lines = []
    lines.append("# Oracle Deep Parser Report — HRMS Source Code\n")

    total_br   = sum(1 for r in rules if r["category"] == "business_rule")
    total_vr   = sum(1 for r in rules if r["category"] == "validation_rule")
    total_con  = sum(1 for r in rules if r["category"] == "constraint")
    total_bug  = sum(1 for r in rules if r["category"] == "known_bug")
    total_err  = sum(1 for r in rules if r["category"] == "error_rule")
    total_chk  = sum(1 for r in rules if r["category"] == "check_constraint")

    lines.append("## Summary\n")
    lines.append(f"| Category | Count |")
    lines.append(f"|---|---|")
    lines.append(f"| PL/SQL Packages parsed | {len(packages)} |")
    lines.append(f"| Oracle Forms parsed | {len(forms)} |")
    lines.append(f"| DDL Tables parsed | {len(schema['tables'])} |")
    lines.append(f"| Views parsed | {len(schema['views'])} |")
    lines.append(f"| DB Triggers parsed | {len(schema['triggers'])} |")
    lines.append(f"| Business rules extracted | {total_br} |")
    lines.append(f"| Validation rules extracted | {total_vr} |")
    lines.append(f"| Constraints extracted | {total_con} |")
    lines.append(f"| Known bugs extracted | {total_bug} |")
    lines.append(f"| Error codes extracted | {total_err} |")
    lines.append(f"| Check constraints extracted | {total_chk} |")
    lines.append(f"| **Total rules** | **{len(rules)}** |\n")

    lines.append("---\n")
    lines.append("## PL/SQL Packages — Deep Extraction\n")

    for pkg_name, pkg in sorted(packages.items()):
        spec = pkg.get("spec") or {}
        body = pkg.get("body") or {}
        lines.append(f"### {pkg_name}")

        if spec.get("known_issues"):
            lines.append(f"**Known Issues:**")
            for issue in spec["known_issues"]:
                lines.append(f"- {issue}")

        if body.get("constants"):
            lines.append(f"\n**Constants ({len(body['constants'])}):**")
            for c in body["constants"]:
                meaning = f" — {c['meaning']}" if c["meaning"] else ""
                lines.append(f"- `{c['name']}` = `{c['value']}`{meaning}")

        if body.get("business_rules"):
            lines.append(f"\n**Business Rules ({len(body['business_rules'])}):**")
            for r in body["business_rules"]:
                lines.append(f"- {r}")

        if body.get("rules"):
            lines.append(f"\n**Validation Rules ({len(body['rules'])}):**")
            for r in body["rules"]:
                lines.append(f"- {r}")

        if body.get("constraints"):
            lines.append(f"\n**Constraints ({len(body['constraints'])}):**")
            for c in body["constraints"]:
                lines.append(f"- {c}")

        if body.get("bugs"):
            lines.append(f"\n**Known Bugs ({len(body['bugs'])}):**")
            for b in body["bugs"]:
                lines.append(f"- {b}")

        if body.get("raise_errors"):
            lines.append(f"\n**Error Codes ({len(body['raise_errors'])}):**")
            for e in body["raise_errors"]:
                lines.append(f"- `{e['code']}`: {e['message']}")

        if spec.get("procedures"):
            lines.append(f"\n**Procedures ({len(spec['procedures'])}):**")
            for p in spec["procedures"]:
                params = ", ".join(p["params"][:5]) if p["params"] else ""
                lines.append(f"- `{p['name']}({params})`")

        if spec.get("functions"):
            lines.append(f"\n**Functions ({len(spec['functions'])}):**")
            for f in spec["functions"]:
                params = ", ".join(f["params"][:5]) if f["params"] else ""
                lines.append(f"- `{f['name']}({params}) RETURN {f['returns']}`")

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
    lines.append("## Oracle Forms — Deep Extraction\n")

    for form in forms:
        if "error" in form:
            continue
        lines.append(f"### {form['name']} — {form.get('title', '')}")
        lines.append(f"- **First block:** {form.get('first_block', '')}")
        lines.append(f"- **Libraries:** {', '.join(form.get('libraries', []))}")

        if form.get("blocks"):
            lines.append(f"\n**Blocks ({len(form['blocks'])}):**")
            for block in form["blocks"]:
                lines.append(f"\n#### Block: {block['name']}")
                if block.get("table"):
                    lines.append(f"- Table: `{block['table']}`")
                if block.get("default_where"):
                    lines.append(f"- Default WHERE: `{block['default_where']}`")
                if block.get("items"):
                    lines.append(f"- Items ({len(block['items'])}): {', '.join(i['name'] for i in block['items'][:10])}")
                if block.get("triggers"):
                    lines.append(f"- Triggers ({len(block['triggers'])}): {', '.join(t['name'] for t in block['triggers'])}")
                    for trig in block["triggers"]:
                        if trig.get("business_rules"):
                            for r in trig["business_rules"]:
                                lines.append(f"  - RULE: {r}")
                        if trig.get("raise_errors"):
                            for e in trig["raise_errors"]:
                                lines.append(f"  - ERROR {e['code']}: {e['message']}")

        if form.get("form_triggers"):
            lines.append(f"\n**Form Triggers ({len(form['form_triggers'])}):**")
            for trig in form["form_triggers"]:
                lines.append(f"- `{trig['name']}` — pkg calls: {', '.join(trig['pkg_calls']) if trig['pkg_calls'] else 'none'}")

        if form.get("record_groups"):
            lines.append(f"\n**Record Groups / LOV Queries ({len(form['record_groups'])}):**")
            for rg in form["record_groups"]:
                if rg.get("query"):
                    lines.append(f"- `{rg['name']}` queries: {', '.join(rg['tables'])}")

        if form.get("all_package_calls"):
            lines.append(f"\n**All package calls:** {', '.join(sorted(form['all_package_calls']))}")

        lines.append("")

    lines.append("---\n")
    lines.append("## DDL Tables — Deep Extraction\n")

    for tbl_name, tbl in sorted(schema["tables"].items()):
        lines.append(f"### {tbl_name}")
        lines.append(f"- **Columns ({len(tbl['columns'])}):** {', '.join(c['name'] for c in tbl['columns'][:15])}")
        if tbl.get("primary_keys"):
            lines.append(f"- **Primary Key:** {', '.join(tbl['primary_keys'])}")
        if tbl.get("foreign_keys"):
            for fk in tbl["foreign_keys"]:
                lines.append(f"- **FK** `{fk['columns']}` → `{fk['references']}({fk['ref_columns']})`")
        if tbl.get("check_constraints"):
            for chk in tbl["check_constraints"]:
                lines.append(f"- **CHECK:** `{chk}`")
        lines.append("")

    lines.append("---\n")
    lines.append("## Consolidated Business Rules\n")
    lines.append(f"Total: {len(rules)} rules extracted from all source files\n")
    lines.append("| ID | Source | Type | Rule |")
    lines.append("|---|---|---|---|")
    for r in rules[:100]:  # show first 100 in report
        rule_text = r["rule"][:120].replace("|", "/")
        lines.append(f"| {r['id']} | {r['source']} | {r['category']} | {rule_text} |")
    if len(rules) > 100:
        lines.append(f"\n*... and {len(rules) - 100} more rules in business_rules.json*")

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

    print("Deep parsing DDL schema...")
    schema = deep_parse_schema()
    print(f"  Parsed {len(schema['tables'])} tables, {len(schema['views'])} views, {len(schema['triggers'])} triggers")

    print("Consolidating business rules...")
    rules = consolidate_business_rules(packages, forms, schema)
    print(f"  Extracted {len(rules)} total rules")

    print("Writing output files...")
    (OUTPUT_DIR / "plsql_deep.json").write_text(json.dumps(packages, indent=2), encoding="utf-8")
    (OUTPUT_DIR / "forms_deep.json").write_text(json.dumps(forms, indent=2), encoding="utf-8")
    (OUTPUT_DIR / "schema_deep.json").write_text(json.dumps(schema, indent=2), encoding="utf-8")
    (OUTPUT_DIR / "business_rules.json").write_text(json.dumps(rules, indent=2), encoding="utf-8")

    report = generate_deep_report(packages, forms, schema, rules)
    (OUTPUT_DIR / "DEEP_REPORT.md").write_text(report, encoding="utf-8")

    print(f"\n=== DONE ===")
    print(f"  Packages:        {len(packages)}")
    print(f"  Forms:           {len(forms)}")
    print(f"  Tables:          {len(schema['tables'])}")
    print(f"  Views:           {len(schema['views'])}")
    print(f"  DB Triggers:     {len(schema['triggers'])}")
    print(f"  Business rules:  {sum(1 for r in rules if r['category'] == 'business_rule')}")
    print(f"  Validation rules:{sum(1 for r in rules if r['category'] == 'validation_rule')}")
    print(f"  Constraints:     {sum(1 for r in rules if r['category'] == 'constraint')}")
    print(f"  Known bugs:      {sum(1 for r in rules if r['category'] == 'known_bug')}")
    print(f"  Error codes:     {sum(1 for r in rules if r['category'] == 'error_rule')}")
    print(f"  Total rules:     {len(rules)}")
    print(f"\nOutput: graphify-out/deep/")
    print(f"  plsql_deep.json")
    print(f"  forms_deep.json")
    print(f"  schema_deep.json")
    print(f"  business_rules.json")
    print(f"  DEEP_REPORT.md")


if __name__ == "__main__":
    main()
