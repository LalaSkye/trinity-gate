import copy
import unittest
from examples.precita_compiler.compiler import compile_passage

BASE = {'source': {'id':'s','version':'1','author':'Ada','text':'Ada wrote: 1,200 cases. "All cases reviewed."'},
        'target': {'id':'t','version':'1','author':'Ben','text':'Ada wrote: 1,200 cases. "All cases reviewed."'},
        'bindings': [{'id':'q','kind':'quote','original':'All cases reviewed.','rendered':'All cases reviewed.','attributed_to':'Ada'},
                     {'id':'n','kind':'number','original':'1,200','rendered':'1,200','attributed_to':'Ada'}]}
class Tests(unittest.TestCase):
    def test_valid(self):
        self.assertTrue(all(x['status']=='CHECKED' for x in compile_passage(BASE)['findings']))
    def test_quote_changed(self):
        x=copy.deepcopy(BASE);x['bindings'][0]['rendered']='Some cases reviewed.';x['target']['text']+=' Some cases reviewed.'
        self.assertIn('QUOTE_CHANGED',compile_passage(x)['findings'][0]['reasons'])
    def test_number_changed(self):
        x=copy.deepcopy(BASE);x['bindings'][1]['rendered']='1,300';x['target']['text']+=' 1,300'
        self.assertIn('NUMBER_CHANGED',compile_passage(x)['findings'][1]['reasons'])
    def test_wrong_author(self):
        x=copy.deepcopy(BASE);x['bindings'][0]['attributed_to']='Ben'
        self.assertIn('ATTRIBUTION_MISMATCH',compile_passage(x)['findings'][0]['reasons'])
    def test_missing_original(self):
        x=copy.deepcopy(BASE);x['bindings'][0]['original']='never written'
        self.assertIn('ORIGINAL_NOT_FOUND',compile_passage(x)['findings'][0]['reasons'])
    def test_missing_rendered(self):
        x=copy.deepcopy(BASE);x['target']['text']='gone'
        self.assertIn('RENDERED_NOT_FOUND',compile_passage(x)['findings'][0]['reasons'])
    def test_empty(self):
        x=copy.deepcopy(BASE);x['bindings']=[]
        self.assertEqual(compile_passage(x)['findings'][0]['status'],'HOLD')
    def test_duplicate(self):
        x=copy.deepcopy(BASE);x['bindings'].append(x['bindings'][0])
        with self.assertRaises(ValueError):compile_passage(x)
    def test_no_authority(self):
        self.assertFalse(compile_passage(BASE)['authority_verified'])
    def test_deterministic(self):
        self.assertEqual(compile_passage(BASE),compile_passage(BASE))
if __name__=='__main__':
    unittest.main()
