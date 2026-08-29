"""
Accumulated Local Effects (ALE) for the top-k SHAP-ranked features (RQ2).

Complementary to SHAP, not a substitute: SHAP answers "why did the model
flag this specific wafer" (local); ALE answers "on average, how does fail
probability move as one sensor's reading changes" (global). ALE is used in
place of Partial Dependence Plots (PDP) because PDP assumes feature
independence when averaging, which is a poor assumption given the
correlation clustering already required elsewhere in this pipeline to
handle SECOM's known multicollinearity (Apley & Zhu, 2020).

See docs/synopsis.docx, "Solution to RQ2" for the full write-up.
"""

import numpy as np
import pandas as pd
from scipy.stats import spearmanr, ttest_rel, wilcoxon


def paired_agreement_significance_test(correlations_a: np.ndarray, correlations_b: np.ndarray) -> dict:
    """
    Formal significance test for whether two models' per-instance SHAP-
    agreement correlations (e.g. TabNet attention vs. SHAP, and an MLP
    control's Integrated Gradients vs. SHAP) genuinely differ, rather than
    reporting the two mean correlations side by side and treating a visible
    gap as self-evidently significant. This is what RQ4's own stated
    hypotheses (H0/Ha) require: a formal test at a stated significance
    level, not an eyeballed comparison.

    Uses a PAIRED test, not an independent-samples test, since both arrays
    are per-instance correlations computed on the SAME wafers (paired by
    instance) -- treating them as independent would throw away that
    pairing and understate the test's power.

    Two tests are reported together, matching this project's established
    pattern of pairing a primary parametric test with a non-parametric
    cross-check elsewhere (e.g. RQ3's bootstrap AUC comparison alongside
    McNemar's test): a paired t-test (primary) and a Wilcoxon signed-rank
    test (robustness check, since per-instance correlations are bounded to
    [-1, 1] and often skewed, which can violate the t-test's normality
    assumption).
    """
    correlations_a = np.asarray(correlations_a)
    correlations_b = np.asarray(correlations_b)
    if correlations_a.shape != correlations_b.shape:
        raise ValueError(
            f"Shape mismatch: {correlations_a.shape} vs {correlations_b.shape} -- "
            "both arrays must be paired, per-instance correlations over the same wafers."
        )

    diffs = correlations_a - correlations_b

    # Guard the degenerate case (identical or near-identical arrays) for BOTH
    # tests: scipy's ttest_rel returns NaN when the differences have zero
    # variance (0/0 internally), which is a real edge case, not hypothetical --
    # caught by testing this function against identical-array inputs before
    # shipping. NaN would be misleading here since the correct semantic
    # answer ("no difference") is well-defined even though the raw t-statistic
    # is not.
    if np.allclose(diffs, 0):
        t_stat, t_pvalue = 0.0, 1.0
        w_stat, w_pvalue = 0.0, 1.0
    else:
        t_stat, t_pvalue = ttest_rel(correlations_a, correlations_b)
        w_stat, w_pvalue = wilcoxon(correlations_a, correlations_b)

    return {
        "mean_diff": float(np.mean(diffs)),
        "paired_ttest_statistic": float(t_stat),
        "paired_ttest_pvalue": float(t_pvalue),
        "wilcoxon_statistic": float(w_stat),
        "wilcoxon_pvalue": float(w_pvalue),
        "n_pairs": int(len(correlations_a)),
    }


def per_instance_agreement(importances_a: np.ndarray, importances_b: np.ndarray, top_k: int = 3) -> dict:
    """
    Compares two per-instance feature-importance matrices (same shape:
    n_instances x n_features), e.g. SHAP values vs. TabNet attention masks,
    or SHAP values vs. Integrated Gradients attributions (RQ4's stated
    methodology). For each instance, computes the Spearman rank correlation
    between the two importance rankings and whether their top-k features
    fully agree (same set, order-independent).

    Returns per-instance arrays plus summary statistics, so both the mean
    agreement AND its distribution can be reported (a single mean can hide
    whether agreement is consistent or highly instance-dependent).
    """
    importances_a = np.asarray(importances_a)
    importances_b = np.asarray(importances_b)
    if importances_a.shape != importances_b.shape:
        raise ValueError(
            f"Shape mismatch: {importances_a.shape} vs {importances_b.shape} -- "
            "both importance matrices must cover the same instances and features."
        )

    n_instances, n_features = importances_a.shape
    correlations = np.zeros(n_instances)
    top_k_agreement = np.zeros(n_instances, dtype=bool)

    for i in range(n_instances):
        rho, _ = spearmanr(importances_a[i], importances_b[i])
        correlations[i] = rho if np.isfinite(rho) else 0.0

        top_a = set(np.argsort(-np.abs(importances_a[i]))[:top_k])
        top_b = set(np.argsort(-np.abs(importances_b[i]))[:top_k])
        top_k_agreement[i] = top_a == top_b

    return {
        "per_instance_correlation": correlations,
        "per_instance_top_k_agreement": top_k_agreement,
        "mean_correlation": float(np.mean(correlations)),
        "median_correlation": float(np.median(correlations)),
        "top_k_agreement_rate": float(np.mean(top_k_agreement)),
    }


def compute_ale(
    model, X: pd.DataFrame, feature: str, n_bins: int = 20, predict_fn=None
) -> pd.DataFrame:
    """
    Compute a 1D ALE curve for a single feature.

    model: a fitted classifier with a .predict_proba(X) method (or pass
        predict_fn explicitly for models with a different interface, e.g.
        model.predict for a raw probability output).
    Returns a DataFrame with bin midpoints and the accumulated local effect
    at each midpoint, centered so the curve's weighted mean is zero (the
    standard ALE convention -- values are effects relative to the average
    prediction, not absolute probabilities).
    """
    if predict_fn is None:
        predict_fn = lambda data: model.predict_proba(data)[:, 1]

    x = X[feature].values
    quantiles = np.unique(np.quantile(x, np.linspace(0, 1, n_bins + 1)))
    if len(quantiles) < 3:
        raise ValueError(
            f"Feature '{feature}' has too few unique values for {n_bins} ALE bins; "
            "reduce n_bins."
        )

    bin_idx = np.clip(np.digitize(x, quantiles[1:-1], right=True), 0, len(quantiles) - 2)

    local_effects = np.zeros(len(quantiles) - 1)
    counts = np.zeros(len(quantiles) - 1)

    for b in range(len(quantiles) - 1):
        mask = bin_idx == b
        if not mask.any():
            continue
        X_lo = X.loc[mask].copy()
        X_hi = X.loc[mask].copy()
        X_lo[feature] = quantiles[b]
        X_hi[feature] = quantiles[b + 1]

        pred_lo = predict_fn(X_lo)
        pred_hi = predict_fn(X_hi)

        local_effects[b] = np.mean(pred_hi - pred_lo)
        counts[b] = mask.sum()

    accumulated = np.concatenate([[0], np.cumsum(local_effects)])
    bin_centers = (quantiles[:-1] + quantiles[1:]) / 2

    # Center the curve so its weighted mean (over observed data density) is zero
    midpoint_values = (accumulated[:-1] + accumulated[1:]) / 2
    weighted_mean = np.average(midpoint_values, weights=np.maximum(counts, 1))
    accumulated_centered = accumulated - weighted_mean

    return pd.DataFrame(
        {
            "bin_edge": quantiles,
            "accumulated_local_effect": accumulated_centered,
        }
    )


def ale_report_for_top_features(
    model, X: pd.DataFrame, top_features: list[str], n_bins: int = 20
) -> dict:
    """
    Convenience wrapper: compute ALE curves for each of RQ3's top-k
    SHAP-selected features, for inclusion alongside the SHAP importance
    ranking in the RQ2/RQ3 write-up.
    """
    return {feat: compute_ale(model, X, feat, n_bins=n_bins) for feat in top_features}
