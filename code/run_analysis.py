"""All empirical results, including exclusions and directional sensitivity."""
import json
import numpy as np
import pandas as pd
from scipy import stats
from paths import RAW, PROCESSED, OUTPUT
from meta import full_meta, regression, weighted_mean, egger
from orientation import orientation
from quality_sensitivity import rating_sensitivity

SEED = 20261002
SPECS = {
    "Basic": (["log_se"], ["method", "region", "pub_week", "estimand"]),
    "Design": (["log_se", "design_strength"], ["method", "region", "pub_week", "estimand"]),
    "Reporting": (["log_se", "design_strength", "policy_intensity", "parallel_trends_tested",
                   "reports_robustness", "data_source_official"], ["method", "region", "pub_week", "estimand"]),
    "Full": (["log_se", "design_strength", "policy_intensity", "parallel_trends_tested",
               "reports_robustness", "data_source_official"], ["method", "region", "pub_week", "estimand", "policy_family"])
}


def design(df, continuous, categorical):
    X, names = [np.ones(len(df))], ["const"]
    references, dropped = {}, []
    for col in continuous:
        values = df[col].to_numpy(float)
        if np.std(values) < 1e-12:
            dropped.append(col)
            continue
        X.append(values); names.append(col)
    for col in categorical:
        values = df[col].fillna("Missing").astype(str)
        counts = values.value_counts()
        values = values.where(values.map(counts) >= 10, "Other")
        reference = values.value_counts().index[0]
        references[col] = reference
        for level in sorted(values.unique()):
            if level == reference:
                continue
            candidate = values.eq(level).to_numpy(float)
            matrix = np.column_stack(X + [candidate])
            if np.linalg.matrix_rank(matrix) == len(X) + 1:
                X.append(candidate); names.append(col + "=" + level)
            else:
                dropped.append(col + "=" + level)
    return np.column_stack(X), names, references, dropped


def fit_specs(df, outcome, specifications):
    continuous = sorted(set(c for name in specifications for c in SPECS[name][0]))
    complete = df.dropna(subset=[outcome] + continuous).copy()
    results = {}
    for name in specifications:
        cc, cat = SPECS[name]
        X, names, references, dropped = design(complete, cc, cat)
        if len(complete) <= X.shape[1] + 2:
            results[name] = {"error": "Insufficient residual degrees of freedom", "n": len(complete)}
            continue
        fit = regression(complete[outcome], X, names)
        fit.update(references=references, dropped=dropped, continuous=cc, categorical=cat,
                   weight="Equal paper weights", sample_ids=complete.paper_version_id.tolist())
        results[name] = fit
    return results


def grouped_bootstrap(df, col, B=999):
    """Country-group resampling for dependence sensitivity, deterministic seed."""
    rng = np.random.default_rng(SEED)
    groups = [g.index.to_numpy() for _, g in df.groupby(df.country.fillna("Missing"), sort=True)]
    draws = []
    for _ in range(B):
        idx = np.concatenate([groups[j] for j in rng.integers(len(groups), size=len(groups))])
        sample = df.loc[idx]
        draws.append(float(sample[col].mean()))
    return {"groups": len(groups), "replications": B, "estimate": float(df[col].mean()),
            "lo": float(np.quantile(draws, .025)), "hi": float(np.quantile(draws, .975))}


def main():
    df = pd.read_csv(PROCESSED / "dataset.csv")
    source = df[df.standardized_sample].copy()
    source["log_se"] = np.log(source.se_sde)
    oriented = source[source.welfare_sign.ne(0)].copy()
    R = {"sample": json.loads((OUTPUT / "sample_flow.json").read_text()), "seed": SEED,
         "sign_reasons": {str(k): int(v) for k, v in source.sign_reason.value_counts().items()},
         "sample_by_estimand": {str(k): int(v) for k, v in source.estimand.value_counts().items()},
         "oriented_by_estimand": {str(k): int(v) for k, v in oriented.estimand.value_counts().items()},
         "notes_empty": int((source.sign_reason == "missing response").sum())}
    R["distribution"] = {}
    for est in ("binary", "continuous"):
        d = source[source.estimand.eq(est)]
        a = d.abs_sde
        R["distribution"][est] = {"k": len(d), "median_abs": float(a.median()), "mean_abs": float(a.mean()),
             "p90_abs": float(a.quantile(.9)), "near_zero": float(a.lt(.005).mean()),
             "significant": float((d.sde_raw.abs() > stats.norm.ppf(.975) * d.se_sde).mean()),
             "sde_identity_fail": int(d.sde_identity.eq("fail").sum()),
             "se_identity_fail": int(d.se_identity.eq("fail").sum()),
             "sde_identity_testable": int(d.sde_identity.ne("untestable").sum()),
             "se_identity_testable": int(d.se_identity.ne("untestable").sum())}
    R["pooled"], R["weighting"], R["robustness"], R["diagnostics"] = {}, {}, {}, {}
    for est in ("binary", "continuous"):
        d = oriented[oriented.estimand.eq(est)].copy()
        y, v = d.sde_welfare.to_numpy(), d.se_sde.to_numpy() ** 2
        R["pooled"][est] = full_meta(y, v, est)
        R["weighting"][est] = {"Equal": weighted_mean(y, np.ones(len(y))),
            "Inverse SE": weighted_mean(y, 1 / np.sqrt(v))}
        R["robustness"][est] = {}
        masks = {"Arithmetic screen": ~d.sde_identity.eq("fail") & ~d.se_identity.eq("fail"),
                 "Direction agreement": d.routes_agree.eq(True),
                 "Confident direction": d.sign_margin.abs().ge(.60) & d.direction_ambiguous.lt(.30),
                 "Drop most precise 1%": d.se_sde.ge(d.se_sde.quantile(.01)),
                 "Clean scan": d.scan_verdict.fillna("Missing").str.lower().eq("clean")}
        for label, mask in masks.items():
            s = d[mask]
            if len(s) >= 5:
                R["robustness"][est][label] = full_meta(s.sde_welfare, s.se_sde ** 2, label)
        goals = source[source.estimand.eq(est) & source.goal_sign.ne(0)]
        if len(goals) >= 5:
            R["robustness"][est]["Policy intent"] = full_meta(goals.sde_goal, goals.se_sde ** 2, "Policy intent")
        # No assumptions about the direction of unclassified outcomes: finite-
        # corpus equal-weight range assigning each missing sign +/- |effect|.
        whole = source[source.estimand.eq(est)]
        missing = whole[whole.welfare_sign.eq(0)]
        observed_sum = d.sde_welfare.sum()
        R["robustness"][est]["Missing direction bounds"] = {
            "k": len(whole), "missing": len(missing),
            "lo": float((observed_sum - missing.abs_sde.sum()) / len(whole)),
            "hi": float((observed_sum + missing.abs_sde.sum()) / len(whole))}
        R["robustness"][est]["Country bootstrap"] = grouped_bootstrap(d, "sde_welfare")
        R["diagnostics"][est] = egger(y, v)
    # Sensitivity starts with ALL standardized papers, never baseline-signable only.
    responses = {r["paper_version_id"]: r["answers"] for r in (
        json.loads(line) for line in (RAW / "jev_direction_context.jsonl").read_text().splitlines())}
    sensitivity = []
    for margin in (.05, .10, .15, .20, .30):
        for desc in (.60, .75, .90):
            signs = source.paper_version_id.map(lambda vid: orientation(responses.get(vid, {}), margin, desc)["sign"])
            for est in ("binary", "continuous"):
                s = source[source.estimand.eq(est) & signs.ne(0)]
                summary = full_meta(s.sde_raw * signs.loc[s.index], s.se_sde ** 2)
                sensitivity.append({"margin": margin, "ambiguity": desc, "estimand": est, **summary})
    R["sign_sensitivity"] = sensitivity
    R['direction_comparison'] = []
    for rule, column in [('Notes / strict', 'notes_strict_sign'),
                         ('Notes / relaxed', 'notes_relaxed_sign'),
                         ('Context / strict', 'context_strict_sign'),
                         ('Context / unguarded', 'context_unguarded_sign'),
                         ('Context / balanced', 'welfare_sign')]:
        for est in ('binary', 'continuous'):
            d = source[source.estimand.eq(est) & source[column].ne(0)]
            R['direction_comparison'].append({'rule':rule,'estimand':est,
                **full_meta(d.sde_raw * d[column], d.se_sde**2)})
    R['direction_transitions'] = {
        'previously_oriented':int(source.notes_strict_sign.ne(0).sum()),
        'currently_oriented':len(oriented),
        'newly_oriented':int((source.notes_strict_sign.eq(0) & source.welfare_sign.ne(0)).sum()),
        'lost_direction':int((source.notes_strict_sign.ne(0) & source.welfare_sign.eq(0)).sum()),
        'reversed_direction':int((source.notes_strict_sign * source.welfare_sign).eq(-1).sum()),
        'with_extra_context':int(source.direction_context_characters.gt(0).sum())}
    R['direction_transitions']['measurement_qualifier_exclusions'] = int(
        (source.context_unguarded_sign.ne(0) & source.welfare_sign.eq(0)).sum())
    R["domains"] = []
    for (est, domain), group in oriented.groupby(["estimand", "policy_family"], sort=True):
        if len(group) >= 5:
            R["domains"].append({"estimand": est, "domain": domain,
                **full_meta(group.sde_welfare, group.se_sde ** 2, domain)})
    R["coverage_by_domain"] = [{"domain": domain, "k": len(g), "oriented": int(g.welfare_sign.ne(0).sum())}
                               for domain, g in source.groupby("policy_family", sort=True)]
    R["policy_regressions"] = {est: fit_specs(oriented[oriented.estimand.eq(est)], "sde_welfare", ["Basic", "Full"])
                               for est in ("binary", "continuous")}
    rated = source[source.rated].copy()
    # SDE is an explanatory quantity here; use magnitude only, never mu/Elo transforms.
    R["quality_regressions"] = fit_specs(rated, "mu", ["Basic", "Design", "Reporting", "Full"])
    protocol = json.loads((RAW.parent / 'quality_protocol.json').read_text(encoding='utf-8'))
    R['quality_weighting'] = {}
    quality_rows, quality_groups, quality_weights = [], [], []
    for est in ('binary', 'continuous'):
        d = oriented[oriented.estimand.eq(est) & oriented.rated].copy()
        result, weights = rating_sensitivity(d.sde_welfare, d.se_sde ** 2, d.mu,
            strengths=protocol['lambdas'], B=protocol['bootstrap_replications'],
            seed=protocol['bootstrap_seed'])
        result['excluded_unrated'] = int((oriented.estimand.eq(est) & ~oriented.rated).sum())
        result['sample_ids'] = d.paper_version_id.tolist()
        R['quality_weighting'][est] = result
        quality_rows.extend({'estimand': est, **row} for row in result['summaries'])
        quality_groups.extend({'estimand': est, **row} for row in result['groups'])
        for j, row in enumerate(result['summaries']):
            quality_weights.extend({'estimand': est, 'paper_version_id': vid,
                'mu': float(mu), 'base': row['base'], 'lambda': row['lambda'],
                'normalized_weight': float(weight)}
                for vid, mu, weight in zip(d.paper_version_id, d.mu, weights[j]))
    pd.DataFrame(quality_rows).to_csv(OUTPUT / 'quality_weighting.csv', index=False)
    pd.DataFrame(quality_groups).to_csv(OUTPUT / 'quality_rating_groups.csv', index=False)
    pd.DataFrame(quality_weights).to_csv(OUTPUT / 'quality_paper_weights.csv', index=False)
    R["selection"] = {}
    for est in ("binary", "continuous"):
        d = source[source.estimand.eq(est)]
        R["selection"][est] = {"oriented_mean_abs": float(d[d.welfare_sign.ne(0)].abs_sde.mean()),
            "unoriented_mean_abs": float(d[d.welfare_sign.eq(0)].abs_sde.mean()),
            "oriented_median_abs": float(d[d.welfare_sign.ne(0)].abs_sde.median()),
            "unoriented_median_abs": float(d[d.welfare_sign.eq(0)].abs_sde.median())}
    # Other valid tabular estimates (unknown estimands/bunching) remain visible.
    excluded = df[df.has_numeric_sde & ~df.standardized_sample]
    R["excluded_numeric"] = {"k": len(excluded), "unknown_estimand": int(excluded.estimand.eq("unknown").sum()),
        "bunching_or_elasticity": int(excluded.standardization_ambiguous.eq(True).sum()),
        "large_sde": int(excluded.sde_raw.abs().gt(5).sum()),
        "no_positive_se": int((excluded.se_sde.isna() | excluded.se_sde.le(0)).sum()),
        "duplicates": int(df.duplicate_of.notna().sum()),
        "comparable_duplicates": int((df.comparable_before_dedup & df.duplicate_of.notna()).sum())}
    # Sensitivity includes otherwise valid >5 SD estimates; do not assert that
    # standardization places a mathematical bound of five on the outcome.
    for est in ("binary", "continuous"):
        extra = df[df.estimand.eq(est) & df.welfare_sign.ne(0) & df.invalid_reason.eq("|SDE| > 5")
                   & df.se_sde.gt(0) & ~df.standardization_ambiguous.eq(True)]
        d = pd.concat([oriented[oriented.estimand.eq(est)], extra])
        R["robustness"][est]["Include large SDEs"] = full_meta(d.sde_welfare, d.se_sde ** 2)
        duplicates = df[df.estimand.eq(est) & df.welfare_sign.ne(0) & df.comparable_before_dedup & df.duplicate_of.notna()]
        d = pd.concat([oriented[oriented.estimand.eq(est)], duplicates])
        R["robustness"][est]["Include duplicate tables"] = full_meta(d.sde_welfare, d.se_sde ** 2)
    (OUTPUT / "results.json").write_text(json.dumps(R, indent=2, allow_nan=False), encoding="utf-8")
    pd.DataFrame(sensitivity).to_csv(OUTPUT / "sign_sensitivity.csv", index=False)
    source.to_csv(OUTPUT / "analysis_sample.csv", index=False)
    source[source.welfare_sign.eq(0)][[
        "paper_version_id", "title", "outcome_label", "estimand", "source_path",
        "higher_benefits", "lower_benefits", "direction_ambiguous", "sign_reason",
        "sign_margin", "direction_request_sha256"]].to_csv(OUTPUT / "direction_review_queue.csv", index=False)
    source[['paper_version_id','outcome_label','estimand','notes_strict_sign',
            'notes_relaxed_sign','context_strict_sign','welfare_sign','higher_benefits',
            'lower_benefits','direction_ambiguous','sign_reason','source_path',
            'direction_context_characters','administrative_detection','group_composition',
            'gross_activity','context_unguarded_sign']].to_csv(OUTPUT/'direction_comparison.csv',index=False)
    for est, result in R["pooled"].items():
        print(est, "k", result["k"], "mean", round(result["estimate"], 4),
              "CI", round(result["ci_lo"], 4), round(result["ci_hi"], 4), "tau2", round(result["tau2"], 4))


if __name__ == "__main__":
    main()
