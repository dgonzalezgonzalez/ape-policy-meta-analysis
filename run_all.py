"""Single driver for offline replication. Run with the desired Python interpreter."""
import argparse
import hashlib
import importlib.metadata
import json
import os
import platform
from pathlib import Path
import shutil
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parent


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--no-pdf', action='store_true', help='Reproduce all analysis and TeX without a TeX installation')
    ap.add_argument('--rebuild-sources', action='store_true', help='Download and parse immutable third-party sources; needs network')
    ap.add_argument('--enrich', action='store_true', help='Request missing Jev annotations; requires --rebuild-sources and an API key')
    args = ap.parse_args()
    if args.enrich and not args.rebuild_sources:
        ap.error('--enrich requires --rebuild-sources')
    checksums = json.loads((ROOT / 'data/input_checksums.json').read_text(encoding='utf-8'))
    for relative, expected in checksums.items():
        actual = hashlib.sha256((ROOT / relative).read_bytes().replace(b'\r\n', b'\n')).hexdigest()
        if actual != expected:
            raise ValueError('Released input checksum mismatch: ' + relative)
    output = ROOT / 'output'
    (output / 'qa').mkdir(parents=True, exist_ok=True)
    (output / 'paper').mkdir(exist_ok=True)
    stages = []
    started = time.perf_counter()
    log = (output / 'replication.log').open('w', encoding='utf-8')
    env = dict(os.environ, PYTHONIOENCODING='utf-8')

    def run(command, cwd=ROOT):
        stamp = time.perf_counter()
        print('Running', Path(command[1]).name if command[0] == sys.executable else Path(command[0]).name, flush=True)
        completed = subprocess.run(command, cwd=cwd, env=env, stdout=subprocess.PIPE,
                                   stderr=subprocess.STDOUT, encoding='utf-8', errors='replace')
        log.write('$ ' + ' '.join(command) + '\n' + completed.stdout + '\n')
        log.flush()
        if completed.returncode:
            raise RuntimeError('Stage failed; see output/replication.log: ' + ' '.join(command))
        stages.append({'command': [Path(command[0]).name, *command[1:]],
                       'seconds': round(time.perf_counter()-stamp, 3)})

    if args.rebuild_sources:
        for script in ('harvest.py', 'parse_sde.py', 'validate.py'):
            run([sys.executable, 'code/' + script])
        if args.enrich:
            run([sys.executable, 'code/jev_enrich.py'])
            run([sys.executable, 'code/jev_direction.py'])
        run([sys.executable, 'code/build_dataset.py', '--extract'])
    else:
        run([sys.executable, 'code/build_dataset.py'])
    for script in ('test_analysis.py', 'run_analysis.py', 'make_tex.py', 'make_figures.py'):
        run([sys.executable, 'code/' + script])
    if not args.no_pdf:
        tex = shutil.which('pdflatex')
        if not tex:
            raise FileNotFoundError('pdflatex not found. Install TeX or use --no-pdf; numerical results already generated.')
        env['MIKTEX_ENABLE_INSTALLER'] = 'm'
        for _ in range(2):
            run([tex, '-interaction=nonstopmode', '-halt-on-error',
                 '-output-directory=../output/paper', 'main.tex'], cwd=ROOT/'paper')
    run([sys.executable, 'code/check_outputs.py', *(['--no-pdf'] if args.no_pdf else [])])
    report = {'date': time.strftime('%Y-%m-%d'), 'python': platform.python_version(),
              'platform': platform.platform(), 'processor': platform.processor(),
              'logical_cpus': os.cpu_count(), 'offline': not args.rebuild_sources,
              'packages': {p: importlib.metadata.version(p) for p in
                           ('numpy', 'pandas', 'scipy', 'statsmodels', 'matplotlib', 'requests', 'pymupdf')},
              'stages': stages, 'total_seconds': round(time.perf_counter()-started, 3)}
    (output/'qa/run_environment.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    log.close()
    print('Replication complete:', report['total_seconds'], 'seconds.', flush=True)


if __name__ == '__main__':
    main()
