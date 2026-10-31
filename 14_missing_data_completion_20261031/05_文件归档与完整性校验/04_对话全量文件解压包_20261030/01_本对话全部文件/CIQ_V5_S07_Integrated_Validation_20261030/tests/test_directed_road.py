import sys,unittest
from pathlib import Path
import networkx as nx
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'code'))
from audit_v5_osm_directed import graph_validity,build_simple_length_graph,route_candidate_matrix,edge_length
class TestRoad(unittest.TestCase):
 def setUp(self):
  self.G=nx.MultiDiGraph();self.G.add_node('1',x=103.75,y=1.5);self.G.add_node('2',x=103.76,y=1.5)
  self.G.add_edge('1','2',length=1500.0)
 def test_directed(self):self.assertTrue(graph_validity(self.G)['is_directed'])
 def test_correct_edge(self):self.assertEqual(edge_length({'length':'100'}),100)
 def test_zero_length_rejected(self):self.assertIsNone(edge_length({'length':0}))
 def test_invalid_graph(self):
  self.G.add_edge('2','1',length=-5)
  self.assertEqual(graph_validity(self.G)['invalid_length'],1)
 def test_directionality_not_symmetry(self):
  D=build_simple_length_graph(self.G);self.assertFalse(nx.has_path(D,'2','1'))
 def test_od_unreachable(self):
  snap=[{'node_id':'A','osm_node_id':'2','candidate_gate_status':'CANDIDATE_WITHIN_100M_NOT_LEGAL_ENTRANCE'}, {'node_id':'B','osm_node_id':'1','candidate_gate_status':'CANDIDATE_WITHIN_100M_NOT_LEGAL_ENTRANCE'}]
  out=route_candidate_matrix(self.G,snap,[{'origin_node_id':'A','destination_node_id':'B'}]);self.assertEqual(out[0]['status'],'HOLD_DIRECTED_DISCONNECTED')
 def test_od_reachable_distance(self):
  snap=[{'node_id':'A','osm_node_id':'1','candidate_gate_status':'CANDIDATE_WITHIN_100M_NOT_LEGAL_ENTRANCE'},{'node_id':'B','osm_node_id':'2','candidate_gate_status':'CANDIDATE_WITHIN_100M_NOT_LEGAL_ENTRANCE'}]
  out=route_candidate_matrix(self.G,snap,[{'origin_node_id':'A','destination_node_id':'B'}]);self.assertEqual(out[0]['route_length_m'],1500)
  self.assertEqual(out[0]['FCD_direction_calibrated'],'NO')
if __name__=='__main__':unittest.main()
