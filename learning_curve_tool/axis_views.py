"""Readable acquisition views without discarding high-valued observations."""
import numpy as np
from matplotlib.text import Text
from matplotlib.ticker import MaxNLocator, StrMethodFormatter


def crosses_box(start,end,box):
    """Whether a leader segment enters another label's padded rectangle."""
    lo,hi=0.,1.
    for a,b,minimum,maximum in zip(start,end,(box.x0,box.y0),(box.x1,box.y1)):
        delta=b-a
        if abs(delta)<1e-12:
            if a<minimum or a>maximum:return False
        else:
            first,last=sorted(((minimum-a)/delta,(maximum-a)/delta))
            lo=max(lo,first);hi=min(hi,last)
            if lo>hi:return False
    return True


def acquisition_view(ax, shots, values, means, points, color):
    """Separate a sparse high tail; protect all original block means.

    This changes display artists only. The source series and statistics retain
    every scored observation. Both visible regions use linear, original units.
    """
    shots=np.asarray(shots,dtype=float);values=np.asarray(values,dtype=float)
    finite=np.isfinite(values)&np.isfinite(shots)
    x,y=shots[finite],values[finite]
    summary=np.asarray(means,dtype=float);summary=summary[np.isfinite(summary)]
    full=dict(separated=False,main_ylim=list(map(float,ax.get_ylim())),high_values=[])
    if len(y)<20 or np.any(y<0):return full
    q1,q3=np.quantile(y,[.25,.75]);iqr=q3-q1
    if iqr<=np.finfo(float).eps*max(1.,abs(q3)):return full
    fence=float(q3+3*iqr)
    protected=float(summary.max()) if len(summary) else 0.
    proposed=max(fence,protected*1.05)
    if proposed<=0 or y.max()<2*proposed:return full
    high=y>proposed
    if not high.any() or high.sum()>.1*len(y):return full
    base=max(float(y[~high].max()),protected)
    upper=base*1.04
    high=y>upper
    if not high.any() or high.sum()>.1*len(y) or y.max()<2*upper:return full
    smallest=float(y[high].min());largest=float(y[high].max())
    high_bottom=(upper+smallest)/2
    if not upper<high_bottom<=smallest:return full

    position=ax.get_position().frozen()
    original_offsets=points.get_offsets().copy()
    original_title=ax.get_title(loc='left')
    original_locator=ax.yaxis.get_major_locator();original_formatter=ax.yaxis.get_major_formatter()
    original_gid=ax.get_gid();original_transforms=[];break_artists=[]
    ax.set_position([position.x0,position.y0,position.width,position.height*.65])
    high_ax=ax.figure.add_axes([position.x0,position.y0+position.height*.78,
        position.width,position.height*.22],sharex=ax,label=f'high_values_{len(ax.figure.axes)}')
    high_ax.set_gid('acquisition-high-values')
    ax.set_gid('acquisition-main-values')
    high_ax.set_title(ax.get_title(loc='left'),loc='left',fontsize=9,pad=5)
    ax.set_title('',loc='left')
    high_ax.text(1,1.05,f'High values (n = {int(high.sum())})',transform=high_ax.transAxes,
        ha='right',va='bottom',fontsize=7)
    # Legacy a–f lettering belongs above the complete two-region panel.
    for text in ax.texts:
        if text.get_position()[0]<0 and text.get_position()[1]>1:
            original_transforms.append((text,text.get_transform()))
            text.set_transform(high_ax.transAxes)
    points.set_offsets(np.column_stack((x[~high],y[~high])))
    high_ax.scatter(x[high],y[high],s=9,color=color,alpha=.65,linewidths=0,clip_on=False)
    ax.set_ylim(0,upper)
    ticks=MaxNLocator(nbins=4).tick_values(0,base)
    ax.set_yticks([*ticks[(ticks>=0)&(ticks<base-1e-9)],base])
    ax.set_ylim(0,upper)
    high_ax.set_ylim(high_bottom,largest+max(largest-smallest,largest*.1)*.04)
    high_ax.set_yticks(sorted(set([smallest,largest])))
    for view in (ax,high_ax):view.yaxis.set_major_formatter(StrMethodFormatter('{x:g}'))
    high_ax.tick_params(axis='x',which='both',bottom=False,labelbottom=False)
    high_ax.tick_params(axis='y',labelsize=7,length=3,width=.7)
    high_ax.spines['bottom'].set_visible(False)
    for view,ybreak in ((ax,1),(high_ax,0)):
        marks=view.plot([0],[ybreak],transform=view.transAxes,marker=[(-1,-.5),(1,.5)],
            markersize=6,linestyle='none',color='#555555',markeredgewidth=.8,clip_on=False)
        if view is ax:break_artists.extend(marks)

    # Place labels using rendered bounds, with thin leaders to unchanged points.
    ax.figure.canvas.draw();renderer=ax.figure.canvas.get_renderer();occupied=[];leaders=[]
    anchors=high_ax.transData.transform(np.column_stack((x[high],y[high])))
    entries=[]
    for index,(sx,sy) in enumerate(zip(x[high],y[high])):
        label=high_ax.annotate(f'{sy:g}',xy=(sx,sy),xytext=(4,4),textcoords='offset points',
            fontsize=6.5,ha='left',va='bottom',annotation_clip=False,
            arrowprops=dict(arrowstyle='-',color='#888888',lw=.45,shrinkA=1,shrinkB=2))
        candidates=[(4,4),(4,13),(16,5),(16,14),(4,-13),(-34,4),(-34,13),(-34,-13),(28,4),(28,13)]
        if sy==largest:candidates=[(4,-13),(-34,-13),(4,4)]+candidates
        label.update_positions(renderer)
        initial=Text.get_window_extent(label,renderer)
        grid=[]
        for px in np.arange(high_ax.bbox.x0+3,high_ax.bbox.x1-initial.width-2,initial.width+5):
            for py in np.arange(high_ax.bbox.y0+3,high_ax.bbox.y1-initial.height-2,initial.height+4):
                grid.append(((px-anchors[index,0])*72/ax.figure.dpi,(py-anchors[index,1])*72/ax.figure.dpi))
        candidates+=sorted(grid,key=lambda offset:offset[0]**2+offset[1]**2)
        placed=False
        for offset in candidates:
            label.set_position(offset)
            label.update_positions(renderer)
            box=Text.get_window_extent(label,renderer).expanded(1.03,1.05)
            center=((box.x0+box.x1)/2,(box.y0+box.y1)/2)
            if (box.x0>=high_ax.bbox.x0 and box.x1<=high_ax.bbox.x1 and
                box.y0>=high_ax.bbox.y0-3 and box.y1<=high_ax.bbox.y1+2 and
                not any(box.overlaps(other) for other in occupied) and
                not any(box.contains(*anchor) for anchor in anchors) and
                not any(crosses_box(anchors[index],center,other) for other in occupied) and
                not any(crosses_box(start,end,box) for start,end in leaders)):
                placed=True
                break
        if not placed:
            # Readability wins over an optional split. Restore the full view
            # rather than pushing high-value labels into another panel/title.
            high_ax.remove()
            for artist in break_artists:artist.remove()
            points.set_offsets(original_offsets);ax.set_position(position);ax.set_gid(original_gid)
            ax.yaxis.set_major_locator(original_locator);ax.yaxis.set_major_formatter(original_formatter)
            ax.set_ylim(full['main_ylim']);ax.set_title(original_title,loc='left')
            for text,transform in original_transforms:text.set_transform(transform)
            return dict(full,separation_declined='Insufficient nonoverlapping label space')
        occupied.append(box);leaders.append((anchors[index],center))
        entries.append(dict(shot=int(sx),value=float(sy)))
    return dict(separated=True,method='Q3 + 3 IQR; sparse tail and 2x scale gain; all block means protected',
        q1=float(q1),q3=float(q3),fence=fence,main_ylim=list(map(float,ax.get_ylim())),
        high_ylim=list(map(float,high_ax.get_ylim())),
        main_scored=int((~high).sum()),high_scored=int(high.sum()),
        high_values=entries,label_layout_verified=True,
        statistics='All scored observations; display split does not exclude data.')
