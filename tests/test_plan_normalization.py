import unittest
from src.plan_normalization import normalize_plan


class PlanNormalizationTest(unittest.TestCase):
    def test_moves_split_literal_into_binary_operator_array(self):
        plan={'steps':[{'id':'f','op':'filter','input':'r','where':{'and':[
            {'lt':[{'col':'I'}],'value':2000}, {'gt':[{'col':'F'}],'value':57}]}}],
              'output':{'step':'f','columns':['A']}}
        fixed,changes=normalize_plan(plan,[],{},repair_split_literals=True)
        where=fixed['steps'][0]['where']['and']
        self.assertEqual(where[0],{'lt':[{'col':'I'},{'value':2000}]})
        self.assertEqual(where[1],{'gt':[{'col':'F'},{'value':57}]})
        self.assertEqual(len(changes),2)

    def test_legacy_mode_does_not_rewrite_ambiguous_shape(self):
        plan={'steps':[{'id':'f','op':'filter','input':'r','where':{'lt':[{'col':'I'}],'value':2000}}],
              'output':{'step':'f','columns':['A']}}
        fixed,changes=normalize_plan(plan,[],{},repair_split_literals=False)
        self.assertEqual(fixed,plan);self.assertEqual(changes,[])

    def test_declared_predicates_inside_and_retain_each_operator(self):
        p={'steps':[{'id':'f','op':'filter','input':'r','missing':'skip','where':{'and':[
            {'contains':[{'col':'A'},{'value':'wide'}],'is_number':[{'col':'B'}]}]}}],
            'output':{'step':'f','columns':['A']}}
        fixed,changes=normalize_plan(p,[],{},repair_split_literals=True)
        self.assertEqual(fixed['steps'][0]['where'],{'and':[
            {'contains':[{'col':'A'},{'value':'wide'}]}, {'is_number':[{'col':'B'}]}]})
        self.assertNotIn('missing',fixed['steps'][0])
        self.assertIn('missing',p['steps'][0])


if __name__=='__main__':unittest.main()
