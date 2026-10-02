# Automated Policy Evaluation and the Interpretation of Evidence

**Author:** Diego GonzÃ¡lez-GonzÃ¡lez  
**Paper:** *A Meta-Analysis of Project APE*  
**Release:** 1.0.0, October 2, 2026  
**Repository:** <https://github.com/dgonzalezgonzalez/ape-policy-meta-analysis>

This package reproduces the paper's analysis of standardized estimates reported in Project APE policy evaluations. It includes frozen factual inputs, cached model annotations, all analysis programs, machine-readable results, LaTeX sources, vector figures, and the compiled paper at `output/paper/main.pdf`. The numerical replication runs offline without an API key.

The organization and documentation follow the [JPE package guidance](https://jpedataeditor.github.io/package.html) and the [Social Science Data Editors README template](https://social-science-data-editors.github.io/template_README/). `replication_report.qmd` adapts the [JPE reproducibility-report template](https://github.com/JPE-Reproducibility/JPEtemplate). That template is a report for a journal-appointed replicator; the included report is an author-side self-check. This package has not been evaluated or approved by JPE.

## Overview

The unit of observation is a paper family, represented by its latest version containing the designated `tabF1_sde.tex` filename in a frozen public repository tree. The release accounts for 699 families, including seven latest tables without a numeric standardized estimate. It keeps 626 comparable estimates after the reported-uncertainty, estimand, magnitude, bunching, and duplicate-table screens. The balanced contextual rule assigns outcome direction to 485 of these papers: 335 binary-treatment and 150 continuous-exposure estimates, compared with 299 in the original notes-only strict setup. The tournament-rating regressions use 620 comparable rated papers, including papers without a directional classification.

Binary-treatment contrasts and continuous-exposure slopes are analyzed separately. The main REML means are âˆ’0.0023 and 0.0113 outcome SDs, with modified Hartungâ€“Knapp 95% intervals of [âˆ’0.0411, 0.0366] and [âˆ’0.0180, 0.0406]. These summarize selected reported outcome changes. They are not net welfare estimates, a systematic review of all policy evidence, or independent replications of the source evaluations. The paper reports heterogeneity, directional-coverage sensitivity, alternative samples and weights, and descriptive associations with tournament ratings.

## Data availability and provenance

### Source 1: Project APE tables and metadata

Social Catalyst Lab, *Project APE papers*: <https://github.com/SocialCatalystLab/ape-papers>, accessed October 2, 2026. The frozen tree is `70c660ea5a7de722e9a12ad965e1c665890208d8`. There are 712 version-specific designated tables, 710 associated metadata files, and 691 locally acquired latest-version paper sources used for contextual direction coding. One numeric table has no paper.tex in the frozen tree and uses notes alone. The source versions with an SDE are dated Marchâ€“April 2026. Public access requires neither an account nor authentication.

`data/raw/sources_manifest.csv` records every original path, immutable download URL, Git blob SHA1, and content SHA256. Tables are compared after converting CRLF to LF; metadata checksums use canonical JSON. All 712 locally acquired table contents matched the frozen Git blob SHA1 after newline normalization. There are two table versions without a metadata file in the snapshot. They are not replaced with invented metadata.

`data/raw/source_records.json` contains the selected factual numerical observations and short descriptive labels for all 699 latest families. Each row includes the selected source path, row index where available, table hash, extraction status, arithmetic diagnostics, and eligibility fields. Original papers and full table prose are excluded from this release. Optional acquisition code retrieves tables, metadata and selected paper.tex files directly from immutable upstream URLs.

### Source 2: Project APE leaderboard

Social Catalyst Lab, *Project APE leaderboard*: <https://ape.socialcatalystlab.org/leaderboard.json>, accessed October 2, 2026. The snapshot reports `last_updated = 2026-07-01 16:01:11`. Its original file SHA256 is in `data/raw/provenance.json`. The URL is mutable; the analysis never replaces the frozen observations with a current leaderboard.

`data/raw/rating_records.json` freezes the selected factual rating fields for 698 matching latest version identifiers; the remaining family has no matching rating record. It includes TrueSkill mean and uncertainty, match counts, integrity verdict, annulment status, and authoring-model label. The same fields are merged into `source_records.json`. Elo is an affine transformation of the rating mean and is not analyzed as a separate outcome. The source's assessment methodology is documented at <https://ape.socialcatalystlab.org/methodology>.

### Source 3: Author-generated annotations

The package includes 692 successful latest-version annotation responses from TypeSafe's System One API, generated October 2, 2026 with `jev-1.13.0`. API documentation: <https://docs.typesafe.ai/api>. These are author-generated measurements, not a welfare field supplied by APE. `data/raw/jev_annotations.jsonl` contains the returned model label, typed answers, usage, access time, and request SHA256. Earlier responses and unsuccessful experiments are excluded from the release.

`code/jev_questions.py` and `code/jev_enrich.py` freeze the original table-notes covariate route. `code/jev_direction.py` supplies eight literal contextual-direction questions: five concerning ordering/intent and three concerning measurement type. `data/raw/jev_direction_context.jsonl` contains 692 successful pinned-model contextual responses, section names, selected-context length and hash, request hash and usage. The direction model receives the selected outcome, sanitized table notes, and at most seven relevant paragraphs (about 5,000 characters) from data, measurement or institutional-setting sections. It excludes abstracts, introductions, results, conclusions and table inputs, removes effect/uncertainty passages and prioritizes outcome definitions. Neither the SDE, standard error nor rating enters its state. Original prose stays local.

`data/direction_protocol.json` specifies the balanced margin 0.15, directional support 0.55 and ambiguity ceiling 0.75, with no separate opposite-support ceiling. These baseline thresholds were selected before contextual pooled results. Subsequent result-blind source inspection motivated measurement safeguards: group-composition probability at least 0.65 makes ordering unresolved; reporting/enforcement or gross-activity probability at least 0.65 additionally requires ambiguity at least 0.40. The latter avoids discarding clear harm or beneficial access merely because it is measured administratively. These are exploratory choices, not an externally calibrated error-minimizing classifier.

The original strict notes route, relaxed notes route, strict contextual route, contextual route without safeguards and final balanced route are reproduced in Table A5. Context and question framing both change across routes; this comparison does not isolate the effect of text alone. The final route admits 194 previously unresolved outcomes, removes eight prior assignments and reverses one direction after its definition is clarified. Across the 626 comparable observations, 625 receive additional context. `output/direction_comparison.csv` preserves every transition and the measurement flags. The AI-assisted definition audit in `data/direction_audit.csv` records illustrative cases and unresolved assumptions; it is neither a random independent validation sample nor an estimate of false-positive/false-negative rates.

Unresolved directions remain missing in `sde_welfare`; they are never assigned a zero effect. `output/direction_review_queue.csv` lists 141 unresolved comparable outcomes with probabilities and source locations. Stated policy intent and conventional favourable outcome direction remain distinct. Agreement between model questions is a consistency check only. Without independent reference labels, neither coverage nor confidence can identify an optimal classification-error tradeoff.

### Rights and restrictions

The inputs were obtained from publicly accessible sources; no confidential or individual-level administrative data are included. This meta-analysis uses publicly reported aggregates and model-generated descriptions. It conducts no human-subject experiment and claims no new IRB approval.

The frozen APE source tree did not contain an explicit redistribution licence. Public access alone does not establish permission to republish full papers or table prose. Accordingly, those materials remain outside this repository; the package supplies factual extracts, provenance and direct acquisition instructions. `LICENSE` covers the author's replication code. `LICENSE-DATA-AND-PAPER.txt` covers the author's manuscript, generated outputs and annotations to the extent of the author's rights, without granting rights in third-party material.

**Outstanding submission requirements:** the author must confirm the right to use and publish the selected third-party material, resolve any necessary source permissions, and deposit the final version in a journal-acceptable persistent archive with a DOI. No signed rights certification, DOI or journal approval is asserted here. GitHub provides the requested public working repository; it does not complete JPE's archival or rights-certification process.

## Dataset list

| File | Contents | Role / format |
| --- | --- | --- |
| `data/raw/source_records.json` | 699 latest-family factual extracts, exclusions and source hashes | Frozen analysis input; UTF-8 JSON |
| `data/raw/rating_records.json` | 698 selected leaderboard records | Frozen extraction input; UTF-8 JSON |
| `data/raw/jev_annotations.jsonl` | 692 successful typed annotation responses | Frozen annotation input; UTF-8 JSON Lines |
| `data/raw/sources_manifest.csv` | 2,113 immutable table/metadata/paper source paths and checksums | Optional acquisition manifest; CSV |
| `data/raw/provenance.json` | Source dates, tree identifier, leaderboard hash and model | Provenance; JSON |
| `data/input_checksums.json` | LF-normalized SHA256 for the seven frozen input files | Integrity check; JSON |
| `data/raw/jev_direction_context.jsonl` | 692 contextual direction responses and selected-context metadata | Frozen annotation input; JSON Lines |
| `data/direction_protocol.json` | Direction thresholds, measurement safeguards and revision timing | Frozen coding protocol; JSON |
| `data/direction_audit.csv` | Illustrative AI-assisted source-definition review | Author audit; CSV |
| `data/processed/dataset.csv` | 699 rows, all extracted and constructed variables | Generated complete dataset; CSV |
| `data/data_dictionary.csv` | Definition, origin, units/coding and missingness for every dataset column | Codebook; CSV |
| `output/analysis_sample.csv` | 626 comparable observations | Generated main sample; CSV |
| `output/direction_review_queue.csv` | 141 unresolved comparable outcomes | Generated review queue; CSV |
| `output/direction_comparison.csv` | 626 paper-level annotation transitions and measurement flags | Generated comparison; CSV |
| `output/results.json` | All summaries, specifications, diagnostics and sensitivities | Generated results; JSON |
| `output/sign_sensitivity.csv` | 15 threshold pairs Ã— 2 estimands | Generated sensitivity results; CSV |
| `output/tables/` | Domain summaries, coverage, all regression coefficients, exhibit map | Generated numerical exports; CSV |

Missing numeric values in CSV are blank; JSON uses `null`. Zero is retained when it is a reported value and does not mean missing. Probabilistic binary descriptions range from zero to one. The dictionary points to exact question definitions and categorical alternatives. No long paper prose or original microdata are shipped. The optional `data/raw/sde/` and `data/raw/meta/` and `data/raw/papers/` directories are gitignored.

## Computational requirements

### Software

The tested environment is Python **3.12.10**, Windows 11 build 26200, with exact analysis-library versions pinned in `requirements.txt`: NumPy 2.5.2, pandas 3.0.5, SciPy 1.18.1, statsmodels 0.15.0, Matplotlib 3.11.1, requests 2.34.2 and PyMuPDF 1.28.2. The Python interpreter is passed through every subprocess. The scripts use paths relative to the driver, not a hardcoded personal directory.

Compiling the paper requires `pdflatex` on PATH and the standard packages used by `paper/main.tex`: `geometry`, `lmodern`, `amsmath`, `amssymb`, `booktabs`, `graphicx`, `array`, `natbib`, `caption`, `hyperref`, and `setspace`. MiKTeX was tested. Compilation runs twice from `paper/` for references. No Perl, `latexmk`, R, Stata, Quarto or proprietary statistical software is needed for the main replication. The analysis and TeX can be regenerated with `--no-pdf` if TeX is unavailable. The published PDF is already included.

Installing Python packages or missing TeX packages requires internet access. Once those dependencies are installed, the default replication makes no API or source-data requests. MiKTeX may prompt to install missing packages on a machine without the required TeX dependencies.

### Hardware, storage, time and randomness

Tested on an Intel i7-1165G7 laptop, eight logical processors and approximately 16 GB RAM. The full offline analysis, checks, figures, TeX tables and two PDF passes took about **25 seconds**. `output/qa/run_environment.json` records actual stage timings and software versions for each run. No GPU is needed. Allow 1 GB free RAM for the main analysis and 200 MB of free storage for a working checkout and optional original tables; these are conservative allowances, not measured peak requirements.

The optional detector uses a separate Python environment and a neural model download; allow several GB of additional storage and memory. It is outside the numerical replication. Optional full-source acquisition involves 2,113 public source downloads; duration depends on the network. Request regeneration requires a TypeSafe account and key and may incur charges. Frozen responses are sufficient for every paper result. New API responses need not be identical even with a pinned model.

Country-group bootstrap calculations use 999 resamples and seed `20261002`. No other main analysis stage uses randomness. Generated figures have fixed PDF date metadata. TeX PDF timestamps and file identifiers can vary; numerical files, generated table text and figure content are the replication targets, not byte-identical manuscript PDFs.

## Instructions to replicators

### Offline reproduction

Clone or download this repository into any writable directory, including paths containing spaces. Create an isolated environment with Python 3.12 and install the pinned requirements. From the repository root:

```powershell
# Windows: use an actual Python installation, not the Microsoft Store stub.
$PY = 'C:\Users\dgonzalez\AppData\Local\Programs\Python\Python312\python.exe'
& $PY -m venv .venv
& .venv\Scripts\python.exe -m pip install -r requirements.txt
& .venv\Scripts\python.exe run_all.py
```

Replace the example interpreter path with the replicator's own Python installation. On this author's machine, the displayed absolute path is necessary because `python` on PATH resolves to a Store stub.

```bash
# Equivalent on a system with Python 3.12 and pdflatex installed:
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python run_all.py
```

Use `run_all.py --no-pdf` to reproduce the numerical analysis, figures and generated LaTeX without a TeX installation. The driver verifies frozen inputs (SHA256 after CRLF-to-LF normalization), rebuilds the dataset, runs thirteen benchmark/parser checks, runs the analysis, generates tables and figures, compiles the paper twice, and checks the outputs. It fails on a subprocess error, stale input checksum, invalid sample invariant, unresolved table placeholder, undefined LaTeX reference or overfull horizontal box. It writes `output/replication.log` and machine-readable QA reports. The log is overwritten on each run.

### Optional source-level reconstruction

```powershell
& .venv\Scripts\python.exe run_all.py --rebuild-sources
```

This acquires immutable originals, verifies their checksums, parses the designated tables, runs non-circular arithmetic diagnostics, rebuilds factual extracts using the frozen rating subset and cached annotations, then completes the ordinary analysis. It does not download a current leaderboard. Original prose remains local and gitignored. `parsed_full.json` contains source notes and is also gitignored. The source-arithmetic QA report includes every parsed version; Table A3 restricts the same diagnostics to the comparable latest-family sample.

`run_all.py --rebuild-sources --enrich` additionally requests missing or stale Jev annotations. Set `TYPESAFE_API_KEY` in the environment or a local `.env` file using `.env.example`. No key belongs in the repository. Unchanged request hashes are skipped. Changing questions, the selected source outcome, notes processing or model changes the request hash and requires new annotations. Intentional changes to released inputs require updating `data/input_checksums.json` and creating a new documented release.

### Optional detector check

```powershell
& $PY -m venv .venv-detector
& .venv-detector\Scripts\python.exe -m pip install -r requirements-detector.txt
& .venv-detector\Scripts\python.exe code/check_detector.py
```

The requested [econ-ai-detector](https://github.com/paulgp/econ-ai-detector) is pinned to commit `11285447a3ccdc300bef25bc0a4a1eb42fd489cb`; the neural model revision is pinned in the checker. Its wheel omits the logistic-regression assets, so the checker downloads the matching files from that commit. The check scores the compiled PDF using the repository's default prose gate, reference cutoff and 0.001 target false-positive operating point. `output/qa/detector.json` records thresholds, window scores, model identifiers, asset hashes and the checked PDF hash. A non-flag is not proof of human authorship. The manuscript discloses AI assistance regardless of the classification.

## Description of programs

| Program | Function | Main dependencies |
| --- | --- | --- |
| `run_all.py` | Single driver, input integrity, timings, compilation | All analysis dependencies; optional pdflatex |
| `code/paths.py` | Portable project locations | Python standard library |
| `code/harvest.py` | Optional immutable-source acquisition and verification | requests |
| `code/parse_sde.py` | Header-based table extraction and primary-row selection | Python standard library |
| `code/validate.py` | Column alignment and non-circular SDE/SE arithmetic diagnostics | Extracted sources; dataset identity helper |
| `code/jev_questions.py` | Literal covariate questions and local key loading | Python standard library |
| `code/jev_enrich.py` | Optional pinned-model batched annotation and request-hash cache | requests; source notes; optional API key |
| `code/jev_direction.py` | Context selection and eight pinned direction/measurement questions | requests; local paper definitions; optional API key |
| `code/orientation.py` | Favourable-direction and policy-intent rules | Python standard library |
| `code/build_dataset.py` | Frozen-input merge, latest-version sample, missingness, duplicates | NumPy, pandas |
| `code/meta.py` | REML, modified HK, weighting, HC3 regressions and Egger diagnostic | NumPy, SciPy, statsmodels |
| `code/run_analysis.py` | Corpus summaries, regressions, thresholds and robustness | Numerical libraries; frozen dataset |
| `code/make_tex.py` | Numeric macros and ten conventional regression/summary tables | pandas; read-only results |
| `code/make_figures.py` | Two vector figures | Matplotlib; numerical results |
| `code/test_analysis.py` | Thirteen analytical, context and parser benchmark checks | Numerical libraries |
| `code/check_outputs.py` | Sample, regression, table and PDF invariants | pandas; optional PyMuPDF |
| `code/check_detector.py` | Optional pinned detector check | Separate detector dependencies |
| `paper/main.tex` | Manuscript, equations, interpretation and references | Generated numeric macros, tables and figures |

The table generator does not modify analysis CSVs. It can be rerun safely without rerunning the analysis. The manuscript includes `\end{document}`. These correct two fragilities in the earlier pipeline.

## Tables, figures and in-text numbers

| Exhibit | Analysis object | Generated file |
| --- | --- | --- |
| Table 1: Sample construction | `sample_flow.json` | `paper/generated/sample.tex` |
| Table 2: Magnitude and precision | `results.json:distribution` | `paper/generated/distribution.tex` |
| Table 3: Direction-oriented means | `results.json:pooled` | `paper/generated/pooled.tex` |
| Table 4: Policy-outcome regressions | `results.json:policy_regressions` | `paper/generated/policy_regressions.tex` |
| Table 5: Tournament-rating regressions | `results.json:quality_regressions` | `paper/generated/quality_regressions.tex` |
| Figure 1: Magnitude distributions | `analysis_sample.csv` | `output/figures/magnitude_cdf.pdf` |
| Figure 2: Policy domains | `results.json:domains` | `output/figures/domains.pdf` |
| Table A1: Direction thresholds | `results.json:sign_sensitivity` | `paper/generated/thresholds.tex` |
| Table A2: Alternative samples | `results.json:robustness` | `paper/generated/robustness.tex` |
| Table A3: Arithmetic diagnostics | `results.json:distribution` | `paper/generated/identities.tex` |
| Table A4: Alternative weights | `results.json:weighting` | `paper/generated/weights.tex` |
| Table A5: Annotation setups | `results.json:direction_comparison` | `paper/generated/direction_comparison.tex` |

`output/tables/exhibit_map.csv` supplies the same mapping for machine use. `paper/generated/numbers.tex` supplies 59 macros used for the numerical claims in the text. All coefficient estimates, including omitted-from-display categorical controls, are exported in `output/tables/*_all_coefficients.csv`; the results JSON also records reference categories and omitted dependent/constant columns. Conventional regression displays include the intercept, observations, RÂ², adjusted RÂ², unweighted RMSE, residual degrees of freedom and HC3 Wald statistics. Standard errors appear below coefficients.

## Validation and interpretation

The thirteen checks cover a closed-form homoskedastic REML solution, translation invariance, the zero-variance boundary, modified HK inference, weighted-mean uncertainty, the Egger intercept, unresolved direction, the earlier probability inversion, escaped ampersands/parenthesized errors, table/panel selection, exclusion of results from contextual paragraphs, retention of supported moderate-confidence directions, and an enforcement-proxy safeguard. Source arithmetic failures are reported rather than corrected or hidden. The primary sample retains them; a sensitivity removes them. Standard errors rounded to zero are not replaced with an invented floor.

Exact duplicate table files are removed; this is not a test of independence among all remaining papers. Reported variances, common data sources, outcome selection and the shared automated production process limit inference. Country-group bootstrap intervals are additional sensitivity summaries, not a solution to every dependence pattern. Model probabilities and design descriptions lack an independent validation sample. The more confident subset changes point estimates but its intervals also include zero. The package exposes annotation and safeguard sensitivity rather than maximizing coverage by assigning directions to every measure.

## References and citation

Source citations and methods references appear in `paper/main.tex`; `CITATION.cff` identifies this package. The README sources above document acquisition and replication requirements. Please cite the paper and the frozen package version, and retain the separate upstream APE citations. A persistent archive citation should be added when a DOI has actually been assigned.
