import math, os, sys
import numpy as np
from collections import deque

'''
Same as canonical Dragonfly, just that there can be arbitrary number of links connecting each group
'''
class UniformGroupDragonfly():
    '''
    num_groups is always equal to num_switches_per_group + 1
    (could potentially just pass in one parameter)
    '''
    def __init__(self, G, A, number_links_between_each_group):
        assert(G - 1 <= A)
        self.h = (G - 1) * number_links_between_each_group / A
        assert(((G - 1) * number_links_between_each_group) % A == 0)
        self.num_groups = G
        self.num_switches_per_group = A #number of switches per group
        self.number_links_between_each_group = number_links_between_each_group
        self.total_num_switches = G * A
        self.adjacency_matrix = np.zeros((self.total_num_switches, self.total_num_switches))
        return

    ##########################################################################################
    ## Get functions (Start)
    ##########################################################################################
    def get_num_blocks(self):
        return self.num_groups

    def get_num_switches_per_block(self):
        return self.num_switches_per_group

    def get_total_num_switches(self):
        return self.total_num_switches

    def get_adjacency_matrix(self):
        return self.adjacency_matrix
    
    def get_num_intergroup_links_per_switch(self):
        return self.h

    def get_adjacency_list(self):
        adj_list = {}
        for switch in range(self.total_num_switches):
            adj_list[switch] = []
            for target_switch in range(self.total_num_switches):
                if switch != target_switch:
                    links_formed = 0
                    while links_formed < self.adjacency_matrix[switch][target_switch]:
                        adj_list[switch].append(target_switch)
                        links_formed += 1
        return adj_list

    def get_name(self):
        return "dfly_g{}_a{}_h{}".format(self.num_groups, self.num_switches_per_group, self.h)

    ## returns a map of each switch id to its corresponding block (i.e. group in dragonfly context) id
    def get_switch_id_to_block_id_map(self):
        switch_to_block_map = {}
        offset = 0
        for block_id in range(self.num_groups):
            for switch in range(self.num_switches_per_group):
                switch_to_block_map[offset] = block_id
                offset += 1
        return switch_to_block_map

    def get_block_id_to_switch_ids(self):
        block_to_switches_map = {}
        offset = 0
        for block_id in range(self.num_groups):
            block_to_switches_map[block_id] = []
            for _ in range(self.num_switches_per_group):
                block_to_switches_map[block_id].append(offset)
                offset += 1
        return block_to_switches_map

    ##########################################################################################
    ## Get functions (Start)
    ##########################################################################################


    ## Checks for the correctness of the topology
    ## NOTE : This is an internal method only to be called by methods belonging to this class
    def __check_correctness(self): 
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
                assert(intergroup_connectivity[src_group][dst_group] == supposed_intergroup_connectivity)
        return

    ## subroutine that forms a full mesh among the group of switches in switch_ids    
    def __form_full_mesh(self, switch_ids):
        for switch1 in switch_ids:
            for switch2 in switch_ids:
                if switch1 != switch2:
                    self.adjacency_matrix[switch1][switch2] = 1
        return
    
    def design_full_topology(self):
        # iterate through each group to form the full meshes first
        for group in range(self.num_groups):
            offset = group * self.num_switches_per_group
            switch_ids_in_group = range(offset, offset + self.num_switches_per_group, 1)
            self.__form_full_mesh(switch_ids_in_group)
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
        self.__check_correctness()
        print(self.adjacency_matrix)
        return

