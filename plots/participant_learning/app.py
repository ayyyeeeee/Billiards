"""Participant-level descriptive motor-learning figures, with CLI and desktop UI."""
from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass, field, replace
from decimal import Decimal, InvalidOperation
import hashlib
import json
import math
import os
from pathlib import Path
import queue
import re
import sys
import textwrap
import threading
from typing import Callable

from common.paths import PROJECT_ROOT, PARTICIPANT_ROOT, output_path
APP_DIR = PROJECT_ROOT / "learning_curve_tool"  # Preserve installed .deps and .tcl runtime.
DEFAULT_ROOT = PARTICIPANT_ROOT
for stream in (sys.stdout, sys.stderr):
    if stream is not None and hasattr(stream, 'reconfigure'):
        stream.reconfigure(encoding='utf-8')
os.environ.setdefault('MPLCONFIGDIR', str(APP_DIR / '.mplconfig'))
if (APP_DIR / '.deps').is_dir():
    sys.path.append(str(APP_DIR / '.deps'))  # Prefer a consistent installed scientific stack.
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.ticker import MaxNLocator
from plots.participant_learning.axis_views import acquisition_view

CONDITIONS = ('both', 'strength', 'angle')
FILE_PATTERN = re.compile(r'^(\d+)_(\d+)_(baseline|training|test)_(both|regular|strength|angle)(?:_.*)?$', re.I)
plt.rcParams.update({
    'font.family': 'DejaVu Sans', 'font.size': 9, 'axes.titlesize': 10,
    'axes.labelsize': 9, 'axes.linewidth': .7, 'xtick.labelsize': 8,
    'ytick.labelsize': 8, 'axes.spines.top': False, 'axes.spines.right': False,
    'svg.fonttype': 'path', 'pdf.fonttype': 42,
})
BLUE, GRAY = '#24618E', '#777777'


@dataclass
class Series:
    path: Path
    stage: str
    condition: str
    shot: np.ndarray
    value: np.ndarray
    capped: np.ndarray
    cap_known: np.ndarray
    units: tuple[str, ...]
    metric: str = ''
    components: dict[str, 'Series'] = field(default_factory=dict)
    outlier: np.ndarray = field(default_factory=lambda: np.zeros(0, dtype=bool))


@dataclass
class Participant:
    identifier: str
    folder: Path
    series: dict[tuple[str, str], Series]
    training_condition: str
    warnings: list[str]


def normalize_id(value: str) -> str:
    if not re.fullmatch(r'\d+', value.strip()):
        raise ValueError(f'受试者编号必须是数字：{value}')
    return value.strip().zfill(2)


def parse_ids(value: str) -> list[str]:
    result = []
    for token in re.split(r'[\s,，、;；]+', value.strip()):
        if not token:
            continue
        match = re.fullmatch(r'(\d+)\s*[-–]\s*(\d+)', token)
        if match:
            first, last = map(int, match.groups())
            if last < first or last - first > 999:
                raise ValueError('编号范围应从小到大，且一次最多包含 1000 个编号。')
            candidates = [normalize_id(str(i)) for i in range(first, last + 1)]
        else:
            candidates = [normalize_id(token)]
        for identifier in candidates:
            if identifier not in result:
                result.append(identifier)
    if not result:
        raise ValueError('请输入受试者编号，例如 01 或 01,02,04。')
    return result


def locate_folder(root: Path, identifier: str) -> Path:
    exact = root / identifier
    if exact.is_dir():
        return exact
    candidates = [p for p in root.iterdir() if p.is_dir() and p.name.isdigit() and int(p.name) == int(identifier)]
    if len(candidates) == 1:
        return candidates[0]
    raise ValueError(f'找不到唯一的受试者文件夹：{root / identifier}')


def csv_folder(folder: Path) -> Path:
    newest = folder / 'MOLT4_results_v3' / 'csv'
    if newest.is_dir() and any(newest.glob('*.csv')):
        return newest
    paths = [folder / 'MOLT4_results' / 'csv', folder / 'MOLT4' / '_results' / 'csv']
    found = [p for p in paths if p.is_dir() and any(p.glob('*.csv'))]
    if len(found) != 1:
        raise ValueError(f'{folder.name}：未找到唯一的 CSV 数据目录（支持 MOLT4_results/csv 和 MOLT4/_results/csv）。')
    return found[0]


def discover_ids(root: Path) -> list[str]:
    if not root.is_dir():
        raise ValueError(f'实验目录不存在：{root}')
    result = []
    for folder in sorted(root.iterdir(), key=lambda p: (int(p.name) if p.name.isdigit() else float('inf'), p.name)):
        if not folder.is_dir() or not folder.name.isdigit():
            continue
        try:
            proc = folder / 'processed_csv'
            if proc.is_dir() and any(FILE_PATTERN.match(p.stem) for p in proc.rglob('*.csv')):
                result.append(normalize_id(folder.name))
                continue
            data = csv_folder(folder)
            if any(FILE_PATTERN.match(p.stem) for p in data.glob('*.csv')):
                result.append(normalize_id(folder.name))
        except ValueError:
            continue
    if not result:
        raise ValueError('没有找到包含实验 CSV 的数字编号文件夹。')
    return result


def _collect_participant_files(folder: Path, identifier: str, legacy: bool = False) -> tuple[list[tuple[Path, str, str]], list[str]]:
    proc = folder / 'processed_csv'
    labeled = folder / 'outlier_results' / 'labeled_csv'
    warnings: list[str] = []
    files: list[tuple[Path, str, str]] = []

    use_new = (not legacy) and proc.is_dir() and any(proc.rglob('*.csv'))
    if use_new:
        for path in sorted(proc.rglob('*.csv')):
            match = FILE_PATTERN.match(path.stem)
            if not match or int(match[1]) != int(identifier):
                warnings.append(f'未纳入不匹配文件：{path.name}')
                continue
            stage, condition = match[3].lower(), match[4].lower()
            if stage in ('baseline', 'test'):
                files.append((path, stage, condition))
        found_training = False
        if labeled.is_dir():
            for path in sorted(labeled.glob('*.csv')):
                match = FILE_PATTERN.match(path.stem)
                if not match or int(match[1]) != int(identifier):
                    warnings.append(f'未纳入不匹配文件：{path.name}')
                    continue
                stage, condition = match[3].lower(), match[4].lower()
                if stage == 'training':
                    files.append((path, stage, condition))
                    found_training = True
        if not found_training:
            raise ValueError(f'{identifier}：训练必须读取 outlier_results/labeled_csv，未找到标记文件；不回退原始训练CSV。')
    else:
        data = csv_folder(folder)
        for path in sorted(data.glob('*.csv')):
            match = FILE_PATTERN.match(path.stem)
            if not match or int(match[1]) != int(identifier):
                warnings.append(f'未纳入不匹配文件：{path.name}')
                continue
            stage, condition = match[3].lower(), match[4].lower()
            files.append((path, stage, condition))

    return files, warnings


def load_series(path: Path, stage: str, condition: str, metric: str | None = None, exclude_outliers: bool = True) -> Series:
    condition = 'both' if condition == 'regular' else condition
    with path.open(encoding='utf-8-sig', newline='') as stream:
        headers = csv.DictReader(stream).fieldnames or []
    if condition == 'both' and metric is None and any(c+'_value' in headers for c in ('strength','angle')):
        if not all(c+'_value' in headers for c in ('strength','angle')):
            raise ValueError(f'{path.name}：both 双分量结构缺少 strength_value 或 angle_value。')
        components = {c: load_series(path, stage, condition, c, exclude_outliers) for c in ('strength','angle')}
        return replace(components['strength'], components=components)
    selected = metric or (condition if condition+'_value' in headers else '')
    value_column = selected+'_value' if selected else 'value'
    maximum_column = selected+'_maximum' if selected else 'maximum'
    records = []
    units = set()
    with path.open(encoding='utf-8-sig', newline='') as stream:
        reader = csv.DictReader(stream)
        if not {'shot', value_column}.issubset(reader.fieldnames or []):
            raise ValueError(f'{path.name}：缺少 shot 或 value 列。')
        for line, row in enumerate(reader, 2):
            if not any((v or '').strip() for v in row.values() if isinstance(v, str)):
                continue
            try:
                shot_raw = float(row['shot'])
                value_text = row[value_column].strip()
                status = (row.get(selected+'_status') or '').strip().lower() if selected else ''
                outlier_raw = (row.get(selected+'_outlier') or '') if selected else ''
                if not outlier_raw:
                    outlier_raw = row.get('outlier') or ''
                is_outlier = outlier_raw.strip().lower() in ('1', '1.0', 'true')
                labeled_training = stage == 'training' and selected+'_outlier' in headers
                if labeled_training:
                    # User-reviewed labels are authoritative for training.
                    missing = is_outlier or not value_text or not math.isfinite(float(value_text))
                else:
                    missing = (is_outlier and exclude_outliers) or (status in ('unresolved', 'invalid', 'not_requested')) or (not value_text)
                if not labeled_training and not exclude_outliers and selected:
                    valid = (row.get(selected+'_valid') or '1').strip()
                    missing = missing or valid not in ('1', '1.0', 'true', 'True')
                    if not status:
                        missing = missing or (row.get('score_complete') or '1').strip() not in ('1', '1.0')
                value = float('nan') if missing else float(value_text)
                if not math.isfinite(shot_raw) or not shot_raw.is_integer() or shot_raw < 1 or (not missing and not math.isfinite(value)):
                    raise ValueError('invalid shot or non-missing NaN value')
                if not labeled_training and selected and value_text and not missing and status not in ('', 'scored'):
                    raise ValueError(f'{selected}_status={status} 与非空分数冲突')
                maximum_text = (row.get(maximum_column) or '').strip()
                known, capped = False, False
                if not missing and maximum_text and maximum_text.lower() not in ('nan', 'na', 'n/a', 'none'):
                    maximum = float(maximum_text)
                    if not math.isfinite(maximum):
                        raise ValueError()
                    tolerance = .5 * 10.0 ** Decimal(value_text).as_tuple().exponent
                    known = True
                    capped = abs(abs(value) - abs(maximum)) <= tolerance + 1e-12
                mode = (row.get('mode') or '').strip().lower()
                mode = 'both' if mode == 'regular' else mode
                if mode and mode != condition:
                    raise ValueError(f'mode={mode} 与文件名条件 {condition} 不一致')
            except (ValueError, TypeError, OverflowError, InvalidOperation) as exc:
                raise ValueError(f'{path.name} 第 {line} 行：shot/value/maximum 无效或条件不一致。{exc}') from exc
            records.append((int(shot_raw), value, capped, known, is_outlier))
            unit = (row.get('unit') or '').strip()
            if metric and ':' in unit:
                unit = dict(part.split(':',1) for part in unit.split(';') if ':' in part).get(metric, '')
            if unit:
                units.add(unit)
    if not records:
        raise ValueError(f'{path.name}：没有可用记录。')
    records.sort(key=lambda row: row[0])
    shots = np.array([r[0] for r in records], dtype=int)
    if len(np.unique(shots)) != len(shots):
        raise ValueError(f'{path.name}：shot 有重复，无法确定击球顺序，请先检查数据。')
    if len(units) > 1:
        raise ValueError(f'{path.name}：同一文件含多个单位，不能合并统计。')
    return Series(path, stage, condition, shots,
                  np.array([r[1] for r in records]),
                  np.array([r[2] for r in records], dtype=bool),
                  np.array([r[3] for r in records], dtype=bool), tuple(sorted(units)), selected,
                  components={},
                  outlier=np.array([r[4] for r in records], dtype=bool))


def load_participant(root: Path, identifier: str, legacy: bool = False) -> Participant:
    identifier = normalize_id(identifier)
    folder = locate_folder(root, identifier)
    files, warnings = _collect_participant_files(folder, identifier, legacy=legacy)
    result = {}
    for path, stage, condition in files:
        condition = 'both' if condition == 'regular' else condition
        key = stage, condition
        if key in result:
            raise ValueError(f'{identifier}：{stage}/{condition} 有多个文件，请保留唯一分析文件。')
        series = load_series(path, stage, condition, exclude_outliers=False)
        result[key] = series
        for name, component in (series.components or {series.metric or condition: series}).items():
            missing = int((~np.isfinite(component.value)).sum())
            if missing:
                warnings.append(f'{path.name}/{name}：{missing} 个未纳入计算记录（训练outlier=1或缺失；其他阶段按有效性字段）；保留 shot 位置，不填零，统计仅使用该分量可用数值。')
        if np.any(np.diff(series.shot) != 1):
            warnings.append(f'{path.name}：shot 存在间隔；按现有记录顺序分块，不补值。')
        count_match = re.search(r'_(\d+)shots', path.stem, re.I)
        if count_match and int(count_match[1]) != len(series.value):
            warnings.append(f'{path.name}：实际 {len(series.value)} 球，使用实际数据而非文件名球数。')
    training = [condition for stage, condition in result if stage == 'training']
    if len(training) != 1:
        raise ValueError(f'{identifier}：应有唯一 training 条件，实际找到 {len(training)} 个。')
    for condition in CONDITIONS:
        b, t = result.get(('baseline', condition)), result.get(('test', condition))
        if b is None or t is None:
            warnings.append(f'{condition} 缺少 baseline 或 test；图中注明缺失，不补造数据。')
        if b is not None and t is not None:
            if bool(b.components) != bool(t.components):
                raise ValueError(f'{identifier}/{condition}：baseline/test 新旧指标结构混用，不能将旧综合值当作分量比较。')
            for name in (b.components or {'value': b}):
                bs, ts = (b.components[name], t.components[name]) if b.components else (b, t)
                if bs.units and ts.units and bs.units != ts.units:
                    raise ValueError(f'{identifier}/{condition}/{name}：baseline 与 test 单位不同，不能直接比较。')
    return Participant(identifier, folder, result, training[0], warnings)


def blocks(series: Series, size: int) -> list[dict]:
    if size < 1:
        raise ValueError('分块大小必须大于 0。')
    result = []
    for start in range(0, len(series.value), size):
        stop = min(start + size, len(series.value))
        raw_values, shots = series.value[start:stop], series.shot[start:stop]
        valid = np.isfinite(raw_values)
        values = raw_values[valid]
        known = int(series.cap_known[start:stop].sum())
        capped = int(series.capped[start:stop].sum())
        result.append(dict(start=int(shots[0]), end=int(shots[-1]), n=len(values), rows=stop-start,
                           center=float(shots.mean()), mean=float(values.mean()) if len(values) else None,
                           sd=float(values.std(ddof=1)) if len(values) > 1 else None,
                           cap_known=known, capped=capped,
                           cap_pct=100 * capped / known if known else None,
                           values=values, shots=shots[valid]))
    return result


def unit_label(series: Series) -> str:
    if series.units and series.units[0].lower() in ('degree', 'degrees', 'deg'):
        return 'degrees'
    return 'recorded units'


def panel(ax, letter: str, title: str):
    ax.text(-.17, 1.065, letter, transform=ax.transAxes, fontsize=15, weight='bold')
    ax.set_title(title, loc='left', pad=12)
    ax.tick_params(direction='out', length=3, width=.7)


def bounds(ax, values):
    finite = np.asarray(values, dtype=float)
    finite = finite[np.isfinite(finite)]
    lower, upper = (min(0., finite.min()), max(0., finite.max())) if len(finite) else (0., 1.)
    margin = max(upper - lower, abs(upper), .01) * .14
    ax.set_ylim(lower - margin if lower < 0 else 0, upper + margin)


def plain_block(block):
    return {key: value for key, value in block.items() if key not in ('values', 'shots')}


def create_figure(participant: Participant, size: int = 10):
    if any(s.components or s.metric for s in participant.series.values()):
        from plots.participant_learning.components import create_component_figure
        return create_component_figure(participant, size, sys.modules[__name__])
    p = participant
    train = p.series['training', p.training_condition]
    grouped = blocks(train, size)
    n = len(train.value)
    bx = np.array([b['center'] for b in grouped])
    means = np.array([b['mean'] for b in grouped])
    sds = np.array([b['sd'] if b['sd'] is not None else np.nan for b in grouped])
    fig, axes = plt.subplots(2, 3, figsize=(14, 10.1))
    fig.subplots_adjust(left=.07, right=.98, top=.85, bottom=.32, wspace=.31, hspace=.53)
    total = sum(len(s.value) for s in p.series.values())
    has_signed = any(np.any(np.asarray(s.value)[np.isfinite(s.value)] < 0) for s in p.series.values())
    perf_text = 'Values closer to zero indicate better performance' if has_signed else 'Lower values indicate better performance'
    fig.text(.07, .963, f'Participant {p.identifier}: acquisition and immediate post-test performance', fontsize=15, weight='bold')
    fig.text(.07, .934, f'Training condition: {p.training_condition}   |   {total} trials across {len(p.series)} recordings   |   {perf_text}', fontsize=10)
    ax = axes[0, 0]
    panel(ax, 'a', f'Acquisition: {p.training_condition}')
    points=ax.scatter(train.shot, train.value, s=9, c=GRAY, alpha=.42, linewidths=0, zorder=2)
    ax.axhline(0, color='#b8b8b8', lw=.7, ls='--', zorder=1)
    if hasattr(train, 'outlier') and train.outlier.any():
        outlier_shots = train.shot[train.outlier]
        ax.scatter(outlier_shots, np.zeros_like(outlier_shots), s=18, color='#d62728', edgecolors='#8b0000', linewidths=0.5, zorder=6)
    ax.plot(bx, means, 'o-', color=BLUE, lw=1.7, ms=3.5, zorder=4)
    ax.set(xlabel='Training trial (shot)', ylabel=f'{p.training_condition.capitalize()} error ({unit_label(train)})')
    bounds(ax, train.value)
    ax = axes[0, 1]
    panel(ax, 'b', 'Within-block variability')
    ax.plot(bx, sds, 'o-', color=BLUE, lw=1.5, ms=3.5)
    ax.set(xlabel='Training trial (shot)', ylabel=f'Within-block SD ({unit_label(train)})')
    bounds(ax, sds)
    if not np.isfinite(sds).any():
        ax.text(.5, .5, 'SD requires at least two trials', transform=ax.transAxes, ha='center', fontsize=9)
    ax = axes[0, 2]
    panel(ax, 'c', 'Capped observations during training')
    known_total = int(train.cap_known.sum())
    cap_pct = [b['cap_pct'] if b['cap_pct'] is not None else np.nan for b in grouped]
    width = [max(.6, (b['end'] - b['start'] + 1) * .7) for b in grouped]
    ax.bar(bx, cap_pct, width=width, color='#8b9eaa', edgecolor='none')
    ax.set(ylim=(0, 115), xlabel='Training trial (shot)', ylabel='Capped observations (%)')
    ax.set_yticks([0, 25, 50, 75, 100])
    if known_total:
        label = f'{int(train.capped.sum())}/{known_total} trials ({train.capped.sum()/known_total:.1%})'
        if known_total != n:
            label += f'\nCap metadata: {known_total}/{n} trials'
        ax.text(.97, .95, label, transform=ax.transAxes, ha='right', va='top', fontsize=9)
    else:
        ax.text(.5, .5, 'Cap metadata unavailable', transform=ax.transAxes, ha='center', fontsize=9)
    xmin, xmax = train.shot[0], train.shot[-1]
    pad = max(1, (xmax - xmin) * .025)
    for ax in axes[0]:
        ax.set_xlim(xmin-pad, xmax+pad)
        ax.xaxis.set_major_locator(MaxNLocator(nbins=5, integer=True, min_n_ticks=2))
    acquisition_display=acquisition_view(axes[0,0],train.shot,train.value,means,points,GRAY)

    captions = [
        ('a', f'{p.training_condition.capitalize()} acquisition ({n} trials). Points show individual trials; the line joins means of successive blocks of up to {size} observed trials. Final block: n = {grouped[-1]["n"]}. Red dots on the x-axis (y = 0) mark outlier trials excluded from calculation.'),
        ('b', f'Sample standard deviation within the training blocks shown in a. SD is omitted for blocks containing only one observation.'),
        ('c', 'Percentage of capped observations in each training block, using trials with available cap metadata. Capping can compress observed means and variability.'),
    ]
    if acquisition_display['separated']:
        letter,body=captions[0]
        captions[0]=(letter,body+' High values appear in the separate upper region (broken y-axis); all trials remain in statistics.')
    comparisons = {}
    for ax, letter, condition in zip(axes[1], 'def', CONDITIONS):
        role = 'trained condition' if condition == p.training_condition else 'transfer assessment'
        panel(ax, letter, f'{condition.capitalize()}: {role}')
        baseline, test = p.series.get(('baseline', condition)), p.series.get(('test', condition))
        groups = []
        labels = []
        if baseline is not None:
            b = blocks(baseline, len(baseline.value))[0]
            groups.append((0, b, GRAY))
            labels.append(f'Baseline\nn = {b["n"]}')
        else:
            labels.append('Baseline\nnot available')
        test_blocks = blocks(test, size) if test is not None else []
        for i, block in enumerate(test_blocks, 1):
            groups.append((i, block, BLUE))
            labels.append(f'Test\n{block["start"]}–{block["end"]}\nn = {block["n"]}')
        if test is None:
            labels.append('Test\nnot available')
        ax.axvline(.5, color='#b8b8b8', lw=.7, ls=':')
        ax.axhline(0, color='#b8b8b8', lw=.7, ls='--', zorder=1)
        scale_values = []
        for position, block, color in groups:
            values = block['values']
            offset = np.linspace(-.18, .18, len(values)) if len(values) > 1 else np.array([0.])
            ax.scatter(position+offset, values, s=15, c=color, alpha=.48, linewidths=0, zorder=2)
            ax.plot(position, block['mean'], 's', color='#111111', ms=4.5, zorder=5)
            scale_values.extend(values)
            if block['sd'] is not None:
                ax.errorbar(position, block['mean'], yerr=block['sd'], fmt='none', color='#111111', elinewidth=1.1, capsize=4, zorder=4)
                scale_values.extend([block['mean']-block['sd'], block['mean']+block['sd']])
        ax.plot(range(1, len(test_blocks)+1), [b['mean'] for b in test_blocks], color=BLUE, lw=1.1, zorder=3)
        ax.set_xlim(-.5, len(labels)-.5)
        available = baseline if baseline is not None else test
        units = unit_label(available) if available is not None else 'recorded units'
        ax.set_ylabel(f'{condition.capitalize()} error ({units})')
        ax.set_xticks(range(len(labels)), labels)
        if len(labels) > 5:
            ax.tick_params(axis='x', labelsize=6)
            for tick in ax.get_xticklabels():
                tick.set_rotation(35)
                tick.set_ha('right')
        bounds(ax, scale_values)
        if baseline is None or test is None:
            missing = 'baseline and test' if available is None else ('baseline' if baseline is None else 'test')
            ax.text(.5, .95, f'Missing {missing} data', transform=ax.transAxes, ha='center', va='top', fontsize=9)
        bn, tn = len(baseline.value) if baseline is not None else 0, len(test.value) if test is not None else 0
        if baseline is not None and test is not None:
            bm, tm = float(baseline.value.mean()), float(test.value.mean())
            comparisons[condition] = dict(baseline_n=bn, test_n=tn, baseline_mean=bm, test_mean=tm,
                                          test_minus_baseline=tm-bm, relative_reduction=(bm-tm)/bm if bm else None,
                                          test_blocks=[plain_block(b) for b in test_blocks])
        interpretation = 'This is the trained condition.' if condition == p.training_condition else 'This untrained condition assesses possible transfer.'
        captions.append((letter, f'{condition.capitalize()} baseline (n = {bn}) and immediate test (n = {tn}). {interpretation} Squares and error bars show means ± SD; test is split into blocks of up to {size} trials.'))
    legend = [Line2D([], [], marker='o', ls='none', ms=4, color=GRAY, label='Individual trial'),
              Line2D([], [], marker='o', lw=1.5, ms=4, color=BLUE, label=f'Block mean (up to {size} trials)'),
              Line2D([], [], marker='s', ls='none', ms=4, color='black', label='Mean ± SD (d–f)'),
              Line2D([], [], marker='o', ls='none', color='#d62728', markeredgecolor='#8b0000', markeredgewidth=0.5, ms=4.5, label='Outlier on x-axis (excluded)')]
    fig.legend(handles=legend, loc='upper center', bbox_to_anchor=(.53, .912), ncol=4, frameon=False, fontsize=8, columnspacing=2.0)
    fig.add_artist(Line2D([.07, .98], [.252, .252], transform=fig.transFigure, color='#777777', lw=.6))
    fig.text(.07, .23, 'Figure 1. Single-participant descriptive analysis.', fontsize=10, weight='bold')
    for i, (letter, body) in enumerate(captions):
        column, row = i // 3, i % 3
        left, top = .07 + column * .465, .203 - row * .064
        fig.text(left, top, f'({letter})', fontsize=9, weight='bold', va='top')
        fig.text(left+.027, top, textwrap.fill(body, width=84), fontsize=8.5, va='top', linespacing=1.35)
    for obj in fig.findobj(matplotlib.text.Text):
        if any('\u4e00' <= char <= '\u9fff' for char in obj.get_text()):
            plt.close(fig)
            raise ValueError('图中意外出现中文字符。')
    outliers = [int(s) for s in train.shot[train.outlier]] if hasattr(train, 'outlier') and train.outlier.any() else []
    return fig, dict(participant=p.identifier, training_condition=p.training_condition, block_size=size,
                     total_trials=total, training_outliers=outliers, training_outlier_count=len(outliers),
                     training_blocks=[plain_block(b) for b in grouped], comparisons=comparisons,
                     acquisition_display=acquisition_display,
                     sources=[dict(file=str(s.path), n=len(s.value), sha256=hashlib.sha256(s.path.read_bytes()).hexdigest()) for s in p.series.values()],
                     warnings=p.warnings)


def process_one(root: Path, identifier: str, output: Path, size: int = 10) -> dict:
    participant = load_participant(root, identifier)
    fig, statistics = create_figure(participant, size)
    output.mkdir(parents=True, exist_ok=True)
    (output / 'statistics').mkdir(exist_ok=True)
    try:
        for suffix in ('png', 'svg'):
            destination = output / f'{participant.identifier}.{suffix}'
            temporary = output / f'.{participant.identifier}.tmp.{suffix}'
            fig.savefig(temporary, dpi=240, facecolor='white')
            os.replace(temporary, destination)
        if 'captions' in statistics:
            (output / f'{participant.identifier}_caption.md').write_text(
                '\n\n'.join(f'({letter}) {body}' for letter, body in statistics['captions']), encoding='utf-8')
        stats_path = output / 'statistics' / f'{participant.identifier}.json'
        stats_path.write_text(json.dumps(statistics, ensure_ascii=False, indent=2, allow_nan=False), encoding='utf-8')
    finally:
        plt.close(fig)
    return statistics


def run_batch(root: Path, identifiers: list[str], output: Path, size: int = 10,
              report: Callable[[str], None] = print) -> list[dict]:
    results = []
    for index, identifier in enumerate(identifiers, 1):
        report(f'[{index}/{len(identifiers)}] 正在绘制 {identifier}…')
        try:
            stats = process_one(root, identifier, output, size)
            results.append(dict(id=identifier, status='ok', training=stats['training_condition'], trials=stats['total_trials'], warnings=stats['warnings']))
            report(f'完成 {identifier}：training={stats["training_condition"]}，共 {stats["total_trials"]} 球。')
            for warning in stats['warnings']:
                report(f'  提示：{warning}')
        except Exception as exc:
            results.append(dict(id=identifier, status='error', error=str(exc)))
            report(f'失败 {identifier}：{exc}')
    output.mkdir(parents=True, exist_ok=True)
    (output / 'batch_report.json').write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding='utf-8')
    return results


def launch_gui():
    import tkinter as tk
    from tkinter import ttk, filedialog, messagebox
    try:
        window = tk.Tk()
    except tk.TclError:
        # Some embedded Python installations cannot locate their Tcl scripts.
        local_tcl = APP_DIR / '.tcl'
        if not (local_tcl / 'tcl8.6' / 'init.tcl').is_file():
            raise
        os.environ['TCL_LIBRARY'] = str(local_tcl / 'tcl8.6')
        os.environ['TK_LIBRARY'] = str(local_tcl / 'tk8.6')
        window = tk.Tk()
    window.title('学习曲线批处理')
    window.geometry('760x530')
    window.minsize(660, 450)
    root_value = tk.StringVar(value=str(DEFAULT_ROOT))
    ids_value = tk.StringVar()
    status = tk.StringVar(value='输入受试者编号即可绘图，例如 01,02,04 或 01-05。')
    events = queue.Queue()
    running = False
    container = ttk.Frame(window, padding=18)
    container.pack(fill='both', expand=True)
    container.columnconfigure(1, weight=1)
    ttk.Label(container, text='学习曲线批处理', font=('Microsoft YaHei UI', 15, 'bold')).grid(row=0, column=0, columnspan=3, sticky='w', pady=(0, 18))
    ttk.Label(container, text='实验总目录').grid(row=1, column=0, sticky='w', padx=(0, 10))
    directory_entry = ttk.Entry(container, textvariable=root_value)
    directory_entry.grid(row=1, column=1, sticky='ew')

    def browse():
        chosen = filedialog.askdirectory(initialdir=root_value.get())
        if chosen:
            root_value.set(chosen)

    browse_button = ttk.Button(container, text='选择目录', command=browse)
    browse_button.grid(row=1, column=2, padx=(8, 0))
    ttk.Label(container, text='受试者编号').grid(row=2, column=0, sticky='w', pady=14)
    identifier_entry = ttk.Entry(container, textvariable=ids_value)
    identifier_entry.grid(row=2, column=1, columnspan=2, sticky='ew')
    ttk.Label(container, text='支持单个编号、逗号分隔多个编号、连续范围；也可直接“绘制全部受试者”。', wraplength=680).grid(row=3, column=0, columnspan=3, sticky='w')
    buttons = ttk.Frame(container)
    buttons.grid(row=4, column=0, columnspan=3, sticky='w', pady=16)
    log = tk.Text(container, height=13, wrap='word', state='disabled', font=('Microsoft YaHei UI', 9))
    log.grid(row=6, column=0, columnspan=3, sticky='nsew')
    container.rowconfigure(6, weight=1)
    ttk.Label(container, textvariable=status, wraplength=700).grid(row=5, column=0, columnspan=3, sticky='w', pady=(0, 8))
    ttk.Label(container, text='输出：默认 results/learning_curves 文件夹（自定义数据目录仍输出其 learning_curves 子目录）中的 编号.png 和 编号.svg。\n再次运行会更新同编号的图片；原始 CSV 保持不变。', wraplength=700).grid(row=7, column=0, columnspan=3, sticky='w', pady=(12, 0))

    def start(all_subjects=False):
        nonlocal running
        if running:
            return
        try:
            root = Path(root_value.get()).expanduser().resolve()
            if not root.is_dir():
                raise ValueError('实验总目录不存在。')
            identifiers = discover_ids(root) if all_subjects else parse_ids(ids_value.get())
        except ValueError as exc:
            messagebox.showerror('输入有误', str(exc))
            return
        running = True
        for control in controls:
            control.configure(state='disabled')
        status.set(f'正在处理 {len(identifiers)} 位受试者…')

        def worker():
            try:
                results = run_batch(root, identifiers, output_path(root, 'learning_curves'), report=lambda msg: events.put(('log', msg)))
                events.put(('done', results))
            except Exception as exc:
                events.put(('fatal', str(exc)))

        threading.Thread(target=worker, daemon=True).start()

    def open_output():
        output = output_path(Path(root_value.get()).expanduser(), 'learning_curves')
        if output.is_dir():
            os.startfile(str(output))
        else:
            messagebox.showinfo('尚无输出', '请先绘图。')

    selected_button = ttk.Button(buttons, text='绘制输入编号', command=start)
    selected_button.pack(side='left', padx=(0, 10))
    all_button = ttk.Button(buttons, text='绘制全部受试者', command=lambda: start(True))
    all_button.pack(side='left', padx=(0, 10))
    ttk.Button(buttons, text='打开输出文件夹', command=open_output).pack(side='left')
    controls = [selected_button, all_button, directory_entry, identifier_entry, browse_button]

    def poll():
        nonlocal running
        try:
            while True:
                kind, value = events.get_nowait()
                if kind == 'log':
                    log.configure(state='normal')
                    log.insert('end', value+'\n')
                    log.see('end')
                    log.configure(state='disabled')
                else:
                    running = False
                    for control in controls:
                        control.configure(state='normal')
                    if kind == 'done':
                        passed = sum(r['status']=='ok' for r in value)
                        status.set(f'已完成：成功 {passed} 位，失败 {len(value)-passed} 位。可打开输出文件夹查看。')
                    else:
                        status.set('运行失败：'+value)
        except queue.Empty:
            pass
        window.after(120, poll)

    def close():
        if running:
            messagebox.showinfo('正在绘图', '请等当前批次完成后再关闭窗口。')
            return
        window.destroy()

    window.protocol('WM_DELETE_WINDOW', close)
    window.bind('<Return>', lambda event: start())
    identifier_entry.focus_set()
    poll()
    window.mainloop()


def main():
    parser = argparse.ArgumentParser(description='Create English six-panel motor-learning figures by participant ID.')
    parser.add_argument('ids', nargs='*', help='IDs or ranges, e.g. 01 02 or 01-05')
    parser.add_argument('--all', action='store_true', help='Process all participant folders containing CSV data')
    parser.add_argument('--gui', action='store_true')
    parser.add_argument('--root', type=Path, default=DEFAULT_ROOT)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--block-size', type=int, default=10)
    args = parser.parse_args()
    if args.gui or (not args.ids and not args.all):
        launch_gui()
        return 0
    if args.block_size < 1:
        parser.error('--block-size must be positive')
    root = args.root.resolve()
    identifiers = discover_ids(root) if args.all else parse_ids(' '.join(args.ids))
    results = run_batch(root, identifiers, args.output or output_path(root, 'learning_curves'), args.block_size)
    return int(any(r['status']=='error' for r in results))


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except Exception as exc:
        (APP_DIR/'startup_error.txt').write_text(str(exc), encoding='utf-8')
        if '--gui' in sys.argv or len(sys.argv) == 1:
            import tkinter.messagebox
            tkinter.messagebox.showerror('学习曲线程序启动失败', str(exc))
        else:
            print(f'ERROR: {exc}', file=sys.stderr)
        raise SystemExit(1)
