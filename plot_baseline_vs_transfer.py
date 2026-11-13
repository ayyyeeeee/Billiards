#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Baseline versus immediate post-test, with separate Student-t mean/variance.

Scans all 30 participants and recursive processed_csv directories. Primary stage
estimates use constant location/scale Student-t likelihood (fixed nu=5); raw
sample moments and absolute errors remain available for sensitivity analysis.
Only valid scored finite values are used; statistical outliers are not deleted.
Zero-safe log variance axes retain the full participant range. Source data are
read-only. See generated METHODS.txt for interpretation and limitations.
"""

import os
import re
import glob
import argparse
import warnings
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

sys.path.insert(0, str(Path(__file__).resolve().parent / "tools" / "outlier_batch"))
from robust_model import fit_student_t
from censoring import censor_values, censor_codes

try:
    from scipy import stats as sp_stats
    HAS_SCIPY = True
except ImportError:
    HAS_SCIPY = False

warnings.filterwarnings("ignore", category=RuntimeWarning)

# ==============================================================================
# Publication Style & Color Palette (Okabe-Ito Colorblind-Safe)
# ==============================================================================
plt.rcParams.update({
    "font.family": "sans-serif",
    "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans"],
    "font.size": 10,
    "axes.titlesize": 8,
    "axes.titleweight": "bold",
    "axes.labelsize": 7,
    "axes.labelweight": "bold",
    "xtick.labelsize": 6.5,
    "ytick.labelsize": 6.5,
    "legend.fontsize": 9,
    "figure.titlesize": 13,
    "figure.titleweight": "bold",
    "axes.linewidth": 1.0,
    "grid.linewidth": 0.5,
    "lines.linewidth": 1.5,
    "savefig.dpi": 300,
    "savefig.bbox": None,
    "pdf.fonttype": 42,
    "ps.fonttype": 42,
})

GROUP_ORDER = ["both", "strength", "angle"]
GROUP_LABELS = {
    "both": "Both Training Group",
    "strength": "Strength Training Group",
    "angle": "Angle Training Group",
}
GROUP_SHORT_LABELS = {
    "both": "Both Grp",
    "strength": "Strength Grp",
    "angle": "Angle Grp",
}
GROUP_COLORS = {
    "both": "#0072B2",      # Blue
    "strength": "#D55E00",  # Orange / Vermilion
    "angle": "#009E73",     # Bluish Green
}
GROUP_MARKERS = {
    "both": "o",
    "strength": "s",
    "angle": "^",
}

TASK_ORDER = ["both", "strength", "angle"]
TASK_LABELS = {
    "both": "Both Task (Strength + Angle)",
    "strength": "Strength-Only Task",
    "angle": "Angle-Only Task",
}

# Measure metadata: (key, display_name, short_name, unit, dimension, zero_origin, lower_is_better)
PRIMARY_MEASURES = [
    ("strength_mean", "Strength Mean (Signed)", "Strength Mean", "O->B units", "strength", False, False),
    ("strength_variance", "Strength Variance", "Strength Variance", "(O->B units)^2", "strength", True, True),
    ("angle_mean", "Angle Mean (Signed)", "Angle Mean", "deg", "angle", False, False),
    ("angle_variance", "Angle Variance", "Angle Variance", "deg^2", "angle", True, True),
]

SUPPLEMENTARY_MEASURES = [
    ("strength_abs_err", "Mean Abs. Strength Error", "Mean |Strength Error|", "O->B units", "strength", True, True),
    ("angle_abs_err", "Mean Abs. Angle Error", "Mean |Angle Error|", "deg", "angle", True, True),
]

ALL_MEASURES = PRIMARY_MEASURES + SUPPLEMENTARY_MEASURES


# ==============================================================================
# Data Loading & Filtering Helpers
# ==============================================================================

def find_csv_file(subj_dir: Path, stage_prefix: str, search_subdirs: List[str]) -> Optional[Path]:
    """
    Search for a segment CSV matching `stage_prefix` (e.g. '01_baseline', '04_training', '05_test')
    across priority subdirectories inside a subject folder.
    """
    subj_id = subj_dir.name
    patterns = [
        f"{subj_id}_{stage_prefix}*.csv",
        f"*_{stage_prefix}*.csv",
        f"{stage_prefix}*.csv",
    ]
    for subdir in search_subdirs:
        folder = subj_dir / subdir if subdir else subj_dir
        if not folder.exists() or not folder.is_dir():
            continue
        for pat in patterns:
            matches = sorted(folder.rglob(pat)) if subdir else sorted(folder.glob(pat))
            if matches:
                return matches[0]
    return None


def detect_training_group_from_file(filepath: Path, df: pd.DataFrame) -> Optional[str]:
    """
    Identify whether the participant's training condition is 'both', 'strength', or 'angle'
    from the training filename or 'mode' column.
    """
    fname = filepath.name.lower()
    for mode in ["both", "strength", "angle"]:
        if f"training_{mode}" in fname or f"04_{mode}" in fname:
            return mode
    if "training_regular" in fname:
        return "both"
    if "mode" in df.columns:
        modes = df["mode"].dropna().astype(str).str.strip().str.lower().unique()
        for m in modes:
            if m == "regular":
                return "both"
            if m in ("both", "strength", "angle"):
                return m
    return None


def extract_clean_series(df: pd.DataFrame, value_col: str, outlier_col: str, is_training: bool = False) -> pd.Series:
    """Scored, valid finite component observations; historical review flags ignored.

    Baseline/test retain scored valid values; historical flags do not delete them.
    Training uses finite labeled values, excluding exactly outlier=1, per the
    2026-11-08 user rule; status/review flags are not additional training filters.
    """
    if value_col not in df.columns:
        return pd.Series(dtype=float)
    channel = value_col.removesuffix('_value')
    values = pd.to_numeric(df[value_col], errors="coerce")
    mask = pd.Series(np.isfinite(values), index=df.index)
    if is_training:
        if outlier_col in df:
            mask &= ~pd.to_numeric(df[outlier_col], errors='coerce').eq(1)
        return values[mask]
    status = channel + '_status'
    if status in df:
        mask &= df[status].astype(str).str.lower().eq('scored')
    elif 'score_complete' in df:
        mask &= pd.to_numeric(df.score_complete, errors='coerce').eq(1)
    valid = channel + '_valid'
    if valid in df:
        mask &= pd.to_numeric(df[valid], errors='coerce').eq(1)
    return values[mask]


def compute_stage_metrics(df: pd.DataFrame, is_training: bool = False) -> Dict[str, float]:
    """Separate Student-t location/variance estimates and unmodified sample moments.

    Fixed nu=5 provides finite variance; location/scale are constant within a
    baseline or post-test stage. No data-driven hard statistical deletion.
    Model variance = scale**2 * nu/(nu-2), not scale**2.
    """
    res = {'n_rows_raw': len(df)}
    for channel in ('strength', 'angle'):
        values = extract_clean_series(df, channel+'_value', channel+'_outlier', is_training=is_training)
        n = len(values)
        res['n_'+channel] = n
        mean = float(values.mean()) if n else np.nan
        variance = float(values.var(ddof=1)) if n >= 2 else np.nan
        res['raw_'+channel+'_mean'] = mean
        res['raw_'+channel+'_variance'] = variance
        res[channel+'_abs_err'] = float(values.abs().mean()) if n else np.nan
        res[channel+'_mean'] = res[channel+'_variance'] = res[channel+'_sd'] = np.nan
        observed = censor_values(df, channel)
        codes = censor_codes(df, channel)
        positions = df.index.get_indexer(values.index)
        censor = codes[positions]
        fit_values = observed[positions]
        res[channel+'_n_censored'] = int(np.count_nonzero(censor))
        res[channel+'_fit_success'] = False
        res[channel+'_fit_message'] = 'Fewer than 5 valid observations'
        if n >= 5:
            fit = fit_student_t(np.arange(n, dtype=float), fit_values,
                                censor=censor, df_mean=1, df_scale=1, nu=5)
            res[channel+'_fit_success'] = bool(fit.success)
            res[channel+'_fit_message'] = fit.message
            if fit.success:
                pred = fit.predict(np.array([0.]))
                for key in ('mean','variance','sd'):
                    res[channel+'_'+key] = float(pred[key][0])
    return res


def load_all_subjects(root_dir: Path, subject_ids: Optional[List[str]] = None) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Scan subjects 01..30 in `root_dir`, load Baseline, Training, and Test CSVs,
    and return:
      1. `wide_df`: One row per (subject, group, task_condition) with Baseline & Transfer metrics.
      2. `train_df`: One row per subject summarizing Training shot counts & outlier exclusions.
    """
    if subject_ids is None:
        subject_ids = [f"{i:02d}" for i in range(1, 31)]

    # Search priority for Baseline & Test:
    # 1. processed_csv
    # 2. outlier_results/labeled_csv
    # 3. MOLT4_results/csv
    # 4. MOLT4_results_tests/csv (for subject 07 supplemental tests if needed)
    # 5.MOLT4_results_v3/csv
    # 6. subject root
    bt_subdirs = [
        "processed_csv",
        os.path.join("outlier_results", "labeled_csv"),
        os.path.join("MOLT4_results", "csv"),
        os.path.join("MOLT4_results_tests", "csv"),
        os.path.join("MOLT4_results_v3", "csv"),
        "",
    ]

    # Training must use the reviewed labeled source; do not silently fall back
    # to an unlabelled CSV where required outlier exclusions would be lost.
    train_subdirs = [os.path.join("outlier_results", "labeled_csv")]

    stage_map = {
        ("baseline", "both"): "01_baseline_both",
        ("baseline", "strength"): "02_baseline_strength",
        ("baseline", "angle"): "03_baseline_angle",
        ("transfer", "both"): "05_test_both",
        ("transfer", "strength"): "06_test_strength",
        ("transfer", "angle"): "07_test_angle",
    }

    records = []
    train_records = []

    for sid in subject_ids:
        subj_dir = root_dir / sid
        if not subj_dir.exists():
            continue

        # 1. Locate Training file & determine subject's group
        train_file = find_csv_file(subj_dir, "04_training", train_subdirs)
        group = None
        train_metrics = {}
        if train_file is not None and train_file.exists():
            try:
                t_df = pd.read_csv(train_file)
                group = detect_training_group_from_file(train_file, t_df)
                train_metrics = compute_stage_metrics(t_df, is_training=True)
                s_out_cnt = int((pd.to_numeric(t_df.get("strength_outlier", pd.Series(dtype=float)), errors="coerce") == 1).sum())
                a_out_cnt = int((pd.to_numeric(t_df.get("angle_outlier", pd.Series(dtype=float)), errors="coerce") == 1).sum())
                train_records.append({
                    "subject": sid,
                    "group": group if group else "unknown",
                    "training_file": str(train_file.relative_to(root_dir)),
                    "raw_training_shots": len(t_df),
                    "strength_outliers_removed": s_out_cnt,
                    "valid_strength_shots": train_metrics["n_strength"],
                    "angle_outliers_removed": a_out_cnt,
                    "valid_angle_shots": train_metrics["n_angle"],
                    "train_strength_mean": train_metrics["strength_mean"],
                    "train_strength_variance": train_metrics["strength_variance"],
                    "train_angle_mean": train_metrics["angle_mean"],
                    "train_angle_variance": train_metrics["angle_variance"],
                })
            except Exception as e:
                print(f"[WARN] Failed reading training file for subject {sid}: {e}")

        if group is None:
            print(f"[WARN] Could not determine training group for subject {sid}; skipping.")
            continue

        # 2. Locate and compute Baseline & Transfer metrics for all 3 task conditions
        for task in TASK_ORDER:
            b_prefix = stage_map[("baseline", task)]
            t_prefix = stage_map[("transfer", task)]

            # Also allow fallback prefix matching by stage number (01_, 02_, 03_, 05_, 06_, 07_)
            b_file = find_csv_file(subj_dir, b_prefix, bt_subdirs)
            if b_file is None:
                b_file = find_csv_file(subj_dir, b_prefix[:3], bt_subdirs)

            t_file = find_csv_file(subj_dir, t_prefix, bt_subdirs)
            if t_file is None:
                t_file = find_csv_file(subj_dir, t_prefix[:3], bt_subdirs)

            b_stats = compute_stage_metrics(pd.read_csv(b_file)) if (b_file and b_file.exists()) else {}
            t_stats = compute_stage_metrics(pd.read_csv(t_file)) if (t_file and t_file.exists()) else {}

            row = {
                "subject": sid,
                "group": group,
                "task": task,
                "baseline_file": str(b_file.relative_to(root_dir)) if b_file else "",
                "transfer_file": str(t_file.relative_to(root_dir)) if t_file else "",
            }
            for m_key, *_ in ALL_MEASURES:
                b_val = b_stats.get(m_key, np.nan)
                t_val = t_stats.get(m_key, np.nan)
                row[f"baseline_{m_key}"] = b_val
                row[f"transfer_{m_key}"] = t_val
                row[f"delta_{m_key}"] = t_val - b_val if (pd.notna(b_val) and pd.notna(t_val)) else np.nan

            for stage, metrics in [('baseline', b_stats), ('transfer', t_stats)]:
                for channel in ('strength', 'angle'):
                    for suffix in ('mean', 'variance'):
                        row[f'{stage}_raw_{channel}_{suffix}'] = metrics.get(f'raw_{channel}_{suffix}', np.nan)
                    for suffix in ('fit_success', 'fit_message', 'n_censored'):
                        row[f'{stage}_{channel}_{suffix}'] = metrics.get(f'{channel}_{suffix}', '')
            row["baseline_n_strength"] = b_stats.get("n_strength", 0)
            row["transfer_n_strength"] = t_stats.get("n_strength", 0)
            row["baseline_n_angle"] = b_stats.get("n_angle", 0)
            row["transfer_n_angle"] = t_stats.get("n_angle", 0)
            records.append(row)

    wide_df = pd.DataFrame(records)
    train_df = pd.DataFrame(train_records)
    return wide_df, train_df


# ==============================================================================
# Statistical Summary Helpers
# ==============================================================================

def compute_group_summary_table(wide_df: pd.DataFrame) -> pd.DataFrame:
    """
    Compute group-level and overall summary statistics (Mean, SD, SEM, Median, IQR,
    paired t-test p-value, Wilcoxon signed-rank p-value, Cohen's dz, % below y=x)
    for every (Task Condition, Measure, Group).
    """
    summary_rows = []
    if wide_df.empty:
        return pd.DataFrame()

    for task in TASK_ORDER:
        for m_key, m_title, m_short, m_unit, m_dim, _, _ in ALL_MEASURES:
            # Skip unmeasured combinations (e.g. strength in angle-only task, angle in strength-only task)
            if (task == "strength" and m_dim == "angle") or (task == "angle" and m_dim == "strength"):
                continue

            b_col = f"baseline_{m_key}"
            t_col = f"transfer_{m_key}"

            for grp in GROUP_ORDER + ["ALL"]:
                if grp == "ALL":
                    sub = wide_df[wide_df["task"] == task]
                else:
                    sub = wide_df[(wide_df["task"] == task) & (wide_df["group"] == grp)]

                paired = sub[[ "subject", b_col, t_col ]].dropna()
                n = len(paired)
                if n == 0:
                    continue

                b_arr = paired[b_col].to_numpy(dtype=float)
                t_arr = paired[t_col].to_numpy(dtype=float)
                d_arr = t_arr - b_arr

                b_mean, t_mean, d_mean = np.mean(b_arr), np.mean(t_arr), np.mean(d_arr)
                b_sd = np.std(b_arr, ddof=1) if n >= 2 else np.nan
                t_sd = np.std(t_arr, ddof=1) if n >= 2 else np.nan
                d_sd = np.std(d_arr, ddof=1) if n >= 2 else np.nan
                b_sem = b_sd / np.sqrt(n) if n >= 2 else np.nan
                t_sem = t_sd / np.sqrt(n) if n >= 2 else np.nan
                d_sem = d_sd / np.sqrt(n) if n >= 2 else np.nan

                n_below = int(np.sum(t_arr < b_arr))
                pct_below = 100.0 * n_below / n

                t_stat, p_val_t, w_stat, p_val_w, cohens_dz = np.nan, np.nan, np.nan, np.nan, np.nan
                if n >= 2 and d_sd > 1e-12:
                    cohens_dz = d_mean / d_sd
                    if HAS_SCIPY:
                        try:
                            res_t = sp_stats.ttest_rel(t_arr, b_arr)
                            t_stat, p_val_t = float(res_t.statistic), float(res_t.pvalue)
                        except Exception:
                            pass
                        try:
                            if np.any(d_arr != 0):
                                res_w = sp_stats.wilcoxon(t_arr, b_arr, zero_method="wilcox")
                                w_stat, p_val_w = float(res_w.statistic), float(res_w.pvalue)
                        except Exception:
                            pass

                summary_rows.append({
                    "task": task,
                    "measure": m_key,
                    "measure_label": m_title,
                    "unit": m_unit,
                    "group": grp,
                    "n_subjects": n,
                    "baseline_mean": b_mean,
                    "baseline_sd": b_sd,
                    "baseline_sem": b_sem,
                    "transfer_mean": t_mean,
                    "transfer_sd": t_sd,
                    "transfer_sem": t_sem,
                    "delta_mean": d_mean,
                    "delta_sd": d_sd,
                    "delta_sem": d_sem,
                    "n_transfer_lt_baseline": n_below,
                    "pct_transfer_lt_baseline": pct_below,
                    "paired_t_stat": t_stat,
                    "paired_t_p": p_val_t,
                    "wilcoxon_stat": w_stat,
                    "wilcoxon_p": p_val_w,
                    "cohens_dz": cohens_dz,
                })

    return pd.DataFrame(summary_rows)


# ==============================================================================
# Core Plotting Functions (1:1 Equal Axis + Red y=x Line)
# ==============================================================================

def compute_shared_limits(x: np.ndarray, y: np.ndarray, zero_origin: bool = False) -> Tuple[float, float]:
    """
    Compute identical (min_val, max_val) for X and Y axes so that the y = x
    reference line runs cleanly from the bottom-left corner to the top-right corner.
    """
    valid = np.concatenate([x[np.isfinite(x)], y[np.isfinite(y)]])
    if len(valid) == 0:
        return (0.0, 1.0) if zero_origin else (-1.0, 1.0)

    vmin, vmax = float(np.min(valid)), float(np.max(valid))
    if zero_origin:
        lo = 0.0
        span = max(vmax - lo, 1e-6)
        hi = vmax + 0.12 * span
        return (lo, hi)
    else:
        extent = max(abs(vmin), abs(vmax), 1e-6) * 1.14
        return (-extent, extent)


def draw_paired_scatter_panel(
    ax: plt.Axes,
    df_task: pd.DataFrame,
    m_key: str,
    m_short: str,
    m_unit: str,
    zero_origin: bool,
    groups_to_show: List[str],
    panel_title: str,
    show_subject_ids: bool = False,
    shared_lims: Optional[Tuple[float, float]] = None,
) -> None:
    """
    Render a single Baseline (X) vs Transfer (Y) paired scatter panel with:
      - Red solid y = x reference line from corner to corner
      - Equal 1:1 aspect ratio and identical X/Y limits
      - Individual participant scatter points + optional subject IDs
      - Group Mean +/- 1 SEM error crosshairs (diamond/square markers)
      - Compact statistical summary box
    """
    b_col = f"baseline_{m_key}"
    t_col = f"transfer_{m_key}"

    sub = df_task[df_task["group"].isin(groups_to_show)][["subject", "group", b_col, t_col]].dropna()
    if sub.empty:
        ax.text(0.5, 0.5, "No Data Available", ha="center", va="center", transform=ax.transAxes, fontsize=10, color="#666666")
        ax.set_title(panel_title)
        ax.set_aspect("equal", adjustable="box")
        return

    all_x = sub[b_col].to_numpy(dtype=float)
    all_y = sub[t_col].to_numpy(dtype=float)

    if shared_lims is not None:
        lo, hi = shared_lims
    else:
        lo, hi = compute_shared_limits(all_x, all_y, zero_origin=zero_origin)

    # 1. Subtle grid and zero reference lines (for signed means)
    ax.grid(True, linestyle=":", alpha=0.45, color="#B0B0B0", zorder=0)
    if not zero_origin and lo < 0 < hi:
        ax.axhline(0, color="#CCCCCC", linestyle="--", linewidth=0.8, zorder=1)
        ax.axvline(0, color="#CCCCCC", linestyle="--", linewidth=0.8, zorder=1)

    # 2. Red y = x identity line (Supervisor's key visual element)
    ax.plot([lo, hi], [lo, hi], color="#E61919", linestyle="-", linewidth=1.6, label="y = x (No Change)", zorder=2)

    # 3. Plot individual participants & group mean +/- SEM crosshairs
    for grp in groups_to_show:
        g_sub = sub[sub["group"] == grp]
        if g_sub.empty:
            continue
        gx = g_sub[b_col].to_numpy(dtype=float)
        gy = g_sub[t_col].to_numpy(dtype=float)
        n_g = len(g_sub)

        color = GROUP_COLORS.get(grp, "#333333")
        marker = GROUP_MARKERS.get(grp, "o")

        # Individual subject points (hollow/semi-transparent fill with crisp edge, matching sketch)
        ax.scatter(
            gx, gy,
            s=46,
            facecolors=color,
            edgecolors="white",
            linewidths=0.7,
            alpha=0.78,
            marker=marker,
            zorder=3,
            label=f"{GROUP_SHORT_LABELS.get(grp, grp)} (n={n_g})"
        )

        if show_subject_ids:
            for _, r in g_sub.iterrows():
                ax.annotate(
                    str(r["subject"]),
                    (float(r[b_col]), float(r[t_col])),
                    xytext=(3, 3),
                    textcoords="offset points",
                    fontsize=6.5,
                    color=color,
                    alpha=0.85,
                    zorder=4,
                )

        # Group Mean +/- 1 SEM crosshair
        if n_g >= 2:
            mx, my = float(np.mean(gx)), float(np.mean(gy))
            sx = float(np.std(gx, ddof=1) / np.sqrt(n_g))
            sy = float(np.std(gy, ddof=1) / np.sqrt(n_g))
            ax.errorbar(
                mx, my,
                xerr=sx, yerr=sy,
                fmt=marker,
                 markersize=7.5,
                color=color,
                ecolor=color,
                elinewidth=1.8,
                capsize=3.5,
                capthick=1.2,
                markeredgecolor="black",
                markeredgewidth=1.0,
                zorder=5,
            )


    # 4. Enforce identical 1:1 axis limits and ticks
    ax.set_xlim(lo, hi)
    ax.set_ylim(lo, hi)
    ax.set_aspect("equal", adjustable="box")

    # Variance spans orders of magnitude. A zero-safe logarithmic display keeps
    # all participants visible without trimming/winsorizing observations.
    variance_axis = m_key.endswith('_variance')
    if variance_axis:
        threshold = 0.01 if m_key.startswith('strength') else 0.1
        ax.set_xscale('symlog', linthresh=threshold, linscale=0.6)
        ax.set_yscale('symlog', linthresh=threshold, linscale=0.6)
        ticks = [v for v in [0, threshold, threshold*10, threshold*100,
                            threshold*1000, threshold*10000] if lo <= v <= hi]
        ax.set_xticks(ticks)
        ax.set_yticks(ticks)
        ax.xaxis.set_major_formatter(matplotlib.ticker.ScalarFormatter())
        ax.yaxis.set_major_formatter(matplotlib.ticker.ScalarFormatter())
        panel_title += "\nZero-safe log axes"

    # Synchronize tick positions on X and Y axes
    locator = matplotlib.ticker.MaxNLocator(nbins=5)
    ticks = locator.tick_values(lo, hi)
    ticks = [t for t in ticks if lo - 1e-9 <= t <= hi + 1e-9]
    if len(ticks) >= 2 and not variance_axis:
        ax.set_xticks(ticks)
        ax.set_yticks(ticks)

    ax.set_xlabel(f"Baseline ({m_unit})")
    ax.set_ylabel(f"Transfer ({m_unit})")
    ax.set_title(panel_title, pad=8)

    # Numeric summaries live in the companion three-rule table, not over data.
    if m_key in ('angle_abs_err', 'angle_mean'):
        _add_focus_inset(ax, sub, b_col, t_col, groups_to_show, zero_origin)


def _add_focus_inset(ax, sub, b_col, t_col, groups, zero_origin):
    """Show the central cloud while the parent axes retain every participant."""
    all_values = sub[[b_col, t_col]].to_numpy(dtype=float).ravel()
    extent = float(np.quantile(np.abs(all_values), .85)) * 1.12
    outer = max(abs(v) for v in ax.get_xlim())
    if extent <= 0 or extent >= outer * .75:
        return
    focus = (0., extent) if zero_origin else (-extent, extent)
    # Put the inset in an empty corner of the FULL plot, avoiding covered dots.
    xy = ax.transAxes.inverted().transform(ax.transData.transform(sub[[b_col,t_col]].to_numpy()))
    candidates = [(0.06,.57,.40,.37), (.57,.57,.40,.37), (.06,.06,.40,.37), (.57,.06,.40,.37)]
    def covered(box):
        x,y,w,h=box
        return int(((xy[:,0]>=x)&(xy[:,0]<=x+w)&(xy[:,1]>=y)&(xy[:,1]<=y+h)).sum())
    box=min(candidates,key=covered)
    if covered(box):
        return  # Never cover a participant just to add a zoom.
    ins=ax.inset_axes(box, zorder=10)
    ins.set_facecolor('white')
    ins.plot(focus,focus,c='#999999',lw=.65,zorder=1)
    for grp in groups:
        d=sub[sub.group==grp]
        if d.empty: continue
        x=d[b_col].to_numpy(); y=d[t_col].to_numpy()
        ins.scatter(x,y,s=10,c=GROUP_COLORS[grp],marker=GROUP_MARKERS[grp],alpha=.7,zorder=2)
        if len(d)>1:
            ins.errorbar(x.mean(),y.mean(),xerr=x.std(ddof=1)/np.sqrt(len(d)),
                yerr=y.std(ddof=1)/np.sqrt(len(d)),fmt=GROUP_MARKERS[grp],
                color=GROUP_COLORS[grp],markersize=3.5,elinewidth=.8,
                markeredgecolor='black',markeredgewidth=.5,zorder=6)
    ins.set(xlim=focus,ylim=focus)
    ins.set_aspect('equal')
    ins.xaxis.set_major_locator(matplotlib.ticker.MaxNLocator(3))
    ins.yaxis.set_major_locator(matplotlib.ticker.MaxNLocator(3))
    ins.tick_params(labelsize=5.5,pad=1,length=2)
    ins.set_title('Central detail',fontsize=6,pad=2)
    from matplotlib.patches import Rectangle
    ax.add_patch(Rectangle((focus[0],focus[0]),focus[1]-focus[0],focus[1]-focus[0],
                          fill=False,edgecolor='#777777',linestyle=':',linewidth=.6,zorder=1))


# ==============================================================================
# Figure Builders
# ==============================================================================

def plot_overview_figure(
    wide_df: pd.DataFrame,
    measures: List[Tuple],
    fig_title: str,
    out_prefix: Path,
    show_subject_ids: bool = False,
) -> List[Path]:
    """
    Create a multi-panel overview figure where:
      - Rows = Measures (e.g. 4 primary measures, or 2 supplementary measures, or all 6)
      - Columns = Relevant Task Conditions:
          Col 1: Both Task (`01_baseline_both` vs `05_test_both`)
          Col 2: Single-Modality Task (`02_baseline_strength` vs `06_test_strength` for Strength metrics;
                 `03_baseline_angle` vs `07_test_angle` for Angle metrics)
    Each panel overlays all 3 Training Groups (Both, Strength, Angle) with distinct colors/markers,
    group mean +/- SEM crosshairs, and the red y = x line.
    """
    n_rows = len(measures)
    n_cols = 2  # Col 0: Both Task; Col 1: Single-Modality Task (Strength-only or Angle-only)

    fig, axes = plt.subplots(
        n_rows, n_cols,
        figsize=(180 / 25.4, 170 / 25.4),
        squeeze=False,
    )

    for r_idx, (m_key, m_title, m_short, m_unit, m_dim, zero_origin, _) in enumerate(measures):
        single_task = "strength" if m_dim == "strength" else "angle"
        single_task_label = "Strength-Only Task" if m_dim == "strength" else "Angle-Only Task"

        tasks_for_row = [
            ("both", "Both Task"),
            (single_task, single_task_label),
        ]

        # Compute shared axis limits across both task columns for the same measure so panels are directly comparable
        b_col, t_col = f"baseline_{m_key}", f"transfer_{m_key}"
        row_sub = wide_df[wide_df["task"].isin(["both", single_task])][[b_col, t_col]].dropna()
        if not row_sub.empty:
            shared_lims = compute_shared_limits(
                row_sub[b_col].to_numpy(dtype=float),
                row_sub[t_col].to_numpy(dtype=float),
                zero_origin=zero_origin,
            )
        else:
            shared_lims = None

        for c_idx, (t_name, t_label) in enumerate(tasks_for_row):
            ax = axes[r_idx, c_idx]
            df_task = wide_df[wide_df["task"] == t_name]
            panel_letter = chr(ord("A") + r_idx * n_cols + c_idx)
            p_title = f"({panel_letter}) {m_title}\n[{t_label}]"

            draw_paired_scatter_panel(
                ax=ax,
                df_task=df_task,
                m_key=m_key,
                m_short=m_short,
                m_unit=m_unit,
                zero_origin=zero_origin,
                groups_to_show=GROUP_ORDER,
                panel_title=p_title,
                show_subject_ids=show_subject_ids,
                shared_lims=shared_lims,
            )

    # Shared Legend at top
    legend_handles = [
        Line2D([0], [0], color="#E61919", lw=1.8, linestyle="-", label="y = x Reference (Transfer = Baseline)"),
    ]
    for grp in GROUP_ORDER:
        legend_handles.append(
            Line2D(
                [0], [0],
                marker=GROUP_MARKERS[grp],
                color="w",
                markerfacecolor=GROUP_COLORS[grp],
                markeredgecolor="black",
                markersize=8,
                label=f"{GROUP_LABELS[grp]} (subjects; group mean ± SEM)",
            )
        )

    fig.suptitle(fig_title, y=.985, fontsize=9, fontweight="bold")
    fig.legend(
        handles=legend_handles,
        loc="upper center",
        bbox_to_anchor=(0.5, 0.958),
        ncol=2,
        fontsize=6.5,
        frameon=False,
        facecolor="white",
        edgecolor="#CCCCCC",
    )
    fig.subplots_adjust(left=.105, right=.975, bottom=.085, top=.83, wspace=.34, hspace=.48)

    saved_files = []
    for ext in ["png", "pdf"]:
        out_path = out_prefix.with_suffix(f".{ext}")
        fig.savefig(out_path, dpi=300, bbox_inches=None)
        saved_files.append(out_path)
    plt.close(fig)
    return saved_files


def plot_by_group_grid_for_measure(
    wide_df: pd.DataFrame,
    m_tuple: Tuple,
    out_prefix: Path,
    show_subject_ids: bool = True,
) -> List[Path]:
    """
    Create a detailed 2 x 3 multi-panel figure for a single measure:
      - Rows (2): Task Condition (Row 0 = Both Task, Row 1 = Single-Modality Task: Strength-Only or Angle-Only)
      - Columns (3): Training Group (Col 0 = Both Group, Col 1 = Strength Group, Col 2 = Angle Group)
    This gives each (Group x Task) cell its own dedicated scatter plot with y=x line, subject points,
    and group mean +/- SEM crosshair, exactly matching the supervisor's sketch.
    """
    m_key, m_title, m_short, m_unit, m_dim, zero_origin, _ = m_tuple
    single_task = "strength" if m_dim == "strength" else "angle"
    single_task_label = "Strength-Only Task" if m_dim == "strength" else "Angle-Only Task"

    tasks_for_grid = [
        ("both", "Both Task"),
        (single_task, single_task_label),
    ]

    b_col, t_col = f"baseline_{m_key}", f"transfer_{m_key}"
    sub_all = wide_df[wide_df["task"].isin(["both", single_task])][[b_col, t_col]].dropna()
    shared_lims = (
        compute_shared_limits(sub_all[b_col].to_numpy(dtype=float), sub_all[t_col].to_numpy(dtype=float), zero_origin=zero_origin)
        if not sub_all.empty else None
    )

    fig, axes = plt.subplots(2, 3, figsize=(14.5, 9.2), squeeze=False)

    for r_idx, (t_name, t_label) in enumerate(tasks_for_grid):
        df_task = wide_df[wide_df["task"] == t_name]
        for c_idx, grp in enumerate(GROUP_ORDER):
            ax = axes[r_idx, c_idx]
            panel_letter = chr(ord("A") + r_idx * 3 + c_idx)
            p_title = f"({panel_letter}) {GROUP_LABELS[grp]}\n[{t_label}]"
            draw_paired_scatter_panel(
                ax=ax,
                df_task=df_task,
                m_key=m_key,
                m_short=m_short,
                m_unit=m_unit,
                zero_origin=zero_origin,
                groups_to_show=[grp],
                panel_title=p_title,
                show_subject_ids=show_subject_ids,
                shared_lims=shared_lims,
            )

    fig.suptitle(f"Baseline vs. Transfer by Training Group & Task — {m_title}", y=1.01, fontsize=14, fontweight="bold")
    fig.tight_layout()

    saved_files = []
    for ext in ["png", "pdf"]:
        out_path = out_prefix.with_suffix(f".{ext}")
        fig.savefig(out_path, dpi=300, bbox_inches=None)
        saved_files.append(out_path)
    plt.close(fig)
    return saved_files


def plot_by_task_3x4_grid(
    wide_df: pd.DataFrame,
    out_prefix: Path,
    show_subject_ids: bool = False,
) -> List[Path]:
    """
    Create a comprehensive 3 (Training Groups) x 4 (Task-Measure Combinations) master grid
    for the Primary Measures or Separate Task Panels so every group can be inspected side by side.
    Specifically:
      - Fig A: Primary Signed Means (Strength Mean & Angle Mean across Both & Single-Modality Tasks)
      - Fig B: Primary Variances (Strength Variance & Angle Variance across Both & Single-Modality Tasks)
    """
    saved_files = []
    subsets = [
        ("means_by_group_grid", [PRIMARY_MEASURES[0], PRIMARY_MEASURES[2]], "Signed Means (Constant Error): Baseline vs. Transfer Across Groups & Tasks"),
        ("variances_by_group_grid", [PRIMARY_MEASURES[1], PRIMARY_MEASURES[3]], "Variances (Variable Error): Baseline vs. Transfer Across Groups & Tasks"),
        ("abs_errors_by_group_grid", SUPPLEMENTARY_MEASURES, "Mean Absolute Errors: Baseline vs. Transfer Across Groups & Tasks"),
    ]

    for slug, m_list, title_str in subsets:
        # 4 rows (Measure x Task: Both & Single) x 3 cols (Groups: Both, Strength, Angle)
        fig, axes = plt.subplots(4, 3, figsize=(14.2, 17.5), squeeze=False)
        row_counter = 0
        for m_key, m_title, m_short, m_unit, m_dim, zero_origin, _ in m_list:
            single_task = "strength" if m_dim == "strength" else "angle"
            single_task_label = "Strength-Only Task" if m_dim == "strength" else "Angle-Only Task"
            b_col, t_col = f"baseline_{m_key}", f"transfer_{m_key}"
            sub_all = wide_df[wide_df["task"].isin(["both", single_task])][[b_col, t_col]].dropna()
            shared_lims = (
                compute_shared_limits(sub_all[b_col].to_numpy(dtype=float), sub_all[t_col].to_numpy(dtype=float), zero_origin=zero_origin)
                if not sub_all.empty else None
            )

            for t_name, t_label in [("both", "Both Task"), (single_task, single_task_label)]:
                df_task = wide_df[wide_df["task"] == t_name]
                for c_idx, grp in enumerate(GROUP_ORDER):
                    ax = axes[row_counter, c_idx]
                    p_title = f"{GROUP_SHORT_LABELS[grp]} — {m_short}\n[{t_label}]"
                    draw_paired_scatter_panel(
                        ax=ax,
                        df_task=df_task,
                        m_key=m_key,
                        m_short=m_short,
                        m_unit=m_unit,
                        zero_origin=zero_origin,
                        groups_to_show=[grp],
                        panel_title=p_title,
                        show_subject_ids=show_subject_ids,
                        shared_lims=shared_lims,
                    )
                row_counter += 1

        fig.suptitle(title_str, y=1.005, fontsize=14, fontweight="bold")
        fig.tight_layout()
        for ext in ["png", "pdf"]:
            out_path = out_prefix.parent / f"{slug}.{ext}"
            fig.savefig(out_path, dpi=300, bbox_inches=None)
            saved_files.append(out_path)
        plt.close(fig)

    return saved_files


# ==============================================================================
# Main Entrypoint
# ==============================================================================

def write_publication_tables(summary, out_dir):
    """Companion statistics in three-rule tables, without overlaying figures."""
    from matplotlib.backends.backend_pdf import PdfPages
    columns = ['Task', 'Group', 'n', 'Baseline ± SEM', 'Post-test ± SEM',
               'Change ± SEM', 'Paired t p', 'Wilcoxon p']
    rows=[]
    def number(v):
        return 'NA' if not np.isfinite(v) else f'{v:.3g}'
    def pair(mean, sem):
        return f'{number(mean)} ± {number(sem)}'
    for _, r in summary.iterrows():
        rows.append({'Measure': r.measure_label, 'Unit': r.unit,
            'Task': r.task, 'Group': r.group, 'n': int(r.n_subjects),
            'Baseline ± SEM': pair(r.baseline_mean, r.baseline_sem),
            'Post-test ± SEM': pair(r.transfer_mean, r.transfer_sem),
            'Change ± SEM': pair(r.delta_mean, r.delta_sem),
            'Paired t p': number(r.paired_t_p), 'Wilcoxon p': number(r.wilcoxon_p)})
    display=pd.DataFrame(rows)
    display.to_csv(out_dir/'publication_statistics.csv',index=False,encoding='utf-8-sig')
    note=('SEM describes between-participant variation. Paired tests are exploratory and unadjusted;\n'
          'they do not propagate stage-fit uncertainty. ALL pools training groups descriptively.')
    md=['# Baseline versus post-test statistics', '', note.replace('\n',' '), '']
    with PdfPages(out_dir/'publication_statistics.pdf') as pdf:
        for measure, data in display.groupby('Measure',sort=False):
            md += ['## '+measure+' ('+str(data.Unit.iloc[0])+')', '', '| '+' | '.join(columns)+' |',
                   '| '+' | '.join(['---']*len(columns))+' |']
            md += ['| '+' | '.join(str(r[c]) for c in columns)+' |' for _,r in data.iterrows()]
            md += ['']
            fig=plt.figure(figsize=(180/25.4, 115/25.4))
            ax=fig.add_axes([.03,.23,.94,.63]); ax.axis('off')
            table=ax.table(cellText=data[columns].astype(str).values, colLabels=columns,
                           colWidths=[.08,.09,.045,.19,.19,.19,.11,.105],
                           loc='upper center',cellLoc='center',bbox=[0,0,1,1])
            table.auto_set_font_size(False); table.set_fontsize(6.7)
            for (r,c),cell in table.get_celld().items():
                cell.visible_edges=''
                if r==0:
                    cell.visible_edges='TB'; cell.set_linewidth(.8)
                    cell.set_text_props(weight='bold')
                elif r==len(data):
                    cell.visible_edges='B'; cell.set_linewidth(.8)
            fig.text(.03,.95,measure+' ('+str(data.Unit.iloc[0])+') — baseline versus post-test',fontsize=9,weight='bold')
            fig.text(.03,.10,note,fontsize=6.5,va='bottom')
            pdf.savefig(fig,bbox_inches=None); plt.close(fig)
    (out_dir/'publication_statistics.md').write_text('\n'.join(md),encoding='utf-8')


def main():
    parser = argparse.ArgumentParser(
        description="Plot Baseline vs. Transfer (Test) for all groups and all measures (Step 4)."
    )
    parser.add_argument(
        "--root",
        type=str,
        default=r"D:\experiment",
        help="Root experiment directory containing subject folders 01 to 30 (default: D:\\experiment)",
    )
    parser.add_argument(
        "--out",
        type=str,
        default=None,
        help="Output directory for figures and summary CSVs (default: <root>\\baseline_vs_transfer_robust)",
    )
    parser.add_argument(
        "--show-ids",
        action="store_true",
        help="Annotate each scatter point with the subject ID (01..30) on overview plots.",
    )
    args = parser.parse_args()

    root_dir = Path(args.root)
    out_dir = Path(args.out) if args.out else (root_dir / "baseline_vs_transfer_robust")
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / 'METHODS.txt').write_text(
        'Primary mean and variance are constant-location/scale Student-t maximum likelihood estimates, fixed df=5.\n'
        'Variance = scale^2 * 5/3. Raw sample moments are retained in raw_* columns.\n'
        'Baseline/post-test: scored valid finite components. Training: finite labeled values excluding outlier=1; no status/review exclusion.\n'
        'Variance axes use symlog (linear below 0.01 strength squared / 0.1 deg squared); no points trimmed.\n'
        'Group crosshairs describe between-participant mean +/- SEM, not within-stage fit uncertainty.\n'
        'Primary overview split into separate 180 x 170 mm mean/variance figures; companion three-rule PDF/CSV/Markdown statistics tables.\n'
        'Paired tests in CSV are exploratory, unadjusted and do not propagate stage-estimation uncertainty.\n'
        'Post-test combines trained-task retention and untrained-task transfer depending on group.\n'
        'Censoring requires value at recorded cap plus uncapped estimate beyond cap; likelihood uses tail probability.\n', encoding='utf-8')

    print(f"[INFO] Scanning experiment data in: {root_dir}")
    wide_df, train_df = load_all_subjects(root_dir)

    if wide_df.empty:
        print(f"[ERROR] No valid subject data found under {root_dir}. Please check the path.")
        return

    # Save subject-level and training-level data tables
    subj_csv_path = out_dir / "subject_baseline_vs_transfer_metrics.csv"
    wide_df.to_csv(subj_csv_path, index=False, float_format="%.6f")
    print(f"[INFO] Saved subject-level metrics table: {subj_csv_path} ({len(wide_df)} rows)")

    if not train_df.empty:
        train_csv_path = out_dir / "subject_training_outlier_summary.csv"
        train_df.to_csv(train_csv_path, index=False, float_format="%.6f")
        print(f"[INFO] Saved training outlier summary: {train_csv_path} ({len(train_df)} subjects)")
        print("\n=== Training Group Counts ===")
        print(train_df.groupby("group")["subject"].count().to_string())

    # Compute and save group summary statistics table
    summary_df = compute_group_summary_table(wide_df)
    summary_csv_path = out_dir / "group_summary_statistics.csv"
    summary_df.to_csv(summary_csv_path, index=False, float_format="%.6f")
    print(f"\n[INFO] Saved group-level statistical summary: {summary_csv_path}")

    # Print key summary table to console
    if not summary_df.empty:
        disp_cols = [
            "task", "measure", "group", "n_subjects",
            "baseline_mean", "baseline_sd", "transfer_mean", "transfer_sd",
            "delta_mean", "pct_transfer_lt_baseline", "paired_t_p", "wilcoxon_p"
        ]
        print("\n=== Baseline vs. Transfer Summary (All Groups & Measures) ===")
        print(summary_df[disp_cols].to_string(index=False))

    for slug, measures, title in [
        ('fig1a_signed_means', [PRIMARY_MEASURES[0], PRIMARY_MEASURES[2]],
         'Baseline vs. Post-test: Signed Means (Student-t, df = 5)'),
        ('fig1b_variances', [PRIMARY_MEASURES[1], PRIMARY_MEASURES[3]],
         'Baseline vs. Post-test: Variances (Student-t, df = 5)')]:
        plot_overview_figure(wide_df, measures, title, out_dir / slug, args.show_ids)
    write_publication_tables(summary_df, out_dir)

    # 2. Plot Supplementary Absolute Error Measures Overview (2 rows x 2 cols)
    print("[INFO] Generating Supplementary Absolute Error Overview...")
    plot_overview_figure(
        wide_df=wide_df,
        measures=SUPPLEMENTARY_MEASURES,
        fig_title="Baseline vs. Post-test: Observed Mean Absolute Error",
        out_prefix=out_dir / "fig2_supplementary_abs_errors_baseline_vs_transfer",
        show_subject_ids=args.show_ids,
    )

    # Tall legacy master/grids are no longer the main publication outputs.
    print(f"\n[SUCCESS] All figures (PNG + PDF) and CSV summary tables have been saved to:\n  {out_dir}")


if __name__ == "__main__":
    main()
