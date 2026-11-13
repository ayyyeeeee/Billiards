"""Component-aware six-panel figures; both-condition metrics remain on separate axes."""
import hashlib
import textwrap
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.ticker import MaxNLocator


def create_component_figure(p, size, core):
    if size < 1:
        raise ValueError('分块大小必须大于 0。')
    fig = plt.figure(figsize=(16, 13.5))
    grid = fig.add_gridspec(2, 3, left=.07, right=.98, top=.85, bottom=.30,
                            wspace=.34, hspace=.39)
    total = sum(len(s.shot) for s in p.series.values())
    fig.text(.07, .965, f'Participant {p.identifier}: acquisition and immediate post-test performance', fontsize=16, weight='bold')
    fig.text(.07, .94, f'Training condition: {p.training_condition}   |   {total} trials across {len(p.series)} recordings   |   Lower values indicate better performance', fontsize=10)
    legend = [Line2D([], [], marker='o', ls='none', color=core.GRAY, ms=4, label='Individual trial'),
              Line2D([], [], marker='o', color=core.BLUE, ms=4, lw=1.4, label=f'Block mean (up to {size} trials)'),
              Line2D([], [], marker='s', color='black', ms=4, ls='none', label='Mean ± SD (d–f)')]
    fig.legend(handles=legend, loc='upper center', bbox_to_anchor=(.53,.921), ncol=3, frameon=False, fontsize=9)

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
    training_axes = [axes_for(grid[0,col], letter, title, len(training_metrics)) for col,letter,title in
                     [(0,'a',f'Acquisition: {p.training_condition}'), (1,'b','Within-block variability'), (2,'c','Capped observations')]]
    training_stats = {}
    for i,(metric,series) in enumerate(training_metrics.items()):
        grouped = core.blocks(series,size)
        centers = [b['center'] for b in grouped]
        means = [nan(b['mean']) for b in grouped]
        sds = [nan(b['sd']) for b in grouped]
        a,b,c = [axes[i] for axes in training_axes]
        scored=int(np.isfinite(series.value).sum())
        for ax in (a,b,c):
            name=f'{metric.capitalize()} component' if len(training_metrics)>1 else metric.capitalize()
            ax.set_title(f'{name} (n = {scored}/{len(series.shot)})', loc='left', fontsize=9, pad=5)
        a.scatter(series.shot, series.value, s=8, color=core.GRAY, alpha=.42, linewidths=0)
        a.plot(centers,means,'o-',color=core.BLUE,lw=1.5,ms=3)
        a.set_ylabel(ylabel(series,metric))
        core.bounds(a,series.value)
        b.plot(centers,sds,'o-',color=core.BLUE,lw=1.4,ms=3)
        b.set_ylabel(f'SD\n({core.unit_label(series)})')
        core.bounds(b,sds)
        if not np.isfinite(sds).any():
            b.text(.5,.5,'SD unavailable (n < 2)',transform=b.transAxes,ha='center',fontsize=8)
        c.bar(centers,[nan(g['cap_pct']) for g in grouped],width=[max(.6,(g['end']-g['start']+1)*.7) for g in grouped],color='#8b9eaa')
        c.set(ylim=(0,130),ylabel='At cap (%)')
        c.set_yticks([0,50,100])
        known=int(series.cap_known.sum())
        text=f'{int(series.capped.sum())}/{known} scored trials' if known else 'Cap metadata unavailable'
        c.text(.98,.96,text,transform=c.transAxes,ha='right',va='top',fontsize=8)
        for ax in (a,b,c):
            first,last=series.shot[0],series.shot[-1]
            pad=max(1,(last-first)*.02)
            ax.set_xlim(first-pad,last+pad)
            ax.xaxis.set_major_locator(MaxNLocator(nbins=5,integer=True))
            ax.set_xlabel('Training trial (shot)',fontsize=8)
            ax.tick_params(labelsize=8)
        training_stats[metric]=dict(n=int(np.isfinite(series.value).sum()),rows=len(series.shot),
                                    units=list(series.units),blocks=[core.plain_block(g) for g in grouped])

    comparisons={}
    captions=[]
    if len(training_metrics)>1:
        captions.append(('a',f'Both-condition training, separated into strength and angle components on independent scales. Points are trial values; lines join means within the same successive {size}-trial blocks.'))
    else:
        captions.append(('a',f'{p.training_condition.capitalize()} training: points are trial values and lines join means within successive blocks of up to {size} trials. Incomplete final blocks are retained.'))
    captions.extend([
        ('b','Within-block sample SD for each training metric. Missing scores are excluded only from their own metric; block boundaries remain aligned. SD is unavailable when n < 2.'),
        ('c','Within-block percentage at each metric\'s own recorded cap, among scored trials with cap metadata. Strength and angle caps are handled separately.')])

    for column,(letter,condition) in enumerate(zip('def',core.CONDITIONS)):
        baseline=p.series.get(('baseline',condition)); test=p.series.get(('test',condition))
        present=baseline if baseline is not None else test
        names=list(metrics(present)) if present is not None else [condition]
        # Never compare a scalar legacy combined value with one new component.
        for source in (baseline,test):
            if source is not None and list(metrics(source))!=names:
                raise ValueError(f'{condition} baseline/test 指标结构不同。')
        role='trained condition' if condition==p.training_condition else 'transfer assessment'
        axes=axes_for(grid[1,column],letter,f'{condition.capitalize()}: {role}',len(names))
        result={}
        for ax,metric in zip(axes,names):
            bs=metrics(baseline)[metric] if baseline is not None else None
            ts=metrics(test)[metric] if test is not None else None
            if len(names)>1:
                ax.set_title(f'{metric.capitalize()} component',loc='left',fontsize=9,pad=5)
            bg=core.blocks(bs,len(bs.shot))[0] if bs is not None else None
            tg=core.blocks(ts,size) if ts is not None else []
            groups=([(0,bg,core.GRAY)] if bg else [])+[(j,g,core.BLUE) for j,g in enumerate(tg,1)]
            labels=[f'Baseline\nn = {bg["n"]}/{bg["rows"]}' if bg else 'Baseline\nnot available']
            labels.extend(f'{g["start"]}–{g["end"]}\nn = {g["n"]}/{g["rows"]}' for g in tg)
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
            ax.set_xticks(range(len(labels)),labels,fontsize=7)
            ax.set_xlim(-.5,len(labels)-.5)
            ax.set_xlabel('Baseline / test trial range',fontsize=8)
            if present is not None:
                ax.set_ylabel(ylabel(bs if bs is not None else ts,metric),fontsize=8)
            core.bounds(ax,extent)
            if baseline is None or test is None:
                ax.text(.5,.93,'Missing baseline or test',transform=ax.transAxes,ha='center',fontsize=8)
            bm=bg['mean'] if bg else None
            finite=ts.value[np.isfinite(ts.value)] if ts is not None else np.array([])
            tm=float(finite.mean()) if len(finite) else None
            result[metric]=dict(baseline_n=bg['n'] if bg else 0,baseline_rows=bg['rows'] if bg else 0,
                                test_n=len(finite),test_rows=len(ts.shot) if ts is not None else 0,
                                units=list((bs if bs is not None else ts).units) if present is not None else [],
                                baseline_mean=bm,test_mean=tm,
                                test_minus_baseline=tm-bm if bm is not None and tm is not None else None,
                                relative_reduction=(bm-tm)/bm if bm not in (None,0) and tm is not None else None,
                                test_blocks=[core.plain_block(g) for g in tg])
        comparisons[condition]=result
        if condition=='both' and len(names)>1:
            body='Both-condition baseline and immediate test, separated into strength and angle components from the same both-condition trials. Each component is compared with its own baseline; neither is pooled with single-condition trials.'
        else:
            body=f'{condition.capitalize()} baseline and immediate test under the {condition} condition. '+('This is the trained condition.' if condition==p.training_condition else 'This untrained condition assesses possible transfer.')
        body+=' n = scored/recorded trials; error bars are ±1 SD.'
        captions.append((letter,body))

    fig.add_artist(Line2D([.07,.98],[.248,.248],transform=fig.transFigure,color='#777777',lw=.6))
    fig.text(.07,.23,'Figure 1. Single-participant descriptive analysis.',fontsize=10,weight='bold')
    for i,(letter,body) in enumerate(captions):
        left=.07+(i//3)*.465; top=.208-(i%3)*.064
        fig.text(left,top,f'({letter})',fontsize=9,weight='bold',va='top')
        fig.text(left+.027,top,textwrap.fill(body,width=92),fontsize=8.5,va='top',linespacing=1.4)
    stats=dict(schema_version=2,participant=p.identifier,training_condition=p.training_condition,
               block_size=size,total_trials=total,training_components=training_stats,comparisons=comparisons,
               sources=[dict(file=str(s.path),n=len(s.shot),sha256=hashlib.sha256(s.path.read_bytes()).hexdigest(),
                             metrics={k:dict(scored=int(np.isfinite(v.value).sum()),missing=int((~np.isfinite(v.value)).sum()),units=list(v.units)) for k,v in metrics(s).items()}) for s in p.series.values()],
               warnings=p.warnings)
    return fig,stats
