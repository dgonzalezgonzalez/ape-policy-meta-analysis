"""Download optional original sources from immutable URLs; verify their content.

Full third-party text is not included in the release. Needs public network access
but no credentials. Never substitutes mutable main-branch data.
"""
import csv
import hashlib
import json
from concurrent.futures import ThreadPoolExecutor
import requests
from paths import RAW


def digest(data, kind):
    if kind == 'json-semantic':
        data = json.dumps(json.loads(data), sort_keys=True, ensure_ascii=False,
                          separators=(',', ':')).encode('utf-8')
    else:
        data = data.replace(b'\r\n', b'\n')
    return hashlib.sha256(data).hexdigest()


def main():
    rows = list(csv.DictReader((RAW / 'sources_manifest.csv').open(encoding='utf-8')))

    def download(row):
        target = RAW / row['local_path']
        if target.exists() and digest(target.read_bytes(), row['checksum_kind']) == row['sha256']:
            return
        response = requests.get(row['url'], timeout=90,
                                headers={'User-Agent': 'ape-policy-meta-analysis-replication'})
        response.raise_for_status()
        data = response.content.replace(b'\r\n', b'\n')
        if digest(data, row['checksum_kind']) != row['sha256']:
            raise ValueError('Source checksum differs: ' + row['local_path'])
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)

    with ThreadPoolExecutor(max_workers=8) as executor:
        for i, _ in enumerate(executor.map(download, rows), 1):
            if i % 200 == 0 or i == len(rows):
                print('Verified source files:', i, '/', len(rows), flush=True)


if __name__ == '__main__':
    main()
