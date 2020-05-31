import math, os, sys, copy
import numpy as np
from collections import deque
from gurobipy import *
import UniformGroupDragonfly
import traffic_generator.DragonflyAdversarialTrafficGenerator
import networkx as nx
import random

'''
Same as canonical uniform Expander, just that there can be arbitrary number of links connecting each group
Essentially Flexspander
'''
class SkewedGroupExpander(UniformGroupDragonfly.UniformGroupDragonfly):
    '''
    num_groups is always equal to num_switches_per_group + 1
    (could potentially just pass in one parameter)
    '''
    def __init__(self, G, A, number_links_between_each_group, number_intragroup_link_per_switch):
        UniformGroupDragonfly.UniformGroupDragonfly.__init__(self, G, A, number_links_between_each_group)
        self.num_intrablock_links_per_switch = number_intragroup_link_per_switch
        return

    def get_interblock_topology(self):
        interblock_topology = [0] * self.num_groups
        for i in range(self.num_groups):
            interblock_topology[i] = [0] * self.num_groups
        for switch_id in range(self.total_num_switches):
            block = switch_id / self.num_switches_per_group
            for target_id in range(self.total_num_switches):
                target_block = target_id / self.num_switches_per_group
                if block != target_block:
                    interblock_topology[block][target_block] += self.adjacency_matrix[switch_id][target_id]

        return interblock_topology

    def get_name(self):
        return "skewedexpander_g{}_a{}_h{}_m{}".format(self.num_groups, self.num_switches_per_group, self.h, self.num_intrablock_links_per_switch)

    ## Checks for the correctness of the topology
    ## NOTE : This is an internal method only to be called by methods belonging to this class
    def __check_correctness(self, target_interblock_topology): 
        ## first, check each group is a full-mesh
        for group in range(self.num_groups):
            offset = group * self.num_switches_per_group
            for i in range(self.num_switches_per_group - 1):
                for j in range(i + 1, self.num_switches_per_group, 1):
                    assert(self.adjacency_matrix[j][i] == 1)
                    assert(self.adjacency_matrix[i][j] == 1)
        
        ## check that each group have exactly the same number of connectivity, and for symmetry
        ## also checks each switch only reaches one target group 
        intergroup_connectivity = np.zeros((self.num_groups, self.num_groups))
        switch_connection_to_target_group = {}
        for i in range(self.total_num_switches):
            src_group = i / self.num_switches_per_group
            switch_connection_to_target_group[i] = {}
            for j in range(self.total_num_switches):
                if i != j :
                    assert(self.adjacency_matrix[j][i] == self.adjacency_matrix[i][j])
                    assert(self.adjacency_matrix[i][j] <= 1)
                    dst_group = j / self.num_switches_per_group
                    if src_group != dst_group and self.adjacency_matrix[i][j] > 0:
                        if dst_group not in switch_connection_to_target_group[i].keys():
                            switch_connection_to_target_group[i][dst_group] = True
                        else:
                            assert(False)

                        intergroup_connectivity[src_group][dst_group] += 1
                else:
                    assert(self.adjacency_matrix[i][j] == 0)

        ## finally, check for symmetry in intergroup connectivity
        supposed_intergroup_connectivity = (self.num_switches_per_group * self.h) / (self.num_groups - 1)
        assert((self.num_switches_per_group * self.h) % (self.num_groups - 1) == 0)
        #print("supposed intergroup_connectivity: {}".format(supposed_intergroup_connectivity))
        for src_group in range(self.num_groups - 1):
            for dst_group in range(src_group + 1, self.num_groups, 1):
                assert(intergroup_connectivity[src_group][dst_group] == intergroup_connectivity[dst_group][src_group])
                assert(intergroup_connectivity[src_group][dst_group] == target_interblock_topology[src_group][dst_group])
        return

    def __make_symmetric(traffic_matrix):
        dimension = len(traffic_matrix)
        symmetric_matrix = np.zeros((dimension, dimension))
        for i in range(dimension - 1):
            for j in range(i + 1, dimension, 1):
                symmetric_matrix[i][j] = traffic_matrix[i][j] + traffic_matrix[j][i]
                symmetric_matrix[j][i] = traffic_matrix[i][j] + traffic_matrix[j][i]
        return symmetric_matrix

    ## designs the interblock topology, given an expected interblock traffic matrix
    def _design_target_interblock_topology(self, expected_interblock_traffic) :
        interblock_topology = [0] * self.num_groups
        for i in range(self.num_groups):
            interblock_topology[i] = [0] * self.num_groups
        ## first thing is to copy the expected interblock traffic matrix
        interblock_tm = copy.deepcopy(expected_interblock_traffic)
        is_symmetrical = True
        for i in range(self.num_groups - 1):
            for j in range(i + 1, self.num_groups, 1):
                if interblock_tm[i][j] != interblock_tm[i][j]:
                    is_symmetrical = False
                    break
            if not is_symmetrical:
                break

        if not is_symmetrical:
            interblock_tm = self.make_symmetric(interblock_tm)

        ## at this point, we can expect the interblock traffic matrix to be symmetrical
        ## first maybe just try to use shortest path routing to maximize minimum throughput 
        interblock_connectivity = [None] * self.num_groups
        for src_block in range(self.num_groups):
            interblock_connectivity[src_block] = [None] * self.num_groups
        model = Model("Designing Interblock Topology")
        model.setParam( 'OutputFlag' , False )
        num_links_per_block = self.num_switches_per_group * self.h
        throughput = model.addVar(obj=0., vtype=GRB.CONTINUOUS, lb=0, ub=GRB.INFINITY, name="throughput")
        for src_block in range(self.num_groups):
            for dst_block in range(src_block + 1, self.num_groups, 1):
                optimization_variable = model.addVar(obj=0., vtype=GRB.CONTINUOUS, lb=1, ub=num_links_per_block, name="l_{}_{}".format(src_block, dst_block))
                interblock_connectivity[src_block][dst_block] = optimization_variable
                interblock_connectivity[dst_block][src_block] = optimization_variable
        ##
        for src_block in range(self.num_groups):
            outgoing_links = LinExpr()
            incoming_links = LinExpr()
            for dst_block in range(self.num_groups):
                if src_block != dst_block:
                    outgoing_links += interblock_connectivity[src_block][dst_block]
                    incoming_links += interblock_connectivity[dst_block][src_block]
            model.addConstr(lhs=num_links_per_block, sense=GRB.GREATER_EQUAL, rhs=outgoing_links)
            model.addConstr(lhs=num_links_per_block, sense=GRB.GREATER_EQUAL, rhs=incoming_links)

        for src_block in range(self.num_groups):
            for dst_block in range(self.num_groups):
                if (src_block != dst_block):
                    throughput_constraint = LinExpr()
                    model.addConstr(lhs=interblock_connectivity[src_block][dst_block], sense=GRB.GREATER_EQUAL, rhs=throughput*interblock_tm[src_block][dst_block])
        model.setObjective(throughput, GRB.MAXIMIZE)
        try:
            model.optimize()
            for i in range(self.num_groups - 1):
                for j in range(i + 1, self.num_groups, 1):
                    interblock_topology[i][j] = interblock_connectivity[i][j].x
                    interblock_topology[j][i] = interblock_connectivity[i][j].x
        except GurobiError as e:
            print ("Error code " + str(e. errno ) + ": " + str(e))
        except AttributeError :
            print ("Encountered an attribute error ")
        print("Fractional interblock connectivity is : \n{}".format(interblock_topology))
        return interblock_topology

    ## assumes that the entire topology is connected via a giant switch
    def __round_fractional_topology_giant_switch(self, fractional_adj_matrix):
        integer_adj_matrix = np.zeros((self.num_groups, self.num_groups))
        nnodes = 2 + (2 * self.num_groups)
        G = nx.DiGraph()
        edges = []
        num_interblock_link_per_group = self.num_switches_per_group * self.h
        # add edges from src to first layer nodes and between second layer nodes to sink
        for i in range(self.num_groups):
            egress_sum = 0.
            ingress_sum = 0.
            for j in range(self.num_groups):
                if i != j:
                    egress_sum += math.floor(fractional_adj_matrix[i][j])
                    ingress_sum += math.floor(fractional_adj_matrix[j][i])
            edges.append((0, i + 1, {'capacity' : num_interblock_link_per_group - egress_sum, 'weight': 0}))
            edges.append((self.num_groups + i + 1, nnodes - 1, {'capacity' : num_interblock_link_per_group - ingress_sum, 'weight' : 0}))
        # next, add edges between first layer nodes and second layer nodes
        for i in range(self.num_groups):
            for j in range(self.num_groups):
                if i != j:
                    score = int((math.ceil(fractional_adj_matrix[i][j]) - fractional_adj_matrix[i][j]) * 1E6)
                    edges.append((i + 1, self.num_groups + j + 1, {'capacity' : 1, 'weight': score}))

        # next, add the edges set into the graph
        G.add_edges_from(edges)
        mincostFlow = nx.max_flow_min_cost(G, 0, nnodes - 1)
        for i in range(self.num_groups):
            for j in range(self.num_groups):
                if i != j:
                    assert(mincostFlow[i + 1][self.num_groups + j + 1] <= 1)
                    integer_adj_matrix[i][j] = int(math.floor(fractional_adj_matrix[i][j]) + mincostFlow[i + 1][self.num_groups + j + 1])
        ## Finally, check to see if some links are 0
        for i in range(self.num_groups):
            for j in range(self.num_groups):
                if i != j and integer_adj_matrix[i][j] < 1:
                    assert(False)
        return integer_adj_matrix

    ## subroutine that forms a full mesh among the group of switches in switch_ids    
    def __form_expander_template(self, num_switches_in_block, num_intrablock_links_per_switch):
        assert(num_switches_in_block - 1 > num_intrablock_links_per_switch)
        adj_matrix = [0] * num_switches_in_block
        for i in range(num_switches_in_block):
            adj_matrix[i] = [0] * num_switches_in_block
        formed_links = [0] * num_switches_in_block
        # now form the remainder of the connections
        link_pairs = []
        num_intrablock_links_per_switch_copy = num_intrablock_links_per_switch
        for i in range(num_switches_in_block):
            potential_targets = list(range(num_switches_in_block))
            random.Random(33632).shuffle(potential_targets)
            offset = 0
            while formed_links[i] < num_intrablock_links_per_switch_copy and offset < num_switches_in_block:
                dst = potential_targets[offset]
                if formed_links[dst] < num_intrablock_links_per_switch_copy and dst != i:
                    adj_matrix[i][dst] += 1
                    adj_matrix[dst][i] += 1
                    formed_links[i] += 1
                    formed_links[dst] += 1
                    link_pairs.append((min(i, dst), max(i , dst)))
                offset += 1
        random.Random(33632).shuffle(link_pairs)
        ##print adj_matrix
        for i in range(num_switches_in_block):
            while num_intrablock_links_per_switch_copy - formed_links[i] >= 2:
                for pair_id in range(len(link_pairs)):
                    found = False
                    if link_pairs[pair_id][0] != i and link_pairs[pair_id][1] != i:
                        sw1 = link_pairs[pair_id][0]
                        sw2 = link_pairs[pair_id][0]
                        adj_matrix[sw1][sw2] -= 1
                        adj_matrix[sw2][sw1] -= 1
                        adj_matrix[i][sw1] += 1
                        adj_matrix[sw1][i] += 1
                        adj_matrix[i][sw2] += 1
                        adj_matrix[sw2][i] += 1
                        formed_links[i] += 2
                        link_pairs.pop(pair_id)
                        found = True
                    if found:
                        break
        ## replace the links that are not formed
        ## now form all the pairs
        return adj_matrix

    def design_full_topology(self, expected_interblock_traffic):
        # iterate through each group to form the expanders first
        expander_template = self.__form_expander_template(self.num_switches_per_group, self.num_intrablock_links_per_switch)
        for group in range(self.num_groups):
            offset = group * self.num_switches_per_group
            switch_ids_in_group = range(offset, offset + self.num_switches_per_group, 1)
            for i in range(self.num_switches_per_group):
                for j in range(self.num_switches_per_group):
                    if expander_template[i][j] > 0 and i != j:
                        src_id = switch_ids_in_group[i]
                        dst_id = switch_ids_in_group[j]
                        self.adjacency_matrix[src_id][dst_id] = expander_template[i][j]

        ## next, go and design the intergroup topology
        ## Step 2.1 : First, figure out what is the ideal interblock (symmetric) connectivity that is fractional
        target_interblock_topology = self._design_target_interblock_topology(expected_interblock_traffic)
        ## Step 2.2 : Then, round this symmetric connectivity into integer
        actual_integer_interblock_topology = self.__round_fractional_topology_giant_switch(target_interblock_topology)
        
        ## Step 2.3 : Finally , wire switches together such that the overall topology resembles the target topology
        switch_offset_in_group = [0] * self.num_groups 
        for group1 in range(self.num_groups - 1):
            for group2 in range(group1 + 1, self.num_groups, 1):
                for _ in range(int(actual_integer_interblock_topology[group1][group2])):
                    sw1 = switch_offset_in_group[group1] + (group1 * self.num_switches_per_group)
                    sw2 = switch_offset_in_group[group2] + (group2 * self.num_switches_per_group)
                    self.adjacency_matrix[sw1][sw2] += 1
                    self.adjacency_matrix[sw2][sw1] += 1
                    switch_offset_in_group[group1] = (switch_offset_in_group[group1] + 1) % self.num_switches_per_group
                    switch_offset_in_group[group2] = (switch_offset_in_group[group2] + 1) % self.num_switches_per_group
        #self.__check_correctness(actual_integer_interblock_topology)
        return

