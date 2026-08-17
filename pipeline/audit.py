"""
audit.py — exhaustive source vs output coverage check
Verifies every named structural element AND accuracy of FKs, CHECKs,
package-body RAISE errors, and parameter directions.
"""
import json, re, xml.etree.ElementTree as ET
from pathlib import Path

SRC = Path(__file__).parent.parent / "source"
OUT = Path(__file__).parent / "parser-output"

def r(p): return Path(p).read_text(encoding="utf-8", errors="ignore")

plsql  = json.loads((OUT/"plsql_deep.json").read_text())
schema = json.loads((OUT/"schema_deep.json").read_text())
forms  = json.loads((OUT/"forms_deep.json").read_text())
menus  = json.loads((OUT/"menu_deep.json").read_text())
pll    = json.loads((OUT/"pll_deep.json").read_text())
seed   = json.loads((OUT/"seed_deep.json").read_text())

hits, misses = [], []
def ok(label):   hits.append(f"  OK   {label}")
def miss(label): misses.append(f"  MISS {label}")


# ── PACKAGES ──────────────────────────────────────────────────────────────────
for pks_file in sorted((SRC/"plsql/packages").glob("*.pks")):
    pkg_stem = pks_file.stem.upper()
    pkg_key  = next((k for k in plsql if pkg_stem in k.upper()), None)
    if not pkg_key: miss(f"package {pkg_stem}"); continue
    ok(f"package {pkg_stem}")

    src = r(pks_file)
    spec = plsql[pkg_key].get("spec") or {}
    out_procs = {p["name"].upper() for p in spec.get("procedures", [])}
    out_funcs = {f["name"].upper() for f in spec.get("functions",  [])}

    for m in re.finditer(r"PROCEDURE\s+(\w+)", src, re.I):
        name = m.group(1).upper()
        if name in out_procs: ok(f"{pkg_stem}.{name}")
        else: miss(f"{pkg_stem}.{name} [procedure missing]")

    for m in re.finditer(r"FUNCTION\s+(\w+)", src, re.I):
        name = m.group(1).upper()
        if name in out_funcs: ok(f"{pkg_stem}.{name}")
        else: miss(f"{pkg_stem}.{name} [function missing]")

    # ── PARAMETER DIRECTIONS ─────────────────────────────────────────────────
    # Build source param map: proc/func name -> list of (name, direction, type)
    def _src_params(text):
        """Extract params with direction from a raw parameter block string."""
        cleaned = re.sub(r"--[^\n]*", "", text)
        params = []
        for p in cleaned.split(","):
            p = p.strip()
            if not p: continue
            m2 = re.match(r"(\w+)\s+(IN\s+OUT|IN|OUT)\s+([\w%()]+)", p, re.I)
            if m2:
                params.append((m2.group(1).upper(),
                                re.sub(r"\s+","",m2.group(2).upper()),
                                m2.group(3).upper()))
        return params

    def _balanced_params(text, start):
        idx = text.find("(", start)
        if idx == -1: return ""
        depth, buf = 0, []
        for ch in text[idx:]:
            if ch == "(":
                depth += 1
                if depth > 1: buf.append(ch)
            elif ch == ")":
                depth -= 1
                if depth == 0: break
                buf.append(ch)
            else: buf.append(ch)
        return "".join(buf)

    # Check each source procedure's params
    all_spec_entries = spec.get("procedures",[]) + spec.get("functions",[])
    out_param_map = {e["name"].upper(): e.get("params",[]) for e in all_spec_entries}

    for pat in [r"PROCEDURE\s+(\w+)\s*\(", r"FUNCTION\s+(\w+)\s*\("]:
        for m in re.finditer(pat, src, re.I):
            name = m.group(1).upper()
            raw = _balanced_params(src, m.end()-1)
            src_params = _src_params(raw)
            out_params = out_param_map.get(name, [])
            out_param_names = {p["name"].upper() if isinstance(p,dict) else p.upper()
                               for p in out_params}
            out_param_dirs  = {(p["name"].upper(), re.sub(r"\s+","",p.get("direction","IN").upper()))
                               for p in out_params if isinstance(p,dict)}
            for pname, pdir, ptype in src_params:
                if pname not in out_param_names:
                    miss(f"{pkg_stem}.{name}.{pname} [param missing]")
                elif (pname, pdir) not in out_param_dirs:
                    miss(f"{pkg_stem}.{name}.{pname} [direction wrong: src={pdir}]")
                else:
                    ok(f"{pkg_stem}.{name}.{pname} direction={pdir}")


# ── PACKAGE BODY RAISE ERRORS ─────────────────────────────────────────────────
for pkb_file in sorted((SRC/"plsql/packages").glob("*.pkb")):
    pkg_stem = pkb_file.stem.upper()
    pkg_key  = next((k for k in plsql if pkg_stem in k.upper()), None)
    if not pkg_key: continue
    body_data = plsql[pkg_key].get("body") or {}

    # Collect all raise errors from package body + its procedures
    out_codes = set()
    for e in body_data.get("raise_errors", []):
        out_codes.add(e["code"])
    for proc in body_data.get("procedures", []):
        for e in proc.get("raise_errors", []):
            out_codes.add(e["code"])

    src_content = r(pkb_file)
    src_codes = set(re.findall(r"RAISE_APPLICATION_ERROR\s*\(\s*(-\d+)", src_content, re.I))
    for code in sorted(src_codes):
        if code in out_codes: ok(f"{pkg_stem} RAISE {code}")
        else: miss(f"{pkg_stem} RAISE {code} [missing from body]")


# ── TABLES ────────────────────────────────────────────────────────────────────
src_tables = set()
for sf in (SRC/"schema/tables").glob("*.sql"):
    for m in re.finditer(r"CREATE TABLE (?:HRMS\.)?(\w+)", r(sf), re.I):
        src_tables.add(m.group(1).upper())

out_tables = {t.replace("HRMS.","").upper(): t for t in schema["tables"]}
for tname in sorted(src_tables):
    if tname in out_tables: ok(f"table {tname}")
    else: miss(f"table {tname}")


# ── TABLE COLUMNS ─────────────────────────────────────────────────────────────
for sf in (SRC/"schema/tables").glob("*.sql"):
    content = r(sf)
    for tm in re.finditer(r"CREATE TABLE (?:HRMS\.)?(\w+)\s*\((.*?)\)\s*;", content, re.DOTALL|re.I):
        tname = tm.group(1).upper()
        full_key = "HRMS." + tname
        out_entry = schema["tables"].get(full_key, {})
        out_cols  = {c["name"].upper() for c in out_entry.get("columns", [])}
        for line in tm.group(2).splitlines():
            s = line.strip().rstrip(",")
            cm = re.match(
                r"^(\w+)\s+(NUMBER|VARCHAR2|CHAR|DATE|TIMESTAMP|CLOB|BLOB|RAW|INTEGER|FLOAT|NVARCHAR2)",
                s, re.I
            )
            if cm:
                col = cm.group(1).upper()
                if col not in {"CONSTRAINT","PRIMARY","FOREIGN","UNIQUE","CHECK","GENERATED"}:
                    if col in out_cols: ok(f"{tname}.{col}")
                    else: miss(f"{tname}.{col} [column missing]")


# ── FK CONSTRAINTS (name + referenced table) ──────────────────────────────────
for sf in (SRC/"schema/tables").glob("*.sql"):
    content = r(sf)
    for tm in re.finditer(r"CREATE TABLE (?:HRMS\.)?(\w+)\s*\((.*?)\)\s*;", content, re.DOTALL|re.I):
        tname = tm.group(1).upper()
        full_key = "HRMS." + tname
        out_entry = schema["tables"].get(full_key, {})
        out_fks = {fk["constraint"].upper(): fk for fk in out_entry.get("foreign_keys", [])}

        for line in tm.group(2).splitlines():
            s = line.strip().rstrip(",")
            fk_m = re.search(
                r"CONSTRAINT\s+(\w+)\s+FOREIGN KEY\s*\(([^)]+)\)\s+REFERENCES\s+(?:HRMS\.)?(\w+)\s*\(([^)]+)\)",
                s, re.I
            )
            if fk_m:
                cname  = fk_m.group(1).upper()
                cols   = fk_m.group(2).strip()
                ref_tbl= fk_m.group(3).upper()
                ref_col= fk_m.group(4).strip()
                if cname not in out_fks:
                    miss(f"{tname} FK {cname} [missing]")
                else:
                    out_ref = out_fks[cname]["references"].replace("HRMS.","").upper()
                    if out_ref == ref_tbl: ok(f"{tname} FK {cname} -> {ref_tbl}")
                    else: miss(f"{tname} FK {cname} ref: got={out_ref} want={ref_tbl}")


# ── UNIQUE CONSTRAINTS ────────────────────────────────────────────────────────
for sf in (SRC/"schema/tables").glob("*.sql"):
    for m in re.finditer(r"CONSTRAINT\s+(\w+)\s+UNIQUE", r(sf), re.I):
        cname = m.group(1).upper()
        found = any(uk["name"].upper()==cname
                    for tbl in schema["tables"].values()
                    for uk in tbl.get("unique_constraints",[]))
        if found: ok(f"UNIQUE {cname}")
        else: miss(f"UNIQUE {cname}")


# ── CHECK CONSTRAINTS (name existence + expression accuracy) ──────────────────
for sf in (SRC/"schema/tables").glob("*.sql"):
    content = r(sf)
    for tm in re.finditer(r"CREATE TABLE (?:HRMS\.)?(\w+)\s*\((.*?)\)\s*;", content, re.DOTALL|re.I):
        tname = tm.group(1).upper()
        full_key = "HRMS." + tname
        out_entry = schema["tables"].get(full_key, {})
        # Normalize check expressions for comparison
        out_checks = {re.sub(r"\s+","",c.upper()) for c in out_entry.get("check_constraints",[])}

        for line in tm.group(2).splitlines():
            s = line.strip().rstrip(",")
            chk_m = re.search(r"CONSTRAINT\s+(\w+)\s+CHECK\s*\((.+)\)", s, re.I)
            if chk_m:
                cname = chk_m.group(1).upper()
                expr  = re.sub(r"\s+","", chk_m.group(2).upper())
                if expr in out_checks: ok(f"{tname} CHECK {cname}")
                else: miss(f"{tname} CHECK {cname}: expr not matched (src={expr[:60]})")


# ── SEQUENCES ─────────────────────────────────────────────────────────────────
seq_file = SRC/"schema/sequences/hrms_sequences.sql"
src_seqs = {m.group(1).upper() for m in re.finditer(r"CREATE SEQUENCE (?:HRMS\.)?(\w+)", r(seq_file), re.I)}
out_seqs = {s["name"].replace("HRMS.","").upper() for s in schema.get("sequences",[])}
for s in sorted(src_seqs):
    if s in out_seqs: ok(f"sequence {s}")
    else: miss(f"sequence {s}")


# ── TRIGGERS ─────────────────────────────────────────────────────────────────
for tf in sorted((SRC/"plsql/triggers").glob("*.sql")):
    content = r(tf)
    for m in re.finditer(r"CREATE OR REPLACE TRIGGER (?:HRMS\.)?(\w+)", content, re.I):
        trig = m.group(1).upper()
        if trig in {t.upper() for t in schema["triggers"]}: ok(f"trigger {trig}")
        else: miss(f"trigger {trig}")
    for m in re.finditer(r"RAISE_APPLICATION_ERROR\s*\(\s*(-\d+)", content, re.I):
        code = m.group(1)
        found = any(e["code"]==code
                    for t in schema["triggers"].values()
                    for e in t.get("raise_errors",[]))
        if found: ok(f"trigger RAISE {code}")
        else: miss(f"trigger RAISE {code}")


# ── VIEWS ─────────────────────────────────────────────────────────────────────
views_file = SRC/"schema/views/hrms_views.sql"
src_views  = {m.group(1).upper() for m in re.finditer(r"CREATE OR REPLACE VIEW (?:HRMS\.)?(\w+)", r(views_file), re.I)}
out_views  = {v.replace("HRMS.","").upper() for v in schema["views"]}
for v in sorted(src_views):
    if v in out_views: ok(f"view {v}")
    else: miss(f"view {v}")


# ── FORMS ─────────────────────────────────────────────────────────────────────
for xf in sorted((SRC/"forms/xml-exports").glob("*.xml")):
    fname = xf.stem.upper()
    out_form = next((f for f in forms if f.get("name","").upper()==fname), None)
    if not out_form: miss(f"form {fname}"); continue
    ok(f"form {fname}")
    try: root = ET.parse(xf).getroot()
    except: continue

    out_blocks = {b["name"].upper() for b in out_form.get("blocks",[])}
    for block in root.findall(".//Block"):
        bname = block.attrib.get("Name","").upper()
        if bname:
            if bname in out_blocks: ok(f"{fname}.block.{bname}")
            else: miss(f"{fname}.block.{bname}")

    out_alerts = {a.get("name","").upper() for a in out_form.get("alerts",[])}
    for alert in root.findall(".//Alert"):
        aname = alert.attrib.get("Name","").upper()
        if aname:
            if aname in out_alerts: ok(f"{fname}.alert.{aname}")
            else: miss(f"{fname}.alert.{aname}")

    out_tabs = {tp["name"].upper()
                for canvas in out_form.get("canvases",[])
                for tp in canvas.get("tab_pages",[])}
    for tp in root.findall(".//TabPage"):
        tpname = tp.attrib.get("Name","").upper()
        if tpname:
            if tpname in out_tabs: ok(f"{fname}.tabpage.{tpname}")
            else: miss(f"{fname}.tabpage.{tpname}")

    out_fmt = {item["name"].upper()
               for block in out_form.get("blocks",[])
               for item in block.get("items",[])
               if item.get("format_mask")}
    for item in root.findall(".//Item"):
        if item.attrib.get("FormatMask"):
            iname = item.attrib.get("Name","").upper()
            if iname in out_fmt: ok(f"{fname}.formatmask.{iname}")
            else: miss(f"{fname}.formatmask.{iname}")


# ── MENU ITEMS ────────────────────────────────────────────────────────────────
menu_src = r(next((SRC/"forms/menus").glob("*.sql")))
src_menu_items = set()
for line in menu_src.splitlines():
    stripped = re.sub(r"^--\s?","",line)
    m = re.match(r"^\s*[│ ]*[├└]──\s+(.+?)\s{2,}\(", stripped)
    if m:
        label = m.group(1).strip()
        if not label.startswith("─"):
            src_menu_items.add(label.upper())
out_items = {i["label"].upper() for m in menus
             for items in m.get("menus",{}).values() for i in items}
for item in sorted(src_menu_items):
    if item in out_items: ok(f"menu.{item}")
    else: miss(f"menu.{item}")


# ── PLL LIBRARIES ─────────────────────────────────────────────────────────────
for lf in sorted((SRC/"forms/libraries").glob("*.sql")):
    lname = lf.stem.replace(".pll","").upper()
    out_lib = next((l for l in pll if l["name"].upper()==lname), None)
    if not out_lib: miss(f"library {lname}"); continue
    ok(f"library {lname}")
    out_procs = {p["name"].upper() for p in out_lib.get("procedures",[])+out_lib.get("functions",[])}
    for m in re.finditer(r"^(?:PROCEDURE|FUNCTION)\s+(\w+)", r(lf), re.M|re.I):
        name = m.group(1).upper()
        if name in out_procs: ok(f"{lname}.{name}")
        else: miss(f"{lname}.{name} [pll missing]")


# ── SEED ROWS ─────────────────────────────────────────────────────────────────
src_inserts = sum(len(re.findall(r"INSERT INTO", r(sf), re.I)) for sf in (SRC/"data/seed").glob("*.sql"))
out_inserts = sum(s["total_rows"] for s in seed)
if out_inserts >= src_inserts: ok(f"seed rows {out_inserts}/{src_inserts}")
else: miss(f"seed rows {out_inserts}/{src_inserts}")


# ── RESULTS ───────────────────────────────────────────────────────────────────
total = len(hits) + len(misses)
pct   = round(100*len(hits)/total, 1) if total else 0

print(f"\n{'='*60}")
print(f"AUDIT RESULT: {len(hits)}/{total} items verified  ({pct}%)")
print(f"{'='*60}")
if misses:
    print(f"\nMISSING {len(misses)} items:")
    for m in misses: print(m)
else:
    print("\nNO MISSES — every element verified against source.")
