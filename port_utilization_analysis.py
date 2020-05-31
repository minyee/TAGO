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
	os.chdir(current_working_directory)
	return

def export_intergrouplinkutilization_as_pdf(output_filename, results_collection, link_utilization_key):
	str_builder = "link_utilization "
	results_vector_keys = sorted(results_collection.keys())
	for results_key in results_vector_keys:
		if results_key == link_utilization_key:
			continue
		print("length of link utilization x : {} y is {}".format(len(results_collection[link_utilization_key]), len (results_collection[results_key])))
		assert(len(results_collection[link_utilization_key]) == len (results_collection[results_key]))
		str_builder += "{} ".format(results_key)
	str_builder += "\n"
	link_utilization_vector = results_collection[link_utilization_key]
	number_of_entries = len(link_utilization_vector)

	for i in range(number_of_entries):
		str_builder += "{} ".format(link_utilization_vector[i])
		for results_key in results_vector_keys:
			if results_key == link_utilization_key:
				continue
			str_builder += "{} ".format(results_collection[results_key][i])
		str_builder += "\n"
	with open(output_filename, "w+") as f:
		f.write(str_builder)
	return

def export_intergrouplinkutilization_dist(output_filename, results_collection):
	str_builder = ""
	results_vector_keys = sorted(results_collection.keys())
	num_entries = -1
	for results_key in results_vector_keys:
		str_builder += "{} ".format(results_key)
		num_entries = max(len(results_collection[results_key]), num_entries)
	str_builder += "\n"
	
	for results_key in results_vector_keys:
		current_len = len(results_collection[results_key])
		if current_len < num_entries:
			## pad with zeros
			padded_zeros = [0.] * (num_entries - current_len)
			results_collection[results_key] = padded_zeros + results_collection[results_key] 
			assert(num_entries == len(results_collection[results_key]))
	for i in range(num_entries):
		for results_key in results_vector_keys:
			str_builder += "{} ".format(results_collection[results_key][i])
		str_builder += "\n"
	with open(output_filename, "w+") as f:
		f.write(str_builder)
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

def process_pdf_link_utilization(port_utilization_vector, switch_to_block_map, nbins):
	bins = np.linspace(0, 1, num=nbins, endpoint=True, )
	frequency = [0] * (len(bins) - 1)
	interblock_utilizations = []
	for (src_switch, dst_switch) in port_utilization_vector:
		(is_server_connection, utilization) = port_utilization_vector[(src_switch, dst_switch)]
		
		if not is_server_connection:
			src_block = switch_to_block_map[src_switch]
			dst_block = switch_to_block_map[dst_switch]	
			if src_block != dst_block:
				interblock_utilizations.append(utilization)
				for i in range(len(bins) - 1):
					if utilization >= bins[i] and utilization < bins[i + 1]:
						frequency[i] += 1
						break
	total_entries = sum(frequency)
	prob = [float(x)/total_entries for x in frequency]
	return (bins[:-1], prob, interblock_utilizations)

def jains_fairness(utilization_vector):
	squared_sum = 0.
	linear_sum = 0.
	for util in utilization_vector:
		squared_sum += (util * util)
		linear_sum += util
	if squared_sum == 0:
		return 0
	fairness = (linear_sum * linear_sum) / (squared_sum * len(utilization_vector))
	return fairness

def plot_intergroup_link_utilizations(results_subdir, topol_name, app_name, load_level, routing_algorithm_names, nbins=50):
	app_subdir = results_subdir + "/" + topol_name + "/" + app_name
	topol_subdir = results_subdir + "/" + topol_name
	switch_to_block_map, block_to_switches_map = read_in_switch_to_block_map(topol_subdir + "/switch_to_block_file.txt")
	routing_algorithm_port_utilization_pdf = {}
	routing_algorithm_port_utilization = {}
	for routing_algorithm_name in routing_algorithm_names:
		port_utilization_filename = app_subdir + "/load_" + load_level + "/" + "results_{}".format(routing_algorithm_name) + "/port_utilization.csv.log"
		port_utilization_vector = read_in_port_utilization(port_utilization_filename)
		
		x, y, interblock_utilizations = process_pdf_link_utilization(port_utilization_vector, switch_to_block_map, nbins)
		print interblock_utilizations
		routing_algorithm_port_utilization_pdf[routing_algorithm_name] = (x, y)
		routing_algorithm_port_utilization[routing_algorithm_name] = sorted(interblock_utilizations)
	fig, ax = plt.subplots(len(routing_algorithm_names), 1)
	ax_offset = 0
	for routing_algorithm_name in routing_algorithm_names:
		(x, y) = routing_algorithm_port_utilization_pdf[routing_algorithm_name]
		bar_width = (x[1] - x[0])/1.
		print("bar width : {}".format(bar_width))
		ax[ax_offset].bar(x, y, align='edge', width=bar_width)
		ax[ax_offset].set_title("{}".format(routing_algorithm_name), fontsize=12)
		ax[ax_offset].set_ylim(ymin=0, ymax=0.9)
		ax[ax_offset].set_xlim(xmax=1, xmin=0)
		ax_offset += 1
	fig = plt.figure()
	all_routing_utilizations = []
	routing_algorithm_names_proxy = ["TA", "ECMP", "MIN", "VLB", "UGAL-L", "UGAL-G",]
	all_link_utilization_barplots_dict = {}
	x = range(1, len(routing_algorithm_names) + 1 , 1)
	for routing_algorithm_name in routing_algorithm_names:
		interblock_utilizations = routing_algorithm_port_utilization[routing_algorithm_name]
		all_routing_utilizations.append(interblock_utilizations)
		all_link_utilization_barplots_dict[routing_algorithm_name] = routing_algorithm_port_utilization_pdf[routing_algorithm_name][1]
		all_link_utilization_barplots_dict["link_utilization"] = routing_algorithm_port_utilization_pdf[routing_algorithm_name][0]
	plt.boxplot(all_routing_utilizations, positions=x)
	plt.ylabel("Inter-block Link Utilization", fontsize=12)
	plt.ylim(ymax=1, ymin=0)
	plt.xlabel("Routing Protocols", fontsize=12)
	plt.xticks(x, routing_algorithm_names_proxy)

	if not os.path.exists(results_subdir + "/" + "simulations_summary"):
		os.mkdir(results_subdir + "/" + "simulations_summary")
	if not os.path.exists(results_subdir + "/" + "simulations_summary/{}".format(topol_name)):
		os.mkdir(results_subdir + "/" + "simulations_summary/{}".format(topol_name))
	if not os.path.exists(results_subdir + "/simulations_summary/{}/{}".format(topol_name, app_name)):
		os.mkdir(results_subdir + "/simulations_summary/{}/{}".format(topol_name, app_name))
	export_intergrouplinkutilization_as_pdf(results_subdir + "/simulations_summary/{}/{}/".format(topol_name, app_name) + "utilization_pdf_load{}.txt".format(load_level), all_link_utilization_barplots_dict, "link_utilization")
	export_intergrouplinkutilization_dist(results_subdir + "/simulations_summary/{}/{}/".format(topol_name, app_name) + "utilization_dist_load{}.txt".format(load_level), routing_algorithm_port_utilization)


	for routing_algorithm_name in routing_algorithm_names:
		fairness = jains_fairness([x * 10 for x in routing_algorithm_port_utilization[routing_algorithm_name]])
		print("{} fairness : {}".format(routing_algorithm_name, fairness))
	return

results_subdir = "/Users/minyee/src/jocn_reconf_expander/routing/netbench_simulations"



topol_name = "sdfly_g5_a16_h1"
#topol_name = "skewedexpander_g5_a16_h1_m10"
#topol_name = "dfly_g5_a16_h1"


app_name = "toy_example"
#app_name = "unifdfly_g4_a3_h2/dfly_adversarial_0p9"
#app_name = "unifdfly_g4_a3_h2/dfly_strain_single_link"
#app_name = "dfly_g5_a16_h1/dfly_uniform_0p5" + "/load_0p9"

app_name = "dfly_singleswitch_adversarial_0p9" 
#app_name = "stencil27P_4_4_5" 
#app_name = "dfly_singleswitch_adversarial_0p9" 
#app_name = "dfly_singleswitch_adversarial_0p9" 
#app_name = "dfly_adversarial_0p9" 
app_name = "dfly_adversarial_0p9" 
#app_name = "dfly_singleswitch_adversarial_0p9" 
#app_name = "AMG1728_Nekbone1024_linear" 
#app_name = "AMG1728_Nekbone1024_randomized" 
#app_name = "fbHadoop_linear"
#app_name = "stencil27P_4_4_5" 
nbins = 50

load_level = "0p7"
load_levels = ["0p5", "0p6", "0p7", "0p8", "0p9"]
routing_algorithm_names = ["traffic_aware_src", "ecmp", "forward", "valiant", "ugalL", "ugalG"]
for load_level in load_levels:
	plot_intergroup_link_utilizations(results_subdir, topol_name, app_name, load_level, routing_algorithm_names, nbins=nbins)

#plt.show()

#for in range():

exit()

