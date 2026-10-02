"""Frozen-model, outcome-specific annotation, with content-addressed caching.

Network use is explicit. Offline replication uses the released responses.
No SDE, SE or leaderboard value enters the state. Notes only; never full papers.
"""
import argparse
import hashlib
import json
import re
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import requests
from paths import ROOT, RAW, PROCESSED
from jev_questions import Q as LEGACY_Q, load_key

MODEL = "jev-1.13.0"
API = "https://api.typesafe.ai/v1/systemone"
OUTPUT = RAW / "jev_annotations.jsonl"
Q = {k: v for k, v in LEGACY_Q.items() if k not in (
    "goal_is_increase", "goal_is_decrease", "outcome_is_purely_descriptive", "lower_is_better")}
COMMON = "Evaluate ONLY `selected_outcome`, using its definition in the table's own notes. "
Q.update({
    "goal_increase": {"type": "noul", "instructions": COMMON +
        "Do the notes explicitly identify increasing this outcome as the intended objective of the evaluated policy? A research question about whether it increases is not by itself an objective."},
    "goal_decrease": {"type": "noul", "instructions": COMMON +
        "Do the notes explicitly identify decreasing this outcome as the intended objective of the evaluated policy? A research question about whether it decreases is not by itself an objective."},
    "higher_benefits": {"type": "noul", "instructions": COMMON +
        "Would a higher value of this outcome, considered by itself, clearly be favourable for the affected people whose circumstances it measures? Require a clear beneficiary and economic interpretation. Greater income, survival or learning can qualify. Policy compliance, arrests, tax revenue, voting, migration, firm exit, redistribution of shares and prices without a specified beneficiary need not. A goal of the policymaker is not sufficient."},
    "lower_benefits": {"type": "noul", "instructions": COMMON +
        "Would a lower value of this outcome, considered by itself, clearly be favourable for the affected people whose circumstances it measures? Require a clear beneficiary and economic interpretation. Lower mortality, illness, unemployment or pollution exposure can qualify. Lower service use, administrative counts, prices or expenditure without a specified beneficiary need not. A goal of the policymaker is not sufficient."},
    "direction_ambiguous": {"type": "noul", "instructions": COMMON +
        "Is the economically favourable direction of this outcome indeterminate from the notes, because beneficiaries are unspecified, gains and losses differ across groups, it is a compositional or descriptive measure, or the desired level is non-monotonic? Counts and take-up can have a direction when a beneficiary and benefit are clearly defined; do not reject them just because they are counts."}
})


def build_state(record):
    notes = record.get("notes_blob", "")
    # Source notes often append standardization formulae and classification
    # thresholds. Strip these before judging outcomes or explanatory variables.
    notes = re.sub(r"\bitem\b|\[\d+pt\]", " ", notes)
    # A classification sentence sometimes PRECEDES the substantive notes.
    # Truncation at that sentence would erase the research question and data.
    notes = re.sub(r"(?i)(?=\b(?:Country|Research question|Policy mechanism|Outcome definition|Treatment|Data|Method|Sample)\s*:)", "\n", notes)
    sentences = re.split(r"\n|(?<=[.!?])\s+(?=[A-Z])", notes)
    kept = [s for s in sentences if not re.search(
        r"(?i)\bSDE\b|standardized (?:diagnostic )?effect|classification|SE\s*\(|statistical significance|"
        r"(?:coefficient|estimate|p[- ]?value)\s*(?:is|=|of|:)\s*[+-]?\d", s)]
    state = {"selected_outcome": record["outcome_label"], "table_notes": " ".join(kept).strip()}
    # Do not leak results through structured fields, which can have overlapping
    # parser windows. No such fields are transmitted.
    if not state["table_notes"]:
        state["table_notes"] = "No informative notes available."
    assert not re.search(r"(?i)\bSDE\b|SE\s*\(SDE\)|\belo\b|\btrueskill\b", json.dumps(state))
    return state


def fingerprint(record):
    body = {"model": MODEL, "questions": Q, "state": build_state(record)}
    return hashlib.sha256(json.dumps(body, sort_keys=True).encode()).hexdigest(), body


def load_cached():
    return [json.loads(line) for line in OUTPUT.read_text(encoding="utf-8").splitlines()] if OUTPUT.exists() else []


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int)
    args = parser.parse_args()
    recs = json.loads((PROCESSED / "parsed_full.json").read_text(encoding="utf-8"))
    # Select latest SOURCE version, even when it has no numeric parse. Do not
    # silently enrich an earlier table that is outside the selected sample.
    latest = {}
    for file in sorted((RAW / "sde").glob("*.tex")):
        fam, ver = file.stem.split("__")
        if fam not in latest or int(ver[1:]) > int(latest[fam][1:]):
            latest[fam] = ver
    best = {r["paper_family_id"]: r for r in recs
            if latest[r["paper_family_id"]] == r["version"]}
    cached = {(r["paper_version_id"], r["request_sha256"]) for r in load_cached() if r.get("answers")}
    todo = [r for r in sorted(best.values(), key=lambda x: x["paper_version_id"])
            if (r["paper_version_id"], fingerprint(r)[0]) not in cached]
    if args.limit:
        todo = todo[:args.limit]
    print("Uncached annotation requests:", len(todo), flush=True)
    if not todo:
        return
    key = load_key()
    def work(rec):
        import time
        sha, body = fingerprint(rec)
        for attempt in range(4):
            response = requests.post(API, headers={"Authorization": "Bearer " + key}, json=body, timeout=90)
            if response.status_code in (429, 500, 502, 503, 504):
                time.sleep(2 ** attempt)
                continue
            if response.status_code != 200:
                raise RuntimeError("TypeSafe HTTP " + str(response.status_code))
            obj = response.json()
            if set(obj.get("answers", {})) != set(Q):
                raise RuntimeError("Incomplete annotation response")
            return {"paper_version_id": rec["paper_version_id"], "request_sha256": sha,
                    "model": obj.get("model"), "answers": obj["answers"], "usage": obj.get("usage"),
                    "accessed_at": datetime.now(timezone.utc).isoformat()}
        raise RuntimeError("TypeSafe retries exhausted")
    with OUTPUT.open("a", encoding="utf-8") as fh, ThreadPoolExecutor(max_workers=8) as executor:
        for i, result in enumerate(executor.map(work, todo), 1):
            fh.write(json.dumps(result) + "\n")
            fh.flush()
            if i % 50 == 0 or i == len(todo):
                print("Annotated", i, "/", len(todo), flush=True)


if __name__ == "__main__":
    main()
