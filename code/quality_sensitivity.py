"""Exploratory rating emphasis, common samples and paired bootstrap comparisons.

TrueSkill means have no calibrated mapping to effect bias or sampling precision.
Only their ordering enters the bounded multipliers. Conventional HK inference
is not applied to the resulting custom weights.
"""
import numpy as np
from scipy import stats
from meta import tau2_reml, full_meta


def rating_multipliers(mu, strength):
    mu = np.asarray(mu, float)
    if mu.ndim != 1 or len(mu) < 3 or not np.isfinite(mu).all():
        raise ValueError("At least three finite ratings required")
    if not np.isfinite(strength) or not 0 <= strength <= 1:
        raise ValueError("Rating emphasis must be between zero and one")
    rank = (stats.rankdata(mu, method="average") - .5) / len(mu)
    return 1 + strength * rank


def _summaries(y, v, mu, strengths):
    tau2 = tau2_reml(y, v)
    rows, normalized_weights = [], []
    for base in ("Equal", "REML"):
        initial = np.ones(len(y)) if base == "Equal" else 1 / (v + tau2)
        for strength in strengths:
            w = initial * rating_multipliers(mu, strength)
            p = w / w.sum()
            rows.append({"base": base, "lambda": float(strength), "k": len(y),
                         "estimate": float(p @ y), "effective_k": float(1 / (p @ p)),
                         "max_weight": float(p.max()), "tau2": float(tau2) if base == "REML" else None})
            normalized_weights.append(p)
    return rows, np.asarray(normalized_weights)


def rating_sensitivity(y, v, mu, strengths=(0., .5, 1.), B=1999, seed=20261002):
    """No silent exclusions: caller supplies the explicitly documented sample."""
    y, v, mu = (np.asarray(z, float) for z in (y, v, mu))
    if (y.ndim != 1 or y.shape != v.shape or y.shape != mu.shape or len(y) < 3
            or not all(np.isfinite(z).all() for z in (y, v, mu)) or (v <= 0).any()):
        raise ValueError("Equal-length finite observations and positive variances required")
    if tuple(strengths) != (0., .5, 1.) or B < 20:
        raise ValueError("Protocol requires strengths 0, 0.5, 1 and at least 20 bootstrap draws")
    rows, weights = _summaries(y, v, mu, strengths)
    rng = np.random.default_rng(seed)
    draws = np.empty((B, len(rows)))
    for b in range(B):
        idx = rng.integers(len(y), size=len(y))
        samples, _ = _summaries(y[idx], v[idx], mu[idx], strengths)
        draws[b] = [r['estimate'] for r in samples]
    for j, row in enumerate(rows):
        reference = 0 if row['base'] == 'Equal' else len(strengths)
        row.update(ci_lo=float(np.quantile(draws[:, j], .025)),
                   ci_hi=float(np.quantile(draws[:, j], .975)),
                   delta=float(row['estimate'] - rows[reference]['estimate']),
                   delta_lo=float(np.quantile(draws[:, j] - draws[:, reference], .025)),
                   delta_hi=float(np.quantile(draws[:, j] - draws[:, reference], .975)),
                   inference="Independent-paper percentile bootstrap", replications=B, seed=seed)
    median = float(np.median(mu))
    groups = []
    for label, mask in [('Below median rating', mu < median), ('At/above median rating', mu >= median)]:
        if mask.sum() >= 3:
            groups.append({"group": label, "median_mu": median,
                           "inference": "REML / modified Hartung-Knapp",
                           **full_meta(y[mask], v[mask], label)})
    return {"summaries": rows, "groups": groups, "median_mu": median,
            "mu_log_se_spearman": float(stats.spearmanr(mu, np.log(np.sqrt(v))).statistic)
                if np.ptp(mu) > 0 and np.ptp(v) > 0 else None}, weights
