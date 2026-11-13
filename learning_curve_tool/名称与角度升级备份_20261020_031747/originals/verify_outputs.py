"""Independently check exported component statistics against the source CSVs."""
import csv
import hashlib
import json
import math
from pathlib import Path
import statistics

root = Path(__file__).resolve().parent.parent
reports = json.loads((root/'learning_curves/batch_report.json').read_text(encoding='utf-8'))
assert reports and all(r['status']=='ok' for r in reports)
checked = 0
for report in reports:
    stats = json.loads((root/'learning_curves/statistics'/(report['id']+'.json')).read_text(encoding='utf-8'))
    count = 0
    for source in stats['sources']:
        path = Path(source['file'])
        assert hashlib.sha256(path.read_bytes()).hexdigest() == source['sha256']
        with path.open(encoding='utf-8-sig') as stream:
            rows = sorted(csv.DictReader(stream), key=lambda row:int(row['shot']))
        count += len(rows)
        stage, condition = path.stem.split('_')[2:4]
        for metric in source['metrics']:
            column = metric+'_value'
            values = [float(r[column]) for r in rows if r.get(column,'').strip()]
            assert len(values) == source['metrics'][metric]['scored']
            if stage in ('baseline','test') and values:
                actual = stats['comparisons'][condition][metric][stage+'_mean']
                assert math.isclose(actual,statistics.mean(values),rel_tol=1e-12,abs_tol=1e-12)
            if stage in ('training','test'):
                exported = stats['training_components'][metric]['blocks'] if stage=='training' else stats['comparisons'][condition][metric]['test_blocks']
                chunks = [rows[i:i+stats['block_size']] for i in range(0,len(rows),stats['block_size'])]
                assert len(exported) == len(chunks)
                for saved,chunk in zip(exported,chunks):
                    numbers = [float(r[column]) for r in chunk if r.get(column,'').strip()]
                    assert saved['n'] == len(numbers) and saved['rows'] == len(chunk)
                    assert (saved['start'],saved['end']) == (int(chunk[0]['shot']),int(chunk[-1]['shot']))
                    for name,expected in [('mean',statistics.mean(numbers) if numbers else None),('sd',statistics.stdev(numbers) if len(numbers)>1 else None)]:
                        assert saved[name] is None if expected is None else math.isclose(saved[name],expected,rel_tol=1e-12,abs_tol=1e-12)
            checked += 1
    assert count == stats['total_trials']
print(f'Independent verification passed: {len(reports)} participants, {checked} source metrics; source hashes, counts, block means and SD match.')
