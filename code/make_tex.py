"""Generate numerical macros and conventional tables; never mutate analysis inputs."""
import json
import pandas as pd
from paths import OUTPUT, PAPER

R = json.loads((OUTPUT / "results.json").read_text(encoding="utf-8"))
TABLES = OUTPUT / "tables"
TABLES.mkdir(exist_ok=True)
GENERATED = PAPER / "generated"
GENERATED.mkdir(exist_ok=True)


def T(text, **kw):
    for key, value in kw.items():
        text = text.replace("@@" + key + "@@", str(value))
    if "@@" in text:
        raise ValueError("Unresolved placeholder")
    return text


def fmt(x, digits=3):
    return format(x, "." + str(digits) + "f")


def esc(x):
    return str(x).replace("&", r"\&").replace("_", r"\_").replace("%", r"\%")


def table(name, title, header, rows, notes, columns, label=None):
    source = T(r"""\begin{table}[htbp]\centering\small
\caption{@@TITLE@@}\label{tab:@@LABEL@@}
\setlength{\tabcolsep}{4pt}
\begin{tabular}{@@COLS@@}\toprule
@@HEADER@@ \\
\midrule
@@ROWS@@
\bottomrule\end{tabular}
\par\vspace{4pt}\begin{minipage}{\textwidth}\footnotesize
\textit{Notes:} @@NOTES@@
\end{minipage}
\end{table}
""", TITLE=title, LABEL=label or name, COLS=columns, HEADER=header,
        ROWS="\n".join(" & ".join(map(str, row)) + r" \\" for row in rows), NOTES=notes)
    (GENERATED / (name + ".tex")).write_text(source, encoding="utf-8")


NICE = {"log_se": r"$\log\,\mathrm{SE}(\mathrm{SDE})$", "design_strength": "Design score",
        "policy_intensity": "Policy intensity", "parallel_trends_tested": "Identifying-assumption test",
        "reports_robustness": "Reports robustness", "data_source_official": "Official data source", "const": "Constant"}


def regressions(name, title, models, headings, notes):
    rows = []
    for variable in list(NICE):
        coeff, se = [NICE[variable]], [""]
        for model in models:
            if variable in model['params']:
                p = model['p'][variable]
                stars = r"$^{***}$" if p < .01 else r"$^{**}$" if p < .05 else r"$^{*}$" if p < .10 else ""
                coeff.append(fmt(model['params'][variable]) + stars)
                se.append("(" + fmt(model['se'][variable]) + ")")
            else:
                coeff.append("--"); se.append("")
        rows.extend([coeff, se])
    rows.append([r"\midrule Observations", *[str(m['n']) for m in models]])
    for label, key in [(r"$R^2$", "r2"), (r"Adjusted $R^2$", "adj_r2"), ("RMSE (unweighted)", "rmse")]:
        rows.append([label, *[fmt(m[key]) for m in models]])
    rows.append(["Residual degrees of freedom", *[str(m['df_resid']) for m in models]])
    rows.append(["HC3 Wald $F$", *[fmt(m['f'], 2) for m in models]])
    rows.append(["Wald $p$-value", *[r"$<0.001$" if m['f_p'] < .001 else fmt(m['f_p']) for m in models]])
    rows.append(["Method, region, week controls", *["Yes"] * len(models)])
    rows.append(["Policy-domain controls", *["Yes" if "policy_family" in m['categorical'] else "No" for m in models]])
    header = " & ".join(["", *headings]) + r" \\" + "\n" + " & ".join(
        ["", *["(" + str(i+1) + ")" for i in range(len(models))]])
    table(name, title, header, rows,
          notes + r" HC3 standard errors in parentheses. $^{*}p<0.10$, $^{**}p<0.05$, $^{***}p<0.01$."
          " Constant is the intercept for the omitted categorical groups; fixed effects are estimated separately."
          " All columns use equal paper weights. Rare categorical levels (fewer than ten papers) are grouped as Other.",
          "l" + "c" * len(models))
    exports = []
    for i, model in enumerate(models, 1):
        for variable, coefficient in model['params'].items():
            exports.append({"column": i, "variable": variable, "coefficient": coefficient,
                            "se_hc3": model['se'][variable], "p": model['p'][variable], "n": model['n']})
    pd.DataFrame(exports).to_csv(TABLES / (name + "_all_coefficients.csv"), index=False)


def main():
    macros = {}
    f = R['sample']
    for key in ('families', 'numeric', 'valid', 'standardized', 'oriented', 'rated'):
        macros[key.capitalize() + 'N'] = str(f[key])
    for est, prefix in [('binary','Binary'),('continuous','Continuous')]:
        r = R['pooled'][est]; d = R['distribution'][est]
        for key, field in [('Mean','estimate'),('Lo','ci_lo'),('Hi','ci_hi'),('PiLo','pi_lo'),('PiHi','pi_hi')]:
            macros[prefix + key] = fmt(r[field])
        macros[prefix + 'N'] = str(r['k'])
        macros[prefix + 'AllN'] = str(d['k'])
        macros[prefix + 'I'] = fmt(r['I2'],1)
        macros[prefix + 'MedianAbs'] = fmt(d['median_abs'])
        macros[prefix + 'Significant'] = fmt(100*d['significant'],1)
        macros[prefix + 'MissingLo'] = fmt(R['robustness'][est]['Missing direction bounds']['lo'])
        macros[prefix + 'MissingHi'] = fmt(R['robustness'][est]['Missing direction bounds']['hi'])
        macros[prefix + 'SelectionAbs'] = fmt(R['selection'][est]['unoriented_median_abs'])
        macros[prefix + 'OrientedAbs'] = fmt(R['selection'][est]['oriented_median_abs'])
        macros[prefix + 'EggerP'] = fmt(R['diagnostics'][est]['p'])
    full = R['quality_regressions']['Full']
    macros['QualityN'] = str(full['n'])
    macros['QualityR'] = fmt(full['r2'])
    macros['QualityAdjR'] = fmt(full['adj_r2'])
    for var, label in [('log_se','Precision'),('design_strength','Design'),('reports_robustness','Robustness'),
                       ('data_source_official','Official'),('parallel_trends_tested','Assumption')]:
        macros['Quality' + label] = fmt(full['params'][var])
        macros['Quality' + label + 'SE'] = fmt(full['se'][var])
    macros['PrecisionDoubling'] = fmt(full['params']['log_se'] * __import__('math').log(2))
    macros['DuplicateN'] = str(R['excluded_numeric']['duplicates'])
    macros['ComparableDuplicateN'] = str(R['excluded_numeric']['comparable_duplicates'])
    macros['BinaryStrictMean'] = fmt(R['robustness']['binary']['Confident direction']['estimate'])
    macros['BinaryStrictLo'] = fmt(R['robustness']['binary']['Confident direction']['ci_lo'])
    macros['BinaryStrictHi'] = fmt(R['robustness']['binary']['Confident direction']['ci_hi'])
    macros['BinaryStrictN'] = str(R['robustness']['binary']['Confident direction']['k'])
    macros['OriginalOrientedN'] = str(R['direction_transitions']['previously_oriented'])
    macros['NewlyOrientedN'] = str(R['direction_transitions']['newly_oriented'])
    macros['ReversedDirectionN'] = str(R['direction_transitions']['reversed_direction'])
    (GENERATED / 'numbers.tex').write_text('\n'.join(chr(92)+'newcommand{'+chr(92)+k+'}{'+v+'}' for k,v in macros.items()) + '\n', encoding='utf-8')
    table('sample', 'Sample construction', 'Stage & Paper families', [
        ['Latest table with designated source filename', f['families']],
        ['Numeric standardized estimate parsed', f['numeric']],
        ['Passes table validity and baseline magnitude screen', f['valid']],
        ['Comparable estimand, positive SE, non-bunching, unique table', f['standardized']],
        ['Favourable outcome direction assignable', f['oriented']],
        ['Rated papers in comparable sample', f['rated']]],
        'One selected estimate per latest paper-family version. Earlier versions are not substituted when the latest table lacks a usable standardized estimate. The comparable sample removes unknown estimands, bunching designs and repeated table files. Directional coding is not required for the ratings sample. The baseline magnitude screen excludes estimates exceeding five SDs; the appendix relaxes that screen.', 'lr')
    rows = []
    for est, label in [('binary','Binary treatment'),('continuous','Continuous exposure')]:
        d = R['distribution'][est]
        rows.append([label, d['k'], fmt(d['median_abs']), fmt(d['mean_abs']), fmt(d['p90_abs']), fmt(100*d['significant'],1)])
    table('distribution', 'Magnitude and reported precision', r'Estimand & $N$ & Median $|d|$ & Mean $|d|$ & 90th pct. & $|t|>1.96$ (\%)', rows,
          'All comparable papers, including outcomes without a favourable direction. Reported standard errors are treated as data, without validating the underlying identification or inference. A nominal significance indicator is not a measure of policy success.', 'lrrrrr')
    rows = []
    for est, label in [('binary','Binary'),('continuous','Continuous')]:
        r = R['pooled'][est]
        rows.append([label, r['k'], fmt(r['estimate']), '['+fmt(r['ci_lo'])+', '+fmt(r['ci_hi'])+']',
                     fmt(r['tau2']), fmt(r['I2'],1), '['+fmt(r['pi_lo'])+', '+fmt(r['pi_hi'])+']'])
    table('pooled', 'Favourable outcome changes by estimand', r'Estimand & $N$ & Mean & 95\% CI & $\tau^2$ & $I^2$ (\%) & 95\% PI', rows,
          'REML between-paper variance and modified Hartung--Knapp inference. Positive values move the selected outcome in the coded favourable direction. These are conditional corpus summaries, not welfare or cost-benefit estimates. PI denotes a normal random-effects prediction interval; it relies on exchangeability within each corpus stratum.', 'lrrlrrl')
    regressions('policy_regressions', 'Correlates of favourable outcome changes',
        [R['policy_regressions'][e][s] for e in ('binary','continuous') for s in ('Basic','Full')],
        ['Binary','Binary','Continuous','Continuous'],
        'Dependent variable is the direction-oriented SDE. Columns (1)--(2) and (3)--(4) retain common samples within each estimand. Probabilistic covariates range from zero to one; design scores from zero to four and intensity scores from zero to three. These relationships are descriptive; none identifies a determinant of policy effectiveness.')
    regressions('quality_regressions', 'Correlates of tournament ratings',
        [R['quality_regressions'][s] for s in ('Basic','Design','Reporting','Full')], ['Rating']*4,
        r'Dependent variable is TrueSkill $\mu$. All columns use the same rated comparable papers, including those without directional coding. An estimand indicator is also included. Ratings measure the automated tournament assessment; underlying validity is not observed.')
    rows = []
    for margin in (.05,.10,.15,.20,.30):
        for ambiguity in (.60,.75,.90):
            pair = [next(x for x in R['sign_sensitivity'] if x['margin']==margin and x['ambiguity']==ambiguity and x['estimand']==e) for e in ('binary','continuous')]
            rows.append([fmt(margin,2),fmt(ambiguity,2), *[z for x in pair for z in [x['k'],fmt(x['estimate']),'['+fmt(x['ci_lo'])+', '+fmt(x['ci_hi'])+']']]])
    table('thresholds', 'Sensitivity to directional coding thresholds', r'Margin & Ambiguity & $N_B$ & Mean$_B$ & 95\% CI$_B$ & $N_C$ & Mean$_C$ & 95\% CI$_C$', rows,
          'Each threshold pair is reapplied to all comparable papers with contextual annotations. B and C denote binary and continuous estimands. Maximum directional support must reach 0.55; there is no separate ceiling for the opposite-direction response. These thresholds are sensitivity choices, not empirically calibrated cutoffs.', 'rrrrlrrl')
    rows=[]
    for est in ('binary','continuous'):
        for name, r in R['robustness'][est].items():
            if 'ci_lo' in r:
                rows.append([est.capitalize(),esc(name),r['k'],fmt(r['estimate']),'['+fmt(r['ci_lo'])+', '+fmt(r['ci_hi'])+']'])
    table('robustness', 'Alternative samples and interpretation rules', r'Estimand & Sample or rule & $N$ & Mean & 95\% CI', rows,
          'All entries use REML and modified Hartung--Knapp inference. Clean scan is the upstream CLEAN verdict; it is not independent verification. The confidence subset requires direction margin at least 0.60 and ambiguity below 0.30. Policy intent uses explicit stated objectives and answers a different question.', 'llrrl')
    rows=[]
    for est in ('binary','continuous'):
        d=R['distribution'][est]
        rows.append([est.capitalize(), d['k'], d['sde_identity_testable'],d['sde_identity_fail'],d['se_identity_testable'],d['se_identity_fail']])
    table('identities', 'Internal arithmetic diagnostics', 'Estimand & Total & SDE tested & SDE fails & SE tested & SE fails',rows,
          r'SDE is checked against the declared standardization and SE against the same multiplier. A test is uninformative when the denominator or continuous exposure SD is unavailable. Tolerances allow 10\% relative SDE and 15\% relative SE discrepancies, with small-value floors of 0.02 and 0.0001. Counts are diagnostics, not estimates of research reliability.', 'lrrrrr')
    rows=[]
    for est in ('binary','continuous'):
        for label,r in R['weighting'][est].items():
            rows.append([est.capitalize(),label,r['k'],fmt(r['estimate']),'['+fmt(r['ci_lo'])+', '+fmt(r['ci_hi'])+']'])
    table('weights', 'Descriptive averages under alternative weights', r'Estimand & Weight & $N$ & Mean & 95\% CI', rows,
          'Intervals use a paper-level sandwich variance for the weighted mean, including observed between-paper variation. Country-group bootstrap ranges are reported in the machine-readable results. No fixed-effect point estimate is presented as a policy result.', 'llrrl')
    rows = []
    for r in R['direction_comparison']:
        rows.append([r['rule'],r['estimand'].capitalize(),r['k'],fmt(r['estimate']),
                     '['+fmt(r['ci_lo'])+', '+fmt(r['ci_hi'])+']'])
    table('direction_comparison', 'Annotation setup and directional coverage',
          r'Setup and rule & Estimand & $N$ & Mean & 95\% CI',rows,
          'Notes refers to the original beneficiary questions and table notes. Context refers to outcome-relevant data/setting paragraphs and questions explicitly about conventional outcome ordering, holding other outcomes and policy costs aside. Thus both context and question framing change across routes. Strict requires margin 0.20, support 0.60, opposite support no greater than 0.40 and ambiguity below 0.60. Balanced requires margin 0.15, support 0.55 and ambiguity below 0.75, with no opposite-support ceiling. Both routes use the same estimator. Contextual guarded rules flag group composition at probability 0.65; reporting/enforcement and gross-activity flags at 0.65 additionally require ambiguity at least 0.40. Unguarded omits these safeguards. These comparisons are not classification-error estimates.',
          'llrrl')
    pd.DataFrame(R['domains']).to_csv(TABLES/'domain_summaries.csv',index=False)
    pd.DataFrame(R['coverage_by_domain']).to_csv(TABLES/'direction_coverage.csv',index=False)
    (TABLES/'exhibit_map.csv').write_text('exhibit,source,output\nTable 1,sample_flow.json,paper/generated/sample.tex\nTable 2,results.json:distribution,paper/generated/distribution.tex\nTable 3,results.json:pooled,paper/generated/pooled.tex\nTable 4,results.json:policy_regressions,paper/generated/policy_regressions.tex\nTable 5,results.json:quality_regressions,paper/generated/quality_regressions.tex\nFigure 1,analysis_sample.csv,output/figures/magnitude_cdf.pdf\nFigure 2,results.json:domains,output/figures/domains.pdf\nTable A1,results.json:sign_sensitivity,paper/generated/thresholds.tex\nTable A2,results.json:robustness,paper/generated/robustness.tex\nTable A3,results.json:distribution,paper/generated/identities.tex\nTable A4,results.json:weighting,paper/generated/weights.tex\nTable A5,results.json:direction_comparison,paper/generated/direction_comparison.tex\n',encoding='utf-8')
    print('Generated',len(macros),'numeric macros and ten tables')


if __name__=='__main__':
    main()
