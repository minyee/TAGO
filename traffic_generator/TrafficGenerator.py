import numpy as np
#import UniformGroupDragonfly

class TrafficGenerator(object):
	def __init__(self, topology_instance):
		self.topology = topology_instance
		return

	'''
	Given a orig_size x orig_size matrix, rescales it to a new_size x new_size matrix
	'''
	def _rescale_square_matrix(self, orig_matrix, new_size):
		orig_size = len(orig_matrix)
		# if new_size is the same as original size, then do nothing
		if (new_size == orig_size):
			return orig_matrix
		new_matrix = [0] * new_size
		for i in range(new_size):
			new_matrix[i] = [0] * new_size
		if new_size > orig_size:
			ratio = float(new_size) / float(orig_size)
			for i in range(new_size):
				x_val = int(float(i) / ratio)
				for j in range(new_size):
					y_val = int(float(j) / ratio)
					#print "(i, j) = ({}, {})".format(i, j)
					#print "(x_val, y_val) = ({}, {})".format(x_val, y_val)
					new_matrix[i][j] = orig_matrix[x_val][y_val] / (ratio * ratio)
		else:
			# compression
			ratio = float(orig_size) / float(new_size)
			for i in range(orig_size):
				x_val = int(float(i) / ratio)
				for j in range(orig_size):
					y_val = int(float(j) / ratio)
					new_matrix[x_val][y_val] += orig_matrix[i][j]
		for i in range(new_size):
			new_matrix[i][i] = 0.
		return new_matrix

	## generates a zero traffic matrix for now
	def generate_traffic(self):
		num_switches = topology.get_total_num_switches()
		traffic_matrix = np.zeros((num_switches, num_switches))
		return traffic_matrix

	def compute_interblock_traffic_from_switch_traffic(self, traffic_matrix, block_to_switches_map):
		num_blocks = len(block_to_switches_map.keys())
		block_traffic_matrix = np.zeros((num_blocks, num_blocks))
		for i in range(num_blocks):
			for j in range(num_blocks):
				if i != j:
					for src_switch in block_to_switches_map[i]:
						for dst_switch in block_to_switches_map[j]:
							block_traffic_matrix[i][j] += traffic_matrix[src_switch][dst_switch]
		return block_traffic_matrix

	def to_string(self):
		return "original_traffic_generator"