import unittest
import numpy as np
import pandas as pd
from plot_publication_figures import select_values, participant_indices, decay, fit_decay


class PublicationTests(unittest.TestCase):
    def test_training_requires_scored_and_nonflagged(self):
        df=pd.DataFrame({'angle_value':[1,1000,3,np.nan,5],
                         'angle_status':['scored','scored','unresolved','scored','scored'],
                         'angle_outlier':[0,1,0,0,0]})
        result=select_values(df,'angle',True)
        self.assertEqual(result.dropna().tolist(),[1,5])
        self.assertEqual(df.angle_value.iloc[1],1000)
        with self.assertRaises(ValueError):
            select_values(df.drop(columns='angle_outlier'),'angle',True)

    def test_component_normalization_no_missing_channel_reweight(self):
        df=pd.DataFrame([dict(participant='01',group='both',block=1,normalized_mae=2.,normalized_sd=1.),
                         dict(participant='01',group='both',block=1,normalized_mae=4.,normalized_sd=np.nan)])
        result=participant_indices(df).iloc[0]
        self.assertEqual(result.normalized_mae,3.)
        self.assertTrue(np.isnan(result.normalized_sd))

    def test_decay_recovers_known_curve_and_rejects_increasing_decay(self):
        x=np.arange(1,15,dtype=float)
        result=fit_decay(x,decay(x,2,3,.4))
        self.assertTrue(result['identifiable'])
        self.assertAlmostEqual(result['tau'],3,places=4)
        self.assertAlmostEqual(result['C'],.4,places=4)
        result=fit_decay(x,x)
        self.assertFalse(result['identifiable'])


if __name__=='__main__': unittest.main()
