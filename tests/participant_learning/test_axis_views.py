from common.paths import PARTICIPANT_ROOT
"""Regression checks for honest zoomed acquisition views."""
from pathlib import Path
import unittest
import numpy as np
from plots.participant_learning import app as lc


class AcquisitionViews(unittest.TestCase):
    def draw(self,values,means=None):
        values=np.asarray(values,dtype=float);shots=np.arange(1,len(values)+1)
        fig,ax=lc.plt.subplots(figsize=(4,3))
        points=ax.scatter(shots,values,color=lc.GRAY)
        if means is None:means=[np.nanmean(values[i:i+10]) for i in range(0,len(values),10)]
        lc.bounds(ax,values)
        result=lc.acquisition_view(ax,shots,values,means,points,lc.GRAY)
        self.addCleanup(lc.plt.close,fig)
        return fig,ax,result

    def test_mild_tail_does_not_break_axis(self):
        fig,ax,view=self.draw(np.linspace(0,20,40))
        self.assertFalse(view['separated'])
        self.assertEqual(len(fig.axes),1)

    def test_short_constant_and_missing_observations(self):
        for values in ([1,2,80],[1]*39+[80],[np.nan]*20+[1]*40):
            with self.subTest(values=values):
                fig,ax,view=self.draw(values)
                self.assertFalse(view['separated'])
                self.assertEqual(len(fig.axes),1)

    def test_all_blue_means_remain_visible(self):
        values=np.tile([1.,2.,3.,4.],10);values[-1]=80.
        fig,ax,view=self.draw(values,means=[80.])
        self.assertFalse(view['separated'])
        self.assertGreater(ax.get_ylim()[1],80)

    def test_both_regions_partition_points_without_moving_x(self):
        values=np.tile([1.,2.,3.,4.],10);values[-1]=80.
        original=values.copy()
        fig,ax,view=self.draw(values)
        self.assertTrue(view['separated'])
        high=next(a for a in fig.axes if a.get_gid()=='acquisition-high-values')
        actual=np.vstack([ax.collections[0].get_offsets(),high.collections[0].get_offsets()])
        expected=np.column_stack((np.arange(1,41),values))
        np.testing.assert_array_equal(actual[np.argsort(actual[:,0])],expected)
        np.testing.assert_array_equal(values,original)
        self.assertGreater(high.get_ylim()[0],ax.get_ylim()[1])
        self.assertAlmostEqual(max(high.get_yticks()),80.)
        self.assertEqual(view['main_scored']+view['high_scored'],40)

    def test_real_04_and_all_original_block_statistics(self):
        root=PARTICIPANT_ROOT
        if not (root/'04/MOLT4_results/csv').is_dir():
            self.fail('Real 04 evidence required for the source regression')
        participant=lc.load_participant(root,'04',legacy=True)
        series=participant.series['training','angle']
        before=series.value.copy();blocks=lc.blocks(series,10)
        fig,stats=lc.create_figure(participant);self.addCleanup(lc.plt.close,fig)
        view=stats['training_components']['angle']['acquisition_display']
        self.assertFalse(view['separated'])
        self.assertIn(view['mode'], ('linear', 'symlog'))
        ax=next(a for a in fig.axes if 'Angular error' in a.get_ylabel())
        self.assertGreaterEqual(ax.get_ylim()[1], np.nanmax(series.value))
        self.assertEqual(stats['training_components']['angle']['blocks'],[lc.plain_block(b) for b in blocks])
        np.testing.assert_array_equal(series.value,before)

    def test_real_02_dense_labels_never_cover_the_heading(self):
        participant=lc.load_participant(PARTICIPANT_ROOT,'02',legacy=True)
        fig,stats=lc.create_figure(participant);self.addCleanup(lc.plt.close,fig)
        view=stats['training_components']['angle']['acquisition_display']
        # This smaller both-component panel cannot fit all nine labels.
        # It must retain the complete range instead of crossing the heading.
        self.assertFalse(view['separated'])
        self.assertIn(view['mode'], ('linear', 'symlog'))
        angle_ax=next(a for a in fig.axes if a.get_title(loc='left').startswith('Angle component (n') and
                      'Angular error' in a.get_ylabel())
        series=participant.series['training','both'].components['angle']
        self.assertGreaterEqual(angle_ax.get_ylim()[1],np.nanmax(series.value))
        self.assertEqual(len(angle_ax.collections[0].get_offsets()),len(series.value))


if __name__=='__main__':unittest.main()
