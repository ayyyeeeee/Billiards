import unittest
from unittest.mock import patch
from pathlib import Path
import tempfile
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import plot_baseline_vs_transfer as p


class TransferTests(unittest.TestCase):
    def test_training_uses_finite_values_and_excludes_flag_one(self):
        df = pd.DataFrame({'strength_value': [1., 2., 3., np.nan, np.inf],
            'strength_outlier': [1, 0, 0, 0, 0],
            'strength_status': ['scored', 'unresolved', 'not_requested', 'scored', 'scored'],
            'strength_valid': [1, 0, 0, 1, 1], 'needs_review': 1})
        self.assertEqual(p.extract_clean_series(df, 'strength_value', 'strength_outlier',
                                               is_training=True).tolist(), [2., 3.])

    def test_publication_size_and_no_statistics_overlay(self):
        records=[]
        for task in ('both','strength','angle'):
            for i in range(10):
                r={'subject':f'{i:02d}', 'group':'both', 'task':task}
                for ch in ('strength','angle'):
                    r['baseline_'+ch+'_mean']=float(i-5)
                    r['transfer_'+ch+'_mean']=float(i-4)
                records.append(r)
        figures=[]
        def inspect(fig, *args, **kwargs):
            self.assertTrue(np.allclose(fig.get_size_inches()*25.4,[180,170]))
            for ax in fig.axes:
                self.assertAlmostEqual(ax.get_xlim()[0],-ax.get_xlim()[1])
                self.assertFalse(any('mean change' in t.get_text() for t in ax.texts))
            figures.append(fig)
        with patch.object(plt.Figure, 'savefig', inspect):
            p.plot_overview_figure(pd.DataFrame(records), [p.PRIMARY_MEASURES[0],p.PRIMARY_MEASURES[2]],
                                  'Test',Path('unused'))
        self.assertEqual(len(figures),2)

    def test_channel_validity_is_independent(self):
        df = pd.DataFrame({'angle_value': [1., 2., 3., np.inf],
            'angle_status': ['scored', 'unresolved', 'scored', 'scored'],
            'angle_valid': [1, 1, 1, 1], 'score_complete': [0, 1, 1, 1],
            'angle_outlier': [1, 0, 0, 0], 'angle_needs_review': [1, 0, 0, 0]})
        self.assertEqual(p.extract_clean_series(df, 'angle_value', 'angle_outlier').tolist(), [1., 3.])

    def test_robust_moments_keep_raw_sensitivity(self):
        rng = np.random.default_rng(17)
        y = np.r_[rng.normal(0, .2, 39), 25.]
        result = p.compute_stage_metrics(pd.DataFrame({'angle_value': y}))
        self.assertEqual(result['n_angle'], 40)
        self.assertTrue(result['angle_fit_success'])
        self.assertAlmostEqual(result['raw_angle_variance'], np.var(y, ddof=1))
        self.assertLess(abs(result['angle_mean']), abs(result['raw_angle_mean']))
        self.assertLess(result['angle_variance'], result['raw_angle_variance'])

    def test_variance_axis_preserves_all_points(self):
        df = pd.DataFrame({'subject': ['01', '02', '03'], 'group': ['both']*3,
            'baseline_angle_variance': [0., .2, 281.],
            'transfer_angle_variance': [.1, .4, 40.]})
        fig, ax = plt.subplots()
        p.draw_paired_scatter_panel(ax, df, 'angle_variance', 'Variance', 'deg²', True, ['both'], 'Test')
        self.assertEqual(ax.get_xscale(), 'symlog')
        self.assertEqual(len(ax.collections[0].get_offsets()), 3)
        self.assertGreater(ax.get_xlim()[1], 281)
        plt.close(fig)


if __name__ == '__main__':
    unittest.main()
