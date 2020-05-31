import sys, os, math
import matplotlib.pyplot as plt
import numpy as np

INFINITY = 1E15

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
					flow_ids.append(flow_id)
					smoothed_RTTs.append(smoothed_RTT)
					number_of_packets_list.append(number_of_packets)
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

def read_in_switch_to_block_map(filename):
	switch_to_block_map = {}
	block_to_switches_map = {}
	try: 
		with open(filename, 'r') as f:
			for line in f:
				row = line.split(',')
				if len(row) < 2 or line[0] == "#":
					continue
				else:
					switch_id = int(row[0])
					block_id = int(row[1])
					switch_to_block_map[switch_id] = block_id
					if block_id not in block_to_switches_map.keys():
						block_to_switches_map[block_id] = []
					block_to_switches_map[block_id].append(switch_id)
	except IOError:
		print("Unable to open file")
	return switch_to_block_map, block_to_switches_map

'''
## returns the x and y values of a cdf plot
'''
def normalized_cdf(array_of_values, nbins):
	hist, bin_edges = np.histogram(array_of_values, bins=nbins, density=False)
	total_amount = sum(hist)
	hist = [float(x)/total_amount for x in np.cumsum(hist)]
	hist = [0, ] + hist
	return (bin_edges, hist)

def normalized_weighted_cdf(array_of_values, weights, nbins):
	assert(len(array_of_values) == len(weights))
	sum_weights = sum(weights)
	weights_normalized = [float(x)/sum_weights for x in weights]
	hist, bin_edges = np.histogram(array_of_values, bins=nbins, weights=weights_normalized, density=True)
	total_amount = sum(hist)
	hist = [float(x)/total_amount for x in np.cumsum(hist)]
	hist = [0, ] + hist
	return (bin_edges, hist)	

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

def plot_routing_scheme_different_load_levels(directory_name, routing_scheme, load_levels, nbins=50):

	# check for the subdirectories
	os.chdir(results_subdir + "/" + app_name)
	load_levels_strings = ["{:.1}".format(x) for x in load_levels]
	load_subdirs = ["load_"+x.replace('.','p') for x in load_levels_strings]
	load_fct_results = {}
	load_rtt_results = {}
	for load_level in load_levels:
		routing_subdir = "results_" + routing_scheme
		load_level_str = "{:.1}".format(load_level)
		load_level_str = load_level_str.replace('.', 'p')
		load_level_str = "load_" + load_level_str
		load_fct_results[load_level] = read_in_fct_file(directory_name + "/" + load_level_str + "/" + routing_subdir + "/" + "flow_completion.csv.log")
		#print("Done with reading fct information {}".format(routing_scheme))
		load_rtt_results[load_level] = read_in_smoothedRTT(directory_name + "/" + load_level_str + "/" + routing_subdir + "/" + "smoothed_rtt.csv.log")
		#print("Done with reading in all files in {}".format(routing_scheme))

	fig = plt.figure()
	legends = []
	markers = ['x', 'o', 'd', '1', 'v']
	marker_offset = 0
	for load_level in load_levels:
		fct = load_fct_results[load_level][7]
		if (len(fct) == 0):
			continue
		xvals, yvals = normalized_cdf([np.log10(x) for x in fct], nbins)
		plt.plot(xvals, yvals, marker=markers[marker_offset])
		legends.append(load_level)
		marker_offset = (marker_offset + 1) % len(markers)
	plt.legend(legends, fontsize=12)
	plt.ylim(ymin=0, ymax=1)
	plt.ylabel("CDF", fontsize=11)
	plt.xlabel("FCT (ns)", fontsize=11)
	plt.title("Flow Completion Time", fontsize=14)

	fig = plt.figure()
	legends = []
	markers = ['x', 'o', 'd', '1', 'v']
	marker_offset = 0
	for load_level in load_levels:
		rtt = load_rtt_results[load_level][1]
		num_packets = load_rtt_results[load_level][2]
		if (len(rtt) == 0):
			continue
		xvals, yvals = normalized_weighted_cdf(rtt, num_packets, nbins)
		plt.plot(xvals, yvals, marker=markers[marker_offset])
		legends.append(load_level)
		marker_offset = (marker_offset + 1) % len(markers)
	plt.legend(legends, fontsize=12)
	plt.ylim(ymin=0, ymax=1)
	plt.ylabel("CDF", fontsize=11)
	plt.xlabel("RTT (ns)", fontsize=11)
	plt.title("Packet RTT", fontsize=14)
	#analyze_port_utilization(results_subdir + "/" + app_name,)
	plt.show()
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
		for key in performance_keys:
			str_builder += (str(performances_dictionary[key][offset]) + " ")
		str_builder += "\n"
	with open(output_filename, "w+") as f:
		f.write(str_builder)
	return



results_subdir = "/Users/minyee/src/jocn_reconf_expander/routing/netbench_simulations"
app_name = "toy_example"
app_name = "unifdfly_g4_a3_h2/dfly_uniform_0p5"
app_name = "unifdfly_g4_a3_h2/dfly_uniform_0p9"
app_name = "unifdfly_g10_a72_h1/dfly_uniform_0p9"
#app_name = "unifdfly_g4_a3_h2/dfly_adversarial_0p9"
#app_name = "unifdfly_g4_a3_h2/dfly_strain_single_link"
#app_name = "dfly_g5_a16_h1/dfly_uniform_0p5" + "/load_0p9"
app_name = "dfly_g5_a16_h1/dfly_uniform_0p9" 
nbins = 50

routing_scheme = "traffic_aware_src"
routing_scheme = "forward"
plot_routing_scheme_different_load_levels(results_subdir + "/" + app_name, "traffic_aware_src", [0.1, 0.3, 0.5, 0.7, 0.9], nbins=50)


#for in range():

exit()

#exit()
# check for the subdirectories
os.chdir(results_subdir + "/" + app_name)
routing_subdirs = filter(os.path.isdir, os.listdir("."))
routing_fct_results = {}
routing_rtt_results = {}
for routing_subdir in routing_subdirs:
	subdir_split = routing_subdir.split('_')
	if len(subdir_split) <= 1 or subdir_split[0] != "results":
		continue
	routing_scheme = subdir_split[1]
	routing_fct_results[routing_scheme] = read_in_fct_file(results_subdir + "/" + app_name + "/" + routing_subdir + "/" + "flow_completion.csv.log")
	print("Done with reading fct information {}".format(routing_scheme))
	routing_rtt_results[routing_scheme] = read_in_smoothedRTT(results_subdir + "/" + app_name + "/" + routing_subdir + "/" + "smoothed_rtt.csv.log")
	print("Done with reading in all files in {}".format(routing_scheme))

fig = plt.figure()
legends = []
markers = ['x', 'o', 'd', '1', 'v']
marker_offset = 0
for routing_scheme in routing_fct_results.keys():
	fct = routing_fct_results[routing_scheme][7]
	if (len(fct) == 0):
		continue
	xvals, yvals = normalized_cdf([np.log10(x) for x in fct], nbins)
	plt.plot(xvals, yvals, marker=markers[marker_offset])
	legends.append(routing_scheme)
	marker_offset = (marker_offset + 1) % len(markers)
plt.legend(legends, fontsize=12)
plt.ylim(ymin=0, ymax=1)
plt.ylabel("CDF", fontsize=11)
plt.xlabel("FCT (ns)", fontsize=11)
plt.title("Flow Completion Time", fontsize=14)

fig = plt.figure()
legends = []
markers = ['x', 'o', 'd', '1', 'v']
marker_offset = 0
for routing_scheme in routing_rtt_results.keys():
	rtt = routing_rtt_results[routing_scheme][1]
	num_packets = routing_rtt_results[routing_scheme][2]
	if (len(rtt) == 0):
		continue
	xvals, yvals = normalized_weighted_cdf(rtt, num_packets, nbins)
	plt.plot(xvals, yvals, marker=markers[marker_offset])
	legends.append(routing_scheme)
	marker_offset = (marker_offset + 1) % len(markers)
plt.legend(legends, fontsize=12)
plt.ylim(ymin=0, ymax=1)
plt.ylabel("CDF", fontsize=11)
plt.xlabel("RTT (ns)", fontsize=11)
plt.title("Packet RTT", fontsize=14)

#analyze_port_utilization(results_subdir + "/" + app_name,)

plt.show() 
