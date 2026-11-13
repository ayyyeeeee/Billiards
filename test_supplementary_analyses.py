import unittest
import numpy as np
import pandas as pd
from plot_supplementary_analyses import paired_metrics, bootstrap_mean


def stage(pid, phase, values):
    a = np.asarray(values, float)
    return dict(participant=pid, group='both', task='both', channel='angle',
                stage=phase, n=len(a), mean=a.mean(), mae=np.abs(a).mean(),
                sd=a.std(ddof=1) if len(a)>1 else np.nan)


class SupplementaryTests(unittest.TestCase):
    def test_identity_and_finite_sample_correction(self):
        pre, post = np.array([-3, 1, 5]), np.array([-2, 0, 1, 3, 4])
        r = paired_metrics(pd.DataFrame([stage('01', 'baseline', pre), stage('01', 'test', post)])).iloc[0]
        self.assertAlmostEqual(r.mse_pre, np.mean(pre**2))
        self.assertAlmostEqual(r.mse_post, np.mean(post**2))
        self.assertAlmostEqual(r.delta_mse, r.delta_bias_squared+r.delta_variance)
        self.assertAlmostEqual(r.delta_mse, r.delta_corrected_bias_squared+r.delta_sample_variance)
        # A zero mean does not justify truncating a corrected estimate at zero.
        r = paired_metrics(pd.DataFrame([stage('01','baseline',[-1,1]), stage('01','test',[-2,2])])).iloc[0]
        self.assertLess(r.corrected_bias_squared_pre, 0)

    def test_pairs_by_id_not_input_order_and_missing_stage(self):
        records = [stage('02','test',[10,20]), stage('01','baseline',[2,4]),
                   stage('03','baseline',[1,2]), stage('02','baseline',[20,30]),
                   stage('01','test',[1,2])]
        p = paired_metrics(pd.DataFrame(records)).set_index('participant')
        self.assertEqual(p.loc['01','delta_mae'], -1.5)
        self.assertEqual(p.loc['02','delta_mae'], -10)
        self.assertTrue(np.isnan(p.loc['03','delta_mae']))
        self.assertFalse(p.loc['03','eligible_mae'])

    def test_single_trial_does_not_create_variance(self):
        p = paired_metrics(pd.DataFrame([stage('01','baseline',[1]),stage('01','test',[2,3])])).iloc[0]
        self.assertTrue(p.eligible_mae)
        self.assertFalse(p.eligible_decomposition)
        self.assertTrue(np.isnan(p.delta_mse))

    def test_bootstrap_constants_contrast_and_reproducibility(self):
        r = bootstrap_mean([1,1,1], np.random.default_rng(1), 1000, other=[3,3,3,3])
        self.assertEqual((r['estimate'],r['low'],r['high']), (-2,-2,-2))
        self.assertEqual((r['n'],r['n_other']), (3,4))
        values = [-2,-1,-.5,0,.1,.3,1,3,4,8]
        a = bootstrap_mean(values,np.random.default_rng(14),1000)
        b = bootstrap_mean(values,np.random.default_rng(14),1000)
        self.assertEqual(a,b)
        self.assertEqual(a['method'],'BCa')
        self.assertLess(a['low'],a['high'])

    def test_duplicate_pair_rejected(self):
        row = stage('01','baseline',[1,2])
        with self.assertRaises(ValueError):
            paired_metrics(pd.DataFrame([row,row]))


if __name__ == '__main__':
    unittest.main()
