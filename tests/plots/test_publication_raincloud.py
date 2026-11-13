import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from statsmodels.stats.multitest import multipletests
from publication_raincloud import participant_deltas, draw_raincloud


def stage_data(constant=False):
    rng=np.random.default_rng(123)
    rows=[]
    for group in ('both','strength','angle'):
        for i in range(10):
            for task,channel in [('both','strength'),('strength','strength'),('both','angle'),('angle','angle')]:
                delta=0. if constant else rng.normal(-.3,.2)
                for stage,value in [('baseline',1.),('test',1.+delta)]:
                    rows.append(dict(participant=f'{group}{i}',group=group,task=task,channel=channel,
                                     stage=stage,n=10,mae=value,mean=0,sd=.1))
    return pd.DataFrame(rows)


class RaincloudTests(unittest.TestCase):
    def test_pairing_uses_participants_not_trials(self):
        data=stage_data()
        result=participant_deltas(data)
        self.assertEqual(len(result),120)
        self.assertTrue(result.groupby(['task','channel','group']).size().eq(10).all())
        data.loc[0,'n']=0
        self.assertEqual(len(participant_deltas(data)),119)
        with self.assertRaisesRegex(ValueError,'Duplicate'):
            participant_deltas(pd.concat([data,data.iloc[:1]],ignore_index=True))

    def test_statistics_and_layout(self):
        captured=[]
        def capture(fig,*args,**kwargs):
            self.assertTrue(np.allclose(fig.get_size_inches(),[15,9]))
            self.assertEqual(len(fig.axes),6)
            self.assertEqual(sum(not ax.axison for ax in fig.axes),2)
            captured.append(fig)
        with tempfile.TemporaryDirectory() as tmp,patch.object(plt.Figure,'savefig',capture):
            result=draw_raincloud(stage_data(),Path(tmp))
            omni=result[(result.kind=='omnibus')&(result.status=='ok')]
            self.assertEqual(len(omni),4)
            self.assertEqual(len(result[result.kind=='tukey']),12)
            self.assertTrue(np.allclose(omni.p_holm,multipletests(omni.p_value,method='holm')[1]))
            self.assertTrue((Path(tmp)/'figure3_caption.txt').exists())
        self.assertEqual(len(captured),2)

    def test_constant_and_missing_data_do_not_invent_tests(self):
        with tempfile.TemporaryDirectory() as tmp,patch.object(plt.Figure,'savefig'):
            result=draw_raincloud(stage_data(constant=True),Path(tmp))
            self.assertFalse(result.kind.eq('tukey').any())
            self.assertTrue(result[result.kind=='omnibus'].p_value.isna().all())
            empty=stage_data().iloc[:0]
            result=draw_raincloud(empty,Path(tmp))
            self.assertEqual(len(result),6)
            self.assertTrue(result.p_value.isna().all())


if __name__=='__main__':
    unittest.main()
