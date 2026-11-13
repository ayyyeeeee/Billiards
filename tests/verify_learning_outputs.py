"""Independently check exported component statistics against the source CSVs."""
import argparse
import csv
import hashlib
import json
import math
from pathlib import Path
from common.paths import PARTICIPANT_ROOT, output_path
import statistics

parser = argparse.ArgumentParser()
parser.add_argument('--root', type=Path, default=PARTICIPANT_ROOT)
parser.add_argument('--output', type=Path)
args = parser.parse_args()
root = args.root
output = args.output or output_path(root, 'learning_curves')
reports = json.loads((output/'batch_report.json').read_text(encoding='utf-8'))
assert reports and all(r['status']=='ok' for r in reports)
checked = 0
for report in reports:
    stats = json.loads((output/'statistics'/(report['id']+'.json')).read_text(encoding='utf-8'))
    count = 0
    for source in stats['sources']:
        path = Path(source['file'])
        assert hashlib.sha256(path.read_bytes()).hexdigest() == source['sha256']
        with path.open(encoding='utf-8-sig') as stream:
            rows = sorted(csv.DictReader(stream), key=lambda row:int(row['shot']))
        count += len(rows)
        stage, condition = path.stem.split('_')[2:4]
        condition = 'both' if condition == 'regular' else condition
        for metric in source['metrics']:
            column = metric+'_value'
            def measurement(r):
                try:
                    v = float(r.get(column, ''))
                    if not math.isfinite(v): return None
                except (ValueError, TypeError): return None
                if stage == 'training':
                    if float(r.get(metric+'_outlier') or 0) == 1: return None
                else:
                    if r.get(metric+'_status', '').lower() in ('unresolved','invalid','not_requested'): return None
                    if r.get(metric+'_valid', '1') not in ('1','1.0','true','True'): return None
                return v
            values = [v for r in rows if (v := measurement(r)) is not None]
            assert len(values) == source['metrics'][metric]['scored']
            if stage == 'training':
                channel = stats['training_components'][metric]
                assert channel['robust_fit']['n_obs'] == len(values)
                exported = channel['blocks']
                chunks = [rows[i:i+stats['block_size']] for i in range(0,len(rows),stats['block_size'])]
                assert len(exported) == len(chunks)
                for saved,chunk in zip(exported,chunks):
                    numbers = [v for r in chunk if (v := measurement(r)) is not None]
                    assert saved['n'] == len(numbers) and saved['rows'] == len(chunk)
                    assert (saved['start'],saved['end']) == (int(chunk[0]['shot']),int(chunk[-1]['shot']))
                    for name,expected in [('mean',statistics.mean(numbers) if numbers else None),('sd',statistics.stdev(numbers) if len(numbers)>1 else None)]:
                        assert saved[name] is None if expected is None else math.isclose(saved[name],expected,rel_tol=1e-12,abs_tol=1e-12)
            else:
                phase = stats['comparisons'][condition][metric]['robust_phases'][stage]
                assert phase['n'] == len(values)
            checked += 1
    assert count == stats['total_trials']
print(f'Independent verification passed: {len(reports)} participants, {checked} source metrics; source hashes, counts, block means and SD match.')
