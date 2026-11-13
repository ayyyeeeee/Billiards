"""Read-only, reproducible Figures 2-4. Run: python plot_publication_figures.py.

Training uses scored AND non-outlier observations. Group assignment JSON is
authoritative. Missing modalities are never imputed. See generated METHODS.md.
"""
from pathlib import Path
import argparse
import hashlib
import json
import re
import warnings

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from scipy.optimize import curve_fit, OptimizeWarning

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
    assignment_path = root/'group_assignments.json'
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


def participant_indices(blocks):
    """Equal component weight in Both; never pool degrees with strength units."""
    records = []
    for (pid,g,b), d in blocks.groupby(['participant','group','block'], sort=True):
        row = dict(participant=pid,group=g,block=b)
        for name in ('normalized_mae','normalized_sd'):
            row[name] = float(d[name].mean()) if len(d)==len(CHANNELS[g]) and d[name].notna().all() else np.nan
        records.append(row)
    return pd.DataFrame(records)


def decay(t, amplitude, tau, asymptote):
    return amplitude*np.exp(-np.asarray(t)/tau)+asymptote


def fit_decay(x,y):
    x,y=np.asarray(x,float),np.asarray(y,float)
    ok=np.isfinite(x)&np.isfinite(y)
    x,y=x[ok],y[ok]
    out=dict(success=False, identifiable=False, A=np.nan,tau=np.nan,C=np.nan,r_squared=np.nan,
             tau_se=np.nan,C_se=np.nan)
    if len(y)<5:
        return out
    try:
        with warnings.catch_warnings():
            warnings.simplefilter('error', OptimizeWarning)
            p,cov=curve_fit(decay,x,y,p0=[max(float(y[0]-y[-1]),.05),4.,max(float(y.min()),0)],
                            bounds=([0.,.05,0.],[np.inf,200.,np.inf]),maxfev=20000)
        r2=1-np.sum((y-decay(x,*p))**2)/np.sum((y-y.mean())**2) if np.std(y)>0 else np.nan
        errors=np.sqrt(np.maximum(np.diag(cov),0))
        # Faster than half a block, or slower than the observed training window,
        # cannot yield a defensible block-resolution rate/asymptote here.
        identified=bool(p[0]>.05*max(float(y.mean()),1e-12) and .5<=p[1]<=np.ptp(x)
                        and np.isfinite(errors).all() and errors[1]<2*p[1] and r2>0)
        out.update(success=True, identifiable=identified,A=float(p[0]),tau=float(p[1]),C=float(p[2]),
                   r_squared=float(r2),tau_se=float(errors[1]),C_se=float(errors[2]))
    except (RuntimeError,ValueError,OptimizeWarning):
        pass
    return out


def draw_learning(blocks,out):
    indices=participant_indices(blocks)
    indices.to_csv(out/'figure2_participant_block_indices.csv',index=False,encoding='utf-8-sig')
    fig,axes=plt.subplots(1,2,figsize=(12,5))
    fits=[]; aggregates=[]
    for ax,measure,title in zip(axes,('normalized_mae','normalized_sd'),
                                ('(A) Trained-task performance','(B) Within-block variability')):
        for g in GROUPS:
            agg=indices[indices.group==g].groupby('block')[measure].agg(['mean','std','count'])
            sem=agg['std']/np.sqrt(agg['count'])
            x=agg.index.to_numpy(); y=agg['mean'].to_numpy()
            fit=fit_decay(x,y);fits.append(dict(group=g,measure=measure,**fit))
            label=(f"{g.title()}: tau={fit['tau']:.2g} blocks, C={fit['C']:.2g}"
                   if fit['identifiable'] else f'{g.title()}: decay not identifiable')
            ax.plot(x,y,'o-',ms=3,color=COLORS[g],lw=1.2,label=label)
            ax.fill_between(x,y-sem.to_numpy(),y+sem.to_numpy(),color=COLORS[g],alpha=.14)
            if fit['identifiable']:
                xx=np.linspace(1,14,150);ax.plot(xx,decay(xx,fit['A'],fit['tau'],fit['C']),ls='--',color=COLORS[g],lw=1.5)
            for b,r in agg.iterrows():
                aggregates.append(dict(group=g,measure=measure,block=b,mean=r['mean'],sem=float(r['std']/np.sqrt(r['count'])),n=int(r['count'])))
        ax.set(title=title,xlabel='Training block (original shots, 10 per block)',
               ylabel='Baseline-normalized MAE' if measure.endswith('mae') else 'Baseline-normalized trial SD',xlim=(.7,14.3))
        ax.set_xticks(range(1,15));ax.grid(alpha=.2);ax.legend(fontsize=8,loc='best')
    fig.suptitle('Group learning dynamics: normalized trained-task indices',fontsize=13)
    fig.text(.5,.025,'Shading: between-participant mean +/- SEM; dashed: single-exponential fit. Different trained modalities; no raw-unit pooling.',ha='center',fontsize=8)
    fig.subplots_adjust(left=.075,right=.98,bottom=.15,top=.88,wspace=.30)
    for ext in ('png','pdf'):
        fig.savefig(out/f'figure2_learning_dynamics.{ext}',dpi=300)
    plt.close(fig)
    pd.DataFrame(fits).to_csv(out/'figure2_decay_fits.csv',index=False,encoding='utf-8-sig')
    pd.DataFrame(aggregates).to_csv(out/'figure2_group_blocks.csv',index=False,encoding='utf-8-sig')
    return pd.DataFrame(fits)


METHODS = '''# Figures 2-4: methods and interpretation

Only IDs 01-30 are included; group_assignments.json contains additional IDs that are outside this request. Groups are taken from JSON, checked against training filenames, and each contain 10 participants. Original CSVs are read-only and hashes are checked before/after. Sources are exactly processed_csv for baseline/test and labeled_csv for training. Every measurement must be finite and its channel status scored; any available channel outlier=1 is excluded. Training labels are required. There is no review-flag filtering, padding, interpolation of missing scores, or renumbering of shots.

## Figure 2
Groups train different modalities, so degrees and strength units cannot form one raw MAE/SD axis. For each participant and channel, divide training MAE or within-block sample SD by that channel's matched-task baseline RMS error. Both participants use an equal-weight mean of the two normalized channel summaries; single-modality groups use their trained channel. Thus this is a descriptive normalized trained-task index, NOT a direct same-endpoint group efficacy comparison. Raw per-channel blocks and normalization denominators are exported. A block is original shot positions 1-10,11-20,...,131-140; exclusions leave holes and partial blocks. At least 2 valid trials are required for SD. Both index is missing when either channel statistic is missing. Group SEM uses participant block summaries, never pooled trials. Group n per block is exported.

Single exponential A exp(-block/tau)+C fitted to group means, A>=0, .05<=tau<=200, C>=0. With 14 blocks a double exponential is unnecessarily weakly identified. Point estimates have no inferential CI. Boundary/near-flat fits, tau below half-block resolution or beyond the observed block span, and large numerical tau uncertainty are labelled decay not identifiable; their raw optimizer estimates remain in CSV but must not be interpreted as learning rates. Covariance-based numerical standard errors are diagnostics only; repeated group blocks are correlated. Nonmonotonic data remain visible. Decreasing observed SD alone does not prove elimination of internal motor noise.

## Figure 3
Outcome is change in participant observed MAE (post minus baseline); negative means smaller absolute error. Signed mean changes would not generally have this interpretation. Two cells are structurally unmeasured: strength during angle-only task and angle during strength-only task. These panels explicitly say not measured; no synthetic points or tests. Measured panels use between-participant one-way ANOVA and Tukey HSD on independent participant changes. Levene and omnibus Holm adjustment across measured panels are exported. Figure pairwise Tukey p-values adjust the three comparisons within each panel, not all panels together. These analyses are exploratory; assumptions and small n matter.

## Figure 4
Each point is a participant's signed mean in Both-task, computed from jointly scored finite angle/strength trials. Baseline/post include the same participants. Axes are divided by pooled baseline participant SD for each channel, without subtracting the mean, so target stays (0,0); this makes equal geometric scaling meaningful across different physical units. Raw-unit coordinates are exported. Ellipses are 95% normal-reference covariance contours of participant mean coordinates (chi-square df=2 quantile), NOT a 95% confidence interval for the group mean and NOT an ellipse of within-person trial noise. Area ratios and centroid drift are descriptive. The proposed group-specific contraction is a hypothesis to check, not a programmed outcome; covariance shapes cannot by themselves prove control-mechanism decoupling.

Scores include recorded censoring; these figures summarize observed MAE/SD and observed participant means rather than latent censored-model parameters. This differs deliberately from the earlier Student-t location/scale figures. Baseline has roughly 10 trials versus roughly 30 post-test trials; participant means therefore have different measurement precision. A smaller post-test ellipse may partly reflect that difference, not just learning. PNGs are 300 DPI; PDFs preserve vector geometry and embedded text. Physical dimensions follow the requested 12x5,15x9,15x5 inch layouts; final journal sizing may require journal-specific resizing.

Sources: https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.f_oneway.html ; https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.tukey_hsd.html ; https://matplotlib.org/stable/gallery/statistics/confidence_ellipse.html
'''


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,default=Path(__file__).resolve().parent)
    parser.add_argument('--out',type=Path)
    args=parser.parse_args();root=args.root.resolve();out=args.out or root/'publication_figures'
    out.mkdir(parents=True,exist_ok=True)
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':9,'pdf.fonttype':42,
                         'axes.spines.top':False,'axes.spines.right':False,'savefig.dpi':300})
    stages,blocks,pairs,audit,hashes=load_data(root)
    for name,table in (('stage_metrics',stages),('training_channel_blocks',blocks),
                       ('phase_input_coordinates',pairs),('training_selection_audit',audit)):
        table.to_csv(out/(name+'.csv'),index=False,encoding='utf-8-sig')
    draw_learning(blocks,out)
    from publication_raincloud import draw_raincloud
    from publication_phase_space import draw_phase_space
    draw_raincloud(stages,out)
    draw_phase_space(pairs,out)
    assert all(hashlib.sha256(Path(p).read_bytes()).hexdigest()==h for p,h in hashes.items()),'Source changed during run'
    (out/'source_hashes.json').write_text(json.dumps(hashes,indent=2),encoding='utf-8')
    (out/'METHODS.md').write_text(METHODS,encoding='utf-8')
    print(f'Complete: {out}. All {len(hashes)} input hashes unchanged.')


if __name__=='__main__':
    main()
