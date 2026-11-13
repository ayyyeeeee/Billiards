"""Source-reviewed span association; the established strength formula is unchanged.

The legacy scorer pairs departures within 0.40 s. A v3 departure may include
up to one second of preceding near-origin motion. When that time gate finds
no candidate, ownership of one confirmed v2 target event inside the same v3
attempt provides an unambiguous association. No raw observation is changed.
This adapter is activated explicitly by this batch's reviewed re-score only.
"""
from contextlib import contextmanager
import json
from pathlib import Path
import sys

import numpy as np

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT))
from MOLT4.experiment_system import rules_v3


def select_owned_candidate(records,span,times):
    prefix=span['prefix']
    strict=[r for r in records if abs(times[prefix+r['start_frame']]-times[span['start']])<=.40]
    if strict:
        return None
    owned=[r for r in records if r.get('valid') and r.get('bank_frame') is not None
        and span['start']<=prefix+r['start_frame']<=prefix+r['bank_frame']<=span['angle_search_end']]
    return owned[0] if len(owned)==1 else None


def map_component(row,prefix,times):
    fields={key:value for key,value in row.items() if key.startswith('strength_')}
    fields['strength_valid']=int(fields.get('strength_status')=='scored')
    for key in list(fields):
        if key.endswith('_frame') and fields[key] not in ('',None):
            fields[key]+=prefix
        elif key=='strength_crossing_s' and fields[key] not in ('',None):
            fields[key]+=float(times[prefix])
    fields['strength_needs_review']=1
    evidence=json.loads(row.get('collision_evidence','[]'))
    for item in evidence:
        for key in ('frame','before_frame','after_frame'):
            if key in item:
                item[key]+=prefix
        if 'time_s' in item:
            item['time_s']+=float(times[prefix])
    bank=row['bank_frame']
    metadata=dict(bank_frame=bank+prefix,bank_s=float(times[bank+prefix]),
        target_bank_valid=1,collision_evidence=json.dumps(evidence,separators=(',',':')))
    return fields,metadata


@contextmanager
def reviewed_association(events):
    legacy=rules_v3._strength_for_span
    def evaluate(data,fps,cal,cfg,angle_cap,model,span,times):
        original=legacy(data,fps,cal,cfg,angle_cap,model,span,times)
        if original[1]['target_bank_valid']:
            return original
        prefix,end=span['prefix'],span['end']
        sample=data[prefix:end+1].copy()
        if sample.shape[1]>4:
            sample[:,4]=times[prefix:end+1]*1000.
        records,_=rules_v3.analyze_v2(sample,fps,cal,'strength',cfg,angle_cap,model)
        row=select_owned_candidate(records,span,times)
        if row is None:
            return original
        events.append(dict(span_start=span['start'],span_end=end,span_prefix=prefix,
            v2_start_frame=prefix+row['start_frame'],bank_frame=prefix+row['bank_frame'],
            departure_time_difference_s=float(times[prefix+row['start_frame']]-times[span['start']]),
            strength_status=row['strength_status'],strength_value=row['strength_value'],
            method='Unique confirmed target event owned by this physical attempt; legacy time gate had no candidate.'))
        return map_component(row,prefix,times)
    rules_v3._strength_for_span=evaluate
    try:
        yield
    finally:
        rules_v3._strength_for_span=legacy


def source_check():
    here=Path(__file__).resolve().parent
    stem='23_05_test_both_030shots'
    report=json.loads((here/'analysis/23/audit'/(stem+'_report.json')).read_text())
    with np.load(here/'analysis/23/cache'/(stem+'_evidence.npz')) as z:
        data=z['data'].copy()
    cfg=report['config'];cal=report['calibration'];fps=report['fps']
    # These are the same frozen physical coefficients used by the native run.
    model=report['motion_model']
    args=(data,fps,cal,'both',cfg,report['constants']['angle_max_degrees'],model)
    before,_=rules_v3.analyze_v3(*args)
    events=[]
    with reviewed_association(events):
        after,_=rules_v3.analyze_v3(*args)
    assert len(events)==1 and events[0]['span_start']==2429,events
    assert sum(r['valid'] for r in before)==29
    assert sum(r['valid'] for r in after)==30
    assert len(before)==len(after)
    differences=[]
    for a,b in zip(before,after):
        changed=sorted(k for k in set(a)|set(b) if a.get(k)!=b.get(k))
        if a['start_frame']!=2429:
            assert set(changed)<= {'shot'},(a['start_frame'],changed)
        else:
            assert b['target_bank_valid']==1 and b['valid']==1
            assert all(a.get(k)==b.get(k) for k in a if k.startswith('angle_'))
        if changed:
            differences.append(dict(start_frame=a['start_frame'],fields=changed))
    # Selection rejects missing banks, candidates outside this attempt,
    # ambiguous ownership, and cases already handled by the original time gate.
    t=np.arange(100)/10.
    span=dict(prefix=0,start=10,end=60,angle_search_end=60)
    candidate=dict(start_frame=20,bank_frame=40,valid=1)
    assert select_owned_candidate([candidate],span,t)==candidate
    assert select_owned_candidate([candidate,dict(candidate,start_frame=21)],span,t) is None
    assert select_owned_candidate([dict(candidate,bank_frame=61)],span,t) is None
    assert select_owned_candidate([dict(candidate,valid=0)],span,t) is None
    assert select_owned_candidate([dict(candidate,start_frame=11)],span,t) is None
    assert select_owned_candidate([dict(candidate,bank_frame=None)],span,t) is None
    return dict(status='PASS',source=stem,before_valid=29,after_valid=30,
        unchanged_raw=True,association_events=events,differences=differences,
        existing_angle_fields_unchanged=True,selection_boundary_checks=6)


if __name__=='__main__':
    result=source_check()
    target=Path(__file__).resolve().parent/'association_review_2305'
    target.mkdir(exist_ok=True)
    (target/'adapter_verification.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf8')
    print(json.dumps(result,ensure_ascii=False))
