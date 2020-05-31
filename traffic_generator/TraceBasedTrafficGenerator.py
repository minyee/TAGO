# given a traffic trace file produces a rank to rank traffic matrix
# too slow, try to make this function go faster

import TrafficGenerator, sys, os, math, copy, random
sys.path.append('../')
import UniformGroupDragonfly
import numpy as np
#import matplotlib as mpl
#import matplotlib.pyplot as plt
#import matplotlib.image as img
#from matplotlib import cm
#import seaborn as sns; sns.set() 


SEED = 12538

class TraceBasedTrafficGenerator(TrafficGenerator.TrafficGenerator):
	def __init__(self, topology, trace_files, trace_alias, randomize_job_mapping=False):
		TrafficGenerator.TrafficGenerator.__init__(self, topology)
		self.trace_file_list = trace_files
		self.trace_aliases = trace_alias
		assert(len(trace_files) == len(trace_alias))
		self.randomize_job_mapping = randomize_job_mapping
		return

	# read in the trace files from the arpa-e directory in the format of booksim
	def _read_trace_file(self, trace_file_name):
		traffic_entries = {}
		max_entry = 0
		with open(trace_file_name) as f:
			for line in f:
				values = line.split(" ")
				source = int(values[2])
				dest = int(values[3])
				if source not in traffic_entries:
					traffic_entries[source] = {}
				if dest not in traffic_entries:
					traffic_entries[dest] = {}
				max_entry = max(max_entry, dest, source)
				size = int(values[4])
				if dest in traffic_entries[source]:
					traffic_entries[source][dest] += size
				else: 
					traffic_entries[source][dest] = size
		## next, we need to compress the ids so that it is contiguous 
		all_keys = sorted(traffic_entries.keys())
		reshifted_traffic_entries = {}
		# maps unshifted key to corresponding shifted key
		# shifted key is what we output in this function, unshifted is what the trace feeds us back
		key_shift_map = {} 
		for i in range(len(all_keys)):
			key_shift_map[all_keys[i]] = i
			reshifted_traffic_entries[i] = {}
		for shifted_src in range(len(all_keys)):
			unshifted_src = all_keys[shifted_src]
			for unshifted_dst in traffic_entries[unshifted_src]:
				shifted_dst = key_shift_map[unshifted_dst]
				reshifted_traffic_entries[shifted_src][shifted_dst] = traffic_entries[unshifted_src][unshifted_dst]
		return reshifted_traffic_entries

	def generate_traffic(self):
		num_switches = self.topology.get_total_num_switches()
		num_blocks = self.topology.get_num_blocks()
		switch_to_block_id_map = self.topology.get_switch_id_to_block_id_map()
		block_to_switches_map = self.topology.get_block_id_to_switch_ids()

		trace_traffic_entries = []
		total_ranks = 0
		trace_id_rank_id_pairs = []
		for trace_id in range(len(self.trace_file_list)):
			trace_filename = self.trace_file_list[trace_id]
			traffic_entries = self._read_trace_file(trace_filename)
			total_ranks += len(traffic_entries.keys())
			trace_traffic_entries.append(traffic_entries)
		all_global_ranks_vector = range(total_ranks)	
		rank2rank_tm = np.zeros((total_ranks, total_ranks))
		if self.randomize_job_mapping:
			random.seed(SEED)
			random.shuffle(all_global_ranks_vector)

		## now we go on to map each rank of trace onto the global ranks
		global_rank_to_trace_rank_pairs_map = {}
		trace_rank_pairs_to_global_rank_map = {}
		offset = 0
		for trace_id in range(len(self.trace_file_list)):
			for rank in range(len(trace_traffic_entries[trace_id].keys())):
				global_id = all_global_ranks_vector[offset]
				trace_rank_pair = (trace_id, rank)
				global_rank_to_trace_rank_pairs_map[global_id] = trace_rank_pair
				trace_rank_pairs_to_global_rank_map[trace_rank_pair] = global_id
				offset += 1

		## finally, go and occupy the traffic matrix
		for trace_id in range(len(self.trace_file_list)):
			for rank in range(len(trace_traffic_entries[trace_id].keys())):
				src = trace_rank_pairs_to_global_rank_map[(trace_id, rank)]
				for dst_rank in trace_traffic_entries[trace_id][rank].keys():
					dst = trace_rank_pairs_to_global_rank_map[(trace_id, dst_rank)]
					rank2rank_tm[src][dst] = trace_traffic_entries[trace_id][rank][dst_rank]
		switch2switch_tm = self._rescale_square_matrix(rank2rank_tm, num_switches)
		## finally, normalize the traffic matrix
		traffic_sum = sum([sum(x) for x in switch2switch_tm])
		for i in range(num_switches):
			for j in range(num_switches):
				switch2switch_tm[i][j] /= traffic_sum
		return switch2switch_tm

	def to_string(self):
		name = ""
		for trace_name in self.trace_aliases:
			name += trace_name + "_"
		if self.randomize_job_mapping:
			name += "randomized"
		else:
			name += "linear"
		return name

'''
number_links_between_each_group = 4
number_of_groups = 5
number_of_switches_per_group = (number_of_groups - 1) * number_links_between_each_group
uniform_dfly = UniformGroupDragonfly.UniformGroupDragonfly(number_of_groups, number_of_switches_per_group, number_links_between_each_group)
uniform_dfly.design_full_topology()

trace_subdir = "/Users/minyee/src/arpa_e/traces/"
traces = ["AMG_1728", "nekbone_1024_shortened_original"]
traces = ["facebook_hadoop_6690.txt"]
traces = [trace_subdir + x for x in traces]
trace_aliases = ["AMG1728", "Nekbone1024"]
trace_aliases = ["facebook hadoop"]
trace_traffic_generator = TraceBasedTrafficGenerator(uniform_dfly, traces, trace_aliases, randomize_job_mapping=True)
interswitch_tm = trace_traffic_generator.generate_traffic()


interblock_tm = np.zeros((number_of_groups, number_of_groups))
num_switches = len(interswitch_tm)
for i in range(num_switches):
	src_group = i / number_of_switches_per_group
	for j in range(num_switches):
		dst_group = j / number_of_switches_per_group
		#if src_group != dst_group:
		interblock_tm[src_group][dst_group] += interswitch_tm[i][j]
### start plotting

fig = plt.figure()
#plt.imshow(interswitch_tm)
sns.heatmap(interswitch_tm, robust=True)
plt.title("Interswitch TM", fontsize=13)


fig = plt.figure()
#plt.imshow(interswitch_tm)
sns.heatmap(interblock_tm, robust=True)
plt.title("Interblock TM", fontsize=13)
plt.show()
print("filename : {}".format(trace_traffic_generator.to_string()))
'''
