"""Random-effects summaries and descriptive regressions with explicit assumptions."""
import numpy as np
from scipy import optimize, stats
import statsmodels.api as sm


def tau2_reml(y, v):
    """Profile restricted likelihood with an estimated intercept and boundary."""
    y, v = np.asarray(y, float), np.asarray(v, float)
    def objective(tau2):
        total = v + tau2
        weights = 1 / total
        mean = weights @ y / weights.sum()
        return .5 * (np.log(total).sum() + np.log(weights.sum())
                     + np.sum(weights * (y - mean) ** 2))
    upper = max(float(np.var(y, ddof=1)) * 4, float(np.max(v)), 1e-6)
    fit = optimize.minimize_scalar(objective, bounds=(0, upper), method="bounded",
                                   options={"xatol": 1e-12})
    if not fit.success:
        raise RuntimeError("REML optimization failed")
    return 0.0 if objective(0) <= fit.fun else float(fit.x)


def full_meta(y, v, label=""):
    y, v = np.asarray(y, float), np.asarray(v, float)
    ok = np.isfinite(y) & np.isfinite(v) & (v > 0)
    y, v = y[ok], v[ok]
    k = len(y)
    if k < 3:
        raise ValueError("At least three usable studies required")
    wfe = 1 / v
    mfe = wfe @ y / wfe.sum()
    qfe = float(np.sum(wfe * (y - mfe) ** 2))
    df = k - 1
    c = wfe.sum() - np.sum(wfe ** 2) / wfe.sum()
    dl = max(0., (qfe - df) / c)
    tau2 = tau2_reml(y, v)
    weights = 1 / (v + tau2)
    mean = float(weights @ y / weights.sum())
    qhk = float(np.sum(weights * (y - mean) ** 2) / df)
    # Modified Hartung-Knapp: intervals never narrower than unadjusted RE.
    variance = max(1., qhk) / weights.sum()
    se = np.sqrt(variance)
    critical = stats.t.ppf(.975, df)
    pi_width = stats.t.ppf(.975, k - 2) * np.sqrt(tau2 + variance)
    return {"label": label, "k": k, "estimate": mean, "se": float(se),
            "ci_lo": float(mean - critical * se), "ci_hi": float(mean + critical * se),
            "p": float(2 * stats.t.sf(abs(mean / se), df)),
            "tau2": tau2, "tau2_dl": float(dl), "hk_q": qhk,
            "Q": qfe, "Q_df": df, "Q_p": float(stats.chi2.sf(qfe, df)),
            "I2": max(0., (qfe - df) / qfe * 100) if qfe else 0.,
            "pi_lo": float(mean - pi_width), "pi_hi": float(mean + pi_width),
            "effective_k": float(weights.sum() ** 2 / (weights @ weights)),
            "max_re_weight": float(weights.max() / weights.sum()),
            "max_fe_weight": float(wfe.max() / wfe.sum())}


def weighted_mean(y, weights):
    """Sandwich SE for a weighted descriptive mean, including paper variation."""
    y, weights = np.asarray(y, float), np.asarray(weights, float)
    k = len(y)
    normalized = weights / weights.sum()
    mean = float(normalized @ y)
    se = float(np.sqrt(k / (k - 1) * np.sum(normalized ** 2 * (y - mean) ** 2)))
    width = stats.t.ppf(.975, k - 1) * se
    return {"k": k, "estimate": mean, "se": se,
            "ci_lo": float(mean - width), "ci_hi": float(mean + width)}


def regression(y, X, names, weights=None):
    """OLS/WLS, HC3 covariance and t inference; refuse rank-deficient designs."""
    y, X = np.asarray(y, float), np.asarray(X, float)
    if np.linalg.matrix_rank(X) != X.shape[1]:
        raise ValueError("Rank-deficient design matrix")
    if len(y) <= X.shape[1] + 2:
        raise ValueError("Insufficient residual degrees of freedom")
    model = sm.OLS(y, X) if weights is None else sm.WLS(y, X, weights=weights)
    fit = model.fit(cov_type="HC3", use_t=True)
    return {"n": int(fit.nobs), "rank": int(X.shape[1]), "df_resid": int(fit.df_resid),
            "r2": float(fit.rsquared), "adj_r2": float(fit.rsquared_adj),
            "rmse": float(np.sqrt(np.mean(fit.resid ** 2))),
            "f": float(fit.fvalue), "f_p": float(fit.f_pvalue),
            "params": dict(zip(names, map(float, fit.params))),
            "se": dict(zip(names, map(float, fit.bse))),
            "p": dict(zip(names, map(float, fit.pvalues)))}


def egger(y, v):
    """Standard normal deviate on precision; asymmetry tests INTERCEPT."""
    y, v = np.asarray(y, float), np.asarray(v, float)
    se = np.sqrt(v)
    X = np.column_stack([np.ones(len(y)), 1 / se])
    res = regression(y / se, X, ["const", "precision"])
    return {"k": res["n"], "intercept": res["params"]["const"],
            "se": res["se"]["const"], "p": res["p"]["const"]}
