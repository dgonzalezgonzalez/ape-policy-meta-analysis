"""Build one record per latest SDE-table family, without silent version fallback."""
import argparse
import hashlib
import json
import re
import numpy as np
import pandas as pd
from paths import RAW, PROCESSED, OUTPUT
from orientation import orientation


def identity(record, se=False):
    """Diagnostic, allowing 10% SDE / 15% SE rounding discrepancy.

    Not testable if continuous SD(X) is unreported. Never infer SD(X) from the
    effect whose validity is being checked (that would make the check circular).
    """
    value = record.get("se" if se else "beta")
    target = record.get("se_sde" if se else "sde")
    sy, sx = record.get("sd_y"), record.get("sd_x")
    est = record.get("estimand")
    if value is None or target is None or sy is None or sy <= 0 or est not in ("binary", "continuous"):
        return "untestable"
    if est == "continuous" and sx is None:
        return "untestable"
    implied = value / sy * (sx if est == "continuous" else 1)
    tolerance = (.15 if se else .10) * max(abs(target), 1e-4 if se else .02)
    return "pass" if abs(implied - target) <= tolerance else "fail"


def extract_sources():
    """Release factual numeric/metadata extracts; upstream prose stays local."""
    recs = json.loads((PROCESSED / "parsed_full.json").read_text(encoding="utf-8"))
    # Frozen factual rating subset is sufficient; do not refresh the leaderboard.
    lb = json.loads((RAW / "rating_records.json").read_text(encoding="utf-8"))
    lbi = {p["id"]: p for p in lb}
    rawfiles = sorted((RAW / "sde").glob("*.tex"))
    latest = {}
    for file in rawfiles:
        fam, ver = file.stem.split("__")
        if fam not in latest or int(ver[1:]) > int(latest[fam][1:]):
            latest[fam] = ver
    # Whitelist prevents long source prose and unintended fields entering release.
    keep = ["paper_version_id", "paper_family_id", "version", "sde", "se_sde", "beta", "se", "sd_x", "sd_y",
            "valid", "invalid_reason", "classification", "outcome_label", "estimand", "method", "country",
            "region", "published_at", "study_year_start", "study_year_end", "n_obs", "row_index", "n_cells",
            "n_header_cells", "n_rows_in_table", "standardization_ambiguous", "source_path", "title"]
    records = []
    recindex = {r["paper_version_id"]: r for r in recs}
    for fam, ver in sorted(latest.items()):
        vid = fam + "_" + ver
        src = recindex.get(vid, {})
        record = {k: src.get(k) for k in keep}
        record.update(paper_family_id=fam, paper_version_id=vid, version=ver,
                      has_numeric_sde=bool(src), sde_identity=identity(src), se_identity=identity(src, se=True))
        record["source_path"] = fam + "/" + ver + "/tables/tabF1_sde.tex"
        metadata_path = RAW / "meta" / (fam + "__" + ver + ".json")
        if not src and metadata_path.exists():
            metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
            for key in ("title", "method", "published_at"):
                record[key] = metadata.get(key)
        record["table_sha256"] = hashlib.sha256((RAW / "sde" / (fam + "__" + ver + ".tex")).read_bytes()).hexdigest()
        for k in ("mu", "sigma", "matches", "valid_matches", "scan_verdict", "is_annulled", "authoring_model"):
            record[k] = lbi.get(vid, {}).get(k)
        if not src:
            record.update(valid=False, invalid_reason="latest table has no parseable standardized effect")
        records.append(record)
    (RAW / "source_records.json").write_text(json.dumps(records, ensure_ascii=False, indent=1), encoding="utf-8")
    print("Factual source snapshot:", len(records), "latest families")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--extract", action="store_true")
    args = ap.parse_args()
    if args.extract:
        extract_sources()
    records = json.loads((RAW / "source_records.json").read_text(encoding="utf-8"))
    responses = {}
    directions = {}
    from jev_enrich import Q, MODEL
    for line in (RAW / "jev_annotations.jsonl").read_text(encoding="utf-8").splitlines():
        r = json.loads(line)
        if r.get("answers"):
            responses[r["paper_version_id"]] = r
    for line in (RAW/'jev_direction_context.jsonl').read_text(encoding='utf-8').splitlines():
        response = json.loads(line)
        if response.get('answers'):
            directions[response['paper_version_id']] = response
    # Verify annotation hashes when source notes are available. Offline users
    # verify the shipped response file checksum instead of needing upstream prose.
    full_path = PROCESSED / "parsed_full.json"
    if args.extract and full_path.exists():
        from jev_enrich import fingerprint
        for rec in json.loads(full_path.read_text(encoding="utf-8")):
            response = responses.get(rec["paper_version_id"])
            if response and response["request_sha256"] != fingerprint(rec)[0]:
                raise ValueError("Stale annotation: " + rec["paper_version_id"])
            contextual = directions.get(rec['paper_version_id'])
            if contextual:
                from jev_direction import fingerprint as direction_fingerprint
                if contextual['request_sha256'] != direction_fingerprint(rec)[0]:
                    raise ValueError('Stale contextual direction: '+rec['paper_version_id'])
    rows = []
    seen_tables = {}
    for rec in records:
        row = dict(rec)
        res = responses.get(rec["paper_version_id"], {})
        base_answers = res.get('answers', {})
        contextual = directions.get(rec['paper_version_id'], {})
        if rec['has_numeric_sde'] and not contextual.get('answers'):
            raise ValueError('Missing frozen contextual direction: '+rec['paper_version_id'])
        a = dict(base_answers)
        a.update(contextual.get('answers', {}))
        o = orientation(a)
        original = orientation(base_answers, .20, .60, .60, .40)
        notes_relaxed = orientation(base_answers)
        context_strict = orientation(a, .20, .60, .60, .40)
        unguarded = orientation(a, apply_qualifiers=False)
        sign = o["sign"]
        sde = rec["sde"]
        row.update(sde_raw=sde, welfare_sign=sign, sign_reason=o["reason"], sign_margin=o["margin"],
                   goal_sign=o["goal_sign"], routes_agree=o["agreement"], annotation_model=res.get("model"),
                   request_sha256=res.get("request_sha256"),
                   sde_welfare=sde * sign if sde is not None and sign else None,
                   sde_goal=sde * o["goal_sign"] if sde is not None and o["goal_sign"] else None,
                   abs_sde=abs(sde) if sde is not None else None)
        row.update(notes_strict_sign=original['sign'], notes_relaxed_sign=notes_relaxed['sign'],
                   context_strict_sign=context_strict['sign'],
                   context_unguarded_sign=unguarded['sign'],
                   direction_annotation_model=contextual.get('model'),
                   direction_request_sha256=contextual.get('request_sha256'),
                   direction_context_characters=contextual.get('context_characters'),
                   direction_context_sha256=contextual.get('context_sha256'))
        for key, answer in a.items():
            if answer["type"] == "noul":
                row[key] = answer["noul"]
            elif answer["type"] == "choice":
                row[key] = answer["choice"]
                row["conf_" + key] = answer["confidence"]
            elif answer["type"] == "score":
                row[key] = answer["score"]
        row["duplicate_of"] = seen_tables.get(rec["table_sha256"])
        seen_tables.setdefault(rec["table_sha256"], rec["paper_version_id"])
        row["comparable_before_dedup"] = bool(rec["valid"] and rec["se_sde"] is not None and rec["se_sde"] > 0
            and rec["estimand"] in ("binary", "continuous") and not rec["standardization_ambiguous"]
            and rec["method"] != "Bunching")
        row["standardized_sample"] = row["comparable_before_dedup"] and row["duplicate_of"] is None
        row["rated"] = bool(rec["mu"] is not None and rec["valid_matches"] is not None
                            and rec["valid_matches"] > 0 and not rec["is_annulled"])
        row["pub_week"] = pd.to_datetime(rec["published_at"], utc=True).isocalendar().week if rec["published_at"] else None
        row["study_year_mid"] = (rec["study_year_start"] + rec["study_year_end"]) / 2 if rec["study_year_start"] and rec["study_year_end"] else None
        rows.append(row)
    df = pd.DataFrame(rows)
    df.to_csv(PROCESSED / "dataset.csv", index=False)
    summary = {"families": len(df), "numeric": int(df.has_numeric_sde.sum()), "valid": int(df.valid.sum()),
               "standardized": int(df.standardized_sample.sum()),
               "oriented": int((df.standardized_sample & df.welfare_sign.ne(0)).sum()),
               "rated": int((df.standardized_sample & df.rated).sum()),
               "exclusions": {str(k): int(v) for k, v in df.invalid_reason.value_counts().items()}}
    (OUTPUT / "sample_flow.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
