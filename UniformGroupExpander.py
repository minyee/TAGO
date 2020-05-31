import math, os, sys, copy
import numpy as np
from collections import deque
from gurobipy import *
import UniformGroupDragonfly
import traffic_generator.DragonflyAdversarialTrafficGenerator
import networkx as nx
import random

'''
Same as uniform Dragonfly, just that there can be arbitrary number of links connecting each group
Not only that, each group is not a full mesh, but an expander instead
'''
class UniformGroupExpander(UniformGroupDragonfly.UniformGroupDragonfly):
    '''
    num_groups is always equal to num_switches_per_group + 1
    (could potentially just pass in one parameter)
    '''
    def __init__(self, G, A, number_links_between_each_group, number_intragroup_link_per_switch):
        assert(number_intragroup_link_per_switch < A - 1)
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
        return "uexpander_g{}_a{}_h{}_m{}".format(self.num_groups, self.num_switches_per_group, self.h, self.num_intrablock_links_per_switch)

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
            random.shuffle(potential_targets)
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
        random.shuffle(link_pairs)
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

    def design_full_topology(self):
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
            
        switch_offset_in_group = [0] * self.num_groups 
        for group1 in range(self.num_groups - 1):
            for group2 in range(group1 + 1, self.num_groups, 1):
                for _ in range(self.number_links_between_each_group):
                    sw1 = switch_offset_in_group[group1] + (group1 * self.num_switches_per_group)
                    sw2 = switch_offset_in_group[group2] + (group2 * self.num_switches_per_group)
                    self.adjacency_matrix[sw1][sw2] += 1
                    self.adjacency_matrix[sw2][sw1] += 1
                    switch_offset_in_group[group1] = (switch_offset_in_group[group1] + 1) % self.num_switches_per_group
                    switch_offset_in_group[group2] = (switch_offset_in_group[group2] + 1) % self.num_switches_per_group
        #self.__check_correctness()
        print(self.adjacency_matrix)
        return



