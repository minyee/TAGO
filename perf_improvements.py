import sys, os, math
import matplotlib.pyplot as plt
import numpy as np
from sets import Set

INFINITY = 1E9


'''
Reads in all the flow completion time (FCT) stats
'''
def read_in_fct_file(filename):
	flow_ids = []
	source_ids = []
	target_ids = []
	sent_bytes = []
	total_size_bytes = []
	start_time = []
	end_time = []
	duration = []
	completed = []
	try:
		with open(filename, 'r') as f:
			for line in f:
				row = line.split(',')
				if len(row) == 9:
					st = float(row[5])
					#if st >= 250000000 and st < 750000000:
					flow_ids.append(float(row[0]))
					source_ids.append(float(row[1]))
					target_ids.append(float(row[2]))
					sent_bytes.append(float(row[3]))
					total_size_bytes.append(float(row[4]))
					start_time.append(float(row[5]))
					end_time.append(float(row[6]))
					completed_or_not = row[8][:4] == 'TRUE'
					if completed_or_not:
						duration.append(float(row[7]))
					else:
						duration.append(INFINITY)
					completed.append(completed_or_not)
	except IOError:
		print("Could not open file : {}".format(filename))
	return (flow_ids, source_ids, target_ids, sent_bytes, total_size_bytes, start_time, end_time, duration, completed)

def read_in_smoothedRTT(filename):
	flow_ids = []
	number_of_packets_list = []
	smoothed_RTTs = []
	try:
		with open(filename, 'r') as f:
			for line in f:
				row = line.split(',')
				if len(row) == 3:
					flow_id = int(row[0])
					smoothed_RTT = float(row[1])
					number_of_packets = int(row[2])
					if (number_of_packets > 0):
						flow_ids.append(flow_id)
						smoothed_RTTs.append(smoothed_RTT)
						number_of_packets_list.append(number_of_packets)
					else:
						flow_ids.append(flow_id)
						smoothed_RTTs.append(float(INFINITY))
						number_of_packets_list.append(100)
	except IOError:
		print("Could not open file : {}".format(filename))
	return (flow_ids, smoothed_RTTs, number_of_packets_list)

def read_in_port_utilization(filename):
	port_utilization = {}
	try:
		with open(filename, 'r') as f:
			for line in f:
				#10,2,N,993886524,99.3886524
				row = line.split(',')
				if len(row) < 5 or line[0] == "#":
					continue
				else:
					source_id = int(row[0])
					dest_id = int(row[1])
					is_server_connection = (row[2]=='Y')
					utilization = float(row[4]) / 100
					port_utilization[(source_id, dest_id)] = (is_server_connection, utilization)
	except IOError:
		print("Could not open file : {}".format(filename))
	return port_utilization


def analyze_port_utilization(base_directory):
	current_working_directory = os.getcwd()
	os.chdir(base_directory)
	routing_port_utilization = {}
	routing_subdirs = filter(os.path.isdir, os.listdir("."))
	for routing_subdir in routing_subdirs:
		subdir_split = routing_subdir.split('_')
		if len(subdir_split) <= 1 or subdir_split[0] != "results":
			continue
		routing_scheme = subdir_split[1]
		routing_port_utilization[routing_scheme] = read_in_port_utilization(routing_subdir + "/" + "port_utilization.csv.log")
		#routing_rtt_results[routing_scheme] = read_in_smoothedRTT(results_subdir + "/" + app_name + "/" + routing_subdir + "/" + "smoothed_rtt.csv.log")

	switch_to_block_map, block_to_switches_map = read_in_switch_to_block_map(base_directory + "/../switch_to_block_file.txt")
	## arrange the links in order
	block_pairs_sorted = {}
	block_pair_links = {}
	
	for src_block in range(len(block_to_switches_map.keys())):
		for dst_block in range(len(block_to_switches_map.keys())):
			if src_block != dst_block:
				block_pair_links[(src_block, dst_block)] = []
				

	## now, assuming if all ports have same links
	for routing_scheme in routing_port_utilization.keys():
		for (src_switch, dst_switch) in routing_port_utilization[routing_scheme].keys():
			if routing_port_utilization[routing_scheme][(src_switch, dst_switch)][0]:
				continue
			src_block = switch_to_block_map[src_switch]
			dst_block = switch_to_block_map[dst_switch]
			if src_block != dst_block:
				block_pair_links[(src_block, dst_block)].append((src_switch, dst_switch,))
		break

	## finally, assign the order to each and every one of the links
	order = 0
	link_pair_order = {}
	string_link_pair = {}
	total_interblock_links = 0
	for src_block in range(len(block_to_switches_map.keys())):
		for dst_block in range(len(block_to_switches_map.keys())):
			if src_block != dst_block:
				for link in block_pair_links[(src_block, dst_block)]:
					link_pair_order[link] = order
					string_link_pair[link] = "{} -> {} - {}, {}".format(src_block, dst_block,link[0], link[1])
					order += 1
					total_interblock_links += 1
	fig = plt.figure()
	
	x_positions = [0]
	space_between_links = 2
	for i in range(1,total_interblock_links, 1):
		x_positions.append(x_positions[i - 1] + len(routing_port_utilization.keys()) + space_between_links)
	x_positions_initial = list(x_positions)
	for routing_scheme in routing_port_utilization.keys():
		y_vals = [0] * total_interblock_links
		x_str = [""] * total_interblock_links
		x = range(total_interblock_links)
		for link in link_pair_order.keys():
			index = link_pair_order[link]
			y_vals[index] = routing_port_utilization[routing_scheme][link][1]
			x_str[index] = string_link_pair[link]
		plt.bar(x_positions, y_vals, label="{}".format(routing_scheme))
		x_positions = [x + 1 for x in x_positions]
	x_ticks = []
	for i in range(len(x_positions)):
		x_ticks.append((x_positions[i] - 1 + x_positions_initial[i])/2.)
	plt.xticks(x_ticks, x_str, rotation=90)
	plt.legend()
	#plt.show()
		#for (src_switch, dst_switch) in routing_port_utilization[routing_scheme].keys():
		#	if 

	## before exiting, make sure we go back to the directory we came in from
	os.chdir(current_working_directory)
	return


def export_load_level_performance_to_file(output_filename, load_levels, performances_dictionary):
	str_builder = "load_level "
	vector_length = -1
	performance_keys = sorted(performances_dictionary.keys())
	for key in performance_keys:
		str_builder += (str(key) + " ")
		if vector_length < 0:
			vector_length = len(performances_dictionary[key])
		else:
			assert(len(performances_dictionary[key]) == vector_length)
	str_builder += "\n"
	for offset in range(vector_length):
		str_builder += (str(load_levels[offset]) + " ")
		for key in performance_keys:
			str_builder += (str(performances_dictionary[key][offset]) + " ")
		str_builder += "\n"
	with open(output_filename, "w+") as f:
		f.write(str_builder)
	return

def compute_weighted_median(array_of_vals, weights):
	assert(len(array_of_vals) == len(weights))
	tuple_pair_vector = [0] * len(array_of_vals)
	#print(weights)
	for i in range(len(array_of_vals)):
		tuple_pair_vector[i] = (array_of_vals[i], weights[i])
	sorted_tuple_pair_vector = sorted(tuple_pair_vector, key=lambda tup: tup[0])
	cumulative = np.cumsum([x[1] for x in sorted_tuple_pair_vector])
	#print(cumulative)
	median_location = cumulative[-1] / 2
	for i in range(len(sorted_tuple_pair_vector)):
		if cumulative[i] >= median_location:
			print i
			return sorted_tuple_pair_vector[i][0]
	return -1

## returns ave tput in order : zero unfinished, halfway unfinished, ignore unfinished
def compute_various_ave_throughputs(fct_tuples):
	tput_zero_unfinished_vector = []
	tput_halfway_unfinished_vector = []
	tput_ignore_unfinished_vector = []
	num_unfinished_flows = 0
	total_flows = len(fct_tuples[7])
	for i in range(total_flows):
		completed = fct_tuples[8][i]
		if completed:
			flow_size = fct_tuples[4][i]
			duration = fct_tuples[7][i]
			tput = float(flow_size) / float(duration)
			tput_zero_unfinished_vector.append(tput)
			tput_halfway_unfinished_vector.append(tput)
			tput_ignore_unfinished_vector.append(tput)
		else:
			tput_zero_unfinished_vector.append(0)
			completed_size = fct_tuples[3][i]
			duration = fct_tuples[7][i]
			tput = float(completed_size)/float(duration)
			tput_halfway_unfinished_vector.append(tput)
			num_unfinished_flows += 1
	ave_tput_zero_unfinished = sum(tput_zero_unfinished_vector) / len(tput_zero_unfinished_vector)
	ave_tput_halfway_unfinished = sum(tput_halfway_unfinished_vector) / len(tput_halfway_unfinished_vector)
	ave_tput_ignore_unfinished = sum(tput_ignore_unfinished_vector) / len(tput_ignore_unfinished_vector)
	return ave_tput_zero_unfinished, ave_tput_halfway_unfinished, ave_tput_ignore_unfinished

def analyze_improvements(topology_subdirectory, traffic_workload, export_directory):
	# check for the subdirectories
	os.chdir(topology_subdirectory + "/" + traffic_workload + "/")
	load_subdirs = filter(os.path.isdir, os.listdir("."))

	## ready all the dictionary that stores results
	load_level_fct_results = {}
	load_levels = []
	set_of_routing = Set()
	for load_subdir in load_subdirs:
		splitted_subdir = load_subdir.split('_')
		if len(splitted_subdir) == 2 and splitted_subdir[0] == "load":
			load_level_str = splitted_subdir[1].replace('p', '.')
			load_level = float(load_level_str)
			load_levels.append(load_level)
			os.chdir(topology_subdirectory + "/" + traffic_workload + "/" + load_subdir)
			routing_subdirs = filter(os.path.isdir, os.listdir("."))			
			for routing_subdir in routing_subdirs:
				if "results" not in routing_subdir[:7]:
					continue
				else:
					set_of_routing.add(routing_subdir.split('_')[1])
	print(set_of_routing)
	## now we know how many load levels are available, start loading the performance of each routing scheme in each load_level
	## now, initialize the relevant results

	load_levels = sorted(load_levels)
	ave_rtt_performances = {}
	ave_fct_performances = {}
	ave_tput_ignore_unfinished_performances = {} ## straight up ignores unfinished flows
	ave_tput_zero_unfinished_performances = {} ## straight up zeros out unfinished flows
	ave_tput_halfway_unfinished_performances = {} ## cotains the tput by counting unfinished flows as in progress
	tput_improvement = {}
	rtt_improvement = {}
	for routing in set_of_routing:
		ave_rtt_performances[routing] = [-1] * len(load_levels)
		ave_fct_performances[routing] = [-1] * len(load_levels)
		ave_tput_ignore_unfinished_performances[routing] = [-1] * len(load_levels)
		ave_tput_zero_unfinished_performances[routing] = [-1] * len(load_levels)
		ave_tput_halfway_unfinished_performances[routing] = [-1] * len(load_levels)
		tput_improvement[routing] = [-1] * len(load_levels)
		rtt_improvement[routing] = [-1] * len(load_levels)

	offset = 0
	for load_level in load_levels:
		load_level_subdir = "{:.1}".format(load_level)
		load_level_subdir = load_level_subdir.replace('.','p')
		load_level_subdir = "load_" + load_level_subdir
		os.chdir(topology_subdirectory + "/" + traffic_workload + "/" + load_level_subdir)
		routing_subdirs = filter(os.path.isdir, os.listdir("."))			
		for routing_subdir in routing_subdirs:
			if "results" in routing_subdir[:7]:
				routing_scheme = routing_subdir.split('_')[1]
				fcts = read_in_fct_file(routing_subdir + "/flow_completion.csv.log")
				rtts = read_in_smoothedRTT(routing_subdir + "/smoothed_rtt.csv.log")
				ave_fct = np.average(fcts[7])
				#ave_rtt = np.average(rtts[1], weights=rtts[2])
				#ave_rtt = compute_weighted_median(rtts[1], rtts[2])
				ave_rtt = compute_weighted_median(rtts[1], [1] * len(rtts[1]))
				ave_fct_performances[routing_scheme][offset] = ave_fct
				ave_rtt_performances[routing_scheme][offset] = ave_rtt / 1000.
				ave_tput_zero_unfinished, ave_tput_halfway_unfinished, ave_tput_ignore_unfinished = compute_various_ave_throughputs(fcts)
				ave_tput_ignore_unfinished_performances[routing_scheme][offset] = ave_tput_ignore_unfinished
				ave_tput_zero_unfinished_performances[routing_scheme][offset] = ave_tput_zero_unfinished
				ave_tput_halfway_unfinished_performances[routing_scheme][offset] = ave_tput_halfway_unfinished
		offset += 1

	offset = 0
	tput_dict = ave_tput_zero_unfinished_performances
	for load_level in load_levels:
		for routing_scheme in tput_dict.keys():
			tput_tasrc = tput_dict["traffic"][offset]
			rtt_tasrc = ave_rtt_performances["traffic"][offset]
			tput_routing = tput_dict[routing_scheme][offset]
			rtt_routing = ave_rtt_performances[routing_scheme][offset]
			tput_improvement[routing_scheme][offset] = (tput_tasrc - tput_routing) / tput_routing
			rtt_improvement[routing_scheme][offset] = (rtt_tasrc - rtt_routing) / rtt_routing
		offset += 1
	## finally, export to the subdirectory
	#export_load_level_performance_to_file(export_directory + "/" + "ave_rtt.txt", load_levels, ave_rtt_performances)
	#export_load_level_performance_to_file(export_directory + "/" + "ave_fct.txt", load_levels, ave_fct_performances)
	#export_load_level_performance_to_file(export_directory + "/" + "ave_tput_zero_unfinished.txt", load_levels, ave_tput_zero_unfinished_performances)
	#export_load_level_performance_to_file(export_directory + "/" + "ave_tput_ignore_unfinished.txt", load_levels, ave_tput_ignore_unfinished_performances)
	#export_load_level_performance_to_file(export_directory + "/" + "ave_tput_halfway_unfinished.txt", load_levels, ave_tput_halfway_unfinished_performances)
	return tput_improvement, rtt_improvement

results_subdir = "/Users/minyee/src/jocn_reconf_expander/routing/netbench_simulations"
topology_name = "dfly_g5_a16_h1"
topology_name = "sdfly_g5_a16_h1"
#topology_name = "skewedexpander_g5_a16_h1_m10"
#topology_name = "uexpander_g5_a16_h1_m10"




#workload_name = "dfly_uniform_0p9"
#workload_name = "dfly_adversarial_0p9"
#workload_name = "dfly_singleswitch_adversarial_0p9"
#workload_name = "stencil27P_4_4_5"
#workload_name = "AMG1728_Nekbone1024_linear"
#workload_name = "AMG1728_Nekbone1024_randomized"
#workload_name = "fbHadoop_linear"
#workload_name = "dfly_uniform_0p9"

all_workloads = ["dfly_singleswitch_adversarial_0p9", "stencil27P_4_4_5" , "AMG1728_Nekbone1024_linear", "AMG1728_Nekbone1024_randomized", "fbHadoop_linear"]
#all_workloads = ["dfly_singleswitch_adversarial_0p9", "stencil27P_4_4_5"]
performance_summary_subdir = "/Users/minyee/src/jocn_reconf_expander/routing/netbench_simulations/simulations_summary"
'''
if not os.path.exists(performance_summary_subdir):
	os.mkdir(performance_summary_subdir)
if not os.path.exists(performance_summary_subdir + "/" + topology_name):
	os.mkdir(performance_summary_subdir + "/" + topology_name)
if not os.path.exists(performance_summary_subdir + "/" + topology_name + "/" + workload_name):
	os.mkdir(performance_summary_subdir + "/" + topology_name + "/" + workload_name)
'''
tput_improvement_all_apps = {}
rtt_improvement_all_apps = {}
for workload_name in all_workloads:
	tput_improvement, rtt_improvement = analyze_improvements(results_subdir + "/" + topology_name, workload_name, performance_summary_subdir + "/" + topology_name + "/" + workload_name) 
	tput_improvement_all_apps[workload_name] = tput_improvement
	rtt_improvement_all_apps[workload_name] = rtt_improvement

#fig = plt.figure()
fig, ax = plt.subplots(nrows=1, ncols=len(all_workloads), squeeze=True)
index = 0
routing_keys = tput_improvement.keys()
for workload_name in all_workloads:
	tput_improvement = tput_improvement_all_apps[workload_name]
	routing_keys = tput_improvement.keys()
	for routing in routing_keys:
		ax[index].plot(tput_improvement[routing])
	ax[index].set_title(workload_name)
	index += 1
	plt.legend(routing_keys)

index = 0
fig, ax = plt.subplots(nrows=1, ncols=len(all_workloads), squeeze=True)
index = 0
routing_keys = tput_improvement.keys()
for workload_name in all_workloads:
	rtt_improvement = rtt_improvement_all_apps[workload_name]
	routing_keys = rtt_improvement.keys()
	for routing in routing_keys:
		ax[index].plot(rtt_improvement[routing])
	ax[index].set_title(workload_name)
	index += 1
	plt.legend(routing_keys)
#plt.title("Throughput Improvement (Fraction)")
'''
fig = plt.figure()
for routing in routing_keys:
	plt.plot(rtt_improvement[routing])
plt.legend(routing_keys)
plt.title("RTT Improvement (Fraction)")
'''
plt.show()

