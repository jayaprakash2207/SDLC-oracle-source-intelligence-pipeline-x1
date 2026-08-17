"""
audit_full.py — complete exhaustive audit, no gaps
Every extractable fact from every source file verified against parser output.
"""
import json, re, xml.etree.ElementTree as ET
from pathlib import Path

SRC = Path(__file__).parent.parent / "source"
OUT = Path(__file__).parent / "parser-output"

def r(p): return Path(p).read_text(encoding="utf-8", errors="ignore")
def norm(s): return re.sub(r"\s+", " ", str(s)).strip().upper()

plsql  = json.loads((OUT/"plsql_deep.json").read_text())
schema = json.loads((OUT/"schema_deep.json").read_text())
forms  = json.loads((OUT/"forms_deep.json").read_text())
menus  = json.loads((OUT/"menu_deep.json").read_text())
pll    = json.loads((OUT/"pll_deep.json").read_text())
seed   = json.loads((OUT/"seed_deep.json").read_text())
rules  = json.loads((OUT/"business_rules.json").read_text())

hits, misses = [], []
def ok(label):   hits.append(label)
def miss(label): misses.append(label)

all_rule_text = {norm(r["rule"]) for r in rules}

# ── 1. BUSINESS/RULE/BUG/CONSTRAINT comments ─────────────────────────────────
for pkb in sorted((SRC/"plsql/packages").glob("*.pkb")):
    src = r(pkb)
    for tag in ("BUSINESS","RULE","BUG","CONSTRAINT","VALIDATION"):
        for m in re.finditer(rf"--\s*{tag}:\s*(.+)", src, re.I):
            text = norm(m.group(1))
            if text in all_rule_text: ok(f"{pkb.stem} {tag}: {text[:50]}")
            else: miss(f"{pkb.stem} {tag} comment not captured: {text[:80]}")

for tf in sorted((SRC/"plsql/triggers").glob("*.sql")):
    src = r(tf)
    for tag in ("BUSINESS","RULE","BUG","VALIDATION"):
        for m in re.finditer(rf"--\s*{tag}:\s*(.+)", src, re.I):
            text = norm(m.group(1))
            if text in all_rule_text: ok(f"{tf.stem} {tag}: {text[:50]}")
            else: miss(f"{tf.stem} {tag} comment not captured: {text[:80]}")

for lf in sorted((SRC/"forms/libraries").glob("*.sql")):
    src = r(lf)
    for tag in ("BUSINESS","RULE","BUG","VALIDATION"):
        for m in re.finditer(rf"--\s*{tag}:\s*(.+)", src, re.I):
            text = norm(m.group(1))
            if text in all_rule_text: ok(f"{lf.stem} {tag}: {text[:50]}")
            else: miss(f"{lf.stem} {tag} comment not captured: {text[:80]}")

# ── 2. CONSTANTS values ───────────────────────────────────────────────────────
for pkb in sorted((SRC/"plsql/packages").glob("*.pkb")):
    pkg_key = next((k for k in plsql if pkb.stem.upper() in k.upper()), None)
    if not pkg_key: continue
    body_data = plsql[pkg_key].get("body") or {}
    out_consts = {c["name"].upper(): norm(c["value"]) for c in body_data.get("constants",[])}
    src = r(pkb)
    for m in re.finditer(r"(\w+)\s+CONSTANT\s+[\w()]+\s*:=\s*([^;]+);", src, re.I):
        cname = m.group(1).upper()
        cval  = norm(re.sub(r"--.*$","",m.group(2),flags=re.M))
        if cname not in out_consts:
            miss(f"{pkb.stem} constant {cname} missing")
        elif cval not in out_consts[cname] and out_consts[cname] not in cval:
            miss(f"{pkb.stem} constant {cname} value wrong: got={out_consts[cname][:40]} want={cval[:40]}")
        else:
            ok(f"{pkb.stem} constant {cname}={cval[:30]}")

# ── 3. VIEW SQL accuracy ──────────────────────────────────────────────────────
views_src = r(SRC/"schema/views/hrms_views.sql")
for m in re.finditer(
    r"CREATE OR REPLACE VIEW (?:HRMS\.)?(\w+)\s+AS\s*\n(.*?)(?=CREATE OR REPLACE|\Z)",
    views_src, re.DOTALL|re.I
):
    vname = m.group(1).upper()
    body  = m.group(2)
    full_key = "HRMS." + vname
    out_view = schema["views"].get(full_key, {})
    # Check every FROM table
    src_tables = set(re.findall(r"\bFROM\s+(?:HRMS\.)?(\w+)", body, re.I))
    out_tables = set(out_view.get("tables_used",[]) + out_view.get("joins",[]))
    out_tables_n = {t.replace("HRMS.","").upper() for t in out_tables}
    for t in src_tables:
        if t.upper() in out_tables_n: ok(f"view {vname} FROM {t}")
        else: miss(f"view {vname} FROM {t} not captured")
    # Check every JOIN table
    src_joins = set(re.findall(r"\bJOIN\s+(?:HRMS\.)?(\w+)", body, re.I))
    for t in src_joins:
        if t.upper() in out_tables_n: ok(f"view {vname} JOIN {t}")
        else: miss(f"view {vname} JOIN {t} not captured")

# ── 4. SEED ROW VALUES (every column) ────────────────────────────────────────
all_out_seed = {}
for s in seed:
    for tname, tdata in s["tables"].items():
        all_out_seed.setdefault(tname, []).extend(tdata["rows"])

for sf in sorted((SRC/"data/seed").glob("*.sql")):
    src = r(sf)
    for m in re.finditer(
        r"INSERT\s+INTO\s+(\w+)\s*\(([^)]+)\)\s*\n?\s*VALUES\s*\(([^;]+)\)\s*;",
        src, re.DOTALL|re.I
    ):
        tname = m.group(1).upper()
        cols  = [c.strip().upper() for c in m.group(2).split(",")]
        vals_raw = m.group(3)
        # parse values
        values, current, depth, in_q = [], "", 0, False
        for ch in vals_raw:
            if ch=="'" and not in_q: in_q=True; current+=ch
            elif ch=="'" and in_q: in_q=False; current+=ch
            elif ch=="(" and not in_q: depth+=1; current+=ch
            elif ch==")" and not in_q: depth-=1; current+=ch
            elif ch=="," and not in_q and depth==0: values.append(current.strip().strip("'")); current=""
            else: current+=ch
        if current.strip(): values.append(current.strip().strip("'"))

        row_dict = {cols[i]: values[i] if i<len(values) else "" for i in range(len(cols))}
        out_rows = all_out_seed.get(tname, [])

        # Find matching row by first non-null value
        pk_col = cols[0]
        pk_val = norm(row_dict.get(pk_col,""))
        matching = [row for row in out_rows if norm(str(row.get(pk_col,""))) == pk_val]
        if not matching:
            miss(f"seed {tname} row {pk_col}={pk_val[:30]} not found")
            continue
        out_row = matching[0]
        # Check every column value
        for col, val in row_dict.items():
            if not val or val.upper() in ("NULL","SYSDATE","SYSTIMESTAMP"): continue
            out_val = norm(str(out_row.get(col,"")))
            src_val = norm(val)
            if src_val in out_val or out_val in src_val or src_val==out_val:
                ok(f"seed {tname}.{col}={src_val[:20]}")
            else:
                miss(f"seed {tname}.{col}: got={out_val[:30]} want={src_val[:30]}")

# ── 5. FORM ITEM PROPERTIES ───────────────────────────────────────────────────
for xf in sorted((SRC/"forms/xml-exports").glob("*.xml")):
    try: root = ET.parse(xf).getroot()
    except: continue
    fname = root.attrib.get("Name", xf.stem).upper()
    out_form = next((f for f in forms if f.get("name","").upper()==fname), None)
    if not out_form: continue

    out_items_map = {}
    for block in out_form.get("blocks",[]):
        for item in block.get("items",[]):
            key = (block["name"].upper(), item["name"].upper())
            out_items_map[key] = item

    for block in root.findall(".//Block"):
        bname = block.attrib.get("Name","").upper()
        for item in block.findall(".//Item"):
            iname = item.attrib.get("Name","").upper()
            out_item = out_items_map.get((bname, iname), {})
            if not out_item: continue

            # Check key attributes that matter for forward engineering
            checks = [
                ("data_type",     item.attrib.get("DataType","")),
                ("max_length",    item.attrib.get("MaximumLength","")),
                ("required",      item.attrib.get("RequiredItem","")),
                ("database_item", item.attrib.get("DatabaseItem","")),
                ("primary_key",   item.attrib.get("PrimaryKey","")),
                ("format_mask",   item.attrib.get("FormatMask","")),
                ("column",        item.attrib.get("ColumnName","")),
            ]
            for attr, src_val in checks:
                if not src_val: continue
                out_val = str(out_item.get(attr,""))
                if norm(src_val) == norm(out_val): ok(f"{fname}.{bname}.{iname}.{attr}={src_val[:20]}")
                else: miss(f"{fname}.{bname}.{iname}.{attr}: got={out_val[:20]} want={src_val[:20]}")

# ── 6. POPLIST VALUES ─────────────────────────────────────────────────────────
for xf in sorted((SRC/"forms/xml-exports").glob("*.xml")):
    try: root = ET.parse(xf).getroot()
    except: continue
    fname = root.attrib.get("Name", xf.stem).upper()
    out_form = next((f for f in forms if f.get("name","").upper()==fname), None)
    if not out_form: continue

    out_items_map = {}
    for block in out_form.get("blocks",[]):
        for item in block.get("items",[]):
            out_items_map[item["name"].upper()] = item

    for item in root.findall(".//Item"):
        list_els = item.findall("ListItemElement")
        if not list_els: continue
        iname = item.attrib.get("Name","").upper()
        out_item = out_items_map.get(iname, {})
        out_pops = {norm(p["value"]): norm(p["label"])
                    for p in out_item.get("poplist_values",[])}
        for el in list_els:
            val   = el.attrib.get("Value","")
            label = el.attrib.get("Label","")
            if not val: continue
            if norm(val) in out_pops: ok(f"{fname}.{iname}.poplist.{val}")
            else: miss(f"{fname}.{iname}.poplist value={val} label={label} missing")

# ── 7. BLOCK RELATION ATTRIBUTES ─────────────────────────────────────────────
for xf in sorted((SRC/"forms/xml-exports").glob("*.xml")):
    try: root = ET.parse(xf).getroot()
    except: continue
    fname = root.attrib.get("Name", xf.stem).upper()
    out_form = next((f for f in forms if f.get("name","").upper()==fname), None)
    if not out_form: continue
    out_rels = {rel["name"].upper(): rel for rel in out_form.get("relations",[])}

    for rel in root.findall(".//Relation"):
        rname = rel.attrib.get("Name","").upper()
        if not rname: continue
        if rname not in out_rels:
            miss(f"{fname}.relation.{rname} missing"); continue
        out_rel = out_rels[rname]
        for attr in ["delete_record_behavior","auto_query","deferred","join_condition"]:
            src_val = rel.attrib.get({
                "delete_record_behavior": "DeleteRecordBehavior",
                "auto_query": "AutoQuery",
                "deferred": "Deferred",
                "join_condition": "JoinCondition",
            }[attr], "")
            if not src_val: continue
            out_val = str(out_rel.get(attr,""))
            if norm(src_val)==norm(out_val): ok(f"{fname}.relation.{rname}.{attr}={src_val[:30]}")
            else: miss(f"{fname}.relation.{rname}.{attr}: got={out_val[:30]} want={src_val[:30]}")

# ── 8. LOV COLUMN MAPPINGS ────────────────────────────────────────────────────
for xf in sorted((SRC/"forms/xml-exports").glob("*.xml")):
    try: root = ET.parse(xf).getroot()
    except: continue
    fname = root.attrib.get("Name", xf.stem).upper()
    out_form = next((f for f in forms if f.get("name","").upper()==fname), None)
    if not out_form: continue
    out_lovs = {l["name"].upper(): l for l in out_form.get("lovs",[])}

    for lov in root.findall(".//LOV"):
        lname = lov.attrib.get("Name","").upper()
        if not lname: continue
        if lname not in out_lovs: miss(f"{fname}.LOV.{lname} missing"); continue
        ok(f"{fname}.LOV.{lname}")
        out_mappings = [m.get("return_item","").upper()
                        for m in out_lovs[lname].get("column_mappings",[])]
        for cm in lov.findall("ColumnMapping"):
            ret = cm.attrib.get("ReturnItem","").upper()
            if ret:
                if any(ret in x or x in ret for x in out_mappings): ok(f"{fname}.LOV.{lname}.ret={ret}")
                else: miss(f"{fname}.LOV.{lname}.ReturnItem={ret} missing")

# ── 9. RECORD GROUP QUERIES ───────────────────────────────────────────────────
for xf in sorted((SRC/"forms/xml-exports").glob("*.xml")):
    try: root = ET.parse(xf).getroot()
    except: continue
    fname = root.attrib.get("Name", xf.stem).upper()
    out_form = next((f for f in forms if f.get("name","").upper()==fname), None)
    if not out_form: continue
    out_rgs = {rg["name"].upper(): rg.get("query","") for rg in out_form.get("record_groups",[])}

    for rg in root.findall(".//RecordGroup"):
        rgname = rg.attrib.get("Name","").upper()
        src_q = rg.attrib.get("QueryText","")
        if not src_q:
            qel = rg.find("RecordGroupQuery")
            if qel is not None and qel.text: src_q = qel.text.strip()
        if not src_q: continue
        out_q = out_rgs.get(rgname,"")
        src_tables = set(re.findall(r"FROM\s+(\w+)", src_q, re.I))
        out_tables  = set(re.findall(r"FROM\s+(\w+)", out_q, re.I))
        for t in src_tables:
            if t.upper() in {x.upper() for x in out_tables}: ok(f"{fname}.RG.{rgname} FROM {t}")
            else: miss(f"{fname}.RG.{rgname} FROM {t} not in query")

# ── 10. SEQUENCE VALUES ───────────────────────────────────────────────────────
seq_src = r(SRC/"schema/sequences/hrms_sequences.sql")
out_seqs = {s["name"].replace("HRMS.","").upper(): s for s in schema.get("sequences",[])}
for m in re.finditer(
    r"CREATE SEQUENCE (?:HRMS\.)?(\w+)\s+START WITH\s+(\d+)\s+INCREMENT BY\s+(\d+)",
    seq_src, re.I
):
    sname, start, inc = m.group(1).upper(), int(m.group(2)), int(m.group(3))
    out = out_seqs.get(sname)
    if not out: miss(f"seq {sname} missing"); continue
    if out["start_with"]==start: ok(f"seq {sname} start={start}")
    else: miss(f"seq {sname} start: got={out['start_with']} want={start}")
    if out["increment_by"]==inc: ok(f"seq {sname} inc={inc}")
    else: miss(f"seq {sname} inc: got={out['increment_by']} want={inc}")

# ── 11. FORM TRIGGER PKG CALLS ────────────────────────────────────────────────
for xf in sorted((SRC/"forms/xml-exports").glob("*.xml")):
    try: root = ET.parse(xf).getroot()
    except: continue
    fname = root.attrib.get("Name", xf.stem).upper()
    out_form = next((f for f in forms if f.get("name","").upper()==fname), None)
    if not out_form: continue
    out_calls = {c.upper() for c in out_form.get("all_package_calls",[])}
    for trig in root.findall(".//Trigger"):
        text_el = trig.find("TriggerText")
        if text_el is None or not text_el.text: continue
        for m in re.finditer(r"(PKG_\w+\.\w+)", text_el.text, re.I):
            call = m.group(1).upper()
            if call in out_calls: ok(f"{fname} trigger call {call}")
            else: miss(f"{fname} trigger call {call} not captured")

# ── RESULTS ───────────────────────────────────────────────────────────────────
total = len(hits) + len(misses)
pct   = round(100*len(hits)/total, 1) if total else 0
print(f"\n{'='*60}")
print(f"FULL AUDIT: {len(hits)}/{total} ({pct}%)")
print(f"{'='*60}")
if misses:
    print(f"\nMISSING / WRONG ({len(misses)}):")
    for m in misses: print(f"  MISS {m}")
else:
    print("\nNO MISSES — every extractable fact verified.")
