import sys, os
from enum import Enum

class ROUTING(Enum):
	ECMP = 1
	SIMPLE_FORWARDING = 2 ## ecmp but juts use single path
	TRAFFIC_AWARE_SRC = 3
	BLOCK_VALIANT = 4 ## block-aware valiant, which is a valiant like Dfly's valiant routing
	UGAL_L = 5
	UGAL_G = 6


##Given a orig_size x orig_size matrix, rescales it to a new_size x new_size matrix
def rescale_square_matrix(orig_matrix, new_size):
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

## normalizes a square matrix to "norm"
def normalize_square_matrix(matrix, norm):
	num_entries = len(matrix)
	new_matrix = [0] * num_entries
	total = sum([sum(x) for x in matrix])
	multiplicity = float(norm) / total
	for i in range(num_entries):
		new_matrix[i] = [0.] * num_entries
		for j in range(num_entries):
			new_matrix[i][j] = float(matrix[i][j]) * multiplicity
	return new_matrix


## writes the switch to block mapping to an output file
def write_switch_to_block_map(switch_to_block_filename, switch_to_block_map):
	str_builder = "## switch_id, block_id\n"
	for switch_id in switch_to_block_map.keys():
		str_builder += "{},{}\n".format(switch_id, switch_to_block_map[switch_id])
	with open(switch_to_block_filename, "w+") as f:
		f.write(str_builder)
	return

def write_topology_file(topology_filename, topology_adj_list, concentration=1):
	str_builder = "# topology adj list file\n"
	num_switches = len(topology_adj_list.keys())
	str_builder += ("|V|={}".format(num_switches) + "\n")
	num_edges = 0
	for switch in topology_adj_list.keys():
		num_edges += len(topology_adj_list[switch])
	str_builder += ("|E|={}".format(num_edges) + "\n")
	str_builder += ("ToRs=incl_range(" + str(0) + "," + str(num_switches - 1) + ")\n")
	str_builder += ("Servers=incl_range(" + str(0) + "," + str(num_switches - 1) + ")\n")
	#str_builder += ("Servers=incl_range(" + str(num_switches) + "," + str(num_switches + (num_switches * concentration) - 1) + ")\n")
	str_builder += ("Switches=set()\n\n")
	## todo (jason) : write topology file
	for src in topology_adj_list.keys():
		for dst in topology_adj_list[src]:
			str_builder += "{} {}\n".format(src, dst)
	with open(topology_filename, "w+") as f:
		f.write(str_builder)
	return


### Note that this function expects the traffic probability to be between servers, not switches
## This means that if the concentration factor is 1, then things might work. But if the traffic matrix is for switch to switch
## bu the concentration factor for each ToR is greater than 1, then there will be weird bugs in Netbench later on
def write_traffic_probability_file(traffic_probability_filename, traffic_probability_matrix, num_switches):
	str_builder = "#tor_pair_id,src,dst,pdf_num_bytes\n"
	offset = num_switches
	num_servers = len(traffic_probability_matrix)
	current_pair = 0
	for i in range(num_servers):
		for j in range(num_servers):
			if i != j and traffic_probability_matrix[i][j] > 0:
				str_builder += "{},{},{},{:.6E}\n".format(current_pair, i + offset, j + offset, traffic_probability_matrix[i][j])
				current_pair += 1
	str_builder += "\n"
	with open(traffic_probability_filename, "w+") as f:
		f.write(str_builder)
	return

## routing_weights is a dictionary of (src_block, dst_block) to a dictionary of key (switch, entry_switch) to weight
def write_routing_weights_file(routing_weights_filename, routing_weights):
	str_builder = "##switchID, targetBlock, entrySwitch, weight\n"
	print("{}\n\n".format( routing_weights))
	for (src_block, dst_block) in routing_weights.keys():
		#print("pair : {}".format((src_block, dst_block)))
		#print("vals : {}".format(routing_weights))
		#print("###################")
		for (switch_id, entry_id) in routing_weights[(src_block, dst_block)].keys():
			#print("pair : {}".format((switch_id, entry_id)))
			#print("vals : {}".format(routing_weights[(src_block, dst_block)][(switch_id, entry_id)]))
			weight = routing_weights[(src_block, dst_block)][(switch_id, entry_id)]
			str_builder += "{},{},{},{:.6E}\n".format(switch_id, dst_block, entry_id, weight)
		#print("###################")
	str_builder += "\n"
	with open(routing_weights_filename, "w+") as f:
		f.write(str_builder)
	return


## Writes the simulation's parameter filename
def write_simulation_properties_file(output_directory, 
									topology_filename, 
									switch_to_block_filename, 
									traffic_probability_filename, 
									routing_weights_filename, 
									concentration=1, 
									network_link_capacity=10, 
									injection_link_capacity=10, 
									load_level=0.5,
									flow_arrival_per_sec=30000,
									routing_class=ROUTING.TRAFFIC_AWARE_SRC,
									property_filename=None):
	## Parse load level str
	load_level_str = "{:.1}".format(load_level)
	load_level_str = load_level_str.replace('.', 'p')

	# Topology 
	str_builder = "# Topology\n"
	str_builder += "scenario_topology_file={}\n".format(topology_filename)
	str_builder += "switch_to_block_filename={}\n".format(switch_to_block_filename)
	str_builder += "scenario_topology_extend_with_servers=regular\n"
	str_builder += "scenario_topology_extend_servers_per_tl_node={}\n".format(int(concentration))
	str_builder += "\n"

	# Run info 
	results_subdir_name = ""
	if routing_class == ROUTING.TRAFFIC_AWARE_SRC:
		results_subdir_name = "traffic_aware_src"
	elif routing_class == ROUTING.SIMPLE_FORWARDING:
		results_subdir_name = "forward"
	elif routing_class == ROUTING.ECMP:
		results_subdir_name = "ecmp"
	elif routing_class == ROUTING.BLOCK_VALIANT:
		results_subdir_name = "valiant"
	elif routing_class == ROUTING.UGAL_G:
		results_subdir_name = "ugalG"
	elif routing_class == ROUTING.UGAL_L:
		results_subdir_name = "ugalL"
	else:
		raise Exception("Unrecognized routing class")
	str_builder += "# Run Info\n"
	str_builder += "run_time_s=1\n"
	str_builder += "run_folder_name={}\n".format("load_{}/results_{}".format(load_level_str, results_subdir_name))
	str_builder += "run_folder_base_dir={}\n".format(output_directory)
	#str_builder += "analysis_command=python analyze.py\n"
	str_builder += "enable_log_flow_throughput=true\n"
	str_builder += "seed=82788294\n"
	str_builder += "\n"

	# Network device and routing
	str_builder += "# Network Device\n"
	str_builder += "transport_layer=simple_dctcp\n"
	str_builder += "network_device_intermediary=identity\n"
	if routing_class == ROUTING.TRAFFIC_AWARE_SRC:
		str_builder += "network_device=traffic_aware_source_routing_switch\n"
		str_builder += "network_device_routing=traffic_aware_source_routing\n"
		str_builder += "routing_weight_filename={}\n".format(routing_weights_filename)
	elif routing_class == ROUTING.SIMPLE_FORWARDING:
		str_builder += "network_device=forwarder_switch\n"
		str_builder += "network_device_routing=single_forward\n"
	elif routing_class == ROUTING.ECMP:
		str_builder += "network_device=ecmp_switch\n"
		str_builder += "network_device_routing=ecmp\n"
	elif routing_class == ROUTING.BLOCK_VALIANT:
		str_builder += "network_device=block_valiant_switch\n"
		str_builder += "network_device_routing=block_valiant_routing\n"
	elif routing_class == ROUTING.UGAL_G:
		str_builder += "network_device=block_ugalg_queue_switch\n"
		str_builder += "network_device_routing=block_ugalG_queue_based_routing\n"
	elif routing_class == ROUTING.UGAL_L:
		str_builder += "network_device=block_ugall_queue_switch\n"
		str_builder += "network_device_routing=block_ugalL_queue_based_routing\n"
	else:
		raise Exception("Unrecognized routing class")
	str_builder += "\n"

	# Link & output port
	str_builder += "# Link & output port\n"
	str_builder += "output_port=ecn_tail_drop\n"
	str_builder += "output_port_max_queue_size_bytes=150000\n"
	str_builder += "output_port_ecn_threshold_k_bytes=30000\n"
	str_builder += "link=perfect_simple_different_injection_bandwidth\n"
	str_builder += "link_delay_ns=30\n"
	str_builder += "link_bandwidth_bit_per_ns={}\n".format(int(network_link_capacity))
	str_builder += "injection_link_bandwidth_bit_per_ns={}\n".format(int(injection_link_capacity))
	str_builder += "\n"

	#Traffic
	str_builder += "# Traffic\n"
	str_builder += "traffic=poisson_arrival\n"	
	str_builder += "traffic_lambda_flow_starts_per_s={}\n".format(max(int(flow_arrival_per_sec), 1))
	str_builder += "traffic_flow_size_dist=pfabric_web_search_upper_bound\n"
	str_builder += "traffic_probabilities_file={}\n\n".format(traffic_probability_filename)
	
	## Logging rtt of each socket
	str_builder += "enable_smooth_rtt=true\n\n"

	#str_builder += "enable_log_packet_burst_gap=true\n\n"
	#str_builder += "enable_log_congestion_window=true\n\n"

	if property_filename is not None:
		with open(output_directory + "/" + property_filename, 'w+') as f:
			f.write(str_builder)
		return "{}".format(property_filename)
	else:
		with open(output_directory + "/sim_params_{}.properties".format(results_subdir_name) , 'w+') as f:
			f.write(str_builder)
		return "sim_params_{}.properties".format(results_subdir_name)

	
