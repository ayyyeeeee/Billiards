import unittest
import numpy as np
from scipy.stats import t
from analysis.robust.student_t import fit_student_t, observation_loglik


class RobustModelTests(unittest.TestCase):
    def test_censor_likelihood_is_probability_not_density(self):
        y = np.array([-1., 0., 2.])
        actual = observation_loglik(y, 0., 2., [-1, 0, 1], 5)
        expected = [t.logcdf(-.5, 5), t.logpdf(0., 5)-np.log(2), t.logsf(1., 5)]
        np.testing.assert_allclose(actual, expected)

    def test_location_scale_recovery_and_extreme_robustness(self):
        rng = np.random.default_rng(123)
        x = np.linspace(0, 1, 600)
        mean = 1-2*x
        scale = .15*np.exp(1.2*x)
        y = mean + scale*rng.standard_t(5, len(x))
        fit = fit_student_t(x, y)
        self.assertTrue(fit.success, fit.message)
        prediction = fit.predict(x)
        self.assertLess(np.sqrt(np.mean((prediction['mean']-mean)**2)), .09)
        self.assertGreater(prediction['scale'][-1]/prediction['scale'][0], 2)
        np.testing.assert_allclose(prediction['variance'], prediction['scale']**2*5/3)
        dirty = y.copy()
        dirty[300] += 100
        contaminated = fit_student_t(x, dirty)
        self.assertTrue(contaminated.success, contaminated.message)
        self.assertLess(np.max(np.abs(contaminated.predict(x)['mean']-prediction['mean'])), .05)
        self.assertLess(contaminated.weights[300], .001)

    def test_censored_constant_fit_and_missing(self):
        rng = np.random.default_rng(7)
        latent = .4 + .6*rng.standard_t(5, 3000)
        observed = np.minimum(latent, .7)
        censor = (latent >= .7).astype(int)
        fit = fit_student_t(np.arange(len(latent)), observed, censor, df_mean=1, df_scale=1)
        self.assertTrue(fit.success, fit.message)
        pred = fit.predict([0])
        self.assertAlmostEqual(pred['mean'][0], .4, delta=.07)
        self.assertAlmostEqual(pred['scale'][0], .6, delta=.07)
        observed[0] = np.nan
        fit = fit_student_t(np.arange(len(latent)), observed, censor, df_mean=1, df_scale=1)
        self.assertEqual(fit.n_obs, len(latent)-1)
        self.assertFalse(fit.used_mask[0])

    def test_failures_are_explicit(self):
        self.assertFalse(fit_student_t(np.arange(5), np.arange(5)).success)
        self.assertFalse(fit_student_t(np.arange(30), np.ones(30)).success)
        with self.assertRaises(ValueError):
            fit_student_t(np.arange(20), np.arange(20), np.full(20, 2))

    def test_majority_censored_is_not_degenerate_variance(self):
        rng = np.random.default_rng(15)
        latent = 1.5 + rng.standard_t(5, 500)
        observed = np.minimum(latent, 1.)
        result = fit_student_t(np.arange(500), observed, (latent >= 1).astype(int),
                               df_mean=1, df_scale=1)
        self.assertTrue(result.success, result.message)
        self.assertGreater(result.predict([0])['mean'][0], 1.)


if __name__ == '__main__':
    unittest.main()
