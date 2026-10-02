"""Parse the Project APE standardized-effect tables into structured records.

Header-driven (column roles found by name, not position) because the tables
vary: 7 vs 8 columns, parenthesised SEs, panel labels, 4- vs 7-category
thresholds. All arithmetic/classification stays in code.
"""
import json
import os
import re
import sys

from paths import RAW as RAW_ROOT, PROCESSED
RAW = RAW_ROOT / "sde"
META = RAW_ROOT / "meta"

# ---------------------------------------------------------------- utilities

DROP_CMDS = (
    "toprule|midrule|bottomrule|hline|hhline|endheadrule|cline|cmidrule|addlinespace|"
    "multicolumn|cline|centering|raggedright|small|footnotesize|scriptsize|"
    "par|newline|newcolumntype|begin|end|input|include|caption|label|textemdash|ldots|"
    "dots|cdots|quad|qquad|hfill|vspace|hspace|noindent|linewidth|arraystretch|tabcolsep"
)


def detex(s):
    """Flatten enough LaTeX to make text matchable.

    Two rules matter: braces are flattened BEFORE command handling (so
    \\cmd{X} keeps X), and a surviving command keeps its NAME with the
    backslash removed (so \\hat{\\beta} -> 'beta', not '').
    """
    if s is None:
        return ""
    s = s.replace("\\&", "ESCAPEDAMPERSAND").replace("\\\\", " ")
    # accents: drop the command, keep the braced argument
    s = re.sub(r"\\(?:hat|widehat|tilde|widetilde|bar|vec|dot|ddot|overline)\s*", "", s)
    s = re.sub(r"\\begin\{[^}]*\}|\\end\{[^}]*\}", " ", s)
    # \cmd{arg} -> {arg}
    s = re.sub(r"\\(?:textbf|textit|emph|mbox|text|texttt|textsc|mathrm|mathbf|operatorname|"
               r"mathbb|mathcal|mathit|mathsf|footnotesize|scriptsize|label)\s*\{", "{", s)
    s = re.sub(r"\\(?:mathbb|mathcal|mathbf|mathrm|mathit|mathsf)\s*\{([A-Za-z])\}", r"\1", s)
    s = s.replace("{", " ").replace("}", " ").replace("~", " ")
    s = re.sub(r"\\(?:%s)\b" % DROP_CMDS, " ", s)
    s = s.replace("\\&", "&").replace("\\%", "%").replace("\\_", "_")
    s = s.replace("$", "").replace("&", " ")
    s = re.sub(r"\\([a-zA-Z]+)", r"\1", s)          # \beta -> beta
    s = s.replace("\\", " ")
    return re.sub(r"\s+", " ", s).strip().replace("ESCAPEDAMPERSAND", "&")


NUM_RE = re.compile(r"^[+-]?(?:\d{1,3}(?:,\d{3})+|\d+)?(?:\.\d+)?$")


def tonum(cell):
    """Parse a numeric table cell. Parenthesised => negative. Dashes => None."""
    if cell is None:
        return None
    c = cell.strip()
    if not c:
        return None
    c = re.sub(r"\\(?:textemdash|ldots|dots|cdots|dotsb)\b", "--", c)
    c = re.sub(r"\\dashes\b", "--", c)
    c = c.replace("$-$", "--").replace("-{}-", "--")
    c = re.sub(r"\\begin\{[^}]*\}|\\end\{[^}]*\}", "", c)
    c = re.sub(r"\\[a-zA-Z]+", "", c)
    c = c.replace("{", "").replace("}", "").replace("$", "").replace("\\", "")
    c = c.replace("~", " ").strip()
    c = re.sub(r"(?i)\b(na|n/a|nan|null|none|-|--|---|\?+)\b", "--", c).strip()
    c = re.sub(r"\s+", "", c)
    if c in ("--", "-", "", "?"):
        return None
    neg = False
    if c.startswith("(") and c.endswith(")"):
        neg, c = True, c[1:-1]
    if c.startswith("--") and len(c) > 2 and NUM_RE.match(c[2:]):
        c = "-" + c[2:]                      # "--1.2" means negative
    if c.startswith("+"):
        c = c[1:]
    c = c.replace(",", "")
    if not NUM_RE.match(c):
        return None
    try:
        v = float(c)
    except ValueError:
        return None
    return -v if neg else v


def split_row(line):
    # An escaped ampersand is part of the outcome name, not a column delimiter.
    return re.split(r"(?<!\\)&", line)


def se_number(cell):
    """Parentheses mark uncertainty; an explicit minus remains invalid."""
    if cell is None:
        return None
    stripped = cell.strip().replace("$", "")
    value = tonum(cell)
    if stripped.startswith("(") and stripped.rstrip().rstrip("\\").strip().endswith(")"):
        return abs(value) if value is not None else None
    return value


def row_is_rule(line):
    return bool(re.search(r"(toprule|midrule|bottomrule|hline|multicolumn|addlinespace|cmidrule)", line))


HET_KEYS = ("heterogen", "placebo", "robust", "pre-trend", "pretrend", "alternative spec",
            "by baseline", "low baseline", "high baseline", "subsample", "split",
            "interaction", "effect hetero")


# ---------------------------------------------------------------- table parse

def parse_table(tex):
    """Return dict with columns, rows (with panel labels), notes fields."""
    out = {"ok": False, "why": None}

    blocks = re.findall(r"\\begin\{tabular\*?\}.*?\\end\{tabular\*?\}", tex, re.S)
    # Notes can be placed in a second, longer tabular. Select a data header.
    blocks = [b for b in blocks if any("&" in ln and "SDE" in detex(ln)
              and re.search(r"(?i)outcome|beta|spec", detex(ln)) for ln in b.splitlines())] or blocks
    if not blocks:
        out["why"] = "no tabular"
        return out
    tab = max(blocks, key=len)

    lines = tab.split("\n")

    # ---- header -----------------------------------------------------------
    hidx = None
    hdr_cells = None
    for i, ln in enumerate(lines):
        if "&" not in ln or row_is_rule(ln):
            continue
        cells = [detex(c) for c in split_row(ln)]
        flat = " ".join(cells)
        if "SDE" in flat and ("beta" in flat or "β" in flat or len(cells) >= 5):
            hidx, hdr_cells = i, cells
            break
    if hidx is None:
        # header split across two lines: find row with beta and one with SDE
        bidx = next((i for i, ln in enumerate(lines)
                     if "&" in ln and "beta" in detex(ln)), None)
        if bidx is None:
            out["why"] = "no header"
            return out
        hidx = bidx
        hdr_cells = [detex(c) for c in split_row(lines[hidx])]
        sidx = next((i for i, ln in enumerate(lines)
                     if "&" in ln and re.search(r"\bSDE\b", detex(ln))), None)
        if sidx is not None and sidx != hidx:
            extra = [detex(c) for c in split_row(lines[sidx])]
            if len(extra) > len(hdr_cells):
                hdr_cells = hdr_cells + [""] * (len(extra) - len(hdr_cells))

    def find(*pats, exact=None):
        best = None
        for i, h in enumerate(hdr_cells):
            hh = h.strip().lower().replace(".", "")
            if exact is not None and hh == exact:
                return i
            for p in pats:
                if p in hh and (best is None or i < best):
                    best = i
        return best

    col = {
        "outcome": find("outcome", "dependent variab", "result"),
        "spec": find("specification", "spec"),
        "beta": find("hat{beta}", "beta", "est"),
        "se": find(exact="se") or find("se(beta)", "se b", "std err"),
        "sdx": find("sd(x)", "sdx"),
        "sdy": find("sd(y)", "sdy"),
        "sde": find("sde"),
        "se_sde": find("se(sde)", "sesde", "se sde"),
        "class": find("classification", "class"),
    }
    if col["sde"] is None:
        out["why"] = "no SDE column (hdr=%s)" % hdr_cells
        return out

    # ---- body rows --------------------------------------------------------
    rows = []
    panel = ""
    for ln in lines[hidx + 1:]:
        if re.search(r"(?i)panel\s+[a-z0-9]", detex(ln)) and "multicolumn" in ln:
            panel = detex(ln)
            continue
        if row_is_rule(ln):
            continue
        raw = ln.strip()
        if not raw:
            continue
        fl = detex(raw)
        m = re.search(r"(?i)panel\s+([A-Z0-9]+)", fl)
        if m and "&" not in detex(raw).replace("\\multicolumn", "") .replace("{", "") :
            pass
        # panel label line (may or may not be a multicolumn)
        if m and not re.search(r"-?\d+\.\d", detex(raw).split("&")[0] or "x"):
            if "&" not in raw.replace("\\multicolumn", ""):
                panel = fl
                continue
        if "&" not in raw:
            continue
        cells = split_row(raw)
        if len(cells) < 2:
            continue
        plain = detex(raw)
        if re.search(r"(?i)panel\s+[A-Z0-9]", plain) and not re.search(r"-?\d+\.\d|^\s*\(", plain):
            panel = plain
            continue
        label = detex(cells[0])
        if not label:
            continue
        mc = re.match(r"\\multicolumn", cells[0].strip())
        if mc and "panel" in plain.lower():
            panel = plain
            continue

        def cell(key):
            i = col.get(key)
            if i is None or i >= len(cells):
                return None
            return cells[i]

        rec = {
            "outcome_label": label,
            "panel": panel,
            "beta": tonum(cell("beta")),
            "se": se_number(cell("se")),
            "sd_x": tonum(cell("sdx")),
            "sd_y": tonum(cell("sdy")),
            "sde": tonum(cell("sde")),
            "se_sde": se_number(cell("se_sde")),
            "classification": detex(cell("class")) if col.get("class") is not None else None,
            "spec_label": detex(cell("spec")) if col.get("spec") is not None else None,
            "row_index": len(rows),
            "n_cells": len(cells),
        }
        if rec["sde"] is not None:
            rows.append(rec)

    out.update({"ok": True, "cols": col, "rows": rows, "n_cols": len(hdr_cells)})
    return out


# ---------------------------------------------------------------- notes parse

NOTE_KEYS = ["Country", "Research question", "Policy mechanism", "Outcome definition",
             "Treatment", "Data", "Method", "Sample"]

# prose fallbacks: list of (start-regex, chars-to-capture)
PROSE_PATS = {
    "Country": [(r"(?i)\bcountry\s*(?:studied|covered|is|was|=|:)?\s*", 90)],
    "Research question": [(r"(?i)\bresearch question\s*(?:is|was|=|:)?\s*", 420)],
    "Policy mechanism": [(r"(?i)\bpolicy mechanism\s*(?:is|was|=|:)?\s*", 420)],
    "Outcome definition": [(r"(?i)\boutcome (?:definition|variable|measure)(?:\s+is|\s+=|:)?\s*", 420)],
    "Treatment": [(r"(?i)\bthe treatment\s+(?:is|was)\s+", 300)],
    "Data": [(r"(?i)\bdata\s*(?:are|is|:)\s*", 300)],
    "Method": [(r"(?i)\b(?:method|estimation|identified using|we estimate)\s*(?:is|was|=|:)?\s*", 300)],
    "Sample": [(r"(?i)\bsample\s*(?:is|was|of|=|:)?\s*", 300)],
}


def notes_region(tex):
    """The table's own notes paragraph, as plain text."""
    m = re.search(r"(?i)\\textit\{[Nn]otes?\}|\bNotes\b\s*:", tex)
    if m:
        seg = tex[m.start():]
    else:
        ends = [e.end() for e in re.finditer(r"\\end\{tabular\*?\}", tex)]
        seg = tex[ends[-1]:] if ends else tex
    return detex(seg)


def parse_notes(tex):
    """Structured fields when the table bolds them; prose windows otherwise."""
    flat = notes_region(tex)
    res = {}

    # tier 1: explicit "Key:" markers, sliced at the next marker
    marks = []
    for k in NOTE_KEYS + ["Classification", "SDE", "Note"]:
        for m in re.finditer(r"(?i)\b%s\b\s*:" % re.escape(k), flat):
            marks.append((m.start(), m.end(), k))
    marks.sort()
    for i, (s, e, k) in enumerate(marks):
        end = marks[i + 1][0] if i + 1 < len(marks) else len(flat)
        val = flat[e:end].strip(" .;,|-")
        if k in NOTE_KEYS and k not in res and 0 < len(val) < 900:
            res[k] = val

    # tier 2: prose fallback for anything still missing
    for k, pats in PROSE_PATS.items():
        if res.get(k):
            continue
        for pat, cap in pats:
            m = re.search(pat, flat)
            if m:
                val = flat[m.end(): m.end() + cap].strip(" .;,|-")
                if 3 < len(val) < 900:
                    res[k] = val
                    break
    return res


def pick_primary(rows):
    """One headline estimate per table.

    Preference order:
      1. a row in a panel whose label looks like the pooled/main estimate
      2. a row whose label is not heterogeneity-flavoured
      3. the first row with an SDE
    """
    if not rows:
        return None
    main_pat = re.compile(r"(?i)panel\s*a\b|pooled|main|baseline|overall|primary")
    het_pat = re.compile("|".join(HET_KEYS), re.I)

    for r in rows:
        if r["panel"] and main_pat.search(r["panel"]) and not het_pat.search(r["outcome_label"] or ""):
            return r
    for r in rows:
        if main_pat.search(r["outcome_label"] or "") and not het_pat.search(r["outcome_label"] or ""):
            return r
    for r in rows:
        if not het_pat.search(r["outcome_label"] or ""):
            return r
    return rows[0]


def guess_estimand(primary, notes, full_notes=""):
    """Binary treatments report SDE = b/SD(Y); continuous report b*SD(X)/SD(Y)."""
    if primary and primary.get("sd_x") is not None:
        return "continuous"
    blob = full_notes or " ".join(str(v) for v in notes.values())
    declares_cont = bool(re.search(r"continuous\s+(?:treatment|exposure)|treatment\s*(?:is|:)\s*continuous", blob, re.I))
    declares_bin = bool(re.search(r"binary\s+treatment|treatment\s*(?:is|:)\s*binary", blob, re.I))
    if declares_cont and declares_bin:
        return "unknown"
    if declares_cont:
        return "continuous"
    if declares_bin:
        return "binary"
    m = re.search(r"SDE\s*=", blob, re.I)
    seg = blob[m.start(): m.start() + 220] if m else blob[:220]
    if re.search(r"SD\s*\(\s*X\s*\)", seg, re.I):
        return "continuous"
    t = notes.get("Treatment", "") or ""
    if re.match(r"(?i)\s*continuous", t):
        return "continuous"
    if re.match(r"(?i)\s*binary", t):
        return "binary"
    return "binary" if primary and primary.get("sd_x") is None else "unknown"


YEAR_RANGE = re.compile(r"\b(1[89]\d{2}|20\d{2})\s*(?:--|-|to|–|through|thru)\s*(1[89]\d{2}|20\d{2})\b")

NOBS_PATS = [
    re.compile(r"(?i)\bN\s*(?:=|is|of|=|:)\s*([\d][\d,\.]*)"),
    re.compile(r"(?i)\bsample\s+(?:of|comprising|contains|consists of|covers)\s+"
               r"(?:about |approximately |roughly |around )?([\d][\d,\.]*)"),
    re.compile(r"(?i)\b([\d][\d,]{2,})\s+(?:municipality|county|state|country|region|province|"
               r"district|individual|person|household|premise|firms?|firms|schools?|hospitals?|"
               r"laws?|students?|cases?|observations?|municipality-year|county-year|state-year|"
               r"person-year|city-year|farm|tax filers?|votes?)\b"),
    re.compile(r"(?i)\b([\d][\d,]{3,})\s+(?:LA-|quarter|observations|records|policies|"
               r"bills?|resolutions?)\b"),
]


def parse_n(sample_notes):
    """Sample size for the N-weighting robustness. Best-effort; may be None."""
    if not sample_notes:
        return None
    s = sample_notes
    for pat in NOBS_PATS:
        m = pat.search(s)
        if not m:
            continue
        raw = (m.group(1) or "").strip().rstrip(".")
        raw = re.sub(r"(?i)\s*(million|m\b|thousand|k\b)$", "", raw).strip()
        mult = 1.0
        if re.search(r"(?i)million\s*$", m.group(0)):
            mult = 1e6
        elif re.search(r"(?i)(thousand|k)\s*$", m.group(0)):
            mult = 1e3
        try:
            v = float(raw.replace(",", ""))
        except ValueError:
            continue
        if v < 5 or v > 5e8:
            continue
        return v * mult
    return None


# ---- validity of the parsed standardized effect ----------------------------
CLASS_TOKENS = ("large", "moderate", "medium", "small", "sm", "mod", "lg", "null", "negligible",
                "positive", "negative", "none")
MAX_ABS_SDE = 5.0


def norm_class(c):
    if c is None:
        return None
    s = c.lower()
    s = re.sub(r"[\[\(\{].*?[\]\)\}]", " ", s)
    s = re.sub(r"[^a-z ]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s or None


def validity(sde, se_sde, sd_y, classification):
    """Ladder of parse-validity checks. Returns (ok, reason)."""
    if sde is None:
        return False, "no SDE"
    c = norm_class(classification)
    if c is None:
        return False, "no classification label"
    if not any(t in c.split() or t in c for t in CLASS_TOKENS):
        return False, "classification not a label (column shift?)"
    if not re.search(r"(?i)\b(large|moderate|medium|small|sm|mod|lg|null|negligible)\b", c):
        return False, "classification not a magnitude label"
    if se_sde is not None and se_sde <= 0:
        return False, "SE(SDE) <= 0"
    if sd_y is not None and sd_y <= 0:
        return False, "SD(Y) <= 0"
    if abs(sde) > MAX_ABS_SDE:
        return False, "|SDE| > %.0f" % MAX_ABS_SDE
    return True, "ok"

REGION = {
    "usa": "North America", "united states": "North America", "u.s.": "North America",
    "canada": "North America", "mexico": "North America",
    "france": "Western Europe", "uk": "Western Europe", "united kingdom": "Western Europe",
    "england": "Western Europe", "scotland": "Western Europe", "wales": "Western Europe",
    "ireland": "Western Europe", "germany": "Western Europe", "netherlands": "Western Europe",
    "belgium": "Western Europe", "austria": "Western Europe", "switzerland": "Western Europe",
    "spain": "Western Europe", "portugal": "Western Europe", "italy": "Western Europe",
    "sweden": "Western Europe", "norway": "Western Europe", "denmark": "Western Europe",
    "finland": "Western Europe", "eu": "Western Europe", "european union": "Western Europe",
    "poland": "Central & Eastern Europe", "czechia": "Central & Eastern Europe",
    "czech republic": "Central & Eastern Europe", "slovakia": "Central & Eastern Europe",
    "slovenia": "Central & Eastern Europe", "croatia": "Central & Eastern Europe",
    "hungary": "Central & Eastern Europe", "romania": "Central & Eastern Europe",
    "bulgaria": "Central & Eastern Europe", "greece": "Southern Europe",
    "estonia": "Northern Europe", "latvia": "Northern Europe", "lithuania": "Northern Europe",
    "ukraine": "Eastern Europe", "russia": "Eastern Europe", "belarus": "Eastern Europe",
    "india": "South Asia", "pakistan": "South Asia", "bangladesh": "South Asia",
    "sri lanka": "South Asia", "nepal": "South Asia",
    "china": "East Asia", "japan": "East Asia", "korea": "East Asia", "taiwan": "East Asia",
    "singapore": "East Asia", "hong kong": "East Asia", "vietnam": "Southeast Asia",
    "thailand": "Southeast Asia", "indonesia": "Southeast Asia", "malaysia": "Southeast Asia",
    "philippines": "Southeast Asia", "myanmar": "Southeast Asia", "cambodia": "Southeast Asia",
    "australia": "Oceania", "new zealand": "Oceania",
    "nigeria": "Sub-Saharan Africa", "kenya": "Sub-Saharan Africa", "south africa": "Sub-Saharan Africa",
    "ghana": "Sub-Saharan Africa", "ethiopia": "Sub-Saharan Africa", "tanzania": "Sub-Saharan Africa",
    "uganda": "Sub-Saharan Africa", "zimbabwe": "Sub-Saharan Africa", "egypt": "North Africa",
    "morocco": "North Africa", "brazil": "Latin America", "mexico ": "Latin America",
    "argentina": "Latin America", "chile": "Latin America", "colombia": "Latin America",
    "peru": "Latin America", "venezuela": "Latin America", "bolivia": "Latin America",
    "ecuador": "Latin America", "uruguay": "Latin America", "paraguay": "Latin America",
    "costa rica": "Latin America", "dominican": "Latin America", "turkey": "Middle East",
    "israel": "Middle East", "saudi": "Middle East", "uae": "Middle East", "iran": "Middle East",
    "qatar": "Middle East", "kuwait": "Middle East", "jordan": "Middle East",
}


def to_region(country_raw):
    c = (country_raw or "").strip().lower()
    if not c:
        return None
    for k, v in REGION.items():
        if re.search(r"(?<![a-z])%s" % re.escape(k.strip()), c):
            return v
    return "Other / not stated"


def clean_country(country_raw):
    c = (country_raw or "").strip()
    c = re.split(r"(?<=[a-z])\.\s", c)[0]
    c = re.sub(r"\s*\(.*?\)\s*", " ", c)
    c = re.sub(r"\b(and|with)\s+(five|six|seven|[a-z]+)\s+[A-Za-z ]*(peer|comparison|control)\b.*$",
               "", c, flags=re.I)
    c = re.sub(r"\s+", " ", c).strip(" .,-")
    return c or None


# ---------------------------------------------------------------- driver

def main():
    files = sorted(f for f in os.listdir(RAW) if f.endswith(".tex"))
    recs, problems = [], []
    for fn in files:
        ver = fn[:-4].replace("__", "/")
        tex = open(os.path.join(RAW, fn), encoding="utf-8").read()
        p = parse_table(tex)
        notes = parse_notes(tex)
        nfull = notes_region(tex)
        if not p["ok"]:
            problems.append((ver, p["why"]))
            continue
        primary = pick_primary(p["rows"])
        if primary is None or primary["sde"] is None:
            problems.append((ver, "no sde rows"))
            continue
        mp = os.path.join(META, ver.replace("/", "__") + ".json")
        md = json.load(open(mp, encoding="utf-8")) if os.path.exists(mp) else {}

        ctry_raw = notes.get("Country")
        ctry = clean_country(ctry_raw)
        yr = YEAR_RANGE.search(" ".join(str(v) for v in notes.values()))
        n_obs = parse_n(notes.get("Sample"))

        api = md.get("api_usage") or {}
        ok_v, why_v = validity(primary["sde"], primary["se_sde"], primary["sd_y"],
                               primary["classification"])
        recs.append({
            "paper_family_id": ver.split("/")[0],
            "version": ver.split("/")[1],
            "paper_version_id": "%s_%s" % (ver.split("/")[0], ver.split("/")[1]),
            "title": md.get("title"),
            "method": md.get("method"),
            "workflow": md.get("workflow"),
            "authoring_model": md.get("authoring_model"),
            "published_at": md.get("published_at"),
            "is_revision": md.get("is_revision"),
            "cost_usd": api.get("total_cost_usd"),
            "tokens_in": api.get("total_tokens_in"),
            "sde": primary["sde"],
            "se_sde": primary["se_sde"],
            "beta": primary["beta"],
            "se": primary["se"],
            "sd_x": primary["sd_x"],
            "sd_y": primary["sd_y"],
            "classification": primary["classification"],
            "outcome_label": primary["outcome_label"],
            "spec_label": primary["spec_label"],
            "panel_label": primary["panel"],
            "estimand": guess_estimand(primary, notes, nfull),
            "country_raw": ctry_raw,
            "country": ctry,
            "region": to_region(ctry_raw),
            "outcome_definition": notes.get("Outcome definition"),
            "research_question": notes.get("Research question"),
            "policy_mechanism": notes.get("Policy mechanism"),
            "treatment": notes.get("Treatment"),
            "data_src": notes.get("Data"),
            "method_notes": notes.get("Method"),
            "sample_notes": notes.get("Sample"),
            "study_year_start": int(yr.group(1)) if yr else None,
            "study_year_end": int(yr.group(2)) if yr else None,
            "n_obs": n_obs,
            "n_rows_in_table": len(p["rows"]),
            "valid": ok_v,
            "invalid_reason": why_v,
            "notes_blob": nfull,
            "row_index": primary["row_index"],
            "n_cells": primary["n_cells"],
            "n_header_cells": p["n_cols"],
            "source_path": ver + "/tables/tabF1_sde.tex",
            "standardization_ambiguous": bool(re.search(r"(?i)bunching|excess mass|elasticity", primary["outcome_label"])),
        })

    out = PROCESSED / "parsed_full.json"
    json.dump(recs, open(out, "w", encoding="utf-8"))
    json.dump(problems, open(PROCESSED / "parse_failures.json", "w", encoding="utf-8"))
    print("parsed tables with a usable SDE : %d / %d" % (len(recs), len(files)))
    print("problems: %d" % len(problems))
    for v, w in problems[:20]:
        print("   ", v, "|", w)
    fams = {r["paper_family_id"] for r in recs}
    print("paper families: %d" % len(fams))
    n_se = sum(1 for r in recs if r["se_sde"] is not None and r["se_sde"] > 0)
    print("with usable SE(SDE)>0: %d" % n_se)
    from collections import Counter
    print("validity ladder:")
    for k, v in Counter(r["invalid_reason"] for r in recs).most_common():
        print("   %-38s %d" % (k, v))
    print("estimand:", {k: sum(1 for r in recs if r["estimand"] == k)
                        for k in ("binary", "continuous", "unknown")})
    print("country parsed:", sum(1 for r in recs if r["country"]),
          " region parsed:", sum(1 for r in recs if r["region"]))
    print("study year range:", sum(1 for r in recs if r["study_year_start"]))
    print("n_obs parsed:", sum(1 for r in recs if r["n_obs"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
