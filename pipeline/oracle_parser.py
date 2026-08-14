"""
oracle_parser.py
----------------
Parses Oracle PL/SQL package files (.pks, .pkb) and Oracle Forms XML files (.xml)
and outputs structured JSON + a human-readable report into the graphify-out folder.

Usage:
    python oracle_parser.py

Output:
    graphify-out/oracle_plsql_graph.json   — PL/SQL packages graph nodes + edges
    graphify-out/oracle_forms_graph.json   — Oracle Forms graph nodes + edges
    graphify-out/oracle_combined_graph.json — merged with existing graph.json
    graphify-out/ORACLE_PARSER_REPORT.md   — human-readable full report
"""

import re
import json
import xml.etree.ElementTree as ET
from pathlib import Path

SOURCE_DIR   = Path(__file__).parent.parent / "source"
OUTPUT_DIR   = Path(__file__).parent.parent / "output" / "graphify-out"
PACKAGES_DIR = SOURCE_DIR / "plsql" / "packages"
FORMS_DIR    = SOURCE_DIR / "forms" / "xml-exports"
EXISTING_GRAPH = OUTPUT_DIR / "graph.json"

# ─────────────────────────────────────────────────────────────────────────────
# PL/SQL PACKAGE PARSER
# ─────────────────────────────────────────────────────────────────────────────

def parse_pks(filepath: Path) -> dict:
    """Parse a .pks (package spec) file — extracts procedures, functions, types, exceptions."""
    content = filepath.read_text(encoding="utf-8", errors="ignore")
    pkg_name_match = re.search(r"CREATE\s+OR\s+REPLACE\s+PACKAGE\s+(\S+)\s+AS", content, re.IGNORECASE)
    pkg_name = pkg_name_match.group(1) if pkg_name_match else filepath.stem

    procedures = re.findall(r"PROCEDURE\s+(\w+)\s*\(", content, re.IGNORECASE)
    functions  = re.findall(r"FUNCTION\s+(\w+)\s*\(", content, re.IGNORECASE)
    exceptions = re.findall(r"(\w+)\s+EXCEPTION;", content, re.IGNORECASE)
    types      = re.findall(r"TYPE\s+(\w+)\s+IS", content, re.IGNORECASE)
    deps_match = re.search(r"Dependencies:\s*(.+)", content)
    callers_match = re.search(r"Called by:\s*(.+)", content)
    issues_match  = re.search(r"Known issues:(.*?)(?=\n--\s*={5,}|\Z)", content, re.DOTALL)

    dependencies = [d.strip() for d in deps_match.group(1).split(",")] if deps_match else []
    callers      = [c.strip() for c in callers_match.group(1).split(",")] if callers_match else []
    issues       = []
    if issues_match:
        for line in issues_match.group(1).splitlines():
            line = line.strip().lstrip("-").strip()
            if line:
                issues.append(line)

    return {
        "name": pkg_name,
        "file": filepath.name,
        "type": "package_spec",
        "procedures": procedures,
        "functions": functions,
        "exceptions": exceptions,
        "types": types,
        "dependencies": dependencies,
        "callers": callers,
        "known_issues": issues,
    }


def parse_pkb(filepath: Path) -> dict:
    """Parse a .pkb (package body) file — extracts procedure/function implementations."""
    content = filepath.read_text(encoding="utf-8", errors="ignore")
    pkg_name_match = re.search(r"CREATE\s+OR\s+REPLACE\s+PACKAGE\s+BODY\s+(\S+)\s+AS", content, re.IGNORECASE)
    pkg_name = pkg_name_match.group(1) if pkg_name_match else filepath.stem

    procedures = re.findall(r"PROCEDURE\s+(\w+)\s*[\(\n]", content, re.IGNORECASE)
    functions  = re.findall(r"FUNCTION\s+(\w+)\s*[\(\n]", content, re.IGNORECASE)

    # Extract SQL table references (SELECT/INSERT/UPDATE/DELETE on tables)
    table_refs = re.findall(
        r"(?:FROM|JOIN|INTO|UPDATE)\s+(HRMS\.)?(\w+)\b",
        content, re.IGNORECASE
    )
    tables_used = list(set(
        ("HRMS." + t[1] if t[0] else t[1]).upper()
        for t in table_refs
        if t[1].upper() not in ("DUAL", "SYSDATE", "NULL", "SELECT", "WHERE", "SET")
    ))

    # Extract package calls (PKG_xxx.xxx)
    pkg_calls = list(set(re.findall(r"(PKG_\w+)\.\w+", content, re.IGNORECASE)))

    # Extract exception raises
    raises = list(set(re.findall(r"RAISE\s+(\w+)", content, re.IGNORECASE)))

    return {
        "name": pkg_name,
        "file": filepath.name,
        "type": "package_body",
        "procedures": list(set(procedures)),
        "functions": list(set(functions)),
        "tables_used": tables_used,
        "package_calls": pkg_calls,
        "exceptions_raised": raises,
    }


def parse_all_packages() -> dict:
    """Parse all .pks and .pkb files and return combined package map."""
    packages = {}

    for pks_file in sorted(PACKAGES_DIR.glob("*.pks")):
        data = parse_pks(pks_file)
        name = data["name"]
        packages[name] = {"spec": data, "body": None}

    for pkb_file in sorted(PACKAGES_DIR.glob("*.pkb")):
        data = parse_pkb(pkb_file)
        name = data["name"]
        if name in packages:
            packages[name]["body"] = data
        else:
            packages[name] = {"spec": None, "body": data}

    return packages


# ─────────────────────────────────────────────────────────────────────────────
# ORACLE FORMS XML PARSER
# ─────────────────────────────────────────────────────────────────────────────

def parse_form_xml(filepath: Path) -> dict:
    """Parse an Oracle Forms XML export file."""
    try:
        tree = ET.parse(filepath)
        root = tree.getroot()
    except ET.ParseError as e:
        return {"name": filepath.stem, "file": filepath.name, "error": str(e)}

    form_name = root.attrib.get("Name", filepath.stem)
    first_block = root.attrib.get("FirstNavigationBlock", "")
    menu_module = root.attrib.get("MenuModule", "")
    title = root.attrib.get("Title", "")

    # Attached libraries
    libraries = [el.attrib.get("Name", "") for el in root.findall(".//AttachedLibrary")]

    # Data blocks
    blocks = []
    for block in root.findall(".//Block"):
        b = {
            "name": block.attrib.get("Name", ""),
            "table": block.attrib.get("DMLDataTargetName", ""),
            "items": [item.attrib.get("Name", "") for item in block.findall(".//Item")],
        }
        blocks.append(b)

    # Form-level triggers
    triggers = []
    for trig in root.findall(".//Trigger"):
        t = {
            "name": trig.attrib.get("Name", ""),
            "style": trig.attrib.get("TriggerStyle", ""),
        }
        text_el = trig.find("TriggerText")
        if text_el is not None and text_el.text:
            pkg_calls = list(set(re.findall(r"(PKG_\w+)\.\w+", text_el.text, re.IGNORECASE)))
            t["package_calls"] = pkg_calls
        triggers.append(t)

    # LOVs
    lovs = [el.attrib.get("Name", "") for el in root.findall(".//LOV")]

    # Canvases
    canvases = [el.attrib.get("Name", "") for el in root.findall(".//Canvas")]

    # Windows
    windows = [el.attrib.get("Name", "") for el in root.findall(".//Window")]

    # All package calls across entire form
    all_pkg_calls = list(set(re.findall(r"(PKG_\w+)\.\w+", ET.tostring(root, encoding="unicode"), re.IGNORECASE)))

    return {
        "name": form_name,
        "file": filepath.name,
        "title": title,
        "first_block": first_block,
        "menu_module": menu_module,
        "libraries": libraries,
        "blocks": blocks,
        "triggers": triggers,
        "lovs": lovs,
        "canvases": canvases,
        "windows": windows,
        "package_calls": all_pkg_calls,
    }


def parse_all_forms() -> list:
    """Parse all Oracle Forms XML files."""
    forms = []
    for xml_file in sorted(FORMS_DIR.glob("*.xml")):
        forms.append(parse_form_xml(xml_file))
    return forms


# ─────────────────────────────────────────────────────────────────────────────
# GRAPH BUILDER
# ─────────────────────────────────────────────────────────────────────────────

def build_plsql_graph(packages: dict) -> dict:
    """Build graph nodes and edges from parsed packages."""
    nodes = []
    edges = []
    node_ids = set()

    def add_node(node_id, label, file_type, source_file, extra=None):
        if node_id not in node_ids:
            n = {
                "id": node_id,
                "label": label,
                "file_type": file_type,
                "source_file": source_file,
                "_origin": "oracle_parser",
            }
            if extra:
                n.update(extra)
            nodes.append(n)
            node_ids.add(node_id)

    for pkg_name, pkg in packages.items():
        pkg_id = pkg_name.lower().replace(".", "_").replace(" ", "_")
        spec = pkg.get("spec") or {}
        body = pkg.get("body") or {}

        add_node(pkg_id, pkg_name, "plsql_package", spec.get("file", body.get("file", "")), {
            "procedures": spec.get("procedures", body.get("procedures", [])),
            "functions": spec.get("functions", body.get("functions", [])),
            "exceptions": spec.get("exceptions", []),
            "types": spec.get("types", []),
            "tables_used": body.get("tables_used", []),
            "known_issues": spec.get("known_issues", []),
        })

        # Edges: package → package dependency
        for dep in spec.get("dependencies", []):
            dep_id = dep.lower().replace(".", "_").replace(" ", "_")
            add_node(dep_id, dep, "plsql_package", dep + ".pks")
            edges.append({
                "source": pkg_id,
                "target": dep_id,
                "relation": "depends_on",
                "confidence": "EXTRACTED",
                "source_file": spec.get("file", ""),
                "weight": 1.0,
            })

        # Edges: package → tables used
        for table in body.get("tables_used", []):
            table_id = table.lower().replace(".", "_").replace(" ", "_")
            add_node(table_id, table, "oracle_table", "schema/tables/")
            edges.append({
                "source": pkg_id,
                "target": table_id,
                "relation": "reads_writes",
                "confidence": "EXTRACTED",
                "source_file": body.get("file", ""),
                "weight": 1.0,
            })

        # Edges: package → package calls from body
        for called in body.get("package_calls", []):
            called_id = called.lower().replace(".", "_").replace(" ", "_")
            if called_id != pkg_id:
                add_node(called_id, called, "plsql_package", called + ".pks")
                edges.append({
                    "source": pkg_id,
                    "target": called_id,
                    "relation": "calls",
                    "confidence": "EXTRACTED",
                    "source_file": body.get("file", ""),
                    "weight": 1.0,
                })

        # Procedure/function nodes
        for proc in spec.get("procedures", []):
            proc_id = f"{pkg_id}__{proc.lower()}"
            add_node(proc_id, f"{pkg_name}.{proc}", "plsql_procedure", spec.get("file", ""))
            edges.append({
                "source": pkg_id,
                "target": proc_id,
                "relation": "contains",
                "confidence": "EXTRACTED",
                "source_file": spec.get("file", ""),
                "weight": 1.0,
            })

        for func in spec.get("functions", []):
            func_id = f"{pkg_id}__fn_{func.lower()}"
            add_node(func_id, f"{pkg_name}.{func}()", "plsql_function", spec.get("file", ""))
            edges.append({
                "source": pkg_id,
                "target": func_id,
                "relation": "contains",
                "confidence": "EXTRACTED",
                "source_file": spec.get("file", ""),
                "weight": 1.0,
            })

    return {"directed": True, "nodes": nodes, "links": edges}


def build_forms_graph(forms: list) -> dict:
    """Build graph nodes and edges from parsed Oracle Forms."""
    nodes = []
    edges = []
    node_ids = set()

    def add_node(node_id, label, file_type, source_file, extra=None):
        if node_id not in node_ids:
            n = {
                "id": node_id,
                "label": label,
                "file_type": file_type,
                "source_file": source_file,
                "_origin": "oracle_parser",
            }
            if extra:
                n.update(extra)
            nodes.append(n)
            node_ids.add(node_id)

    for form in forms:
        if "error" in form:
            continue

        form_id = form["name"].lower()
        add_node(form_id, form["name"], "oracle_form", form["file"], {
            "title": form.get("title", ""),
            "first_block": form.get("first_block", ""),
            "canvases": form.get("canvases", []),
            "windows": form.get("windows", []),
            "lovs": form.get("lovs", []),
        })

        # Blocks
        for block in form.get("blocks", []):
            block_id = f"{form_id}__block_{block['name'].lower()}"
            add_node(block_id, f"{form['name']}.{block['name']}", "form_block", form["file"], {
                "table": block.get("table", ""),
                "items": block.get("items", []),
            })
            edges.append({
                "source": form_id,
                "target": block_id,
                "relation": "contains_block",
                "confidence": "EXTRACTED",
                "source_file": form["file"],
                "weight": 1.0,
            })
            # Block → table edge
            if block.get("table"):
                table_id = ("hrms_" + block["table"].lower()).replace(".", "_")
                add_node(table_id, "HRMS." + block["table"], "oracle_table", "schema/tables/")
                edges.append({
                    "source": block_id,
                    "target": table_id,
                    "relation": "reads_writes",
                    "confidence": "EXTRACTED",
                    "source_file": form["file"],
                    "weight": 1.0,
                })

        # Triggers
        for trig in form.get("triggers", []):
            trig_id = f"{form_id}__trig_{trig['name'].lower()}"
            add_node(trig_id, f"{form['name']}.{trig['name']}", "form_trigger", form["file"])
            edges.append({
                "source": form_id,
                "target": trig_id,
                "relation": "has_trigger",
                "confidence": "EXTRACTED",
                "source_file": form["file"],
                "weight": 1.0,
            })
            # Trigger → package calls
            for pkg_call in trig.get("package_calls", []):
                pkg_id = pkg_call.lower().replace(".", "_")
                add_node(pkg_id, pkg_call.upper(), "plsql_package", pkg_call + ".pks")
                edges.append({
                    "source": trig_id,
                    "target": pkg_id,
                    "relation": "calls",
                    "confidence": "EXTRACTED",
                    "source_file": form["file"],
                    "weight": 1.0,
                })

        # Libraries
        for lib in form.get("libraries", []):
            lib_id = lib.lower()
            add_node(lib_id, lib, "forms_library", lib + ".pll.sql")
            edges.append({
                "source": form_id,
                "target": lib_id,
                "relation": "attaches_library",
                "confidence": "EXTRACTED",
                "source_file": form["file"],
                "weight": 1.0,
            })

        # Form-level package calls
        for pkg_call in form.get("package_calls", []):
            pkg_id = pkg_call.lower().replace(".", "_")
            add_node(pkg_id, pkg_call.upper(), "plsql_package", pkg_call + ".pks")
            edges.append({
                "source": form_id,
                "target": pkg_id,
                "relation": "calls",
                "confidence": "EXTRACTED",
                "source_file": form["file"],
                "weight": 1.0,
            })

    return {"directed": True, "nodes": nodes, "links": edges}


def merge_graphs(base: dict, *extras) -> dict:
    """Merge multiple graph dicts into one combined graph."""
    all_nodes = {n["id"]: n for n in base.get("nodes", [])}
    all_links = list(base.get("links", []))

    for g in extras:
        for n in g.get("nodes", []):
            if n["id"] not in all_nodes:
                all_nodes[n["id"]] = n
        for e in g.get("links", []):
            all_links.append(e)

    return {
        "directed": True,
        "multigraph": False,
        "graph": {},
        "nodes": list(all_nodes.values()),
        "links": all_links,
    }


# ─────────────────────────────────────────────────────────────────────────────
# REPORT GENERATOR
# ─────────────────────────────────────────────────────────────────────────────

def generate_report(packages: dict, forms: list, combined: dict) -> str:
    lines = []
    lines.append("# Oracle Parser Report — HRMS Source Code\n")
    lines.append(f"**Total nodes in combined graph:** {len(combined['nodes'])}")
    lines.append(f"**Total edges in combined graph:** {len(combined['links'])}\n")

    lines.append("---\n")
    lines.append("## PL/SQL Packages\n")
    lines.append(f"**Packages parsed:** {len(packages)}\n")

    for pkg_name, pkg in sorted(packages.items()):
        spec = pkg.get("spec") or {}
        body = pkg.get("body") or {}
        lines.append(f"### {pkg_name}")
        procs = spec.get("procedures", body.get("procedures", []))
        funcs = spec.get("functions", body.get("functions", []))
        deps  = spec.get("dependencies", [])
        tables = body.get("tables_used", [])
        calls  = body.get("package_calls", [])
        issues = spec.get("known_issues", [])

        lines.append(f"- **Procedures ({len(procs)}):** {', '.join(procs) if procs else 'none'}")
        lines.append(f"- **Functions ({len(funcs)}):** {', '.join(funcs) if funcs else 'none'}")
        lines.append(f"- **Dependencies:** {', '.join(deps) if deps else 'none'}")
        lines.append(f"- **Tables used ({len(tables)}):** {', '.join(tables) if tables else 'none'}")
        lines.append(f"- **Package calls:** {', '.join(calls) if calls else 'none'}")
        if issues:
            lines.append(f"- **Known issues:**")
            for issue in issues:
                lines.append(f"  - {issue}")
        lines.append("")

    lines.append("---\n")
    lines.append("## Oracle Forms\n")
    lines.append(f"**Forms parsed:** {len(forms)}\n")

    for form in forms:
        if "error" in form:
            lines.append(f"### {form['name']} — ERROR: {form['error']}\n")
            continue
        lines.append(f"### {form['name']}")
        lines.append(f"- **Title:** {form.get('title', '')}")
        lines.append(f"- **First Block:** {form.get('first_block', '')}")
        blocks = form.get("blocks", [])
        lines.append(f"- **Blocks ({len(blocks)}):** {', '.join(b['name'] for b in blocks)}")
        lines.append(f"- **Triggers ({len(form.get('triggers', []))}):** {', '.join(t['name'] for t in form.get('triggers', []))}")
        lines.append(f"- **LOVs ({len(form.get('lovs', []))}):** {', '.join(form.get('lovs', []))}")
        lines.append(f"- **Canvases:** {', '.join(form.get('canvases', []))}")
        lines.append(f"- **Libraries:** {', '.join(form.get('libraries', []))}")
        lines.append(f"- **Package calls:** {', '.join(form.get('package_calls', []))}")
        lines.append("")

    lines.append("---\n")
    lines.append("## Coverage Summary\n")
    lines.append("| Category | Files | Nodes Extracted |")
    lines.append("|---|---|---|")

    pkg_nodes = [n for n in combined["nodes"] if n.get("file_type") == "plsql_package"]
    proc_nodes = [n for n in combined["nodes"] if n.get("file_type") == "plsql_procedure"]
    func_nodes = [n for n in combined["nodes"] if n.get("file_type") == "plsql_function"]
    form_nodes = [n for n in combined["nodes"] if n.get("file_type") == "oracle_form"]
    block_nodes = [n for n in combined["nodes"] if n.get("file_type") == "form_block"]
    trig_nodes = [n for n in combined["nodes"] if n.get("file_type") == "form_trigger"]
    table_nodes = [n for n in combined["nodes"] if n.get("file_type") == "oracle_table"]

    lines.append(f"| PL/SQL Packages | {len(packages) * 2} (.pks + .pkb) | {len(pkg_nodes)} |")
    lines.append(f"| Procedures | — | {len(proc_nodes)} |")
    lines.append(f"| Functions | — | {len(func_nodes)} |")
    lines.append(f"| Oracle Forms | 6 (.xml) | {len(form_nodes)} |")
    lines.append(f"| Form Blocks | — | {len(block_nodes)} |")
    lines.append(f"| Form Triggers | — | {len(trig_nodes)} |")
    lines.append(f"| Tables (referenced) | — | {len(table_nodes)} |")
    lines.append(f"| **TOTAL** | **34 files** | **{len(combined['nodes'])}** |")

    return "\n".join(lines)


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────

def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print("Parsing PL/SQL packages...")
    packages = parse_all_packages()
    print(f"  Parsed {len(packages)} packages")

    print("Parsing Oracle Forms XML...")
    forms = parse_all_forms()
    print(f"  Parsed {len(forms)} forms")

    print("Building graphs...")
    plsql_graph = build_plsql_graph(packages)
    forms_graph = build_forms_graph(forms)

    # Load existing graphify graph
    base_graph = {"nodes": [], "links": []}
    if EXISTING_GRAPH.exists():
        base_graph = json.loads(EXISTING_GRAPH.read_text(encoding="utf-8"))
        print(f"  Loaded existing graph: {len(base_graph.get('nodes', []))} nodes")

    combined = merge_graphs(base_graph, plsql_graph, forms_graph)

    # Write outputs
    (OUTPUT_DIR / "oracle_plsql_graph.json").write_text(
        json.dumps(plsql_graph, indent=2), encoding="utf-8")

    (OUTPUT_DIR / "oracle_forms_graph.json").write_text(
        json.dumps(forms_graph, indent=2), encoding="utf-8")

    (OUTPUT_DIR / "oracle_combined_graph.json").write_text(
        json.dumps(combined, indent=2), encoding="utf-8")

    report = generate_report(packages, forms, combined)
    (OUTPUT_DIR / "ORACLE_PARSER_REPORT.md").write_text(report, encoding="utf-8")

    print(f"\n=== DONE ===")
    print(f"  PL/SQL nodes:    {len(plsql_graph['nodes'])}")
    print(f"  PL/SQL edges:    {len(plsql_graph['links'])}")
    print(f"  Forms nodes:     {len(forms_graph['nodes'])}")
    print(f"  Forms edges:     {len(forms_graph['links'])}")
    print(f"  Combined nodes:  {len(combined['nodes'])} (graphify + oracle parser)")
    print(f"  Combined edges:  {len(combined['links'])}")
    print(f"\nOutput files:")
    print(f"  graphify-out/oracle_plsql_graph.json")
    print(f"  graphify-out/oracle_forms_graph.json")
    print(f"  graphify-out/oracle_combined_graph.json")
    print(f"  graphify-out/ORACLE_PARSER_REPORT.md")


if __name__ == "__main__":
    main()
