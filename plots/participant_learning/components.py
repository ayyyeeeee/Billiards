"""Component-aware six-panel figures; both-condition metrics remain on separate axes."""
import sys
from pathlib import Path
from dataclasses import replace
import hashlib
import textwrap
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Patch
from matplotlib.ticker import MaxNLocator


def create_component_figure(p, size, core):
    from analysis.robust.student_t import fit_student_t
    from analysis.robust.censoring import censor_codes, censor_values
    if size < 1:
        raise ValueError('分块大小必须大于 0。')
    fig = plt.figure(figsize=(12, 8.5))
    grid = fig.add_gridspec(2, 1, left=.075, right=.98, top=.81, bottom=.09,
                            hspace=.52)
    lower_grid = grid[1].subgridspec(1, 3, wspace=.40)
    total = sum(len(s.shot) for s in p.series.values())
    has_signed = any(np.any(np.asarray(s.value)[np.isfinite(s.value)] < 0) for s in p.series.values())
    perf_text = 'Values closer to zero indicate better performance' if has_signed else 'Lower values indicate better performance'
    fig.text(.07, .965, f'Participant {p.identifier}: acquisition and post-test', fontsize=14, weight='bold')
    fig.text(.07, .94, f'Training: {p.training_condition} | {total} recorded trials | {perf_text}', fontsize=9)
    legend = [Line2D([], [], marker='o', ls='none', color=core.GRAY, ms=4, label='Individual trial'),
              Line2D([], [], marker='o', color=core.BLUE, ms=4, lw=1.4, label='Student-t spline mean (nu=5)'),
              Line2D([], [], marker='s', color='black', ms=4, ls='none', label='Student-t mean ± SD (d–f)'),
              Line2D([], [], marker='|', ls='none', color='#d62728', ms=7, label='Excluded trial (rug below axis)'),
              Patch(facecolor=core.BLUE, alpha=.10, label='Shading: model mean ± trial SD (not 95% CI)')]
    fig.legend(handles=legend, loc='upper center', bbox_to_anchor=(.53,.91), ncol=3, frameon=False, fontsize=8.5, columnspacing=2.0)

    def axes_for(slot, letter, title, count):
        position = slot.get_position(fig)
        fig.text(position.x0-.028, position.y1+.022, letter, fontsize=15, weight='bold')
        fig.text(position.x0, position.y1+.022, title, fontsize=11)
        subgrid = slot.subgridspec(count, 1, hspace=.67 if count > 1 else 0)
        return [fig.add_subplot(subgrid[i]) for i in range(count)]

    def metrics(series):
        return series.components or {series.metric or series.condition: series}

    def nan(value):
        return np.nan if value is None else value

    def ylabel(series, metric):
        label = 'Angular' if metric == 'angle' else metric.capitalize()
        return f'{label} error\n({core.unit_label(series)})'

    train = p.series['training', p.training_condition]
    training_metrics = metrics(train)
    training_sources = {metric: pd.read_csv(sr.path).sort_values('shot') for metric,sr in training_metrics.items()}
    show_censor = any(np.any((censor_codes(training_sources[metric], metric) != 0) & np.isfinite(sr.value))
                      for metric,sr in training_metrics.items())
    upper_grid = grid[0].subgridspec(1, 3 if show_censor else 2, wspace=.40)
    training_axes = [axes_for(upper_grid[col], letter, title, len(training_metrics)) for col,letter,title in
                     [(0,'a',f'Acquisition: {p.training_condition}'), (1,'b','Modelled trial variance')]]
    training_axes.append(axes_for(upper_grid[2], 'c', 'Censored observations', len(training_metrics))
                         if show_censor else [None] * len(training_metrics))
    training_stats = {}
    for i,(metric,series) in enumerate(training_metrics.items()):
        grouped = core.blocks(series,size)
        centers = [b['center'] for b in grouped]
        means = [nan(b['mean']) for b in grouped]
        sds = [nan(b['sd']) for b in grouped]
        a,b,c = [axes[i] for axes in training_axes]
        scored=int(np.isfinite(series.value).sum())
        for ax in (a,b,c):
            if ax is None:
                continue
            name=f'{metric.capitalize()} component' if len(training_metrics)>1 else metric.capitalize()
            ax.set_title(f'{name} (n = {scored}/{len(series.shot)})', loc='left', fontsize=9, pad=5)
        points=a.scatter(series.shot, series.value, s=8, color=core.GRAY, alpha=.42, linewidths=0)
        a.axhline(0, color='#b8b8b8', lw=.7, ls='--', zorder=1)
        if hasattr(series, 'outlier') and series.outlier.any():
            outlier_shots = series.shot[series.outlier]
            a.scatter(outlier_shots, np.full(len(outlier_shots), -.018), transform=a.get_xaxis_transform(),
                      marker='|', s=35, color='#d62728', linewidths=1, clip_on=False, zorder=6, gid='excluded-trial-rug')
        source = pd.read_csv(series.path).sort_values('shot')
        censored = censor_codes(source, metric)
        fit_values = censor_values(source, metric)
        fit_values[~np.isfinite(series.value)] = np.nan
        fit = fit_student_t(series.shot, fit_values, censor=censored)
        grid_x = np.linspace(fit.xmin, fit.xmax, 200) if fit.success else np.array([])
        predicted = fit.predict(grid_x) if fit.success else {k: np.array([]) for k in ('mean','sd','variance')}
        if not fit.success:
            for target in (a,b):
                target.text(.03,.95,'Fit unavailable: '+fit.message,transform=target.transAxes,
                            fontsize=7,va='top',wrap=True)

        a.plot(grid_x, predicted['mean'], color=core.BLUE, lw=1.8)
        # SD describes trial dispersion, not confidence in the estimated mean.
        a.fill_between(grid_x, predicted['mean']-predicted['sd'],
                       predicted['mean']+predicted['sd'], color=core.BLUE, alpha=.10)

        a.set_ylabel(ylabel(series,metric))
        core.bounds(a,series.value)
        b.plot(grid_x, predicted['variance'], color=core.BLUE, lw=1.8)
        b.set_ylabel(f'Variance\n({core.unit_label(series)})²')
        core.bounds(b,predicted['variance'])
        if not np.isfinite(sds).any():
            b.text(.5,.5,'SD unavailable (n < 2)',transform=b.transAxes,ha='center',fontsize=8)
        known=int(np.isfinite(series.value).sum())
        confirmed = (censored != 0) & np.isfinite(series.value)
        if c is not None:
            percentages = []
            for start in range(0, len(series.shot), size):
                valid = np.isfinite(series.value[start:start+size])
                percentages.append(100 * confirmed[start:start+size].sum()/valid.sum() if valid.any() else np.nan)
            c.bar(centers, percentages, width=[max(.6,(g['end']-g['start']+1)*.7) for g in grouped],color='#8b9eaa')
            c.set(ylim=(0,105),ylabel='Censored (%)')
            c.set_yticks([0,50,100])
            c.text(.98,.96,f'{int(confirmed.sum())}/{known} trials',transform=c.transAxes,ha='right',va='top',fontsize=8)
        for ax in (a,b,c):
            if ax is None:
                continue
            first,last=series.shot[0],series.shot[-1]
            pad=max(1,(last-first)*.02)
            ax.set_xlim(first-pad,last+pad)
            ax.xaxis.set_major_locator(MaxNLocator(nbins=5,integer=True))
            ax.set_xlabel('Training trial (shot)' if i == len(training_metrics)-1 else '',fontsize=8)
            ax.tick_params(labelsize=8)
        display=dict(separated=False, mode='linear')
        finite_vals = np.abs(series.value[np.isfinite(series.value)])
        if len(finite_vals) and finite_vals.max() > 8 * max(1., np.percentile(finite_vals, 75)):
            threshold = max(1., 2*np.percentile(finite_vals, 75))
            a.set_yscale('symlog', linthresh=threshold)
            a.set_ylabel(ylabel(series,metric)+'; symlog')
            display.update(mode='symlog', linthresh=float(threshold))

        outliers = [int(s) for s in series.shot[series.outlier]] if hasattr(series, 'outlier') and series.outlier.any() else []
        training_stats[metric]=dict(n=int(np.isfinite(series.value).sum()),rows=len(series.shot),
                                    outlier_count=len(outliers),outliers=outliers,
                                    units=list(series.units),blocks=[core.plain_block(g) for g in grouped],
                                    acquisition_display=display,
                                    robust_fit=dict(method='Student-t location-scale spline', nu=fit.nu,
                                      success=fit.success, message=fit.message, n_censored=fit.n_censored,
                                      shot=grid_x.tolist(), mean=predicted['mean'].tolist(),
                                      variance=predicted['variance'].tolist(),
                                      historical_flags_retained=False, n_obs=fit.n_obs))

    comparisons={}
    captions=[]
    outlier_note = ' Red rug marks below the horizontal axis identify excluded outlier=1 trials; they have no error-value coordinate and never enter statistics or fitting.'
    if len(training_metrics)>1:
        captions.append(('a',f'Both-condition training, separated into strength and angle components on independent scales. Points are trial values; the line is a Student-t spline mean (nu=5). Shading is model trial SD, not a confidence interval.{outlier_note}'))
    else:
        captions.append(('a',f'{p.training_condition.capitalize()} training: points are trial values and the line is a Student-t spline mean (nu=5). Shading is model trial SD, not a confidence interval.{outlier_note}'))
    if any(s['acquisition_display']['separated'] for s in training_stats.values()):
        letter,body=captions[0]
        captions[0]=(letter,body+' High values are labeled in a separate upper region (broken y-axis); all trials remain in statistics.')
    captions.extend([
        ('b','Student-t model variance: scale squared times nu/(nu-2). Mean and log-scale use separate smooth functions of trial. Training outlier=1 and missing measurements are excluded independently per component; remaining finite training values are included.'),
        ('c','Recorded cap rate (descriptive). True censor likelihood requires both a boundary value and uncapped evidence beyond that boundary; censored predictions are not exact measurements.')])

    for column,(letter,condition) in enumerate(zip('def',core.CONDITIONS)):
        baseline=p.series.get(('baseline',condition)); test=p.series.get(('test',condition))
        present=baseline if baseline is not None else test
        names=list(metrics(present)) if present is not None else [condition]
        # Never compare a scalar legacy combined value with one new component.
        for source in (baseline,test):
            if source is not None and list(metrics(source))!=names:
                raise ValueError(f'{condition} baseline/test 指标结构不同。')
        role='trained condition' if condition==p.training_condition else 'transfer assessment'
        axes=axes_for(lower_grid[column],letter,f'{condition.capitalize()}: {role}',len(names))
        result={}
        for ax,metric in zip(axes,names):
            bs=metrics(baseline)[metric] if baseline is not None else None
            ts=metrics(test)[metric] if test is not None else None
            if len(names)>1:
                ax.set_title(f'{metric.capitalize()} component',loc='left',fontsize=9,pad=5)
            bg=core.blocks(bs,len(bs.shot))[0] if bs is not None else None
            tg=core.blocks(ts,len(ts.shot)) if ts is not None else []
            phase_fits = {}
            for phase, sr, group in [('baseline', bs, bg), ('test', ts, tg[0] if tg else None)]:
                if sr is None or group is None:
                    continue
                data = pd.read_csv(sr.path).sort_values('shot')
                values = censor_values(data, metric)
                values[~np.isfinite(sr.value)] = np.nan
                model = fit_student_t(sr.shot, values, censor=censor_codes(data, metric),
                                      df_mean=1, df_scale=1)
                group['raw_mean'], group['raw_sd'] = group['mean'], group['sd']
                if model.success:
                    pred = model.predict([float(sr.shot[0])])
                    group['mean'], group['sd'] = float(pred['mean'][0]), float(pred['sd'][0])
                else:
                    group['mean'], group['sd'] = None, None
                phase_fits[phase] = dict(success=model.success, reason=model.message,
                                        mean=group['mean'], sd=group['sd'], n=model.n_obs,
                                        n_censored=model.n_censored)
            groups=([(0,bg,core.GRAY)] if bg else [])+[(j,g,core.BLUE) for j,g in enumerate(tg,1)]
            labels=[f'Baseline\nn = {bg["n"]}/{bg["rows"]}' if bg else 'Baseline\nnot available']
            labels.extend(f'Immediate test\nn = {g["n"]}/{g["rows"]}' for g in tg)
            if ts is None:
                labels.append('Test\nnot available')
            extent=[]
            for j,g,color in groups:
                vals=g['values']; n=g['n']
                offsets=np.linspace(-.16,.16,n) if n>1 else np.zeros(n)
                ax.scatter(j+offsets,vals,s=12,color=color,alpha=.48,linewidths=0)
                if g['mean'] is not None:
                    ax.plot(j,g['mean'],'s',color='black',ms=4,zorder=5)
                    extent.extend(vals)
                    if g['sd'] is not None:
                        ax.errorbar(j,g['mean'],yerr=g['sd'],fmt='none',color='black',capsize=3,lw=1,zorder=4)
                        extent.extend([g['mean']-g['sd'],g['mean']+g['sd']])
            ax.plot(range(1,len(tg)+1),[nan(g['mean']) for g in tg],color=core.BLUE,lw=1.2)
            ax.axvline(.5,color='#b8b8b8',lw=.7,ls=':')
            ax.axhline(0, color='#b8b8b8', lw=.7, ls='--', zorder=1)
            ax.set_xticks(range(len(labels)),labels,fontsize=7)
            ax.set_xlim(-.5,len(labels)-.5)
            ax.set_xlabel('Baseline / test trial range' if metric == names[-1] else '',fontsize=8)
            if present is not None:
                ax.set_ylabel(ylabel(bs if bs is not None else ts,metric),fontsize=8)
            core.bounds(ax,extent)
            if baseline is None or test is None:
                ax.text(.5,.93,'Missing baseline or test',transform=ax.transAxes,ha='center',fontsize=8)
            bm=bg['mean'] if bg else None
            finite=ts.value[np.isfinite(ts.value)] if ts is not None else np.array([])
            tm=phase_fits.get('test', {}).get('mean')
            result[metric]=dict(baseline_n=bg['n'] if bg else 0,baseline_rows=bg['rows'] if bg else 0,
                                test_n=len(finite),test_rows=len(ts.shot) if ts is not None else 0,
                                units=list((bs if bs is not None else ts).units) if present is not None else [],
                                baseline_mean=bm,test_mean=tm,
                                baseline_raw_mean=bg.get('raw_mean') if bg else None,
                                test_minus_baseline=tm-bm if bm is not None and tm is not None else None,
                                relative_reduction=(bm-tm)/bm if bm not in (None,0) and tm is not None else None,
                                robust_phases=phase_fits, test_blocks=[core.plain_block(g) for g in tg])
        comparisons[condition]=result
        if condition=='both' and len(names)>1:
            body='Both-condition baseline and immediate test, separated into strength and angle components from the same both-condition trials. Each component is compared with its own baseline; neither is pooled with single-condition trials.'
        else:
            body=f'{condition.capitalize()} baseline and immediate test under the {condition} condition. '+('This is the trained condition.' if condition==p.training_condition else 'This untrained condition assesses possible transfer.')
        body+=' Full-stage Student-t mean ± model SD (nu=5); n = valid/recorded. No estimate shown when data are insufficient. Error bars are not confidence intervals.'
        captions.append((letter,body))

    if not show_censor:
        captions[2] = ('c', 'Censor panel omitted because no included training observations are censored; panels a and b use the full row.')
    stats=dict(schema_version=4, captions=captions, censor_panel_visible=show_censor,participant=p.identifier,training_condition=p.training_condition,
               block_size=size,total_trials=total,training_components=training_stats,comparisons=comparisons,
               sources=[dict(file=str(s.path),n=len(s.shot),sha256=hashlib.sha256(s.path.read_bytes()).hexdigest(),
                             metrics={k:dict(scored=int(np.isfinite(v.value).sum()),missing=int((~np.isfinite(v.value)).sum()),units=list(v.units)) for k,v in metrics(s).items()}) for s in p.series.values()],
               warnings=p.warnings)
    return fig,stats
