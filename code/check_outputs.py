"""Check sample invariants, numerical outputs, regression reporting and PDF text."""
import argparse
import hashlib
import json
import re
import pandas as pd
from paths import ROOT, PROCESSED, OUTPUT, PAPER


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--no-pdf', action='store_true')
    args = ap.parse_args()
    df = pd.read_csv(PROCESSED/'dataset.csv')
    r = json.loads((OUTPUT/'results.json').read_text(encoding='utf-8'))
    assert df.paper_family_id.is_unique
    assert df.loc[df.welfare_sign.eq(0), 'sde_welfare'].isna().all()
    assert df.loc[df.standardized_sample, 'table_sha256'].is_unique
    assert set(df.loc[df.standardized_sample, 'estimand']) == {'binary', 'continuous'}
    assert (df.loc[df.standardized_sample, 'se_sde'] > 0).all()
    assert r['sample']['standardized'] == int(df.standardized_sample.sum())
    assert r['sample']['oriented'] == int((df.standardized_sample & df.welfare_sign.ne(0)).sum())
    assert len(r['sign_sensitivity']) == 30
    weights = pd.read_csv(OUTPUT/'quality_paper_weights.csv')
    for est, result in r['quality_weighting'].items():
        expected = df[df.standardized_sample & df.welfare_sign.ne(0) & df.rated & df.estimand.eq(est)]
        assert result['sample_ids'] == expected.paper_version_id.tolist()
        assert len(result['summaries']) == 6
        for s in result['summaries']:
            w = weights[(weights.estimand == est) & (weights.base == s['base']) & (weights['lambda'] == s['lambda'])]
            assert len(w) == len(expected) == s['k']
            assert abs(w.normalized_weight.sum() - 1) < 1e-12
            assert w.normalized_weight.gt(0).all()
            assert abs(w.normalized_weight.to_numpy() @ expected.sde_welfare.to_numpy() - s['estimate']) < 1e-12
            assert s['effective_k'] <= s['k'] + 1e-8
    dictionary = pd.read_csv(ROOT/'data/data_dictionary.csv')
    assert list(dictionary.variable) == list(df.columns)
    for models in [r['quality_regressions'], *r['policy_regressions'].values()]:
        assert len({m['n'] for m in models.values()}) == 1
        for m in models.values():
            assert 'const' in m['params'] and m['df_resid'] > 0
            assert m['n'] - m['rank'] == m['df_resid']
    for file in (PAPER/'generated').glob('*.tex'):
        assert '@@' not in file.read_text(encoding='utf-8')
    report = {'sample_invariants': 'pass', 'common_regression_samples': 'pass',
              'table_placeholders': 'pass', 'tests': 16, 'quality_weighting_common_samples': 'pass',
              'pdf_checked': not args.no_pdf}
    if not args.no_pdf:
        import pymupdf
        log = (OUTPUT/'paper/main.log').read_text(encoding='utf-8', errors='replace')
        assert not re.search(r'^!|Overfull \\hbox|undefined references|undefined citations', log, re.M)
        pdf = OUTPUT/'paper/main.pdf'
        doc = pymupdf.open(pdf)
        text = '\n'.join(p.get_text() for p in doc)
        assert '@@' not in text and 'Constant' in text and 'Observations' in text
        assert 'Table A7' in text and 'Figure 2' in text
        report.update(pdf_pages=len(doc), pdf_sha256=hashlib.sha256(pdf.read_bytes()).hexdigest(),
                      latex_errors=0, overfull_boxes=0)
    (OUTPUT/'qa/output_checks.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
