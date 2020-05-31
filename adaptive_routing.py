import numpy as np
from gurobipy import *
from collections import deque
import copy
import sys, math

class AdaptiveRouting(object):
	def __init__(self, tolerance_fairness, max_intrablock_distance=2):
		## records the maximum number of hops we permit packets to traverse within a block
		self.max_tolerable_intrablock_distance = max_intrablock_distance 
		self.sigma = tolerance_fairness
		return

	## generates the intrablock topology
	## helper for _find_all_short_paths_to_entry_switches
	def __intrablock_topol_gen(self, topology, switches_in_block):
		intrablock_topology = {}
		for switch in switches_in_block:
			intrablock_topology[switch] = []
			for neighbor in topology[switch]:
				if neighbor in switches_in_block:
					intrablock_topology[switch].append(neighbor)
		return intrablock_topology

	## Finds the entrance switches from each block to every other block in the network.
	## Helper to _find_all_short_paths_to_entry_switches
	## DONE
	def __identify_entrance_switches(self, topology, switch_to_block_map, block_to_switches_map, nblocks):
		block_to_block_entrance_switches = {}

		## now go through each block's switch to find out the entrance switches to other blocks
		for src_block_id in range(nblocks):
			# for each switch in the source block
			for switch in block_to_switches_map[src_block_id]:
				for neighbor in topology[switch]:
					target_block_id = switch_to_block_map[neighbor]
					## check if the neighboring switch is in the same block, or belonging to a different block
					if target_block_id != src_block_id:
						if (src_block_id, target_block_id) not in block_to_block_entrance_switches:
							block_to_block_entrance_switches[(src_block_id, target_block_id)] = []
						block_to_block_entrance_switches[(src_block_id, target_block_id)].append(switch)
		return block_to_block_entrance_switches

	## given a topology adjacency list, how each switch id is mapped to a block, and
	## the total number of blocks, form the number of paths between each switch, block pair
	def _find_all_short_paths_to_entry_switches(self, topology, switch_to_block_map, block_to_switches_map, nblocks, inter_block_entrance_switches):
		switch_to_entry_switches_paths = {} ## to return
		## Step 1 : For every pair of blocks, identify the entrance switches
		block_topologies = {}
		for block in range(nblocks):
			block_topologies[block] = self.__intrablock_topol_gen(topology, block_to_switches_map[block])

		## Step 2 : Figure out, for every switch, the path to get to each entry switches
		for current_switch in topology.keys():
			current_switch_block = switch_to_block_map[current_switch]
			for target_block in range(nblocks):
				## check if the target_block is a different block
				if target_block == current_switch_block:
					continue
				## check if the current switch is an entrance switch to this target block
				
				paths_collection = []
				
				entry_switches = inter_block_entrance_switches[(current_switch_block, target_block)]
				for entry_switch in entry_switches:
					paths_collection += self._short_paths_to_switch(current_switch, entry_switch, topology, entry_switches, self.max_tolerable_intrablock_distance)
				switch_to_entry_switches_paths[(current_switch, target_block)] = paths_collection
		return switch_to_entry_switches_paths

	## helper function to _short_paths_to_switch, and essentially recursively performs DFS to locate paths from source to target
	def __dfs_recursive__(self, source, target, current_node, topology, current_hop_count, maximum_hop_counts, prohibited_nodes_for_intermediate_hops, all_paths, path):
		if current_node == target and current_hop_count <= maximum_hop_counts:
			path.append(current_node)
			all_paths.append(tuple(path))
			return
		if current_hop_count < maximum_hop_counts:
			for neighbor in topology[current_node]:
				## ignore neighbor if it is source, or if it has been traversed before
				## also check if neighbor is one of the entry switches without being the target destination entry switch that we actually want to traverse to
				if (neighbor in path) or (neighbor != target and neighbor in prohibited_nodes_for_intermediate_hops):
					continue
				else:
					new_path = copy.deepcopy(path)
					new_path.append(current_node)
					self.__dfs_recursive__(source, target, neighbor, topology, current_hop_count + 1, maximum_hop_counts, prohibited_nodes_for_intermediate_hops, all_paths, new_path)
		return

	## Returns all the short paths for source to destination. Note that the prohibited_nodes_for_intermediate_hops
	## records the nodes which we cannot use as path of the intermediate nodes in the path to destination.
	## In the context of this codebase, the prohibited_nodes_for_intermediate_hops includes the entry switches
	def _short_paths_to_switch(self, source, destination, topology, prohibited_nodes_for_intermediate_hops, maximum_steps):
		short_paths = []
		if source == destination:
			short_paths.append((source,))
		self.__dfs_recursive__(source, destination, source, topology, 0, maximum_steps, prohibited_nodes_for_intermediate_hops, short_paths, [])
		return short_paths

	##
	## src_block - the source block id
	## dst_block - the destination block id
	## total_capacity_between_blocks - the total link capacity that exists between src_block and dst_block, summing across all cross-block links
	## block_to_switches_map - a map from block_id to a list of all the switch ids belonging to said block
	## entry_switches - a collection (i.e. list) of all the entry switches from src_block to dst_block
	## traffic_sent_from_each_switch - the amount of traffic sent from each switch in src_block to dst_block
	## path_to_entry_switches - the paths of all switches in src_block to the entry switches
	def _split_traffic_between_block_pair(self, 
										src_block, 
										dst_block, 
										total_capacity_between_blocks, 
										block_to_switches_map, 
										entry_switches, 
										traffic_sent_from_each_switch, 
										path_to_entry_switches):
		if src_block == dst_block:
			return None
		if len(entry_switches) == 0:
			assert(False)
			raise Exception("No entry switch")
			return None
		model = Model("split traffic between blocks : {} - {}".format(src_block, dst_block))
		model.setParam( 'OutputFlag', False )
		obj_function = LinExpr()
		omega = {}
		for src_switch in block_to_switches_map[src_block]:
			all_paths_to_entry_switches = path_to_entry_switches[(src_switch, dst_block)] ## all paths to ALL entry switches
			all_paths_switch_to_entry_switch = {} ## all paths to a specific entry switch
			for path in all_paths_to_entry_switches:
				assert(path[0] == src_switch)
				entry_switch = path[-1] 
				if entry_switch not in all_paths_switch_to_entry_switch:
					all_paths_switch_to_entry_switch[entry_switch] = []
				all_paths_switch_to_entry_switch[entry_switch].append(path)
			for entry_switch in all_paths_switch_to_entry_switch.keys():
				paths_lengths = [len(x) - 1 for x in all_paths_switch_to_entry_switch[entry_switch]]
				min_path_length_to_entry_switch = min(paths_lengths)
				omega[(src_switch, entry_switch)] = model.addVar(obj=0., vtype=GRB.CONTINUOUS, lb=0, ub=1, name="w_{}_{}".format(src_switch, entry_switch))
				obj_function += omega[(src_switch, entry_switch)] * traffic_sent_from_each_switch[src_switch] * min_path_length_to_entry_switch

		## Programming the constraints
		## Constraints type 1 : all routing weights have to add to 1
		for src_switch in block_to_switches_map[src_block]:
			weight_sum_constraint = LinExpr()
			for entry_switch in entry_switches:
				if entry_switch != src_switch:
					weight_sum_constraint += omega[(src_switch, entry_switch)]
			model.addConstr(lhs=weight_sum_constraint, sense=GRB.EQUAL, rhs=1.)

		## Constraints type 2 : utilization of interblock links have to be more or less equal
		traffic_sum_from_src_block = 0.
		for switch in traffic_sent_from_each_switch.keys():
			traffic_sum_from_src_block += traffic_sent_from_each_switch[switch]
		optimal_fair_share = traffic_sum_from_src_block / float(total_capacity_between_blocks)
		#print("traffic_sent_from_each_switch : {} - sum : {}".format(traffic_sent_from_each_switch, sum(traffic_sent_from_each_switch)))
		#print("optimal fairshare : {} ".format(sum(traffic_sent_from_each_switch)  / float(total_capacity_between_blocks) ))
		for entry_switch in entry_switches:
			entry_switch_traffic_volume = LinExpr()
			## first, add the volume from itself
			entry_switch_traffic_volume += traffic_sent_from_each_switch[entry_switch]
			for src_switch in block_to_switches_map[src_block]:
				if src_switch not in entry_switches:
					entry_switch_traffic_volume += (traffic_sent_from_each_switch[src_switch] * omega[(src_switch, entry_switch)])
			model.addConstr(lhs=optimal_fair_share * (1. + self.sigma), sense=GRB.GREATER_EQUAL, rhs=entry_switch_traffic_volume)
		
		## The final output
		routing_weights = {}
		try:
			model.setObjective(obj_function, GRB.MINIMIZE)
			model.optimize()
			for (src_switch, entry_switch) in omega.keys():
				routing_weights[(src_switch, entry_switch)] = omega[(src_switch, entry_switch)].x
			## evens out the routing weights if traffic sent from each switch is zero
			for switch_id in block_to_switches_map[src_block]:
				if traffic_sent_from_each_switch[switch_id] <= 0:
					### even out the optimization
					if switch_id not in entry_switches:
						for entry_switch in entry_switches:
							routing_weights[(switch_id, entry_switch)] = 1./len(entry_switches)
		except GurobiError as e:
			print ("Error code " + str(e. errno ) + ": " + str(e))
		except AttributeError :
			print ("Encountered an attribute error ")

		if len(routing_weights.keys()) == 0:
			## uniformly assign weights
			# 
			num_entry_switches = len(entry_switches)
			for block_switch in block_to_switches_map[src_block]:
				for entry_switch in entry_switches:
					routing_weights[(block_switch, entry_switch)] = 1./num_entry_switches
		return routing_weights

	################################################################################################################################################################
	################################################################################################################################################################
	'''
	External functions
	'''
	################################################################################################################################################################
	################################################################################################################################################################

	## Selects the paths to use for 
	def path_selection(self, topology, switch_to_block_map, block_to_switches_map, inter_block_entrance_switches):
		nblocks = len(block_to_switches_map.keys())
		shortest_paths = self._find_all_short_paths_to_entry_switches(topology, switch_to_block_map, block_to_switches_map, nblocks, inter_block_entrance_switches)
		print("printing shortest paths : \n {}".format(shortest_paths))
		return shortest_paths

	## Runs LP to figure out how the fair share is distributed
	def load_balance(self, topology, switch_to_block_map, block_to_switches_map, nblocks, switch_to_switch_traffic_matrix, inter_block_entrance_switches, path_to_entry_switches):
		all_routing_weights = {}
		#for src_block in range(nblocks - 1):
			#for dst_block in range(src_block + 1, nblocks, 1):
				#all_routing_weights[(src_block_dst_bloc)]
		## first, derive the interblock connectivity
		interblock_connectivity = np.zeros((nblocks, nblocks,)) ## records the number of links between blocks
		for switch in switch_to_block_map.keys():
			block = switch_to_block_map[switch]
			for neighbor in topology[switch]:
				neighbor_block = switch_to_block_map[neighbor]
				if neighbor_block != block:
					interblock_connectivity[block][neighbor_block] += 1
					#assert(interblock_connectivity[block][neighbor_block] >= 1)

		for src_block in range(nblocks - 1):
			for dst_block in range(src_block + 1, nblocks, 1):
				switch_to_switch_traffic_matrix1 = {}
				switch_to_switch_traffic_matrix2 = {}
				
				for switch in block_to_switches_map[src_block]:
					switch_to_switch_traffic_matrix1[switch] = 0.
					for neighbor in block_to_switches_map[dst_block]:
						switch_to_switch_traffic_matrix1[switch] += switch_to_switch_traffic_matrix[switch][neighbor]
				for switch in block_to_switches_map[dst_block]:
					switch_to_switch_traffic_matrix2[switch] = 0.
					for neighbor in block_to_switches_map[src_block]:
						switch_to_switch_traffic_matrix2[switch] += switch_to_switch_traffic_matrix[switch][neighbor]

				capacity1 = interblock_connectivity[src_block][dst_block]
				capacity2 = interblock_connectivity[dst_block][src_block]
				entry_switches1 = inter_block_entrance_switches[(src_block, dst_block)]
				entry_switches2 = inter_block_entrance_switches[(dst_block, src_block)]

				all_routing_weights[(src_block, dst_block)] = self._split_traffic_between_block_pair(src_block, dst_block, capacity1, block_to_switches_map, entry_switches1, switch_to_switch_traffic_matrix1, path_to_entry_switches)
				all_routing_weights[(dst_block, src_block)] = self._split_traffic_between_block_pair(dst_block, src_block, capacity2, block_to_switches_map, entry_switches2, switch_to_switch_traffic_matrix2, path_to_entry_switches)
		return all_routing_weights
	##
	## topology - the adjacency list of the topology, NOTE: it's not adjacency matrix.
	def route(self, topology, switch_to_block_map, switch_to_switch_traffic_matrix):
		block_to_switches_map = {}
		for switch in switch_to_block_map.keys():
			block_id = switch_to_block_map[switch]
			if block_id not in block_to_switches_map:
				block_to_switches_map[block_id] = []
			block_to_switches_map[block_id].append(switch)
		nblocks = len(block_to_switches_map.keys())
		inter_block_entrance_switches = self.__identify_entrance_switches(topology, switch_to_block_map, block_to_switches_map, nblocks)
		all_paths_to_entry_switches = self.path_selection(topology, switch_to_block_map, block_to_switches_map, inter_block_entrance_switches)
		routing_weights = self.load_balance(topology, switch_to_block_map, block_to_switches_map, nblocks, switch_to_switch_traffic_matrix, inter_block_entrance_switches, all_paths_to_entry_switches)
		return routing_weights

	def evaluate_interblock_link_utilization(topology, switch_to_block_map, routing_weights, switch_to_switch_traffic_matrix):
		nswitches = len(switch_to_block_map.keys())
		block_map = {}
		for switch in switch_to_block_map.keys():
			block_map[switch_to_block_map[switch]] = True
		nblocks = len(block_map.keys())
		## Step 1 : initialize the interblock link utilizations
		interblock_traffic_load = {}
		switch_interblock_links = {}
		for switch in topology.keys():
			src_block = switch_to_block_map[switch]
			for neighbor in topology[switch]:
				dst_block = switch_to_block_map[neighbor]
				if dst_block != src_block:
					interblock_traffic_load[(switch, neighbor)] = 0.
					if (switch, dst_block) not in switch_interblock_links.keys():
						switch_interblock_links[(switch, dst_block)] = []
					switch_interblock_links[(switch, dst_block)].append((switch, neighbor))

		## Step 2 : count the interblock traffic in each link
		## add in the traffic load for the interpod traffic
		for src_block in range(nblocks - 1):
			for dst_block in range(src_block + 1, nblocks, 1):
				## combination 1, src_block - dst_block
				b2b_routing_weights = routing_weights[(src_block, dst_block)] ## now we get a map of routing weights
				for (switch, entry_switch) in b2b_routing_weights.keys():
					switch_traffic_to_dst_block = 0
					for neighbor in topology[switch]:
						if switch_to_block_map[neighbor] == dst_block:
							switch_traffic_dst_block += switch_to_switch_traffic_matrix[switch][neighbor]
					load_at_entry_switch = b2b_routing_weights[(switch, entry_switch)] * switch_traffic_dst_block
					number_of_links = len(switch_interblock_links[(entry_switches, dst_block)])
					for link in switch_interblock_links[(entry_switches, dst_block)]:
						interblock_traffic_load[link] += (load_at_entry_switch / number_of_links)
				## combination 2,  dst_block - src_block
				b2b_routing_weights = routing_weights[(dst_block, src_block)] ## now we get a map of routing weights
				for (switch, entry_switch) in b2b_routing_weights.keys():
					switch_traffic_to_dst_block = 0
					for neighbor in topology[switch]:
						if switch_to_block_map[neighbor] == src_block:
							switch_traffic_dst_block += switch_to_switch_traffic_matrix[switch][neighbor]
					load_at_entry_switch = b2b_routing_weights[(switch, entry_switch)] * switch_traffic_dst_block
					number_of_links = len(switch_interblock_links[(entry_switches, src_block)])
					for link in switch_interblock_links[(entry_switches, src_block)]:
						interblock_traffic_load[link] += (load_at_entry_switch / number_of_links)
		return interblock_traffic_load


'''
For each switch, either find out the destination block.

Condition 1 : if source block and destination blocks are the same, then route to destination via shortest paths.

Condition 2 : if source block and destination blocks are not the same, and I am currently at the

Condition 3 : if currently at the source switch, and destination is in the same block
## make decision on which transit switch to take to get to destination pod, packets will contain a tag

Condition 4 : if currently at the source switch, and destination is in a different block, and at an entrance switch
## route minimally to the destination

Condition 5 : if currently at the source switch, and destination is in a different block, and not at an entrance switch
## then make decision on which entrance router to use, and then tag the packet/flit with the entry switch, and then route minimally to the entry switch first


Condition 5 : if currently in an intermediate switch, and destination is in different block
## in transit to the entry switch, so first route to the entry switch

Condition 6 : if currently in a intermediate switch, and destination is in same block
## route minimally to the destination

Condition 7 : if destination is in different block, and currently at one of the entry switches
## route minimally
'''
