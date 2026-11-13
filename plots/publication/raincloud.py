"""Figure 3: participant MAE changes, independent-group ANOVA and Tukey HSD.

The input is an already audited stage table. No source CSVs are changed here.
ANOVA tests independent participant deltas, never individual shots. Holm covers
available omnibus panels; each Tukey family covers three pairs in one panel.
"""
from pathlib import Path
from itertools import combinations
import warnings

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from scipy import stats
from statsmodels.stats.multicomp import pairwise_tukeyhsd
from statsmodels.stats.multitest import multipletests


GROUPS = ('both', 'strength', 'angle')
COLORS = dict(zip(GROUPS, ('#0072B2', '#D55E00', '#009E73')))
TASKS = ('both', 'strength', 'angle')
CHANNELS = ('strength', 'angle')


def participant_deltas(stage_table):
    """Pair one baseline and test per participant/task/component, without pooling trials."""
    required = {'participant', 'group', 'task', 'channel', 'stage', 'mae'}
    missing = required - set(stage_table)
    if missing:
        raise ValueError(f'Missing stage-table fields: {sorted(missing)}')
    d = stage_table.copy()
    d = d[d.stage.isin(['baseline', 'test'])]
    keys = ['participant', 'group', 'task', 'channel']
    if d.duplicated(keys + ['stage']).any():
        raise ValueError('Duplicate participant/task/channel/stage records; cannot infer independent deltas.')
    if (d.groupby('participant').group.nunique() > 1).any():
        raise ValueError('Participant belongs to more than one training group.')
    d['mae'] = pd.to_numeric(d.mae, errors='coerce')
    d.loc[~np.isfinite(d.mae), 'mae'] = np.nan
    if 'n' in d:
        d.loc[~pd.to_numeric(d['n'], errors='coerce').gt(0), 'mae'] = np.nan
    paired = d.pivot(index=keys, columns='stage', values='mae').reset_index()
    for name in ('baseline', 'test'):
        if name not in paired:
            paired[name] = np.nan
    paired = paired.dropna(subset=['baseline', 'test'])
    paired['delta_mae'] = paired.test - paired.baseline
    return paired.sort_values(keys).reset_index(drop=True)


def _panel_statistics(data, channel, task):
    groups = [data.loc[data.group.eq(g), 'delta_mae'].to_numpy(float) for g in GROUPS]
    base = {'channel': channel, 'task': task,
            **{'n_' + g: len(v) for g, v in zip(GROUPS, groups)}}
    omnibus = dict(base, kind='omnibus', status='unavailable', reason='',
                    statistic=np.nan, p_value=np.nan, p_holm=np.nan,
                    levene_statistic=np.nan, levene_p=np.nan)
    records = []
    for g, values in zip(GROUPS, groups):
        if len(values):
            records.append(dict(base, kind='group', group1=g, n=len(values),
                mean=float(np.mean(values)), median=float(np.median(values)),
                sd=float(np.std(values, ddof=1)) if len(values)>1 else np.nan,
                q1=float(np.quantile(values,.25)), q3=float(np.quantile(values,.75))))
    if not any(len(v) for v in groups):
        omnibus['reason'] = 'No paired measurements'
    elif any(len(v) < 2 for v in groups):
        omnibus['reason'] = 'Need at least two participants in each of three groups'
    elif sum(float(np.sum((v-v.mean())**2)) for v in groups) == 0:
        omnibus['reason'] = 'Zero within-group variation; ANOVA and Tukey undefined'
    else:
        with warnings.catch_warnings():
            warnings.simplefilter('ignore', RuntimeWarning)
            test = stats.f_oneway(*groups)
            lev = stats.levene(*groups, center='median')
        omnibus.update(status='ok', statistic=float(test.statistic), p_value=float(test.pvalue),
                        levene_statistic=float(lev.statistic), levene_p=float(lev.pvalue),
                        df_between=2, df_within=sum(len(v) for v in groups)-3)
        tukey = pairwise_tukeyhsd(np.concatenate(groups),
                np.concatenate([np.repeat(g,len(v)) for g,v in zip(GROUPS,groups)]))
        for k,(i,j) in enumerate(combinations(range(len(tukey.groupsunique)), 2)):
            records.append(dict(base, kind='tukey', status='ok',
                group1=str(tukey.groupsunique[i]), group2=str(tukey.groupsunique[j]),
                mean_difference=float(tukey.meandiffs[k]),
                ci_lower=float(tukey.confint[k,0]), ci_upper=float(tukey.confint[k,1]),
                p_value=float(tukey.pvalues[k]), reject=bool(tukey.reject[k]),
                adjustment='Tukey within panel only'))
    return [omnibus] + records


def _stars(p):
    if not np.isfinite(p): return 'n/a'
    return '***' if p < .001 else '**' if p < .01 else '*' if p < .05 else 'n.s.'


def draw_raincloud(stage_table: pd.DataFrame, out: Path) -> pd.DataFrame:
    """Write Figure 3, caption, participant deltas and statistics to *out* directory."""
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    paired = participant_deltas(stage_table)
    records=[]
    for channel in CHANNELS:
        for task in TASKS:
            data=paired[paired.channel.eq(channel) & paired.task.eq(task)]
            records.extend(_panel_statistics(data,channel,task))
    result=pd.DataFrame(records)
    valid=result.kind.eq('omnibus') & result.p_value.notna()
    if valid.any():
        result.loc[valid,'p_holm']=multipletests(result.loc[valid,'p_value'],method='holm')[1]
    rng=np.random.default_rng(20261108)
    with plt.rc_context({'font.family':'DejaVu Sans', 'font.size':10,
                         'pdf.fonttype':42, 'savefig.bbox':None}):
        fig,axes=plt.subplots(2,3,figsize=(15,9))
        for r,channel in enumerate(CHANNELS):
            for c,task in enumerate(TASKS):
                ax=axes[r,c]
                data=paired[paired.channel.eq(channel)&paired.task.eq(task)]
                panel=result[result.channel.eq(channel)&result.task.eq(task)]
                omni=panel[panel.kind.eq('omnibus')].iloc[0]
                letter=chr(ord('A')+r*3+c)
                ax.set_title(f'({letter}) {channel.capitalize()} MAE change — {task.capitalize()} task',
                             fontsize=11,weight='bold',pad=12)
                if data.empty:
                    ax.text(.5,.5,'Not measured\n(no paired observations)',ha='center',va='center',
                            transform=ax.transAxes,color='#666666',fontsize=12)
                    ax.set_axis_off()
                    continue
                values=data.delta_mae.to_numpy(float)
                lo,hi=float(values.min()),float(values.max())
                span=max(hi-lo,abs(hi)*.1,.1 if channel=='strength' else 1.)
                for i,group in enumerate(GROUPS):
                    v=data.loc[data.group.eq(group),'delta_mae'].to_numpy(float)
                    if not len(v): continue
                    if len(v)>1 and np.std(v)>1e-12:
                        grid=np.linspace(v.min()-.08*span,v.max()+.08*span,200)
                        density=stats.gaussian_kde(v)(grid)
                        ax.fill_betweenx(grid,i-.07-.32*density/density.max(),i-.07,
                                         color=COLORS[group],alpha=.45,lw=.7)
                    else:
                        ax.plot([i-.36,i-.07],[v[0],v[0]],color=COLORS[group],lw=2)
                    box=ax.boxplot([v],positions=[i],widths=.13,patch_artist=True,
                        showfliers=False,whis=(0,100),manage_ticks=False,
                        boxprops={'facecolor':'white','edgecolor':COLORS[group],'linewidth':1.3},
                        medianprops={'color':'black','linewidth':1.7},
                        whiskerprops={'color':COLORS[group]},capprops={'color':COLORS[group]})
                    for artists in box.values():
                        for artist in artists: artist.set_zorder(4)
                    ax.scatter(i+.13+rng.uniform(-.045,.045,len(v)),v,s=26,
                        color=COLORS[group],edgecolor='white',linewidth=.5,zorder=5)
                pairs=panel[panel.kind.eq('tukey')]
                for level,(i,j) in enumerate(((0,1),(1,2),(0,2))):
                    match=(pairs[((pairs.group1==GROUPS[i])&(pairs.group2==GROUPS[j]))|
                                 ((pairs.group1==GROUPS[j])&(pairs.group2==GROUPS[i]))]
                           if not pairs.empty else pairs)
                    label=_stars(float(match.p_value.iloc[0])) if len(match) else 'n/a'
                    y=hi+span*(.15+.12*level)
                    ax.plot([i,i,j,j],[y-.025*span,y,y,y-.025*span],c='#333333',lw=.8,zorder=6)
                    ax.text((i+j)/2,y+.012*span,label,ha='center',va='bottom',fontsize=9)
                note=(f'ANOVA p(Holm) = {omni.p_holm:.3g}' if np.isfinite(omni.p_holm)
                      else 'ANOVA unavailable: insufficient variation/data')
                ax.text(.02,.98,note,ha='left',va='top',transform=ax.transAxes,fontsize=8)
                ax.axhline(0,color='#888888',lw=.8,ls='--',zorder=0)
                ax.set(xlim=(-.55,2.45),ylim=(lo-.18*span,hi+.67*span),
                       ylabel='Δ MAE (post-test − baseline)\n'+('strength units' if channel=='strength' else 'degrees'))
                ax.set_xticks(range(3),[f'{g.capitalize()}\nn={int(omni["n_"+g])}' for g in GROUPS])
                ax.spines[['top','right']].set_visible(False)
                ax.grid(axis='y',alpha=.18)
        fig.suptitle('Figure 3. Change in mean absolute error by training group',fontsize=16,weight='bold',y=.985)
        fig.text(.5,.018,'Negative change = lower MAE. Brackets: Tukey HSD within each panel; no cross-panel Tukey correction.',
                 ha='center',fontsize=10)
        fig.subplots_adjust(left=.075,right=.985,bottom=.115,top=.90,wspace=.30,hspace=.38)
        fig.savefig(out/'figure3_delta_mae_raincloud.png',dpi=300)
        fig.savefig(out/'figure3_delta_mae_raincloud.pdf')
        plt.close(fig)
    result.to_csv(out/'figure3_statistics.csv',index=False,encoding='utf-8-sig')
    paired.to_csv(out/'figure3_participant_deltas.csv',index=False,encoding='utf-8-sig')
    caption=f'''Figure 3. Change in observed mean absolute error (MAE).
Each point is one participant's post-test minus baseline MAE; negative values indicate lower absolute error.
Colors identify the independent training groups (both, strength, angle). Half densities use Gaussian KDE with
Scott bandwidth; boxes show median and interquartile range, whiskers show the observed minimum and maximum.
All participant points are shown with deterministic jitter (seed 20261108). Density is a visual summary,
not additional observations. Unmeasured combinations are shown explicitly and are never filled with zeros.
One-way ANOVA uses independent participant changes. Omnibus p values receive Holm correction across the
{int(valid.sum())} estimable measured panels. All three pairwise comparisons use Tukey HSD within each panel;
these Tukey families are not corrected across panels. Stars: * p<.05, ** p<.01, *** p<.001; n.s. otherwise;
n/a indicates an unavailable comparison. Levene (median-centered) diagnostics and exact statistics are in
figure3_statistics.csv. ANOVA/Tukey assume independent groups, approximately normal residuals and equal
variances; a non-significant Levene test does not establish those assumptions. Groups with insufficient
observations or no within-group variation are shown without manufactured test results.
Tukey mean_difference is group2 minus group1; its reported confidence limits are simultaneous 95% intervals
within that panel's family. Group descriptions use participant deltas, not pooled shot-level values.
Official method documentation:
https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.f_oneway.html
https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.levene.html
https://www.statsmodels.org/stable/generated/statsmodels.stats.multicomp.pairwise_tukeyhsd.html
'''
    (out/'figure3_caption.txt').write_text(caption,encoding='utf-8')
    return result
