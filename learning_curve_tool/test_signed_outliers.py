"""Regression tests for signed data sources and outlier handling."""
import unittest
from pathlib import Path
import numpy as np

import learning_curves as lc

ROOT = Path(__file__).resolve().parent.parent


class TestSignedAndOutliers(unittest.TestCase):
    def test_01_both_sources_and_outliers(self):
        p = lc.load_participant(ROOT, '01')
        self.assertEqual(p.training_condition, 'both')
        # Check source paths
        train_series = p.series['training', 'both']
        self.assertIn('outlier_results', str(train_series.path))
        self.assertIn('labeled_csv', str(train_series.path))
        for (st, cd), s in p.series.items():
            if st in ('baseline', 'test'):
                self.assertIn('processed_csv', str(s.path))

        # Check outliers in training
        str_comp = train_series.components['strength']
        ang_comp = train_series.components['angle']
        # angle outliers at shots 64 and 136
        self.assertEqual(list(ang_comp.shot[ang_comp.outlier]), [64, 136])
        self.assertEqual(list(str_comp.shot[str_comp.outlier]), [])
        self.assertTrue(np.isnan(ang_comp.value[63]))  # shot 64 (0-indexed 63)
        self.assertTrue(np.isnan(ang_comp.value[135]))  # shot 136 (0-indexed 135)
        self.assertEqual(int(np.isfinite(ang_comp.value).sum()), 138)
        # strength component on shot 64 should be finite
        self.assertTrue(np.isfinite(str_comp.value[63]))
        self.assertEqual(int(np.isfinite(str_comp.value).sum()), 140)

        # Check signed values (both positive and negative)
        self.assertTrue((str_comp.value[np.isfinite(str_comp.value)] < 0).any())
        self.assertTrue((str_comp.value[np.isfinite(str_comp.value)] > 0).any())
        self.assertTrue((ang_comp.value[np.isfinite(ang_comp.value)] < 0).any())
        self.assertTrue((ang_comp.value[np.isfinite(ang_comp.value)] > 0).any())

        # Check figure generation, subtitle, legend, and caption
        fig, stats = lc.create_figure(p)
        self.addCleanup(lc.plt.close, fig)
        texts = [t.get_text().replace('\n', ' ') for t in fig.findobj(lc.matplotlib.text.Text)]
        self.assertTrue(any('Values closer to zero indicate better performance' in t for t in texts))
        self.assertTrue(any('Excluded trial (rug below axis)' in t for t in texts))
        self.assertTrue(any('not 95% CI' in t for t in texts))
        self.assertFalse(any('Red dots on the x-axis' in t for t in texts))
        self.assertTrue(any('excluded outlier=1' in body for _,body in stats['captions']))
        rugs = [c for ax in fig.axes for c in ax.collections if c.get_gid() == 'excluded-trial-rug']
        self.assertEqual(len(rugs), 1)
        np.testing.assert_array_equal(rugs[0].get_offsets()[:,0], [64,136])
        self.assertTrue(np.all(rugs[0].get_offsets()[:,1] < 0))
        self.assertFalse(stats['training_components']['angle']['robust_fit']['historical_flags_retained'])
        self.assertEqual(stats['training_components']['angle']['robust_fit']['n_obs'], 138)
        self.assertEqual(stats['total_trials'], 251)
        self.assertEqual(stats['training_components']['angle']['outliers'], [64, 136])
        self.assertEqual(stats['training_components']['angle']['outlier_count'], 2)
        self.assertEqual(stats['training_components']['strength']['outliers'], [])
        self.assertEqual(stats['training_components']['strength']['outlier_count'], 0)

    def test_04_angle_condition(self):
        p = lc.load_participant(ROOT, '04')
        self.assertEqual(p.training_condition, 'angle')
        train_series = p.series['training', 'angle']
        self.assertIn('outlier_results', str(train_series.path))
        self.assertEqual(list(train_series.shot[train_series.outlier]), [116])
        self.assertEqual(int(np.isfinite(train_series.value).sum()), 139)
        self.assertEqual(len(train_series.shot), 140)

    def test_05_strength_condition(self):
        p = lc.load_participant(ROOT, '05')
        self.assertEqual(p.training_condition, 'strength')
        train_series = p.series['training', 'strength']
        self.assertIn('outlier_results', str(train_series.path))
        self.assertEqual(list(train_series.shot[train_series.outlier]), [18])
        self.assertEqual(int(np.isfinite(train_series.value).sum()), 138)
        self.assertEqual(len(train_series.shot), 140)

    def test_variable_shot_counts(self):
        # 07 has 136, 09 has 138, 19 has 139
        p07 = lc.load_participant(ROOT, '07')
        self.assertEqual(len(p07.series['training', 'angle'].shot), 136)
        p09 = lc.load_participant(ROOT, '09')
        self.assertEqual(len(p09.series['training', 'strength'].shot), 138)
        p19 = lc.load_participant(ROOT, '19')
        self.assertEqual(len(p19.series['training', 'both'].shot), 139)

    def test_all_30_participants_loadable(self):
        ids = lc.discover_ids(ROOT)
        self.assertEqual(len(ids), 30)
        cond_counts = {'both': 0, 'angle': 0, 'strength': 0}
        for sub in ids:
            p = lc.load_participant(ROOT, sub)
            cond_counts[p.training_condition] += 1
            self.assertEqual(len(p.series), 7)
        self.assertEqual(cond_counts, {'both': 10, 'angle': 10, 'strength': 10})


if __name__ == '__main__':
    unittest.main()
