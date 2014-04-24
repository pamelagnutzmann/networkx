# -*- coding: utf-8 -*-
"""Maximum flow algorithms test suite.
"""

from functools import partial
from nose.tools import *

import networkx as nx
from networkx.algorithms.flow.utils import *
from networkx.algorithms.flow.edmonds_karp import *
from networkx.algorithms.flow.ford_fulkerson import *
from networkx.algorithms.flow.preflow_push import *
from networkx.algorithms.flow.shortest_augmenting_path import *

flow_funcs = [edmonds_karp, ford_fulkerson, preflow_push,
              shortest_augmenting_path]
max_min_funcs = [nx.maximum_flow, nx.minimum_cut]
all_funcs = sum([flow_funcs, max_min_funcs], [])

msg = "Assertion failed in function: {0}"


def compute_cutset(G, partition):
    reachable, non_reachable = partition
    cutset = set()
    for u, nbrs in ((n, G[n]) for n in reachable):
        cutset.update((u, v) for v in nbrs if v in non_reachable)
    return cutset


def validate_flows(G, s, t, flowDict, solnValue, capacity, flow_func):
    assert_equal(set(G), set(flowDict), msg=msg.format(flow_func.__name__))
    for u in G:
        assert_equal(set(G[u]), set(flowDict[u]),
                     msg=msg.format(flow_func.__name__))
    excess = dict((u, 0) for u in flowDict)
    for u in flowDict:
        for v, flow in flowDict[u].items():
            if capacity in G[u][v]:
                ok_(flow <= G[u][v][capacity])
            ok_(flow >= 0, msg=msg.format(flow_func.__name__))
            excess[u] -= flow
            excess[v] += flow
    for u, exc in excess.items():
        if u == s:
            assert_equal(exc, -solnValue, msg=msg.format(flow_func.__name__))
        elif u == t:
            assert_equal(exc, solnValue, msg=msg.format(flow_func.__name__))
        else:
            assert_equal(exc, 0, msg=msg.format(flow_func.__name__))


def validate_cuts(G, s, t, solnValue, partition, capacity, flow_func):
    assert_true(all(n in G for n in partition[0]),
                msg=msg.format(flow_func.__name__))
    assert_true(all(n in G for n in partition[1]),
                msg=msg.format(flow_func.__name__))
    cutset = compute_cutset(G, partition)
    assert_true(all(G.has_edge(u, v) for (u, v) in cutset),
                msg=msg.format(flow_func.__name__))
    assert_equal(solnValue, sum(G[u][v][capacity] for (u, v) in cutset),
                msg=msg.format(flow_func.__name__))
    H = G.copy()
    H.remove_edges_from(cutset)
    if not G.is_directed():
        assert_false(nx.is_connected(H), msg=msg.format(flow_func.__name__))
    else:
        assert_false(nx.is_strongly_connected(H),
                     msg=msg.format(flow_func.__name__))


def compare_flows_and_cuts(G, s, t, solnFlows, solnValue, capacity='capacity'):
    for flow_func in flow_funcs:
        R = flow_func(G, s, t, capacity)
        # Test both legacy and new implementations.
        legacy = R.graph.get('algorithm') == "ford_fulkerson_legacy"
        flow_value = R.graph['flow_value']
        if legacy:
            flow_dict = R.graph['flow_dict']
        else:
            flow_dict = build_flow_dict(G, R)
        assert_equal(flow_value, solnValue, msg=msg.format(flow_func.__name__))
        if legacy:
            assert_equal(flow_dict, solnFlows, msg=msg.format(flow_func.__name__))
        else:
            validate_flows(G, s, t, flow_dict, solnValue, capacity, flow_func)
        # Minimum cut
        if legacy:
            cut_value, partition = nx.minimum_cut(G, s, t,  capacity=capacity,
                                                  flow_func=nx.ford_fulkerson)
        else:
            cut_value, partition = nx.minimum_cut(G, s, t, capacity=capacity,
                                                  flow_func=flow_func)
        validate_cuts(G, s, t, solnValue, partition, capacity, flow_func)


class TestMaxflowMinCutCommon:

    def test_graph1(self):
        # Trivial undirected graph
        G = nx.Graph()
        G.add_edge(1,2, capacity = 1.0)

        solnFlows = {1: {2: 1.0},
                     2: {1: 1.0}}

        compare_flows_and_cuts(G, 1, 2, solnFlows, 1.0)

    def test_graph2(self):
        # A more complex undirected graph
        # adapted from www.topcoder.com/tc?module=Statc&d1=tutorials&d2=maxFlow
        G = nx.Graph()
        G.add_edge('x','a', capacity = 3.0)
        G.add_edge('x','b', capacity = 1.0)
        G.add_edge('a','c', capacity = 3.0)
        G.add_edge('b','c', capacity = 5.0)
        G.add_edge('b','d', capacity = 4.0)
        G.add_edge('d','e', capacity = 2.0)
        G.add_edge('c','y', capacity = 2.0)
        G.add_edge('e','y', capacity = 3.0)

        H = {'x': {'a': 3, 'b': 1},
             'a': {'c': 3, 'x': 3},
             'b': {'c': 1, 'd': 2, 'x': 1},
             'c': {'a': 3, 'b': 1, 'y': 2},
             'd': {'b': 2, 'e': 2},
             'e': {'d': 2, 'y': 2},
             'y': {'c': 2, 'e': 2}}

        compare_flows_and_cuts(G, 'x', 'y', H, 4.0)

    def test_digraph1(self):
        # The classic directed graph example
        G = nx.DiGraph()
        G.add_edge('a','b', capacity = 1000.0)
        G.add_edge('a','c', capacity = 1000.0)
        G.add_edge('b','c', capacity = 1.0)
        G.add_edge('b','d', capacity = 1000.0)
        G.add_edge('c','d', capacity = 1000.0)

        H = {'a': {'b': 1000.0, 'c': 1000.0},
             'b': {'c': 0, 'd': 1000.0},
             'c': {'d': 1000.0},
             'd': {}}

        compare_flows_and_cuts(G, 'a', 'd', H, 2000.0)

    def test_digraph2(self):
        # An example in which some edges end up with zero flow.
        G = nx.DiGraph()
        G.add_edge('s', 'b', capacity = 2)
        G.add_edge('s', 'c', capacity = 1)
        G.add_edge('c', 'd', capacity = 1)
        G.add_edge('d', 'a', capacity = 1)
        G.add_edge('b', 'a', capacity = 2)
        G.add_edge('a', 't', capacity = 2)

        H = {'s': {'b': 2, 'c': 0},
             'c': {'d': 0},
             'd': {'a': 0},
             'b': {'a': 2},
             'a': {'t': 2},
             't': {}}

        compare_flows_and_cuts(G, 's', 't', H, 2)

    def test_digraph3(self):
        # A directed graph example from Cormen et al.
        G = nx.DiGraph()
        G.add_edge('s','v1', capacity = 16.0)
        G.add_edge('s','v2', capacity = 13.0)
        G.add_edge('v1','v2', capacity = 10.0)
        G.add_edge('v2','v1', capacity = 4.0)
        G.add_edge('v1','v3', capacity = 12.0)
        G.add_edge('v3','v2', capacity = 9.0)
        G.add_edge('v2','v4', capacity = 14.0)
        G.add_edge('v4','v3', capacity = 7.0)
        G.add_edge('v3','t', capacity = 20.0)
        G.add_edge('v4','t', capacity = 4.0)

        H = {'s': {'v1': 12.0, 'v2': 11.0},
             'v2': {'v1': 0, 'v4': 11.0},
             'v1': {'v2': 0, 'v3': 12.0},
             'v3': {'v2': 0, 't': 19.0},
             'v4': {'v3': 7.0, 't': 4.0},
             't': {}}

        compare_flows_and_cuts(G, 's', 't', H, 23.0)

    def test_digraph4(self):
        # A more complex directed graph
        # from www.topcoder.com/tc?module=Statc&d1=tutorials&d2=maxFlow
        G = nx.DiGraph()
        G.add_edge('x','a', capacity = 3.0)
        G.add_edge('x','b', capacity = 1.0)
        G.add_edge('a','c', capacity = 3.0)
        G.add_edge('b','c', capacity = 5.0)
        G.add_edge('b','d', capacity = 4.0)
        G.add_edge('d','e', capacity = 2.0)
        G.add_edge('c','y', capacity = 2.0)
        G.add_edge('e','y', capacity = 3.0)

        H = {'x': {'a': 2.0, 'b': 1.0},
             'a': {'c': 2.0},
             'b': {'c': 0, 'd': 1.0},
             'c': {'y': 2.0},
             'd': {'e': 1.0},
             'e': {'y': 1.0},
             'y': {}}

        compare_flows_and_cuts(G, 'x', 'y', H, 3.0)

    def test_optional_capacity(self):
        # Test optional capacity parameter.
        G = nx.DiGraph()
        G.add_edge('x','a', spam = 3.0)
        G.add_edge('x','b', spam = 1.0)
        G.add_edge('a','c', spam = 3.0)
        G.add_edge('b','c', spam = 5.0)
        G.add_edge('b','d', spam = 4.0)
        G.add_edge('d','e', spam = 2.0)
        G.add_edge('c','y', spam = 2.0)
        G.add_edge('e','y', spam = 3.0)

        solnFlows = {'x': {'a': 2.0, 'b': 1.0},
                     'a': {'c': 2.0},
                     'b': {'c': 0, 'd': 1.0},
                     'c': {'y': 2.0},
                     'd': {'e': 1.0},
                     'e': {'y': 1.0},
                     'y': {}}
        solnValue = 3.0
        s = 'x'
        t = 'y'

        compare_flows_and_cuts(G, s, t, solnFlows, solnValue, capacity = 'spam')

    def test_digraph_infcap_edges(self):
        # DiGraph with infinite capacity edges
        G = nx.DiGraph()
        G.add_edge('s', 'a')
        G.add_edge('s', 'b', capacity = 30)
        G.add_edge('a', 'c', capacity = 25)
        G.add_edge('b', 'c', capacity = 12)
        G.add_edge('a', 't', capacity = 60)
        G.add_edge('c', 't')

        H = {'s': {'a': 85, 'b': 12},
             'a': {'c': 25, 't': 60},
             'b': {'c': 12},
             'c': {'t': 37},
             't': {}}

        compare_flows_and_cuts(G, 's', 't', H, 97)

        # DiGraph with infinite capacity digon
        G = nx.DiGraph()
        G.add_edge('s', 'a', capacity = 85)
        G.add_edge('s', 'b', capacity = 30)
        G.add_edge('a', 'c')
        G.add_edge('c', 'a')
        G.add_edge('b', 'c', capacity = 12)
        G.add_edge('a', 't', capacity = 60)
        G.add_edge('c', 't', capacity = 37)

        H = {'s': {'a': 85, 'b': 12},
             'a': {'c': 25, 't': 60},
             'c': {'a': 0, 't': 37},
             'b': {'c': 12},
             't': {}}

        compare_flows_and_cuts(G, 's', 't', H, 97)


    def test_digraph_infcap_path(self):
        # Graph with infinite capacity (s, t)-path
        G = nx.DiGraph()
        G.add_edge('s', 'a')
        G.add_edge('s', 'b', capacity = 30)
        G.add_edge('a', 'c')
        G.add_edge('b', 'c', capacity = 12)
        G.add_edge('a', 't', capacity = 60)
        G.add_edge('c', 't')

        for flow_func in all_funcs:
            assert_raises(nx.NetworkXUnbounded,
                          flow_func, G, 's', 't')

    def test_graph_infcap_edges(self):
        # Undirected graph with infinite capacity edges
        G = nx.Graph()
        G.add_edge('s', 'a')
        G.add_edge('s', 'b', capacity = 30)
        G.add_edge('a', 'c', capacity = 25)
        G.add_edge('b', 'c', capacity = 12)
        G.add_edge('a', 't', capacity = 60)
        G.add_edge('c', 't')

        H = {'s': {'a': 85, 'b': 12},
             'a': {'c': 25, 's': 85, 't': 60},
             'b': {'c': 12, 's': 12},
             'c': {'a': 25, 'b': 12, 't': 37},
             't': {'a': 60, 'c': 37}}

        compare_flows_and_cuts(G, 's', 't', H, 97)

    def test_digraph4(self):
        # From ticket #429 by mfrasca.
        G = nx.DiGraph()
        G.add_edge('s', 'a', capacity = 2)
        G.add_edge('s', 'b', capacity = 2)
        G.add_edge('a', 'b', capacity = 5)
        G.add_edge('a', 't', capacity = 1)
        G.add_edge('b', 'a', capacity = 1)
        G.add_edge('b', 't', capacity = 3)
        flowSoln = {'a': {'b': 1, 't': 1},
                    'b': {'a': 0, 't': 3},
                    's': {'a': 2, 'b': 2},
                    't': {}}
        compare_flows_and_cuts(G, 's', 't', flowSoln, 4)


    def test_disconnected(self):
        G = nx.Graph()
        G.add_weighted_edges_from([(0,1,1),(1,2,1),(2,3,1)],weight='capacity')
        G.remove_node(1)
        assert_equal(nx.maximum_flow_value(G,0,3), 0)
        flowSoln = {0: {}, 2: {3: 0}, 3: {2: 0}}
        compare_flows_and_cuts(G, 0, 3, flowSoln, 0)

    def test_source_target_not_in_graph(self):
        G = nx.Graph()
        G.add_weighted_edges_from([(0,1,1),(1,2,1),(2,3,1)],weight='capacity')
        G.remove_node(0)
        for flow_func in all_funcs:
            assert_raises(nx.NetworkXError, flow_func, G, 0, 3)
        G.add_weighted_edges_from([(0,1,1),(1,2,1),(2,3,1)],weight='capacity')
        G.remove_node(3)
        for flow_func in all_funcs:
            assert_raises(nx.NetworkXError, flow_func, G, 0, 3)

    def test_source_target_coincide(self):
        G = nx.Graph()
        G.add_node(0)
        for flow_func in all_funcs:
            assert_raises(nx.NetworkXError, flow_func, G, 0, 0)


class TestMaxFlowMinCutInterface:

    def setup(self):
        G = nx.DiGraph()
        G.add_edge('x','a', capacity = 3.0)
        G.add_edge('x','b', capacity = 1.0)
        G.add_edge('a','c', capacity = 3.0)
        G.add_edge('b','c', capacity = 5.0)
        G.add_edge('b','d', capacity = 4.0)
        G.add_edge('d','e', capacity = 2.0)
        G.add_edge('c','y', capacity = 2.0)
        G.add_edge('e','y', capacity = 3.0)
        self.G = G
        H = nx.DiGraph()
        H.add_edge(0, 1, capacity = 1.0)
        H.add_edge(1, 2, capacity = 1.0)
        self.H = H

    def test_flow_func_not_callable(self):
        elements = ['this_should_be_callable', 10, set([1,2,3])]
        G = nx.Graph()
        G.add_weighted_edges_from([(0,1,1),(1,2,1),(2,3,1)], weight='capacity')
        for element in elements:
            assert_raises(nx.NetworkXError,
                          nx.maximum_flow, G, 0, 1, flow_func=element)
            assert_raises(nx.NetworkXError,
                          nx.minimum_cut, G, 0, 1, flow_func=element)

    def test_flow_func_parameters(self):
        G = self.G
        fv = 3.0
        for flow_func in [nx.edmonds_karp, nx.ford_fulkerson,
                          nx.preflow_push, nx.shortest_augmenting_path]:
            assert_equal(fv, nx.maximum_flow(G, 'x', 'y', flow_func=flow_func)[0],
                         msg=msg.format(flow_func.__name__))
            assert_equal(fv, nx.minimum_cut(G, 'x', 'y', flow_func=flow_func)[0],
                         msg=msg.format(flow_func.__name__))
            assert_raises(nx.NetworkXError, nx.minimum_cut, G, 'x', 'y',
                          flow_func=flow_func, cutoff=1.0)

    def test_kwargs(self):
        G = self.H
        fv = 1.0
        assert_equal(fv, nx.maximum_flow_value(G, 0, 2,
                     flow_func=nx.shortest_augmenting_path, two_phase=True))
        assert_equal(fv, nx.minimum_cut_value(G, 0, 2,
                     flow_func=nx.shortest_augmenting_path, two_phase=True))
        assert_equal(fv, nx.maximum_flow_value(G, 0, 2,
                     flow_func=nx.preflow_push, global_relabel_freq=5))
        assert_equal(fv, nx.minimum_cut_value(G, 0, 2,
                     flow_func=nx.preflow_push, global_relabel_freq=5))

    def test_kwargs_default_flow_func(self):
        G = self.H
        assert_raises(nx.NetworkXError,
                      nx.maximum_flow, G, 0, 1, global_relabel_freq=2)
        assert_raises(nx.NetworkXError,
                      nx.minimum_cut, G, 0, 1, global_relabel_freq=2)


# Tests specific to one algorithm
def test_preflow_push_global_relabel_freq():
    G = nx.DiGraph()
    G.add_edge(1, 2, capacity=1)
    R = nx.preflow_push(G, 1, 2, global_relabel_freq=None)
    assert_equal(R.graph['flow_value'], 1)
    assert_raises(nx.NetworkXError, preflow_push, G, 1, 2,
                  global_relabel_freq=-1)

def test_shortest_augmenting_path_two_phase():
    k = 5
    p = 1000
    G = nx.DiGraph()
    for i in range(k):
        G.add_edge('s', (i, 0), capacity=1)
        G.add_path(((i, j) for j in range(p)), capacity=1)
        G.add_edge((i, p - 1), 't', capacity=1)
    R = shortest_augmenting_path(G, 's', 't', two_phase=True)
    assert_equal(R.graph['flow_value'], k)
    R = shortest_augmenting_path(G, 's', 't', two_phase=False)
    assert_equal(R.graph['flow_value'], k)


def test_cutoff():
    k = 5
    p = 1000
    G = nx.DiGraph()
    for i in range(k):
        G.add_edge('s', (i, 0), capacity=2)
        G.add_path(((i, j) for j in range(p)), capacity=2)
        G.add_edge((i, p - 1), 't', capacity=2)
    R = shortest_augmenting_path(G, 's', 't', two_phase=True, cutoff=k)
    ok_(k <= R.graph['flow_value'] <= 2 * k)
    R = shortest_augmenting_path(G, 's', 't', two_phase=False, cutoff=k)
    ok_(k <= R.graph['flow_value'] <= 2 * k)
    R = edmonds_karp(G, 's', 't', cutoff=k)
    ok_(k <= R.graph['flow_value'] <= 2 * k)
