"""Shared observed-score loader for publication and supplementary figures."""
from pathlib import Path
import hashlib
import json
import re
import numpy as np
import pandas as pd
from common.paths import assignments_path

GROUPS = ('both', 'strength', 'angle')
COLORS = dict(both='#0072B2', strength='#D55E00', angle='#009E73')
CHANNELS = dict(both=('strength', 'angle'), strength=('strength',), angle=('angle',))
PATTERN = re.compile(r'(?:^|_)(baseline|training|test)_(both|strength|angle)_', re.I)


def select_values(df, channel, training=False):
    """Same row-aligned rule throughout this new figure set; no source mutation."""
    required = [channel+'_value', channel+'_status']
    if training:
        required.append(channel+'_outlier')
    if not set(required).issubset(df.columns):
        raise ValueError('Missing required columns: '+str(set(required)-set(df.columns)))
    values = pd.to_numeric(df[channel+'_value'], errors='coerce')
    ok = df[channel+'_status'].astype(str).str.strip().str.lower().eq('scored') & np.isfinite(values)
    if channel+'_outlier' in df:
        ok &= ~pd.to_numeric(df[channel+'_outlier'], errors='coerce').eq(1)
    return values.where(ok)


def discover(root, participant):
    files = {}
    for folder, training in ((root/participant/'processed_csv', False),
                             (root/participant/'outlier_results/labeled_csv', True)):
        for path in sorted(folder.rglob('*.csv')):
            m = PATTERN.search(path.stem)
            if not m:
                continue
            stage, task = map(str.lower, m.groups())
            if (stage == 'training') != training:
                continue
            key = stage, task
            if key in files:
                raise ValueError(f'{participant}: ambiguous source {key}: {files[key]} / {path}')
            files[key] = path
    if len(files) != 7:
        raise ValueError(f'{participant}: expected 7 stage/task files, found {len(files)}')
    return files


def load_data(root):
    assignment_path = assignments_path(root)
    assignments = json.loads(assignment_path.read_text(encoding='utf-8-sig'))['assignments']
    groups = {f'{i:02d}': assignments[f'{i:02d}'].lower() for i in range(1, 31)}
    if any(list(groups.values()).count(g) != 10 for g in GROUPS):
        raise ValueError('Expected exactly 10 participants in each group for IDs 01-30.')
    hashes = {str(assignment_path.resolve()): hashlib.sha256(assignment_path.read_bytes()).hexdigest()}
    stages, blocks, pairs, audit = [], [], [], []
    for pid, group in groups.items():
        files = discover(root, pid)
        if ('training', group) not in files:
            raise ValueError(f'{pid}: training filename conflicts with group_assignments.json')
        baseline_scale = {}
        for (stage, task), path in files.items():
            if stage == 'training':
                continue
            hashes[str(path.resolve())] = hashlib.sha256(path.read_bytes()).hexdigest()
            df = pd.read_csv(path)
            cleaned = {}
            for ch in ('strength', 'angle'):
                v = select_values(df, ch)
                cleaned[ch] = v
                finite = v.dropna().to_numpy()
                row = dict(participant=pid, group=group, task=task, channel=ch,
                           stage=stage, n=len(finite), recorded=len(df),
                           mae=float(np.abs(finite).mean()) if len(finite) else np.nan,
                           mean=float(finite.mean()) if len(finite) else np.nan,
                           sd=float(finite.std(ddof=1)) if len(finite)>1 else np.nan)
                stages.append(row)
                if stage == 'baseline' and task == group and ch in CHANNELS[group]:
                    baseline_scale[ch] = float(np.sqrt(np.mean(finite**2))) if len(finite) else np.nan
            if task == 'both':
                joint = pd.DataFrame(cleaned).dropna()
                if len(joint):
                    pairs.append(dict(participant=pid, group=group, stage=stage,
                                      angle=float(joint.angle.mean()), strength=float(joint.strength.mean()),
                                      n_joint=len(joint)))
        path = files['training', group]
        hashes[str(path.resolve())] = hashlib.sha256(path.read_bytes()).hexdigest()
        df = pd.read_csv(path).sort_values('shot')
        shots = pd.to_numeric(df.shot, errors='raise').to_numpy(float)
        if not (np.isfinite(shots).all() and np.equal(shots, np.floor(shots)).all()
                and (shots>=1).all() and (shots<=140).all() and len(np.unique(shots))==len(shots)):
            raise ValueError(f'{path}: shot must be unique integer positions in 1..140')
        for ch in CHANNELS[group]:
            v = select_values(df, ch, training=True)
            scale = baseline_scale[ch]
            if not np.isfinite(scale) or scale <= 0:
                raise ValueError(f'{pid}/{ch}: matched-task baseline RMS must be positive')
            audit.append(dict(participant=pid,group=group,channel=ch,rows=len(df),
                              included=int(v.notna().sum()), baseline_rms=scale,
                              flagged=int(pd.to_numeric(df[ch+'_outlier'],errors='coerce').eq(1).sum())))
            for b in range(1,15):
                values = v[(shots>=10*(b-1)+1)&(shots<=10*b)].dropna().to_numpy()
                blocks.append(dict(participant=pid,group=group,channel=ch,block=b,n=len(values),
                                   mae=float(np.abs(values).mean()) if len(values) else np.nan,
                                   sd=float(values.std(ddof=1)) if len(values)>1 else np.nan,
                                   baseline_rms=scale))
    block_table = pd.DataFrame(blocks)
    block_table['normalized_mae'] = block_table.mae/block_table.baseline_rms
    block_table['normalized_sd'] = block_table.sd/block_table.baseline_rms
    return pd.DataFrame(stages), block_table, pd.DataFrame(pairs), pd.DataFrame(audit), hashes


