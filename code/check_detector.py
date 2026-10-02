"""Optional check with the user-requested economics detector; not an authorship test.

Run in a separate environment containing requirements-detector.txt. The released
paper discloses AI assistance irrespective of the detector's classification.
"""
import hashlib
import json
from pathlib import Path
import time
import requests
import torch
from huggingface_hub import snapshot_download
from econ_ai_detector import Detector
import econ_ai_detector.detector as detector_module

ROOT = Path(__file__).resolve().parent.parent
COMMIT = '11285447a3ccdc300bef25bc0a4a1eb42fd489cb'
HF_REVISION = 'fb7fb8b27bb9014f588fc79fdf2092167b38e7de'


def main():
    # The upstream wheel omits the LR assets. Retrieve pinned public files into
    # its expected models directory; no third-party weights enter this repo.
    directory = detector_module.MODELS
    directory.mkdir(exist_ok=True)
    assets = {}
    for name in ('lr_v3.joblib', 'thresholds.json'):
        target = directory / name
        response = requests.get(f'https://raw.githubusercontent.com/paulgp/econ-ai-detector/{COMMIT}/models/{name}', timeout=90)
        response.raise_for_status()
        data = response.content
        if not target.exists() or target.read_bytes() != data:
            target.write_bytes(data)
        assets[name] = hashlib.sha256(data).hexdigest()
    weights = snapshot_download('paulgp85/econ-ai-detector-distilroberta-v3', revision=HF_REVISION)
    torch.set_num_threads(4)
    started = time.perf_counter()
    pdf = ROOT/'output/paper/main.pdf'
    result = Detector(nn_path=weights, device='cpu', target_fpr='0.001').score_pdf(str(pdf))
    report = result.to_dict()
    report.update(pdf_sha256=hashlib.sha256(pdf.read_bytes()).hexdigest(),
                  detector_commit=COMMIT, neural_model_revision=HF_REVISION,
                  asset_sha256=assets, seconds=round(time.perf_counter()-started, 2),
                  interpretation='A detector classification is not evidence of authorship. This manuscript was prepared with AI assistance.')
    (ROOT/'output/qa/detector.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print({k: v for k, v in report.items() if k != 'windows'})


if __name__ == '__main__':
    main()
