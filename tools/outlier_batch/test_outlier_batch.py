import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np
import pandas as pd

import outlier_batch as batch


class ReviewedDataTests(unittest.TestCase):
    def test_recursive_discovery_with_filename_prefixes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            folder = root / '01/processed_csv'
            (folder / 'csv').mkdir(parents=True)
            names = ['01_04_training_both_140shots.csv',
                     'csv/01_04_training_angle_140shots.csv',
                     'csv/01_04_training_strength_140shots.CSV']
            for name in names + ['csv/01_baseline_both_010shots.csv']:
                (folder / name).touch()
            with patch.object(batch, 'EXPERIMENT_ROOT', root):
                self.assertEqual(set(batch.find_training_csvs('01')),
                                 {folder / name for name in names})

    def test_blank_input_and_eof_default_to_all(self):
        with tempfile.TemporaryDirectory() as tmp:
            for input_options in ({'return_value': ''}, {'side_effect': EOFError}):
                with patch.object(batch, 'EXPERIMENT_ROOT', Path(tmp)), \
                     patch.object(batch.sys, 'argv', ['outlier_batch.py']), \
                     patch('builtins.input', **input_options), \
                     patch('builtins.print'), \
                     patch.object(batch, '_add_file_handler'), \
                     patch.object(batch, 'process_participant', return_value=True) as process:
                    batch.main()
                self.assertEqual([c.args[0] for c in process.call_args_list],
                                 [f'{i:02d}' for i in range(1, 31)])

    def data(self):
        rng = np.random.default_rng(42)
        values = rng.normal(0, 0.1, 140)
        values[70] = 10
        df = pd.DataFrame({'shot': range(1, 141), 'score_complete': 1,
                           'needs_review': 1})
        for ch in ('angle', 'strength'):
            df[ch + '_value'] = values
            df[ch + '_status'] = 'scored'
            df[ch + '_valid'] = 1
            df[ch + '_needs_review'] = 1
        return df

    def test_review_flags_do_not_change_fit(self):
        reviewed = self.data()
        cleared = reviewed.copy()
        for col in ('needs_review', 'angle_needs_review', 'strength_needs_review'):
            cleared[col] = 0
        for ch in ('angle', 'strength'):
            a = batch._fit_channel(reviewed, ch)
            b = batch._fit_channel(cleared, ch)
            self.assertEqual(a.n_eligible, 140)
            pd.testing.assert_series_equal(a.outlier_mask, b.outlier_mask)
            self.assertEqual(a.outlier_mask.iloc[70], 1)
            generic = reviewed.drop(columns=[ch + '_needs_review'])
            self.assertTrue(batch.build_eligibility_mask(generic, ch).all())

    def test_untested_rows_and_skipped_channels_are_zero(self):
        df = self.data()
        df.loc[0, 'strength_status'] = 'not_requested'
        df.loc[1, 'strength_value'] = np.nan
        df.loc[2, 'score_complete'] = 0
        df.loc[3, 'strength_valid'] = 0
        strength = batch._fit_channel(df, 'strength')
        self.assertEqual(strength.outlier_mask.iloc[:4].tolist(), [0]*4)
        df['angle_status'] = 'not_requested'
        angle = batch._fit_channel(df, 'angle')
        output = batch.insert_outlier_columns(df, angle, strength)
        self.assertEqual(set(output.angle_outlier), {0})
        self.assertTrue(output.strength_outlier.isin([0, 1]).all())
        small = self.data().iloc[:7]
        result = batch.insert_outlier_columns(small, batch._fit_channel(small, 'angle'),
                                              batch._fit_channel(small, 'strength'))
        self.assertTrue((result[['angle_outlier', 'strength_outlier']] == 0).all().all())

    def test_csv_preservation_and_plot_legend(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / '01_training_both_140shots.csv'
            df = self.data().astype(str)
            df.loc[0, 'angle_value'] = '0.00000'
            df['note'] = ''
            df.to_csv(source, index=False, encoding='utf-8-sig')
            before = source.read_bytes()
            legends = []
            def capture(fig, *args, **kwargs):
                legends.extend(fig.axes[0].get_legend_handles_labels()[1])
            with patch.object(batch, 'EXPERIMENT_ROOT', root), patch.object(batch.plt.Figure, 'savefig', capture):
                batch.process_csv(source, '01')
            output = next((root / '01/outlier_results/labeled_csv').glob('*.csv'))
            self.assertTrue(output.read_bytes().startswith(b'\xef\xbb\xbf'))
            result = pd.read_csv(output, dtype=str, keep_default_na=False)
            pd.testing.assert_frame_equal(df, result[df.columns])
            self.assertEqual(before, source.read_bytes())
            for ch in ('angle', 'strength'):
                cols = result.columns.tolist()
                self.assertEqual(cols.index(ch+'_outlier'), cols.index(ch+'_value')+1)
                self.assertTrue(set(result[ch+'_outlier']) <= {'0', '1'})
            self.assertFalse(any('review' in label.lower() for label in legends))


if __name__ == '__main__':
    unittest.main()
