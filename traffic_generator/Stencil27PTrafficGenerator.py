import TrafficGenerator, sys, os
sys.path.append('../')
import UniformGroupDragonfly
import numpy as np
import copy

class Stencil27PTrafficGenerator(TrafficGenerator.TrafficGenerator):
	'''
	# nx - a tuple or list of number of entries in each dimension
	'''
	def __init__(self, topology, dimensions):
		TrafficGenerator.TrafficGenerator.__init__(self, topology)
		assert(len(dimensions) == 3)
		self.dimensions = dimensions
		self.total_grid_points = 1
		for n in dimensions:
			self.total_grid_points *= n
		self.index_to_coordinate = {}
		self.coordinate_to_index = {}
		return

	def print_matrix(self, tm):
		size = len(tm)
		str_builder = ""
		for i in range(size):
			for j in range(size):
				str_builder += "{} ".format(tm[i][j])
			str_builder += "\n"
		print(str_builder)

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

	def __increment_grid_point(self, current_point, dimensions):
		next_point = list(copy.deepcopy(current_point))
		current_dim = 2
		proceed_to_next_dim = True
		while proceed_to_next_dim and current_dim >= 0:
			if next_point[current_dim] + 1 >= dimensions[current_dim]:
				next_point[current_dim] = 0
				current_dim -= 1
			else:
				next_point[current_dim] += 1
				proceed_to_next_dim = False
		return tuple(next_point)

	def __local_3D_neighbors(self, coordinate, dimensions):
		current_layer_coords = []
		coordinate_list = list(coordinate)
		n1 = copy.deepcopy(coordinate_list)
		n1[0] += 1
		n2 = copy.deepcopy(coordinate_list)
		n2[0] -= 1
		n3 = copy.deepcopy(coordinate_list)
		n3[1] += 1
		n4 = copy.deepcopy(coordinate_list)
		n4[1] -= 1
		n5 = copy.deepcopy(coordinate_list)
		n5[0] += 1
		n5[1] += 1
		n6 = copy.deepcopy(coordinate_list) 
		n6[0] += 1
		n6[1] -= 1
		n7 = copy.deepcopy(coordinate_list) 
		n7[0] -= 1
		n7[1] -= 1
		n8 = copy.deepcopy(coordinate_list) 
		n8[0] -=1
		n8[1] += 1
		n9 = copy.deepcopy(coordinate_list)
		potential_points = [n1, n2, n3, n4, n5, n6, n7, n8,n9]
		top_layer_points = [copy.deepcopy(x) for x in potential_points]
		for coord in top_layer_points:
			coord[2] += 1
		low_layer_points = [copy.deepcopy(x) for x in potential_points]
		for coord in low_layer_points:
			coord[2] -= 1
		potential_points = potential_points + top_layer_points + low_layer_points
		actual_neighbors = []
		for point  in potential_points:
			valid = True
			for dim in range(len(dimensions)):
				if point[dim] < 0 or point[dim] >= dimensions[dim]:
					valid = False
					break
			if valid:
				actual_neighbors.append(tuple(point))
		return actual_neighbors

	## finds the neighbor in each grid point
	def _find_neighbors_in_grids(self):
		coordinate = (0, 0, 0)
		## initialize the grid points with switch indices
		for i in range(self.total_grid_points):
			self.coordinate_to_index[coordinate] = i
			self.index_to_coordinate[i] = coordinate
			coordinate = self.__increment_grid_point(coordinate, self.dimensions)
		neighbors_of_index = {}
		# next, proceed to find the set of neighbors 
		for i in range(self.total_grid_points):
			coordinate = self.index_to_coordinate[i]
			neighbors = self.__local_3D_neighbors(coordinate, self.dimensions)
			neighbors_of_index[i] = [self.coordinate_to_index[x] for x in neighbors]
		return neighbors_of_index

	def generate_traffic(self):
		num_switches = self.topology.get_total_num_switches()
		num_blocks = self.topology.get_num_blocks()
		## Step 1 : initialize the node to node traffic matrix, which is different from the final switch to switch traffic matrix
		n2n_tm = np.zeros((self.total_grid_points, self.total_grid_points))
		neighbors_of_node = self._find_neighbors_in_grids()
		for src_node in neighbors_of_node.keys():
			all_neighbors = neighbors_of_node[src_node]
			for neighbor_node in all_neighbors:
				if neighbor_node != src_node:
					n2n_tm[neighbor_node][src_node] += 1.
		#self.print_matrix(n2n_tm)
		## Step 2 : convert the node 2 node TM into a switch to switch TM.
		traffic_matrix = self._rescale_square_matrix(n2n_tm, num_switches)
		## Step 3 : finally, normalize the traffic matrix
		traffic_sum = sum([sum(x) for x in traffic_matrix])
		for i in range(num_switches):
			for j in range(num_switches):
				traffic_matrix[i][j] /= traffic_sum

		return traffic_matrix

	def to_string(self):
		return "stencil27P_{}_{}_{}".format(self.dimensions[0], self.dimensions[1], self.dimensions[2])
