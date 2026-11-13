import shutil
import unittest
import numpy as np

import learning_curves as lc
import test_learning_curves as fixtures


class BothCompatibility(unittest.TestCase):
    setUpClass = classmethod(fixtures.LearningCurveTests.setUpClass.__func__)
    fixture = fixtures.LearningCurveTests.fixture

    def test_old_regular_filenames_load_as_both(self):
        self.fixture('181',training='both',count=3,baseline=2,test=2)
        folder=self.root/'181/MOLT4_results/csv'
        for path in list(folder.glob('*_both_*')):
            path.rename(path.with_name(path.name.replace('_both_','_regular_')))
        participant=lc.load_participant(self.root,'181')
        self.assertEqual(participant.training_condition,'both')
        self.assertIn(('baseline','both'),participant.series)
        self.assertNotIn(('baseline','regular'),participant.series)

    def test_old_and_new_alias_duplicate_is_rejected(self):
        self.fixture('182',training='both',count=3,baseline=2,test=2)
        path=next((self.root/'182/MOLT4_results/csv').glob('*_baseline_both_*'))
        shutil.copy2(path,path.with_name(path.name.replace('_both_','_regular_')))
        with self.assertRaisesRegex(ValueError,'多个文件'):
            lc.load_participant(self.root,'182')

    def test_new_version_output_is_selected_explicitly(self):
        self.fixture('183',training='both',count=3,baseline=2,test=2)
        folder=self.root/'183'
        shutil.copytree(folder/'MOLT4_results/csv',folder/'MOLT4_results_v3/csv')
        participant=lc.load_participant(self.root,'183')
        self.assertTrue(all('MOLT4_results_v3' in str(s.path) for s in participant.series.values()))

    def test_new_partial_components_keep_the_other_score_and_trial_alignment(self):
        path=self.root/'both_partial.csv'
        path.write_text('shot,mode,strength_value,angle_value,strength_status,angle_status,unit\n'
                        '1,regular,,12,invalid,scored,strength:origin_to_strip;angle:degree\n'
                        '2,both,0.2,,scored,invalid,strength:origin_to_strip;angle:degree\n',encoding='utf8')
        series=lc.load_series(path,'training','both')
        self.assertEqual(len(series.shot),2)
        self.assertTrue(np.isnan(series.components['strength'].value[0]))
        self.assertEqual(series.components['angle'].value[0],12.)
        self.assertEqual(series.components['strength'].value[1],.2)
        self.assertTrue(np.isnan(series.components['angle'].value[1]))
