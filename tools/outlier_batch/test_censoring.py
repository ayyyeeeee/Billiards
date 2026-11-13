import unittest
import numpy as np
import pandas as pd
from censoring import censor_codes, censor_values


class CensoringTests(unittest.TestCase):
    def test_joint_evidence_and_exact_signed_bounds(self):
        df = pd.DataFrame({
            'strength_value': [1.009013, -1.009013, 1.009013, 2., np.nan, .5],
            'strength_maximum': [1.009013356]*6,
            'strength_uncapped': [2., 2., 1.009013, 2., 3., 3.],
        })
        before = df.copy(deep=True)
        values = censor_values(df, 'strength')
        codes = censor_codes(df, 'strength')
        np.testing.assert_array_equal(codes, [1, -1, 0, 0, 0, 0])
        np.testing.assert_allclose(values[:2], [1.009013356, -1.009013356])
        pd.testing.assert_frame_equal(df, before)

    def test_missing_metadata_and_unrelated_large_values_not_censored(self):
        df = pd.DataFrame({'angle_value': [90., -90., 30.],
                           'angle_maximum': [90., 90., 90.]})
        np.testing.assert_array_equal(censor_codes(df, 'angle'), [0, 0, 0])
        df['angle_uncapped'] = [91., 91., 120.]
        np.testing.assert_array_equal(censor_codes(df, 'angle'), [1, -1, 0])


if __name__ == '__main__':
    unittest.main()
