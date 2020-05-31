import TrafficGenerator, sys, os
sys.path.append('../')
import UniformGroupDragonfly
import numpy as np


class DragonflyAdversarialSingleSwitchTrafficGenerator(TrafficGenerator.TrafficGenerator):
	def __init__(self, topology, intergroup_traffic_fraction=0.5):
		TrafficGenerator.TrafficGenerator.__init__(self, topology)
		assert(intergroup_traffic_fraction >= 0 and intergroup_traffic_fraction <= 1)
		self.intergroup_traffic_fraction = float(intergroup_traffic_fraction)
		return

	def generate_traffic(self):
		num_switches = self.topology.get_total_num_switches()
 		traffic_matrix = np.zeros((num_switches, num_switches))
 		num_blocks = self.topology.get_num_blocks()
 		switch_to_block_id_map = self.topology.get_switch_id_to_block_id_map()
		block_to_switches_map = self.topology.get_block_id_to_switch_ids()

 		total_probability_between_blocks = self.intergroup_traffic_fraction / num_blocks
 		## fill in the inter-block traffic
 		for block in range(num_blocks):
 			target_block = (block + 1) % num_blocks
 			#switch_to_switch_total_traffic = total_probability_between_blocks / (len(block_to_switches_map[block]) * len(block_to_switches_map[target_block]))
 			min_traffic_so_far = 100000.
 			src_switch = -1
 			for swid in block_to_switches_map[block]:
 				src_sum = sum(traffic_matrix[swid])
 				if src_sum < min_traffic_so_far:
 					src_switch = swid
 					min_traffic_so_far = src_sum
 			min_traffic_so_far = 100000.
 			dst_switch = -1
 			for swid in block_to_switches_map[target_block]:
 				dst_sum = sum(traffic_matrix[swid])
 				if dst_sum < min_traffic_so_far:
 					dst_switch = swid
 					min_traffic_so_far = dst_sum
 			traffic_matrix[src_switch][dst_switch] = total_probability_between_blocks

 		## fill in the intra-block traffic
 		intrablock_total_traffic_per_block = (1 - self.intergroup_traffic_fraction) / num_blocks
 		for block in range(num_blocks):
 			num_entries = len(block_to_switches_map[block]) * (len(block_to_switches_map[block]) - 1)
 			traffic_entry = intrablock_total_traffic_per_block / num_entries
 			for src_switch in block_to_switches_map[block]:
 				for dst_switch in block_to_switches_map[block]:
 					if src_switch != dst_switch:
 						traffic_matrix[src_switch][dst_switch] = traffic_entry
 		return traffic_matrix

 	def to_string(self):
 		name = "{:.2}".format(self.intergroup_traffic_fraction)
 		name = name.replace('.', 'p')
 		return "dfly_singleswitch_adversarial_{}".format(name)
