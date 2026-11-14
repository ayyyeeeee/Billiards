"""Regression checks for variable trial counts, conditions and data handling."""
import csv
import json
from pathlib import Path
import unittest
import uuid
from unittest.mock import patch

import learning_curves as lc


class LearningCurveTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parent / '.test_runs' / uuid.uuid4().hex
        cls.root.mkdir(parents=True)

    def fixture(self, identifier, training='angle', count=141, baseline=11, test=23, missing_max=False, gaps=False):
        folder = self.root / identifier / 'MOLT4_results' / 'csv'
        folder.mkdir(parents=True, exist_ok=True)
        sequence = 0
        for stage, conditions in [('baseline', lc.CONDITIONS), ('training', (training,)), ('test', lc.CONDITIONS)]:
            for condition in conditions:
                sequence += 1
                n = {'baseline': baseline, 'training': count, 'test': test}[stage]
                path = folder / f'{identifier}_{sequence:02}_{stage}_{condition}_999shots.csv'
                with path.open('w', newline='', encoding='utf-8') as stream:
                    writer = csv.writer(stream)
                    writer.writerow(['shot','value','unit','maximum','needs_review'])
                    for i in range(n):
                        writer.writerow([i*2+1 if gaps else i+1, '13.05' if condition=='angle' else '0.312580', 'degree' if condition=='angle' else 'origin_to_strip', '' if missing_max else ('13.05260856' if condition=='angle' else '0.312579616'), 1])
        return lc.load_participant(self.root, identifier)

    def test_variable_counts_and_singleton_tail(self):
        p = self.fixture('91', count=141, baseline=11, test=23)
        groups = lc.blocks(p.series['training','angle'], 10)
        self.assertEqual([g['n'] for g in groups], [10]*14+[1])
        self.assertIsNone(groups[-1]['sd'])
        self.assertEqual(groups[-1]['mean'], 13.05)
        figure, stats = lc.create_figure(p)
        self.assertEqual(stats['training_condition'], 'angle')
        self.assertEqual(stats['total_trials'], 243)
        self.assertEqual([b['n'] for b in stats['comparisons']['regular']['test_blocks']], [10,10,3])
        self.assertEqual(stats['comparisons']['regular']['baseline_n'], 11)
        texts = ' '.join(t.get_text() for t in figure.findobj(lc.matplotlib.text.Text))
        self.assertIn('Angle: trained condition', texts)
        self.assertIn('Regular: transfer assessment', texts)
        self.assertIn('Final block: n = 1', texts)
        self.assertNotIn('flagged', texts.lower())
        self.assertNotIn('All recorded values', texts)
        lc.plt.close(figure)

    def test_short_strength_with_missing_cap_and_gaps(self):
        p = self.fixture('92', training='strength', count=7, baseline=9, test=31, missing_max=True, gaps=True)
        groups = lc.blocks(p.series['training','strength'], 10)
        self.assertEqual(groups[0]['n'], 7)
        self.assertEqual((groups[0]['start'], groups[0]['end']), (1,13))
        self.assertIsNone(groups[0]['cap_pct'])
        figure, stats = lc.create_figure(p)
        self.assertEqual([b['n'] for b in stats['comparisons']['angle']['test_blocks']], [10,10,10,1])
        self.assertTrue(any('间隔' in warning for warning in p.warnings))
        figure.savefig(self.root/'variable_counts_preview.png', dpi=120)
        lc.plt.close(figure)

    def test_one_trial_and_output_names(self):
        self.fixture('93', training='regular', count=1, baseline=1, test=1)
        stats = lc.process_one(self.root, '93', self.root/'output')
        self.assertTrue((self.root/'output/93.png').is_file())
        self.assertTrue((self.root/'output/93.svg').is_file())
        encoded = json.loads((self.root/'output/statistics/93.json').read_text(encoding='utf-8'))
        self.assertIsNone(encoded['training_blocks'][0]['sd'])
        self.assertEqual(stats['total_trials'], 7)

    def test_duplicate_shot_rejected(self):
        p = self.root / 'duplicate.csv'
        p.write_text('shot,value\n1,0.1\n1,0.2\n', encoding='utf-8')
        with self.assertRaisesRegex(ValueError, '重复'):
            lc.load_series(p, 'training', 'regular')

    def test_nan_rejected(self):
        p = self.root / 'nan.csv'
        p.write_text('shot,value\n1,nan\n', encoding='utf-8')
        with self.assertRaises(ValueError):
            lc.load_series(p, 'training', 'regular')

    def test_rounded_cap_and_unknown_denominator(self):
        p = self.root / 'caps.csv'
        p.write_text('shot,value,maximum\n1,13.05,13.05260856\n2,10.00,\n3,1.00,13.05260856\n', encoding='utf-8')
        series = lc.load_series(p,'training','angle')
        block = lc.blocks(series, 10)[0]
        self.assertEqual(block['capped'], 1)
        self.assertEqual(block['cap_known'], 2)
        self.assertEqual(block['cap_pct'], 50)

    def test_ids(self):
        self.assertEqual(lc.parse_ids('1,02，04-05 1'), ['01','02','04','05'])
        with self.assertRaises(ValueError):
            lc.parse_ids('../01')

    def split_fixture(self, identifier='81', training='regular'):
        self.fixture(identifier, training=training, count=21, baseline=3, test=11)
        folder=self.root/identifier/'MOLT4_results'/'csv'
        for path in folder.glob('*.csv'):
            with path.open(encoding='utf-8') as stream:
                rows=list(csv.DictReader(stream))
            condition=path.stem.split('_')[3]
            fields=list(rows[0])+['strength_value','angle_value','strength_maximum','angle_maximum','strength_status','angle_status']
            for i,row in enumerate(rows):
                row.update(strength_value=str((i+1)/10),angle_value=str(i+2),strength_maximum='5.0',angle_maximum='30.0',strength_status='scored',angle_status='scored')
                if condition=='regular':
                    row['value']=''
                    row['unit']='strength:origin_to_strip;angle:degree'
                    if i in (0,10):
                        row['strength_value']=''
                        row['strength_status']='unresolved'
                else:
                    row['value']=row[condition+'_value']
                    other='angle' if condition=='strength' else 'strength'
                    row[other+'_value']=''
                    row[other+'_status']='not_requested'
            with path.open('w',newline='',encoding='utf-8') as stream:
                writer=csv.DictWriter(stream,fieldnames=fields)
                writer.writeheader();writer.writerows(rows)
        return lc.load_participant(self.root,identifier)

    def test_split_components_keep_aligned_blocks(self):
        p=self.split_fixture()
        regular=p.series['training','regular']
        strength=lc.blocks(regular.components['strength'],10)
        angle=lc.blocks(regular.components['angle'],10)
        self.assertEqual([b['n'] for b in strength],[9,9,1])
        self.assertEqual([b['n'] for b in angle],[10,10,1])
        self.assertEqual([(b['start'],b['end'],b['center']) for b in strength],[(b['start'],b['end'],b['center']) for b in angle])
        self.assertAlmostEqual(strength[0]['mean'],.6)
        self.assertEqual(regular.components['angle'].units,('degree',))
        self.assertEqual(regular.components['strength'].units,('origin_to_strip',))
        fig,stats=lc.create_figure(p)
        self.assertEqual(len(fig.axes),10)
        self.assertEqual(stats['total_trials'],63)
        self.assertEqual(set(stats['comparisons']['regular']),{'strength','angle'})
        self.assertEqual(stats['training_components']['strength']['n'],19)
        self.assertEqual(stats['training_components']['angle']['n'],21)
        self.assertAlmostEqual(stats['comparisons']['regular']['strength']['baseline_mean'],.25)
        texts=' '.join(t.get_text() for t in fig.findobj(lc.matplotlib.text.Text))
        self.assertNotIn('flagged',texts.lower())
        self.assertFalse(any('\u4e00'<=c<='\u9fff' for c in texts))
        lc.plt.close(fig)

    def test_split_regular_with_single_condition_training(self):
        p=self.split_fixture('82',training='angle')
        fig,stats=lc.create_figure(p)
        self.assertEqual(len(fig.axes),7)
        self.assertEqual(set(stats['training_components']),{'angle'})
        self.assertEqual(set(stats['comparisons']['regular']),{'strength','angle'})
        lc.plt.close(fig)
        lc.process_one(self.root,'82',self.root/'new_schema_output')
        saved=json.loads((self.root/'new_schema_output/statistics/82.json').read_text(encoding='utf-8'))
        self.assertEqual(saved['schema_version'],2)

    def test_all_missing_component_block_is_not_zero(self):
        p=self.split_fixture('83')
        s=p.series['training','regular'].components['strength']
        s.value[:10]=float('nan')
        s.cap_known[:10]=False
        first=lc.blocks(s,10)[0]
        self.assertEqual(first['rows'],10)
        self.assertEqual(first['n'],0)
        self.assertIsNone(first['mean'])
        self.assertIsNone(first['sd'])
        fig,stats=lc.create_figure(p)
        json.dumps(stats,allow_nan=False)
        lc.plt.close(fig)

    def test_partial_regular_schema_rejected(self):
        path=self.root/'partial_regular.csv'
        path.write_text('shot,value,strength_value\n1,,0.2\n',encoding='utf-8')
        with self.assertRaisesRegex(ValueError,'双分量'):
            lc.load_series(path,'training','regular')

    def test_gui_generates_by_id(self):
        import tkinter as tk
        from tkinter import ttk
        self.split_fixture('94', training='strength')
        original_mainloop = tk.Tk.mainloop
        failures = []
        finished = []

        def descendants(widget):
            for child in widget.winfo_children():
                yield child
                yield from descendants(child)

        def mainloop(window):
            window.withdraw()
            widgets = list(descendants(window))
            entries = [w for w in widgets if isinstance(w, ttk.Entry)]
            entries[1].insert(0, '94')
            button = next(w for w in widgets if isinstance(w, ttk.Button) and w.cget('text') == '绘制输入编号')

            def check():
                if str(button.cget('state')) == 'normal':
                    labels = [w.cget('text') for w in widgets if isinstance(w, ttk.Label)]
                    finished.extend(labels)
                    window.destroy()
                else:
                    window.after(100, check)

            def invoke():
                try:
                    button.invoke()
                    window.after(100, check)
                except Exception as exc:
                    failures.append(str(exc))
                    window.destroy()

            def timeout():
                failures.append('GUI generation timed out')
                window.destroy()

            window.after(50, invoke)
            window.after(15000, timeout)
            original_mainloop(window)

        with patch.object(lc, 'DEFAULT_ROOT', self.root), patch.object(tk.Tk, 'mainloop', mainloop):
            lc.launch_gui()
        self.assertEqual(failures, [])
        self.assertTrue((self.root/'learning_curves/94.png').is_file())
        self.assertTrue(any('成功 1 位' in text for text in finished))


if __name__ == '__main__':
    unittest.main()
