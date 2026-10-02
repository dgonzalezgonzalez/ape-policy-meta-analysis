"""Non-circular arithmetic and column-alignment diagnostics after parsing."""
import json
from collections import Counter
from build_dataset import identity
from paths import PROCESSED, OUTPUT


def main():
    records = json.loads((PROCESSED / 'parsed_full.json').read_text(encoding='utf-8'))
    diagnostics = []
    for record in records:
        if record['n_cells'] != record['n_header_cells']:
            raise AssertionError('Column alignment: ' + record['paper_version_id'])
        diagnostics.append({'paper_version_id': record['paper_version_id'],
                            'estimand': record['estimand'],
                            'sde_identity': identity(record),
                            'se_identity': identity(record, se=True)})
    report = {'parsed_versions': len(records), 'diagnostics': diagnostics}
    (OUTPUT / 'qa').mkdir(exist_ok=True)
    (OUTPUT / 'qa' / 'source_arithmetic.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    for field in ('sde_identity', 'se_identity'):
        print(field, dict(Counter(row[field] for row in diagnostics)))
    print('Failures are source diagnostics, not silently repaired values.')


if __name__ == '__main__':
    main()
