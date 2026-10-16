import copy
import unittest
from src.reliability import normalize
from src.tools.executor import execute
from src.workbook_index import Region


class DirectionTest(unittest.TestCase):
    def data(self, a='11.2', b='38.5', labels=('Group A','Group B')):
        region=Region('t1','Rates',1,3,1,2,
                      {(1,1):'Identity',(1,2):'Rate',(2,1):labels[0],(2,2):a,(3,1):labels[1],(3,2):b},[],[],[1])
        plan={'steps':[{'id':'a','op':'cell','table':'t1','row':2,'column':'B'},
                       {'id':'b','op':'cell','table':'t1','row':3,'column':'B'},
                       {'id':'diff','op':'calculate','expr':{'sub':[{'ref':'a'},{'ref':'b'}]}}],
              'output':{'step':'diff','decimals':1},'answer_spec':{'answer_type':'number','answer_field':'rate','operation':'difference'}}
        return plan,region

    def test_lower_comparison_is_bound_to_labels_not_operand_order(self):
        p,r=self.data();before=copy.deepcopy(p)
        fixed,changes=normalize(p,question='How many percentage points lower is Group A than Group B?',regions=[r])
        self.assertEqual(execute(fixed,[r])['answer'],'27.3')
        self.assertEqual(changes[0]['subject_source'],'Rates!B2')
        self.assertEqual(changes[0]['reference_source'],'Rates!B3')
        self.assertEqual(p,before)
        self.assertEqual(normalize(fixed,question='How many percentage points lower is Group A than Group B?',regions=[r]),(fixed,[]))

    def test_chinese_overlapping_names_resolve_by_longest_label(self):
        p,r=self.data('21.6','42.8',('甲居民','非甲居民'))
        fixed,changes=normalize(p,question='对于某类人群，甲居民的就业率比非甲居民低多少个百分点？只回答数字。',regions=[r])
        self.assertEqual(execute(fixed,[r])['answer'],'21.2')
        self.assertEqual(changes[0]['formula'],'reference-subject')

    def test_vietnamese_and_higher_direction(self):
        p,r=self.data()
        fixed,changes=normalize(p,question='Group B cao hơn Group A bao nhiêu điểm phần trăm?',regions=[r])
        self.assertEqual(execute(fixed,[r])['answer'],'27.3')
        self.assertEqual(changes[0]['formula'],'subject-reference')

    def test_genuine_negative_and_signed_changes_are_preserved(self):
        p,r=self.data('50','20')
        q='How much lower is Group A than Group B?'
        fixed,_=normalize(p,question=q,regions=[r])
        self.assertEqual(execute(fixed,[r])['answer'],'-30.0')
        q+=' Return a signed value.'
        self.assertEqual(normalize(p,question=q,regions=[r]),(p,[]))
        self.assertEqual(normalize(p,question='Compute the signed change new-old.',regions=[r]),(p,[]))

    def test_no_rewrite_without_unique_binding_or_same_metric(self):
        p,r=self.data(labels=('Same','Same'))
        self.assertEqual(normalize(p,question='How much lower is Same than Same?',regions=[r]),(p,[]))
        p,r=self.data()
        self.assertEqual(normalize(p,question='How much lower is Unknown than Group B?',regions=[r]),(p,[]))
        p['steps'][1]['column']='A'
        self.assertEqual(normalize(p,question='How much lower is Group A than Group B?',regions=[r]),(p,[]))

    def test_row_reordering_preserves_label_binding(self):
        p,r=self.data()
        r.cells[(2,1)],r.cells[(3,1)]=r.cells[(3,1)],r.cells[(2,1)]
        r.cells[(2,2)],r.cells[(3,2)]=r.cells[(3,2)],r.cells[(2,2)]
        fixed,changes=normalize(p,question='How much lower is Group A than Group B?',regions=[r])
        self.assertEqual(execute(fixed,[r])['answer'],'27.3')
        self.assertEqual(changes,[])  # Source order is already reference-subject.


if __name__=='__main__':unittest.main()
