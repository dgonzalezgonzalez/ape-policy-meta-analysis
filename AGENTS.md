# Replication-package instructions

This project analyzes reported standardized estimates from Project APE. See the
root README for the research population, provenance, rights, software and outputs.
The frozen sources and analytical definitions must not change silently.

## Environment

On the author's Windows machine use:

```powershell
$PY = 'C:\Users\dgonzalez\AppData\Local\Programs\Python\Python312\python.exe'
& $PY run_all.py
```

`python` on PATH is the Microsoft Store stub. Use an actual interpreter. The
portable driver uses its current interpreter for every child stage. MiKTeX
`latexmk` needs unavailable Perl; use the driver's two direct `pdflatex` passes.
The manuscript is a multi-file project compiled from `paper/`.

## Pipeline

Default offline replication is `run_all.py`. It verifies inputs, builds the
dataset, runs benchmark checks, analyzes, generates TeX and figures, compiles and
checks outputs. `--no-pdf` omits TeX compilation. Optional `--rebuild-sources`
downloads immutable third-party files, parses, validates and reconstructs the
factual extracts before analysis. `--enrich` additionally permits paid API use.

`make_tex.py` is now read-only with respect to analysis inputs and can safely be
rerun. `paper/main.tex` has its own end-of-document command. Do not restore the
obsolete generator's input mutations or incomplete document behavior.

After any parser edit run `code/validate.py` on the acquired originals, run the
benchmark checks and inspect source disagreements. Classification is a
magnitude-only field; its presence provides a column-alignment guard. Locate
columns by header names, preserve escaped ampersands and panels, and treat only
parenthesized SEs as positive. Never infer missing SD(X) from the very SDE being
validated. Source arithmetic failures are diagnostics, not parser-test failures.

## Analytical invariants

- Binary `beta/SD(Y)` and continuous `beta*SD(X)/SD(Y)` are different estimands.
  Keep pooling, domain summaries and policy regressions separate.
- Source papers in this frozen SDE cohort date to March–April 2026 and use the
  Claude Opus 4.6 production cohort. The AA v4.3.2 value 31.95 is constant and
  cannot identify an intelligence effect. Do not reintroduce that regression.
- Elo is an affine transformation of TrueSkill mu, not a second assessment
  outcome. Do not add redundant transformed-outcome tables.
- Source classifications do not encode welfare direction. `welfare_sign` and
  `sde_welfare` are legacy dataset names for constructed favourable-outcome
  directions, not net-welfare estimates. Unknown directions must remain NaN.
- Outcome benefit, stated intent and net welfare are distinct. Never equate
  descriptive measures or a policymaker's goal with beneficiary welfare.
- Use the latest source version, with no silent fallback to an earlier parse.
  Exact repeated tables are deduplicated, but other dependence remains possible.
- Reported standard errors are data. Preserve zero/missing/negative errors as
  exclusions, never manufacture a positive precision floor.
- Fixed-effect weights can be concentrated in one paper. Do not quote the old
  fixed-effect point estimate as a policy result. REML, modified HK and prediction
  intervals carry the explicitly stated assumptions in the manuscript.
- Strict directional subsets may differ from baseline; report disagreement.
  Apply all fifteen threshold pairs to the whole comparable sample.

## Annotation

Jev is pinned to `jev-1.13.0`. One request batches literal questions per paper.
Covariates use own-table notes. The user explicitly authorized richer directional
context: selected data/setting paragraphs only, excluding results, numerical effects,
standard errors, ratings and full-paper transmission. See jev_direction.py. Numerical operations, thresholding and
combination remain in Python. Use explicit higher/lower beneficiary questions;
absence of support for one is not support for the other. Request hashes cover
questions, state and model. Do not reuse stale responses or leak `.env` keys.

No API key or network is needed for the released cached-input replication.
Intentional input revisions require new checksums and a documented new release.

## Writing and output

Use Diego's academic-writing skill for manuscript edits. Sole author: singular.
Keep descriptive coefficients distinct from causal determinants. Avoid novelty
fluff, unsupported claims, and treating insignificance as proof of zero effects.
Remove redundant affine-output analyses and irrelevant model-index discussion.

Economics regression tables have left-aligned variable labels and centered result
columns. Column label precedes number, with the horizontal rule beneath both.
Include constants, N, R2, adjusted R2, RMSE and relevant inference statistics.
Coefficients and parenthesized standard errors occupy separate rows.

Use safe LaTeX placeholder replacement, not percent-formatting of TeX templates.
Each table is emitted as one block. Long notes sit outside tabular in a minipage.
Escape percent/ampersand/underscore in ordinary labels. Render and inspect the
whole PDF after substantive changes; compiler exit status alone is insufficient.
Check margins, tables, axes, legends, unresolved placeholders and log warnings.

The requested detector is optional, pinned in separate requirements and checked
against the exact final PDF hash. Retain the AI-assistance disclosure regardless
of its classification; a non-flag establishes no authorship claim.

## Publication

The user authorized a public GitHub replication package. Preserve `.local/`
originals and never commit secrets or full third-party prose. Original source text
is gitignored because the source snapshot has no explicit redistribution licence.
Do not invent third-party permissions, author certification, an archive DOI or
JPE approval. The QMD is an author-side adaptation of a replicator template.

Direction revision: use data/direction_protocol.json. Baseline is margin .15,
support .55, ambiguity below .75, no opposite-response ceiling. Group composition
flags at .65 are unresolved; reporting/activity flags additionally require ambiguity
.40. Retain strict, notes-only and unguarded comparisons. Treat the illustrative
AI-assisted audit as provisional; it is not independent validation.
