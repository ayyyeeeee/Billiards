#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Billiard Motor-Learning Experiment — Outlier Detection Batch Tool
=================================================================

Detects statistical outliers in 140-shot training CSVs using externally
studentized residuals from a cubic-spline regression that captures the
learning trend, with Bonferroni-corrected t-distribution p-values.

Angle and strength channels are fitted and tested independently.

Usage:
    python outlier_batch.py          # interactive prompt
    python outlier_batch.py 01       # single participant
    python outlier_batch.py 01,02    # multiple participants
    python outlier_batch.py 01-30    # range
    python outlier_batch.py all      # all participants
"""

from __future__ import annotations

import hashlib
import io
import logging
import os
import re
import sys
import textwrap
import traceback
from datetime import datetime
from pathlib import Path
from typing import Optional

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats as sp_stats

# statsmodels imports
import statsmodels.api as sm
from patsy import dmatrix

# ──────────────────────────────────────────────────────────────
# Constants
# ──────────────────────────────────────────────────────────────
EXPERIMENT_ROOT = Path(r"D:\experiment")
TRAINING_PATTERN = re.compile(r"training_(both|angle|strength)_140shots", re.IGNORECASE)
SPLINE_DF = 6          # initial cubic-spline degrees of freedom
ALPHA = 0.05           # family-wise significance level (before Bonferroni)
MIN_OBS_FOR_FIT = 15   # minimum valid observations to attempt spline fit

# ──────────────────────────────────────────────────────────────
# Logging setup
# ──────────────────────────────────────────────────────────────
LOG_FORMAT = "%(asctime)s  %(levelname)-8s  %(message)s"
_root_logger = logging.getLogger("outlier_batch")
_root_logger.setLevel(logging.DEBUG)

_console_handler = logging.StreamHandler(sys.stdout)
_console_handler.setLevel(logging.INFO)
_console_handler.setFormatter(logging.Formatter(LOG_FORMAT))
_root_logger.addHandler(_console_handler)

log = _root_logger


def _add_file_handler(log_path: Path):
    """Add a rotating file handler to *log_path*."""
    log_path.parent.mkdir(parents=True, exist_ok=True)
    fh = logging.FileHandler(str(log_path), encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(logging.Formatter(LOG_FORMAT))
    _root_logger.addHandler(fh)
    return fh


# ──────────────────────────────────────────────────────────────
# SHA-256 integrity helpers
# ──────────────────────────────────────────────────────────────
def sha256_of_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


# ──────────────────────────────────────────────────────────────
# Participant / file discovery
# ──────────────────────────────────────────────────────────────
def parse_participant_ids(raw: str) -> list[str]:
    """
    Parse user input into zero-padded participant IDs.
    Accepts: '01', '1', '01,02,05', '01-30', 'all'.
    """
    raw = raw.strip().lower()
    if raw == "all":
        return [f"{i:02d}" for i in range(1, 31)]

    ids: list[str] = []
    for part in raw.split(","):
        part = part.strip()
        m = re.match(r"^(\d+)\s*-\s*(\d+)$", part)
        if m:
            lo, hi = int(m.group(1)), int(m.group(2))
            ids.extend(f"{i:02d}" for i in range(lo, hi + 1))
        else:
            ids.append(f"{int(part):02d}")
    # deduplicate, keep order
    seen = set()
    unique = []
    for pid in ids:
        if pid not in seen:
            seen.add(pid)
            unique.append(pid)
    return unique


def find_training_csvs(pid: str) -> list[Path]:
    """Find training CSVs in processed_csv, including nested csv directories."""
    csv_dir = EXPERIMENT_ROOT / pid / "processed_csv"
    if not csv_dir.is_dir():
        return []
    return sorted(
        p for p in csv_dir.rglob("*")
        if p.is_file() and p.suffix.lower() == ".csv" and TRAINING_PATTERN.search(p.stem)
    )


def detect_training_mode(filename: str) -> str:
    m = TRAINING_PATTERN.search(filename)
    return m.group(1) if m else "unknown"


# ──────────────────────────────────────────────────────────────
# Data quality helpers
# ──────────────────────────────────────────────────────────────
def _channel_eligible(row: pd.Series, channel: str, df_columns: list[str]) -> bool:
    """
    Determine whether a row is eligible for statistical fitting on *channel*
    ('angle' or 'strength').

    Rules
    -----
    1. The channel's status must be 'scored' (not 'not_requested' / 'unresolved').
    2. The value must be a finite number.
    3. score_complete must be 1 (scoring finished).
    4. Channel-specific valid flag must be 1 (if the column exists).
    5. Retained data have been manually reviewed. Historical needs_review
       flags do not exclude observations from fitting.
    6. Zero with score_complete == 0 remains an excluded placeholder.
    """
    val_col = f"{channel}_value"
    status_col = f"{channel}_status"
    valid_col = f"{channel}_valid"

    # status must be 'scored'
    if status_col in df_columns:
        st = row.get(status_col, "")
        if not isinstance(st, str) or st.lower() != "scored":
            return False

    # value must be finite
    v = row.get(val_col)
    if v is None or (isinstance(v, float) and (np.isnan(v) or np.isinf(v))):
        return False

    # score_complete
    sc = row.get("score_complete", 1)
    try:
        if int(sc) != 1:
            return False
    except (ValueError, TypeError):
        return False

    # channel-specific valid
    if valid_col in df_columns:
        try:
            if int(row.get(valid_col, 1)) != 1:
                return False
        except (ValueError, TypeError):
            return False

    return True


def build_eligibility_mask(df: pd.DataFrame, channel: str) -> pd.Series:
    """Return a boolean Series: True for rows eligible for spline fitting."""
    cols = list(df.columns)
    return df.apply(lambda r: _channel_eligible(r, channel, cols), axis=1)


# ──────────────────────────────────────────────────────────────
# Spline regression + externally studentized residuals
# ──────────────────────────────────────────────────────────────

class OutlierResult:
    """Container for the detection output of one channel."""
    __slots__ = (
        "channel", "eligible_mask", "n_eligible", "n_outliers",
        "outlier_mask", "fit_performed", "skip_reason",
        "shot_numbers", "values", "predicted", "residuals",
        "ext_stud_resid", "p_raw", "p_corrected",
        "spline_df_used", "diagnostics",
    )

    def __init__(self, channel: str):
        self.channel = channel
        self.eligible_mask: pd.Series | None = None
        self.n_eligible = 0
        self.n_outliers = 0
        self.outlier_mask: pd.Series | None = None
        self.fit_performed = False
        self.skip_reason: str | None = None
        # arrays aligned to eligible indices
        self.shot_numbers: np.ndarray | None = None
        self.values: np.ndarray | None = None
        self.predicted: np.ndarray | None = None
        self.residuals: np.ndarray | None = None
        self.ext_stud_resid: np.ndarray | None = None
        self.p_raw: np.ndarray | None = None
        self.p_corrected: np.ndarray | None = None
        self.spline_df_used: int = 0
        self.diagnostics: dict = {}


def _fit_channel(df: pd.DataFrame, channel: str) -> OutlierResult:
    """
    Fit a cubic B-spline to the learning curve for *channel* and return
    externally studentized residual outlier flags.
    """
    res = OutlierResult(channel)
    val_col = f"{channel}_value"

    if val_col not in df.columns:
        res.skip_reason = f"Column '{val_col}' not present in CSV."
        return res

    # Build eligibility mask
    elig = build_eligibility_mask(df, channel)
    res.eligible_mask = elig
    res.n_eligible = int(elig.sum())

    if res.n_eligible < MIN_OBS_FOR_FIT:
        res.skip_reason = (
            f"Only {res.n_eligible} eligible observations "
            f"(need ≥ {MIN_OBS_FOR_FIT})."
        )
        return res

    # Extract eligible data
    df_elig = df.loc[elig].copy()
    shots = df_elig["shot"].values.astype(float)
    y = df_elig[val_col].values.astype(float)

    # Determine usable spline df (must be < n_eligible)
    df_spline = min(SPLINE_DF, res.n_eligible - 2)
    if df_spline < 3:
        df_spline = 3
    if df_spline >= res.n_eligible:
        res.skip_reason = (
            f"Too few observations ({res.n_eligible}) for "
            f"spline with df={df_spline}."
        )
        return res

    res.spline_df_used = df_spline

    # Build design matrix with cubic B-spline basis
    try:
        X = dmatrix(
            f"bs(x, df={df_spline}, degree=3, include_intercept=True) - 1",
            {"x": shots},
            return_type="dataframe",
        )
    except Exception as exc:
        res.skip_reason = f"Spline basis construction failed: {exc}"
        return res

    # Fit OLS
    try:
        model = sm.OLS(y, X).fit()
    except Exception as exc:
        res.skip_reason = f"OLS fitting failed: {exc}"
        return res

    res.fit_performed = True
    yhat = model.fittedvalues
    resids = model.resid

    # Hat matrix diagonal
    try:
        hat = model.get_influence().hat_matrix_diag
    except Exception:
        # fallback manual computation
        Xm = np.asarray(X, dtype=float)
        try:
            hat = np.diag(Xm @ np.linalg.pinv(Xm.T @ Xm) @ Xm.T)
        except Exception as exc:
            res.skip_reason = f"Hat matrix computation failed: {exc}"
            return res

    n = len(y)
    p = X.shape[1]  # number of parameters

    # Externally studentized residuals (leave-one-out)
    ext_stud = np.full(n, np.nan)
    for i in range(n):
        ei = resids[i]
        hii = hat[i]
        # s_{(i)}^2 — residual variance deleting observation i
        sse = np.sum(resids**2)
        denom_var = (sse - ei**2 / (1 - hii)) / (n - p - 1)
        if denom_var <= 0 or (1 - hii) <= 0:
            continue
        s_deleted = np.sqrt(denom_var)
        ext_stud[i] = ei / (s_deleted * np.sqrt(1 - hii))

    # p-values from t-distribution with (n - p - 1) df
    dof = n - p - 1
    if dof < 1:
        res.skip_reason = f"Degrees of freedom too low ({dof})."
        return res

    p_raw = np.full(n, np.nan)
    valid_t = np.isfinite(ext_stud)
    p_raw[valid_t] = 2 * sp_stats.t.sf(np.abs(ext_stud[valid_t]), dof)

    # Bonferroni correction
    n_tests = int(valid_t.sum())
    p_corr = np.minimum(p_raw * n_tests, 1.0)

    outlier_flags = p_corr < ALPHA

    res.shot_numbers = shots
    res.values = y
    res.predicted = yhat
    res.residuals = resids
    res.ext_stud_resid = ext_stud
    res.p_raw = p_raw
    res.p_corrected = p_corr
    res.n_outliers = int(np.sum(outlier_flags))

    # Map back to full dataframe index
    outlier_full = pd.Series(0, index=df.index, dtype="int64")
    eligible_idx = df_elig.index
    for j, idx in enumerate(eligible_idx):
        if valid_t[j]:
            outlier_full.loc[idx] = int(outlier_flags[j])
        # Undefined tests remain 0: no statistical outlier flagged.
    res.outlier_mask = outlier_full

    # ── Assumption diagnostics ──
    diag = {}

    # 1. Normality of residuals (Shapiro-Wilk)
    if n >= 3:
        try:
            sw_stat, sw_p = sp_stats.shapiro(resids)
            diag["shapiro_wilk"] = {"statistic": sw_stat, "p_value": sw_p}
            if sw_p < 0.05:
                diag["normality_warning"] = (
                    f"Shapiro-Wilk p = {sw_p:.4f} < 0.05 — residuals may "
                    f"not be normally distributed; t-test p-values may be "
                    f"unreliable."
                )
        except Exception:
            pass

    # 2. Heteroscedasticity (Breusch-Pagan)
    try:
        bp_stat, bp_p, _, _ = sm.stats.diagnostic.het_breuschpagan(resids, X)
        diag["breusch_pagan"] = {"statistic": bp_stat, "p_value": bp_p}
        if bp_p < 0.05:
            diag["heteroscedasticity_warning"] = (
                f"Breusch-Pagan p = {bp_p:.4f} < 0.05 — residual variance "
                f"may change over shots; t-test p-values may be unreliable."
            )
    except Exception:
        pass

    # 3. Autocorrelation (Durbin-Watson)
    try:
        dw = sm.stats.stattools.durbin_watson(resids)
        diag["durbin_watson"] = dw
        if dw < 1.5 or dw > 2.5:
            diag["autocorrelation_warning"] = (
                f"Durbin-Watson = {dw:.4f} — suggests serial correlation "
                f"in residuals; t-test p-values may be unreliable."
            )
    except Exception:
        pass

    res.diagnostics = diag
    return res


# ──────────────────────────────────────────────────────────────
# CSV labelling
# ──────────────────────────────────────────────────────────────
def insert_outlier_columns(df: pd.DataFrame,
                           angle_result: OutlierResult,
                           strength_result: OutlierResult) -> pd.DataFrame:
    """
    Return a *new* DataFrame with outlier columns inserted right after
    the corresponding value columns.  Original columns are untouched.
    """
    out = df.copy()
    cols = list(out.columns)

    # Insert strength_outlier right after strength_value
    if "strength_value" in cols:
        idx_s = cols.index("strength_value") + 1
        if strength_result.outlier_mask is not None:
            val = strength_result.outlier_mask
        else:
            val = pd.Series(0, index=out.index, dtype="int64")
        out.insert(idx_s, "strength_outlier", val)

    # Insert angle_outlier right after angle_value
    # (account for possible shift from strength_outlier insertion)
    cols_now = list(out.columns)
    if "angle_value" in cols_now:
        idx_a = cols_now.index("angle_value") + 1
        if angle_result.outlier_mask is not None:
            val = angle_result.outlier_mask
        else:
            val = pd.Series(0, index=out.index, dtype="int64")
        out.insert(idx_a, "angle_outlier", val)

    return out


# ──────────────────────────────────────────────────────────────
# Reporting
# ──────────────────────────────────────────────────────────────
def _fmt_diagnostics(diag: dict) -> str:
    lines = []
    for key in ("shapiro_wilk", "breusch_pagan", "durbin_watson"):
        if key in diag:
            v = diag[key]
            if isinstance(v, dict):
                lines.append(f"  {key}: statistic={v['statistic']:.6f}, p={v['p_value']:.6f}")
            else:
                lines.append(f"  {key}: {v:.4f}")
    for key in ("normality_warning", "heteroscedasticity_warning",
                "autocorrelation_warning"):
        if key in diag:
            lines.append(f"  ⚠ {diag[key]}")
    return "\n".join(lines) if lines else "  No warnings."


def write_report(report_dir: Path, csv_name: str, pid: str,
                 mode: str, n_total: int,
                 angle_res: OutlierResult,
                 strength_res: OutlierResult):
    """Write a plain-text statistical report for one CSV."""
    report_dir.mkdir(parents=True, exist_ok=True)
    stem = Path(csv_name).stem
    report_path = report_dir / f"{stem}_report.txt"

    buf = io.StringIO()
    w = buf.write

    w(f"{'='*72}\n")
    w(f"  Outlier Detection Report\n")
    w(f"{'='*72}\n\n")
    w(f"Participant : {pid}\n")
    w(f"CSV File    : {csv_name}\n")
    w(f"Mode        : {mode}\n")
    w(f"Total shots : {n_total}\n")
    w("Review policy: retained data are manually reviewed; historical review flags are ignored.\n")
    w("Flags: 1 = statistical outlier; 0 = not flagged (including untested rows).\n")
    w(f"Generated   : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    w(f"\n{'─'*72}\n")

    for res in (angle_res, strength_res):
        ch = res.channel.upper()
        w(f"\n  Channel: {ch}\n")
        w(f"  {'─'*40}\n")
        if not res.fit_performed:
            w(f"  Fit skipped : {res.skip_reason}\n")
            w(f"  Eligible obs: {res.n_eligible}\n")
            w(f"  Outliers    : N/A\n\n")
            continue
        w(f"  Eligible obs     : {res.n_eligible}\n")
        w(f"  Spline df        : {res.spline_df_used}\n")
        w(f"  Outliers detected: {res.n_outliers}\n")
        n_no_test = int(n_total - res.n_eligible)
        w(f"  Not tested (ineligible): {n_no_test}\n")
        w(f"  Undefined tests (flag 0): {int((~np.isfinite(res.p_raw)).sum())}\n")

        if res.n_outliers > 0:
            w(f"\n  Outlier details:\n")
            w(f"  {'Shot':>5}  {'Value':>12}  {'Predicted':>12}  {'Residual':>12}  "
              f"{'t_ext':>10}  {'p_raw':>12}  {'p_Bonf':>12}\n")
            w(f"  {'─'*85}\n")
            for j in range(len(res.shot_numbers)):
                if res.p_corrected[j] < ALPHA:
                    w(f"  {int(res.shot_numbers[j]):5d}  "
                      f"{res.values[j]:12.6f}  "
                      f"{res.predicted[j]:12.6f}  "
                      f"{res.residuals[j]:12.6f}  "
                      f"{res.ext_stud_resid[j]:10.4f}  "
                      f"{res.p_raw[j]:12.8f}  "
                      f"{res.p_corrected[j]:12.8f}\n")

        w(f"\n  Assumption diagnostics:\n")
        w(_fmt_diagnostics(res.diagnostics))
        w("\n")

    w(f"\n{'='*72}\n")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(buf.getvalue())
    return report_path


def write_summary(report_dir: Path, pid: str,
                  file_results: list[dict]):
    """Write a participant-level summary TSV."""
    report_dir.mkdir(parents=True, exist_ok=True)
    summary_path = report_dir / f"participant_{pid}_summary.txt"

    buf = io.StringIO()
    w = buf.write
    w(f"{'='*72}\n")
    w(f"  Participant {pid} — Outlier Summary\n")
    w(f"{'='*72}\n\n")
    w(f"{'CSV File':<50}  {'Mode':<12}  {'Ch':<10}  {'Eligible':>8}  "
      f"{'Outliers':>8}  {'Outlier shots'}\n")
    w(f"{'─'*120}\n")

    for fr in file_results:
        for res in (fr["angle"], fr["strength"]):
            if not res.fit_performed:
                outlier_shots = "N/A"
                n_out = "-"
            elif res.n_outliers == 0:
                outlier_shots = "(none)"
                n_out = "0"
            else:
                shots_list = []
                for j in range(len(res.shot_numbers)):
                    if res.p_corrected[j] < ALPHA:
                        shots_list.append(str(int(res.shot_numbers[j])))
                outlier_shots = ", ".join(shots_list)
                n_out = str(res.n_outliers)
            w(f"{fr['csv_name']:<50}  {fr['mode']:<12}  "
              f"{res.channel:<10}  {res.n_eligible:>8}  "
              f"{n_out:>8}  {outlier_shots}\n")

    w(f"\n{'='*72}\n")
    with open(summary_path, "w", encoding="utf-8") as f:
        f.write(buf.getvalue())
    return summary_path


# ──────────────────────────────────────────────────────────────
# Visualisation
# ──────────────────────────────────────────────────────────────
def plot_channel(df: pd.DataFrame, res: OutlierResult,
                 plot_dir: Path, csv_stem: str, pid: str, mode: str):
    """Save one outlier-detection scatter plot for a channel."""
    if res.channel == "angle":
        val_col = "angle_value"
        ylabel = "Angle (degrees)"
    else:
        val_col = "strength_value"
        ylabel = "Strength value"

    if val_col not in df.columns:
        return

    plot_dir.mkdir(parents=True, exist_ok=True)

    fig, ax = plt.subplots(figsize=(14, 5))

    # All data points (grey, small)
    all_shots = df["shot"].values
    all_vals = pd.to_numeric(df[val_col], errors="coerce").values

    # Separate eligible and non-eligible for plotting
    elig = res.eligible_mask if res.eligible_mask is not None else pd.Series(False, index=df.index)

    # Normal eligible points (grey)
    normal_mask = elig.copy()
    if res.outlier_mask is not None:
        # remove outliers from "normal" set
        normal_mask = normal_mask & (res.outlier_mask != 1)
    norm_idx = normal_mask[normal_mask].index
    ax.scatter(df.loc[norm_idx, "shot"], pd.to_numeric(df.loc[norm_idx, val_col], errors="coerce"),
               c="grey", s=18, alpha=0.6, label="Normal", zorder=2)

    # Historical review flags are ignored; other eligibility rules still apply.
    other_inelig = ~elig

    # Other ineligible (light grey X)
    if other_inelig.any():
        oi_idx = other_inelig[other_inelig].index
        vals_oi = pd.to_numeric(df.loc[oi_idx, val_col], errors="coerce")
        finite_mask = np.isfinite(vals_oi)
        if finite_mask.any():
            ax.scatter(df.loc[oi_idx, "shot"][finite_mask], vals_oi[finite_mask],
                       marker="x", c="lightgrey", s=24, alpha=0.5,
                       label="Ineligible", zorder=1)

    # Learning trend line
    if res.fit_performed and res.shot_numbers is not None:
        order = np.argsort(res.shot_numbers)
        ax.plot(res.shot_numbers[order], res.predicted[order],
                c="blue", linewidth=1.8, label="Learning trend (spline)", zorder=4)

    # Outlier points (red)
    if res.fit_performed and res.n_outliers > 0:
        out_j = [j for j in range(len(res.shot_numbers))
                 if res.p_corrected[j] < ALPHA]
        out_shots = res.shot_numbers[out_j]
        out_vals = res.values[out_j]
        ax.scatter(out_shots, out_vals, c="red", s=50, edgecolors="darkred",
                   linewidths=0.8, label=f"Outlier (n={res.n_outliers})", zorder=5)
        for j in out_j:
            ax.annotate(f"{int(res.shot_numbers[j])}",
                        (res.shot_numbers[j], res.values[j]),
                        textcoords="offset points", xytext=(4, 6),
                        fontsize=7, color="red")

    ax.set_xlabel("Shot number")
    ax.set_ylabel(ylabel)
    ax.set_title(
        f"Participant {pid} — {mode} — {res.channel.capitalize()} "
        f"Outlier Detection",
        fontsize=11,
    )
    ax.legend(fontsize=8, loc="best")
    ax.grid(True, alpha=0.3)

    if not res.fit_performed:
        ax.text(0.5, 0.5, f"Fit skipped:\n{res.skip_reason}",
                transform=ax.transAxes, ha="center", va="center",
                fontsize=10, color="grey",
                bbox=dict(boxstyle="round", facecolor="lightyellow"))

    fig.tight_layout()
    fname = f"{csv_stem}_{res.channel}_outliers.png"
    fig.savefig(str(plot_dir / fname), dpi=200)
    plt.close(fig)


# ──────────────────────────────────────────────────────────────
# Main processing pipeline
# ──────────────────────────────────────────────────────────────
def process_csv(csv_path: Path, pid: str) -> dict:
    """Process one training CSV.  Returns a result dict for the summary."""
    csv_name = csv_path.name
    mode = detect_training_mode(csv_name)

    log.info(f"  Processing: {csv_name}  (mode={mode})")

    # Preserve original cell text (including empty cells and numeric formatting).
    source_df = pd.read_csv(str(csv_path), dtype=str, keep_default_na=False,
                            encoding="utf-8-sig")
    df = pd.read_csv(str(csv_path))
    n_total = len(df)
    log.info(f"    Rows: {n_total}")

    if n_total != 140:
        log.warning(f"    [!] Expected 140 rows but got {n_total}. Proceeding.")

    # Run detection for each channel
    angle_res = _fit_channel(df, "angle")
    strength_res = _fit_channel(df, "strength")

    for res in (angle_res, strength_res):
        ch = res.channel
        if res.fit_performed:
            log.info(f"    {ch}: eligible={res.n_eligible}, outliers={res.n_outliers}")
        else:
            log.info(f"    {ch}: SKIPPED — {res.skip_reason}")

    # Build output directories
    out_base = EXPERIMENT_ROOT / pid / "outlier_results"
    csv_out_dir = out_base / "labeled_csv"
    report_dir = out_base / "reports"
    plot_dir = out_base / "plots"

    csv_out_dir.mkdir(parents=True, exist_ok=True)

    # Build labelled CSV
    df_out = insert_outlier_columns(source_df, angle_res, strength_res)

    # Binary flags only, including channels/rows that could not be tested.
    for col in ("angle_outlier", "strength_outlier"):
        if col in df_out.columns:
            df_out[col] = df_out[col].fillna(0).astype("int64")
            assert df_out[col].isin([0, 1]).all(), "Non-binary outlier flag!"

    csv_out_path = csv_out_dir / f"{csv_path.stem}_outlier_labeled.csv"
    df_out.to_csv(str(csv_out_path), index=False, encoding="utf-8-sig")
    log.info(f"    → Labelled CSV: {csv_out_path.name}")

    # Verify row count
    assert len(df_out) == n_total, "Output row count mismatch!"

    # Report
    rpt = write_report(report_dir, csv_name, pid, mode, n_total,
                       angle_res, strength_res)
    log.info(f"    → Report: {rpt.name}")

    # Plots
    plot_channel(df, angle_res, plot_dir, csv_path.stem, pid, mode)
    plot_channel(df, strength_res, plot_dir, csv_path.stem, pid, mode)
    log.info(f"    → Plots saved.")

    return {
        "csv_name": csv_name,
        "mode": mode,
        "angle": angle_res,
        "strength": strength_res,
    }


def process_participant(pid: str) -> bool:
    """Process all training 140-shot CSVs for one participant."""
    log.info(f"\n{'━'*60}")
    log.info(f"  Participant {pid}")
    log.info(f"{'━'*60}")

    csvs = find_training_csvs(pid)
    if not csvs:
        log.warning(f"  No training_*_140shots CSV found for participant {pid}.")
        return False

    log.info(f"  Found {len(csvs)} training CSV(s).")

    # SHA-256 of originals (for post-run integrity check)
    original_hashes = {p: sha256_of_file(p) for p in csvs}

    file_results = []
    any_error = False

    for csv_path in csvs:
        try:
            result = process_csv(csv_path, pid)
            file_results.append(result)
        except Exception:
            log.error(f"  ✗ FAILED: {csv_path.name}\n{traceback.format_exc()}")
            any_error = True

    # Write participant summary
    if file_results:
        report_dir = EXPERIMENT_ROOT / pid / "outlier_results" / "reports"
        sp = write_summary(report_dir, pid, file_results)
        log.info(f"  → Summary: {sp.name}")

    # Post-run integrity verification
    for csv_path, orig_hash in original_hashes.items():
        current_hash = sha256_of_file(csv_path)
        if current_hash != orig_hash:
            log.error(f"  ✗ INTEGRITY VIOLATION: {csv_path.name} was modified!")
        else:
            log.debug(f"  ✓ Integrity OK: {csv_path.name}")

    return not any_error


# ──────────────────────────────────────────────────────────────
# Entry point
# ──────────────────────────────────────────────────────────────
def main():
    print("=" * 60)
    print("  Billiard Training — Outlier Detection Tool")
    print("=" * 60)
    print()
    print("Enter participant ID(s):")
    print("  Single  :  01   or  1")
    print("  Multiple:  01,02,05")
    print("  Range   :  01-30")
    print("  All     :  all (default: press Enter)")
    print()

    if len(sys.argv) > 1:
        raw_input = " ".join(sys.argv[1:])
        print(f"  → Using command-line argument: {raw_input}")
    else:
        try:
            raw_input = input("  [all] > ").strip()
        except EOFError:
            raw_input = ""

    if not raw_input:
        raw_input = "all"
        print("  No selection entered; processing all participants (01-30).")

    try:
        pids = parse_participant_ids(raw_input)
    except Exception as e:
        print(f"Invalid input: {e}")
        return

    print(f"\n  Participants to process: {', '.join(pids)}")
    print()

    # Set up log file
    log_dir = EXPERIMENT_ROOT / "tools" / "outlier_batch" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = log_dir / f"outlier_batch_{ts}.log"
    fh = _add_file_handler(log_file)
    log.info(f"Log file: {log_file}")

    n_ok = 0
    n_fail = 0
    for pid in pids:
        try:
            ok = process_participant(pid)
            if ok:
                n_ok += 1
            else:
                n_fail += 1
        except Exception:
            log.error(f"Participant {pid} FAILED:\n{traceback.format_exc()}")
            n_fail += 1

    print()
    print(f"{'='*60}")
    print(f"  Done.  Success: {n_ok}   Errors: {n_fail}")
    print(f"  Log: {log_file}")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
