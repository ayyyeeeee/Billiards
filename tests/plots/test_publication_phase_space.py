import tempfile
import unittest
from pathlib import Path
import numpy as np
import pandas as pd
from publication_phase_space import draw_phase_space, ellipse_geometry, Q95, COLORS


class PhaseSpaceTests(unittest.TestCase):
    def test_requested_group_colors(self):
        self.assertEqual(COLORS, {'both': '#0072B2', 'strength': '#D55E00', 'angle': '#009E73'})

    def sample(self):
        rng = np.random.default_rng(51)
        rows = []
        for gi, group in enumerate(('both', 'strength', 'angle')):
            points = rng.normal(size=(10, 2)) @ np.array([[1., .3], [0., .5]])
            for i, point in enumerate(points):
                for stage, multiplier in [('baseline', 1.), ('test', 1.5)]:
                    rows.append(dict(participant=f'{gi*10+i+1:02}', group=group, stage=stage,
                                     angle=point[0]*multiplier, strength=point[1]*multiplier))
        return pd.DataFrame(rows)

    def test_covariance_ellipse_area_and_extent(self):
        p = np.array([[-2, 0], [2, 0], [0, -1], [0, 1.]])
        g = ellipse_geometry(p)
        self.assertAlmostEqual(g['area'], np.pi*Q95*np.sqrt(np.linalg.det(np.cov(p.T))))
        np.testing.assert_allclose(g['extent'], np.sqrt(Q95*np.diag(g['covariance'])))

    def test_expansion_is_reported_and_coordinates_preserved(self):
        data = self.sample()
        original = data.copy(deep=True)
        with tempfile.TemporaryDirectory() as tmp:
            stem = Path(tmp)/'figure4.png'
            summary = draw_phase_space(data, stem)
            np.testing.assert_allclose(summary.area_change_pct, 125., atol=1e-8)
            np.testing.assert_allclose(summary.angle_variance_post_pre_ratio, 2.25)
            self.assertEqual(summary.n_pairs.tolist(), [10, 10, 10])
            for suffix in ('.png', '.pdf', '_coordinates.csv', '_summary.csv', '_caption.txt'):
                self.assertTrue((Path(tmp)/('figure4'+suffix)).is_file())
            coordinates = pd.read_csv(Path(tmp)/'figure4_coordinates.csv', dtype={'participant': str})
            np.testing.assert_allclose(coordinates[['angle', 'strength']], data[['angle', 'strength']])
        pd.testing.assert_frame_equal(data, original)

    def test_incomplete_pairs_are_explicit_error(self):
        data = self.sample().iloc[1:]
        with self.assertRaisesRegex(ValueError, 'baseline/test pair'):
            draw_phase_space(data, Path('unused'))


if __name__ == '__main__': unittest.main()
