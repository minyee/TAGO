import TrafficGenerator, sys, os
sys.path.append('../')
import UniformGroupDragonfly
import numpy as np


class DragonflyLoadSingleGlobalLinkTrafficGenerator(TrafficGenerator.TrafficGenerator):
	def __init__(self, topology):
		TrafficGenerator.TrafficGenerator.__init__(self, topology)
		return

	def generate_traffic(self):
		num_switches = self.topology.get_total_num_switches()
 		traffic_matrix = np.zeros((num_switches, num_switches))
 		num_blocks = self.topology.get_num_blocks()
 		switch_to_block_id_map = self.topology.get_switch_id_to_block_id_map()
		block_to_switches_map = self.topology.get_block_id_to_switch_ids()

		adj_matrix = self.topology.get_adjacency_matrix()

		number_of_global_links = 0
		for i in range(num_switches):
			i_block = switch_to_block_id_map[i]
			for j in range(num_switches):
				j_block = switch_to_block_id_map[j]
				if i_block != j_block and adj_matrix[i][j] > 0:
					number_of_global_links += adj_matrix[i][j]

		entry_probability = 1./number_of_global_links

		for i in range(num_switches):
			i_block = switch_to_block_id_map[i]
			for j in range(num_switches):
				j_block = switch_to_block_id_map[j]
				if i_block != j_block and adj_matrix[i][j] > 0:
					traffic_matrix[i][j] = adj_matrix[i][j] * entry_probability
		print traffic_matrix
 		return traffic_matrix

 	def to_string(self):
 		return "dfly_strain_single_link"
