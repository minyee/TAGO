import sys, os
sys.path.append('../')
sys.path.append('./traffic_generator')
from adaptive_routing import *
import routing_simulation_util as util
import UniformGroupDragonfly
import SkewedGroupDragonfly
import UniformGroupExpander
import SkewedGroupExpander
import DragonflyAdversarialTrafficGenerator
import DragonflyUniformTrafficGenerator
import DragonflyLoadSingleGlobalLinkTrafficGenerator
import DragonflyAdversarialSingleSwitchTrafficGenerator
import Stencil27PTrafficGenerator
import TraceBasedTrafficGenerator

NETBENCH_DIRECTORY = os.environ.get('NETBENCH_TAGO_DIRECTORY')
traces_directory = os.getcwd() + "/traces"

def develop_custom_toy_example():
	topology = {
				0 : [1, 2, 3, ],
				1 : [0, 2, 3, 4],
				2 : [0, 1, 3, 5],
				3 : [0, 1, 2, 6],
				4 : [5, 6, 7, 1],
				5 : [4, 6, 7, 2],
				6 : [4, 5, 7, 3],
				7 : [4, 5, 6, ],
				}
	switch_to_block_map = {
							0 : 0,
							1 : 0,
							2 : 0,
							3 : 0,
							4 : 1,
							5 : 1,
							6 : 1,
							7 : 1,
							}
	s2s_traffic_matrix = [
							[0, 0, 0, 0, 0, 0, 0, 5., ],
							[0, 0, 0, 0, 0, 0, 0, 0, ], 
							[0, 0, 0, 0, 0, 0, 0, 0, ],
							[0, 0, 0, 0, 0, 0, 0, 0, ],
							[0, 0, 0, 0, 0, 0, 0, 0, ],
							[0, 0, 0, 0, 0, 0, 0, 0, ],
							[0, 0, 0, 0, 0, 0, 0, 0, ],
							[0, 0, 0, 0, 0, 0, 0, 0, ],
							]
	return topology, switch_to_block_map, s2s_traffic_matrix

def toy_example_main():
	tolerance_fairness = 0
	concentration = 1
	load_level = 5.
	network_link_capacity = 100 # in gbps
	injection_link_capacity = 200 # in gbps
	average_flow_size_in_bytes = 23199798
	average_flow_size_in_gbits = float(8 * average_flow_size_in_bytes) / 1E9
	per_server_flow_arrival_rate = load_level * injection_link_capacity / average_flow_size_in_gbits
	'''
	adaptive_router = AdaptiveRouting(tolerance_fairness, max_intrablock_distance=2)

	## test it on dfly
	dragonfly = dragonfly_module.Dragonfly(5,4,1)
	dragonfly.DesignFullTopology()
	dfly_adj_list = dragonfly.GetAdjacencyList()
	dfly_switch_to_block = dragonfly.GetSwitchesToBlock()
	'''
	adaptive_router = AdaptiveRouting(tolerance_fairness, max_intrablock_distance=2)
	topology, switch_to_block_map, s2s_traffic_matrix = develop_custom_toy_example()
	routing_weights = adaptive_router.route(topology, switch_to_block_map, s2s_traffic_matrix)


	## generate 
	base_directory = "/Users/minyee/src/jocn_reconf_expander/routing"
	if not os.path.exists(base_directory + "/" + "netbench_simulations"):
		os.mkdir(base_directory + "/" + "netbench_simulations")
	if not os.path.exists(base_directory + "/netbench_simulations/toy_example"):
		os.mkdir(base_directory + "/netbench_simulations/toy_example")
	os.chdir(base_directory + "/netbench_simulations/toy_example")


	topology_adj_list_filename = "logical_topology.topology"
	util.write_topology_file("logical_topology.topology", topology, concentration=concentration)
	switch_to_block_map_filename = "switch_to_block_filename.txt"
	util.write_switch_to_block_map(switch_to_block_map_filename, switch_to_block_map)
	num_switches = len(topology.keys())

	traffic_probability_filename = "traffic_probability_filename"
	server_to_server_traffic_matrix = util.rescale_square_matrix(s2s_traffic_matrix, num_switches * concentration)
	traffic_probability_matrix = util.normalize_square_matrix(server_to_server_traffic_matrix, 1.)
	util.write_traffic_probability_file(traffic_probability_filename, traffic_probability_matrix, num_switches)
	routing_weights_filename = "routing_weights.txt"
	util.write_routing_weights_file(routing_weights_filename, routing_weights)

	## Tested Routing Schemes
	routing_schemes = [util.ROUTING.ECMP, util.ROUTING.SIMPLE_FORWARDING, util.ROUTING.TRAFFIC_AWARE_SRC]
	routing_schemes = [util.ROUTING.BLOCK_VALIANT]
	#routing_schemes = [util.ROUTING.UGAL_L, util.ROUTING.UGAL_G]
	#routing_schemes = [util.ROUTING.UGAL_G]
	output_directory = base_directory + "/netbench_simulations/toy_example"
	for routing_scheme in routing_schemes:
		sim_param_filename = util.write_simulation_properties_file(output_directory,  
																output_directory + "/" + topology_adj_list_filename, 
																output_directory + "/" + switch_to_block_map_filename, 
																output_directory + "/" + traffic_probability_filename, 
																output_directory + "/" + routing_weights_filename, 
																concentration=concentration, 
																network_link_capacity=network_link_capacity, 
																injection_link_capacity=injection_link_capacity,
																load_level=per_server_flow_arrival_rate,
																routing_class=routing_scheme)
		os.chdir(NETBENCH_DIRECTORY)
		os.system('java -jar -ea NetBench.jar {}/{}'.format(output_directory, sim_param_filename))
		os.chdir(output_directory)
	return

### uniform dragonfly simulation
def uniform_dragonfly_simulation():
	print("\n##########################################################################")
	print("Beginning Uniform Dragonfly Simulation")
	print("##########################################################################")
	## preamble, network parameters
	concentration = 1
	number_of_injectors_per_switch = 10
	#load_levels = [0.1, 0.3, 0.5, 0.7, 0.9]
	load_levels = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9]
	network_link_capacity = 40 # in gbps
	injection_link_capacity = number_of_injectors_per_switch * network_link_capacity # in gbps
	average_flow_size_in_bytes = 23199798

	average_flow_size_in_gbits = float(8 * average_flow_size_in_bytes) / 1E9
	

	## define the dragonfly parameters
	number_links_between_each_group = 4
	#number_of_groups = 5
	number_of_groups = 8
	number_of_switches_per_group = (number_of_groups - 1) * number_links_between_each_group
	uniform_dfly = UniformGroupDragonfly.UniformGroupDragonfly(number_of_groups, number_of_switches_per_group, number_links_between_each_group)
	uniform_dfly.design_full_topology()
	uniform_dfly_name_str = uniform_dfly.get_name()

	## Initialize the traffic generator
	interblock_traffic_fraction = 0.9
	#traffic_generator = DragonflyAdversarialTrafficGenerator.DragonflyAdversarialTrafficGenerator(uniform_dfly, intergroup_traffic_fraction=interblock_traffic_fraction)
	traffic_generator = DragonflyAdversarialSingleSwitchTrafficGenerator.DragonflyAdversarialSingleSwitchTrafficGenerator(uniform_dfly, intergroup_traffic_fraction=interblock_traffic_fraction)
	traffic_generator = Stencil27PTrafficGenerator.Stencil27PTrafficGenerator(uniform_dfly, (4,4,5))

	#### Trace based traffic generator 
	randomize_placement = False
	trace_files = ["AMG_1728", "nekbone_1024_shortened_original"]
	trace_alias = ["AMG1728", "Nekbone1024"]
	#trace_files = ["facebook_hadoop_6690.txt"]
	#trace_alias = ["fbHadoop"]
	trace_subdir = "/Users/minyee/src/arpa_e/traces/"
	trace_files = [trace_subdir + x for x in trace_files]
	traffic_generator = TraceBasedTrafficGenerator.TraceBasedTrafficGenerator(uniform_dfly, trace_files, trace_alias, randomize_job_mapping=randomize_placement)

	#traffic_generator = DragonflyUniformTrafficGenerator.DragonflyUniformTrafficGenerator(uniform_dfly, intergroup_traffic_fraction=interblock_traffic_fraction)
	#traffic_generator = DragonflyLoadSingleGlobalLinkTrafficGenerator.DragonflyLoadSingleGlobalLinkTrafficGenerator(uniform_dfly)
	switch_traffic_matrix = traffic_generator.generate_traffic()

	## generate the directories
	base_directory = "/Users/minyee/src/jocn_reconf_expander/routing"

	if not os.path.exists(base_directory + "/" + "netbench_simulations"):
		os.mkdir(base_directory + "/" + "netbench_simulations")
	if not os.path.exists(base_directory + "/netbench_simulations/{}".format(uniform_dfly_name_str)):
		os.mkdir(base_directory + "/netbench_simulations/{}".format(uniform_dfly_name_str))
	#os.chdir(base_directory + "/netbench_simulations/{}".format(uniform_dfly_name_str))
	if not os.path.exists(base_directory + "/netbench_simulations/{}/{}".format(uniform_dfly_name_str, traffic_generator.to_string())):
		os.mkdir(base_directory + "/netbench_simulations/{}/{}".format(uniform_dfly_name_str, traffic_generator.to_string()))

	
	uniform_dfly_adj_list = uniform_dfly.get_adjacency_list();
	## write the topology file
	topology_adj_list_filename = base_directory + "/netbench_simulations/{}/".format(uniform_dfly_name_str) + "topology_description.topology"
	util.write_topology_file(topology_adj_list_filename, uniform_dfly_adj_list)

	## then write the switch to block ID file
	switch_to_block_map_filename = base_directory + "/netbench_simulations/{}/".format(uniform_dfly_name_str) + "switch_to_block_file.txt"
	util.write_switch_to_block_map(switch_to_block_map_filename, uniform_dfly.get_switch_id_to_block_id_map())

	## Generate the traffic files
	traffic_filename = base_directory + "/netbench_simulations/{}/{}/".format(uniform_dfly_name_str, traffic_generator.to_string()) + "traffic_filename.txt"
	util.write_traffic_probability_file(traffic_filename, switch_traffic_matrix, uniform_dfly.get_total_num_switches())

	## Traffic aware source routing (start cracking the routing weights)
	tolerance_fairness = 0.00
	adaptive_router = AdaptiveRouting(tolerance_fairness, max_intrablock_distance=1)
	routing_weights = adaptive_router.route(uniform_dfly.get_adjacency_list(), uniform_dfly.get_switch_id_to_block_id_map(), switch_traffic_matrix)
	routing_weights_filename = base_directory + "/netbench_simulations/{}/{}/".format(uniform_dfly_name_str, traffic_generator.to_string()) + "routing_weights.txt"
	util.write_routing_weights_file(routing_weights_filename, routing_weights)
	
	### Finally, start writing the simulation property file for each routing algorithm, and then run the netbench simulations
	routing_schemes = [util.ROUTING.TRAFFIC_AWARE_SRC, util.ROUTING.ECMP, util.ROUTING.SIMPLE_FORWARDING, util.ROUTING.BLOCK_VALIANT]
	routing_schemes = [util.ROUTING.TRAFFIC_AWARE_SRC, util.ROUTING.ECMP, util.ROUTING.SIMPLE_FORWARDING, util.ROUTING.BLOCK_VALIANT, util.ROUTING.UGAL_G, util.ROUTING.UGAL_L]
	#routing_schemes = [util.ROUTING.TRAFFIC_AWARE_SRC]
	#routing_schemes = [util.ROUTING.ECMP, util.ROUTING.SIMPLE_FORWARDING, util.ROUTING.BLOCK_VALIANT, util.ROUTING.UGAL_G, util.ROUTING.UGAL_L]
	#routing_schemes = [util.ROUTING.BLOCK_VALIANT]
	#routing_schemes = [util.ROUTING.UGAL_L, util.ROUTING.UGAL_G]
	#routing_schemes = [util.ROUTING.UGAL_G, util.ROUTING.UGAL_L]
	output_directory = base_directory + "/netbench_simulations/{}/{}".format(uniform_dfly_name_str, traffic_generator.to_string())
	for routing_scheme in routing_schemes:
		num_total_servers = uniform_dfly.get_total_num_switches() * concentration
		for load_level in load_levels:
			per_server_flow_arrival_rate = load_level * injection_link_capacity / average_flow_size_in_gbits
			sim_param_filename = util.write_simulation_properties_file(output_directory,  
																topology_adj_list_filename, 
																switch_to_block_map_filename, 
																traffic_filename, 
																routing_weights_filename, 
																concentration=concentration, 
																network_link_capacity=network_link_capacity, 
																injection_link_capacity=injection_link_capacity,
																load_level=load_level,
																flow_arrival_per_sec=per_server_flow_arrival_rate * num_total_servers,
																routing_class=routing_scheme)
			os.chdir(NETBENCH_DIRECTORY)
			os.system('java -jar -ea NetBench.jar {}/{}'.format(output_directory, sim_param_filename))
			os.chdir(output_directory)



	print("##########################################################################")
	print("Ending Uniform Dragonfly Simulation")
	print("##########################################################################\n")
	return


### uniform expander simulation
def uniform_expander_simulation():
	print("\n##########################################################################")
	print("Beginning Uniform Expander Simulation")
	print("##########################################################################")
	## preamble, network parameters
	concentration = 1
	number_of_injectors_per_switch = 10
	#load_levels = [0.1, 0.3, 0.5, 0.7, 0.9]
	load_levels = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9]
	network_link_capacity = 40 # in gbps
	injection_link_capacity = number_of_injectors_per_switch * network_link_capacity # in gbps
	average_flow_size_in_bytes = 23199798
	average_flow_size_in_gbits = float(8 * average_flow_size_in_bytes) / 1E9
	

	## define the dragonfly parameters
	number_links_between_each_group = 4
	#number_of_groups = 5
	number_of_groups = 8
	number_of_switches_per_group = (number_of_groups - 1) * number_links_between_each_group
	num_intragroup_links_per_switch = int(0.7 * (number_of_switches_per_group - 1))
	uniform_expander = UniformGroupExpander.UniformGroupExpander(number_of_groups, number_of_switches_per_group, number_links_between_each_group, num_intragroup_links_per_switch)
	uniform_expander.design_full_topology()
	uniform_expander_name_str = uniform_expander.get_name()

	## Initialize the traffic generator
	interblock_traffic_fraction = 0.9
	#traffic_generator = DragonflyAdversarialTrafficGenerator.DragonflyAdversarialTrafficGenerator(uniform_expander, intergroup_traffic_fraction=interblock_traffic_fraction)
	traffic_generator = DragonflyAdversarialSingleSwitchTrafficGenerator.DragonflyAdversarialSingleSwitchTrafficGenerator(uniform_expander, intergroup_traffic_fraction=interblock_traffic_fraction)
	traffic_generator = Stencil27PTrafficGenerator.Stencil27PTrafficGenerator(uniform_expander, (4,4,5))

	#### Trace based traffic generator 
	randomize_placement = False
	trace_files = ["AMG_1728", "nekbone_1024_shortened_original"]
	trace_alias = ["AMG1728", "Nekbone1024"]
	#trace_files = ["facebook_hadoop_6690.txt"]
	#trace_alias = ["fbHadoop"]
	trace_subdir = "/Users/minyee/src/arpa_e/traces/"
	trace_files = [trace_subdir + x for x in trace_files]
	traffic_generator = TraceBasedTrafficGenerator.TraceBasedTrafficGenerator(uniform_expander, trace_files, trace_alias, randomize_job_mapping=randomize_placement)

	#traffic_generator = DragonflyUniformTrafficGenerator.DragonflyUniformTrafficGenerator(uniform_expander, intergroup_traffic_fraction=interblock_traffic_fraction)
	#traffic_generator = DragonflyLoadSingleGlobalLinkTrafficGenerator.DragonflyLoadSingleGlobalLinkTrafficGenerator(uniform_expander)
	switch_traffic_matrix = traffic_generator.generate_traffic()

	## generate the directories
	base_directory = "/Users/minyee/src/jocn_reconf_expander/routing"

	if not os.path.exists(base_directory + "/" + "netbench_simulations"):
		os.mkdir(base_directory + "/" + "netbench_simulations")
	if not os.path.exists(base_directory + "/netbench_simulations/{}".format(uniform_expander_name_str)):
		os.mkdir(base_directory + "/netbench_simulations/{}".format(uniform_expander_name_str))
	#os.chdir(base_directory + "/netbench_simulations/{}".format(uniform_expander_name_str))
	if not os.path.exists(base_directory + "/netbench_simulations/{}/{}".format(uniform_expander_name_str, traffic_generator.to_string())):
		os.mkdir(base_directory + "/netbench_simulations/{}/{}".format(uniform_expander_name_str, traffic_generator.to_string()))

	
	uniform_expander_adj_list = uniform_expander.get_adjacency_list();
	## write the topology file
	topology_adj_list_filename = base_directory + "/netbench_simulations/{}/".format(uniform_expander_name_str) + "topology_description.topology"
	util.write_topology_file(topology_adj_list_filename, uniform_expander_adj_list)

	## then write the switch to block ID file
	switch_to_block_map_filename = base_directory + "/netbench_simulations/{}/".format(uniform_expander_name_str) + "switch_to_block_file.txt"
	util.write_switch_to_block_map(switch_to_block_map_filename, uniform_expander.get_switch_id_to_block_id_map())

	## Generate the traffic files
	traffic_filename = base_directory + "/netbench_simulations/{}/{}/".format(uniform_expander_name_str, traffic_generator.to_string()) + "traffic_filename.txt"
	util.write_traffic_probability_file(traffic_filename, switch_traffic_matrix, uniform_expander.get_total_num_switches())

	## Traffic aware source routing (start cracking the routing weights)
	tolerance_fairness = 0.00
	adaptive_router = AdaptiveRouting(tolerance_fairness, max_intrablock_distance=2)
	routing_weights = adaptive_router.route(uniform_expander.get_adjacency_list(), uniform_expander.get_switch_id_to_block_id_map(), switch_traffic_matrix)
	routing_weights_filename = base_directory + "/netbench_simulations/{}/{}/".format(uniform_expander_name_str, traffic_generator.to_string()) + "routing_weights.txt"
	util.write_routing_weights_file(routing_weights_filename, routing_weights)
	
	### Finally, start writing the simulation property file for each routing algorithm, and then run the netbench simulations
	routing_schemes = [util.ROUTING.TRAFFIC_AWARE_SRC, util.ROUTING.ECMP, util.ROUTING.SIMPLE_FORWARDING, util.ROUTING.BLOCK_VALIANT]
	routing_schemes = [util.ROUTING.TRAFFIC_AWARE_SRC, util.ROUTING.ECMP, util.ROUTING.SIMPLE_FORWARDING, util.ROUTING.BLOCK_VALIANT, util.ROUTING.UGAL_G, util.ROUTING.UGAL_L]
	#routing_schemes = [util.ROUTING.TRAFFIC_AWARE_SRC]
	#routing_schemes = [util.ROUTING.ECMP, util.ROUTING.SIMPLE_FORWARDING, util.ROUTING.BLOCK_VALIANT, util.ROUTING.UGAL_G, util.ROUTING.UGAL_L]
	#routing_schemes = [util.ROUTING.BLOCK_VALIANT]
	#routing_schemes = [util.ROUTING.UGAL_L, util.ROUTING.UGAL_G]
	#routing_schemes = [util.ROUTING.UGAL_G, util.ROUTING.UGAL_L]
	output_directory = base_directory + "/netbench_simulations/{}/{}".format(uniform_expander_name_str, traffic_generator.to_string())
	for routing_scheme in routing_schemes:
		num_total_servers = uniform_expander.get_total_num_switches() * concentration
		for load_level in load_levels:
			per_server_flow_arrival_rate = load_level * injection_link_capacity / average_flow_size_in_gbits
			sim_param_filename = util.write_simulation_properties_file(output_directory,  
																topology_adj_list_filename, 
																switch_to_block_map_filename, 
																traffic_filename, 
																routing_weights_filename, 
																concentration=concentration, 
																network_link_capacity=network_link_capacity, 
																injection_link_capacity=injection_link_capacity,
																load_level=load_level,
																flow_arrival_per_sec=per_server_flow_arrival_rate * num_total_servers,
																routing_class=routing_scheme)
			os.chdir(NETBENCH_DIRECTORY)
			os.system('java -jar -ea NetBench.jar {}/{}'.format(output_directory, sim_param_filename))
			os.chdir(output_directory)



	print("##########################################################################")
	print("Ending Uniform Expander Simulation")
	print("##########################################################################\n")
	return

### skewed dragonfly simulation
def skewed_dragonfly_simulation():
	print("\n##########################################################################")
	print("Beginning Skewed Dragonfly Simulation")
	print("##########################################################################")
	## preamble, network parameters
	## preamble, network parameters
	concentration = 1
	number_of_injectors_per_switch = 10
	load_levels = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9]
	network_link_capacity = 40 # in gbps
	injection_link_capacity = number_of_injectors_per_switch * network_link_capacity # in gbps
	average_flow_size_in_bytes = 23199798
	average_flow_size_in_gbits = float(8 * average_flow_size_in_bytes) / 1E9

	## define the dragonfly parameters
	number_links_between_each_group = 4
	#number_of_groups = 5
	number_of_groups = 8
	number_of_switches_per_group = (number_of_groups - 1) * number_links_between_each_group
	skewed_dfly = SkewedGroupDragonfly.SkewedGroupDragonfly(number_of_groups, number_of_switches_per_group, number_links_between_each_group)
	
	skewed_dfly_name_str = skewed_dfly.get_name()

	## Initialize the traffic generator
	interblock_traffic_fraction = 0.9
	#traffic_generator = DragonflyAdversarialTrafficGenerator.DragonflyAdversarialTrafficGenerator(skewed_dfly, intergroup_traffic_fraction=interblock_traffic_fraction)
	traffic_generator = DragonflyAdversarialSingleSwitchTrafficGenerator.DragonflyAdversarialSingleSwitchTrafficGenerator(skewed_dfly, intergroup_traffic_fraction=interblock_traffic_fraction)
	traffic_generator = Stencil27PTrafficGenerator.Stencil27PTrafficGenerator(skewed_dfly, (4,4,5))

	#### Trace based traffic generator 
	randomize_placement = False
	trace_files = ["AMG_1728", "nekbone_1024_shortened_original"]
	trace_alias = ["AMG1728", "Nekbone1024"]
	#trace_files = ["facebook_hadoop_6690.txt"]
	#trace_alias = ["fbHadoop"]
	trace_subdir = "/Users/minyee/src/arpa_e/traces/"
	trace_files = [trace_subdir + x for x in trace_files]
	traffic_generator = TraceBasedTrafficGenerator.TraceBasedTrafficGenerator(skewed_dfly, trace_files, trace_alias, randomize_job_mapping=randomize_placement)

	#traffic_generator = DragonflyUniformTrafficGenerator.DragonflyUniformTrafficGenerator(skewed_dfly, intergroup_traffic_fraction=interblock_traffic_fraction)
	#traffic_generator = DragonflyLoadSingleGlobalLinkTrafficGenerator.DragonflyLoadSingleGlobalLinkTrafficGenerator(skewed_dfly)
	switch_traffic_matrix = traffic_generator.generate_traffic()

	## generate the traffic by performing bandwidth steering
	block_traffic_matrix = traffic_generator.compute_interblock_traffic_from_switch_traffic(switch_traffic_matrix, skewed_dfly.get_block_id_to_switch_ids())
	skewed_dfly.design_full_topology(block_traffic_matrix) ## need to feed in the interblock traffic

	## generate the directories
	base_directory = "/Users/minyee/src/jocn_reconf_expander/routing"

	if not os.path.exists(base_directory + "/" + "netbench_simulations"):
		os.mkdir(base_directory + "/" + "netbench_simulations")
	if not os.path.exists(base_directory + "/netbench_simulations/{}".format(skewed_dfly_name_str)):
		os.mkdir(base_directory + "/netbench_simulations/{}".format(skewed_dfly_name_str))
	#os.chdir(base_directory + "/netbench_simulations/{}".format(skewed_dfly_name_str))
	if not os.path.exists(base_directory + "/netbench_simulations/{}/{}".format(skewed_dfly_name_str, traffic_generator.to_string())):
		os.mkdir(base_directory + "/netbench_simulations/{}/{}".format(skewed_dfly_name_str, traffic_generator.to_string()))

	
	skewed_dfly_adj_list = skewed_dfly.get_adjacency_list();
	print("Printing the interblock connectivity:\n{}\n".format(skewed_dfly.get_interblock_topology()))
	## write the topology file
	topology_adj_list_filename = base_directory + "/netbench_simulations/{}/".format(skewed_dfly_name_str) + "topology_description.topology"
	util.write_topology_file(topology_adj_list_filename, skewed_dfly_adj_list)

	## then write the switch to block ID file
	switch_to_block_map_filename = base_directory + "/netbench_simulations/{}/".format(skewed_dfly_name_str) + "switch_to_block_file.txt"
	util.write_switch_to_block_map(switch_to_block_map_filename, skewed_dfly.get_switch_id_to_block_id_map())

	## Generate the traffic files
	traffic_filename = base_directory + "/netbench_simulations/{}/{}/".format(skewed_dfly_name_str, traffic_generator.to_string()) + "traffic_filename.txt"
	util.write_traffic_probability_file(traffic_filename, switch_traffic_matrix, skewed_dfly.get_total_num_switches())

	## Traffic aware source routing (start cracking the routing weights)
	tolerance_fairness = 0.00
	adaptive_router = AdaptiveRouting(tolerance_fairness, max_intrablock_distance=1)
	routing_weights = adaptive_router.route(skewed_dfly.get_adjacency_list(), skewed_dfly.get_switch_id_to_block_id_map(), switch_traffic_matrix)
	routing_weights_filename = base_directory + "/netbench_simulations/{}/{}/".format(skewed_dfly_name_str, traffic_generator.to_string()) + "routing_weights.txt"
	util.write_routing_weights_file(routing_weights_filename, routing_weights)
	
	### Finally, start writing the simulation property file for each routing algorithm, and then run the netbench simulations
	routing_schemes = [util.ROUTING.TRAFFIC_AWARE_SRC, util.ROUTING.ECMP, util.ROUTING.SIMPLE_FORWARDING, util.ROUTING.BLOCK_VALIANT]
	routing_schemes = [util.ROUTING.TRAFFIC_AWARE_SRC, util.ROUTING.ECMP, util.ROUTING.SIMPLE_FORWARDING, util.ROUTING.BLOCK_VALIANT, util.ROUTING.UGAL_G, util.ROUTING.UGAL_L]
	#routing_schemes = [util.ROUTING.TRAFFIC_AWARE_SRC]
	#routing_schemes = [util.ROUTING.ECMP, util.ROUTING.SIMPLE_FORWARDING, util.ROUTING.BLOCK_VALIANT, util.ROUTING.UGAL_G, util.ROUTING.UGAL_L]
	#routing_schemes = [util.ROUTING.BLOCK_VALIANT]
	#routing_schemes = [util.ROUTING.UGAL_L, util.ROUTING.UGAL_G]
	#routing_schemes = [util.ROUTING.UGAL_G, util.ROUTING.UGAL_L]
	output_directory = base_directory + "/netbench_simulations/{}/{}".format(skewed_dfly_name_str, traffic_generator.to_string())
	for routing_scheme in routing_schemes:
		num_total_servers = skewed_dfly.get_total_num_switches() * concentration
		for load_level in load_levels:
			per_server_flow_arrival_rate = load_level * injection_link_capacity / average_flow_size_in_gbits
			sim_param_filename = util.write_simulation_properties_file(output_directory,  
																topology_adj_list_filename, 
																switch_to_block_map_filename, 
																traffic_filename, 
																routing_weights_filename, 
																concentration=concentration, 
																network_link_capacity=network_link_capacity, 
																injection_link_capacity=injection_link_capacity,
																load_level=load_level,
																flow_arrival_per_sec=per_server_flow_arrival_rate * num_total_servers,
																routing_class=routing_scheme)
			os.chdir(NETBENCH_DIRECTORY)
			os.system('java -jar -ea NetBench.jar {}/{}'.format(output_directory, sim_param_filename))
			os.chdir(output_directory)

	print("##########################################################################")
	print("Ending Skewed Dragonfly Simulation")
	print("##########################################################################\n")
	return

### skewed expander simulation
def skewed_expander_simulation():
	print("\n##########################################################################")
	print("Beginning Skewed Expander Simulation")
	print("##########################################################################")
	## preamble, network parameters
	## preamble, network parameters
	concentration = 1
	number_of_injectors_per_switch = 10
	load_levels = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9]
	#load_levels = [0.2]
	network_link_capacity = 40 # in gbps
	injection_link_capacity = number_of_injectors_per_switch * network_link_capacity # in gbps
	average_flow_size_in_bytes = 23199798
	average_flow_size_in_gbits = float(8 * average_flow_size_in_bytes) / 1E9

	## define the dragonfly parameters
	number_links_between_each_group = 4
	#number_of_groups = 5
	number_of_groups = 8
	number_of_switches_per_group = (number_of_groups - 1) * number_links_between_each_group
	num_intragroup_links_per_switch = int(0.7 * (number_of_switches_per_group - 1))
	skewed_expander = SkewedGroupExpander.SkewedGroupExpander(number_of_groups, number_of_switches_per_group, number_links_between_each_group, num_intragroup_links_per_switch)
	
	skewed_expander_name_str = skewed_expander.get_name()

	## Initialize the traffic generator
	interblock_traffic_fraction = 0.9
	#traffic_generator = DragonflyAdversarialTrafficGenerator.DragonflyAdversarialTrafficGenerator(skewed_expander, intergroup_traffic_fraction=interblock_traffic_fraction)
	#traffic_generator = DragonflyAdversarialSingleSwitchTrafficGenerator.DragonflyAdversarialSingleSwitchTrafficGenerator(skewed_expander, intergroup_traffic_fraction=interblock_traffic_fraction)
	#traffic_generator = Stencil27PTrafficGenerator.Stencil27PTrafficGenerator(skewed_expander, (4,4,5))

	#### Trace based traffic generator 
	randomize_placement = False
	trace_files = ["AMG_1728", "nekbone_1024_shortened_original"]
	trace_alias = ["AMG1728", "Nekbone1024"]
	#trace_files = ["facebook_hadoop_6690.txt"]
	#trace_alias = ["fbHadoop"]
	trace_subdir = "/Users/minyee/src/arpa_e/traces/"
	trace_files = [trace_subdir + x for x in trace_files]
	traffic_generator = TraceBasedTrafficGenerator.TraceBasedTrafficGenerator(skewed_expander, trace_files, trace_alias, randomize_job_mapping=randomize_placement)

	#traffic_generator = DragonflyUniformTrafficGenerator.DragonflyUniformTrafficGenerator(skewed_expander, intergroup_traffic_fraction=interblock_traffic_fraction)
	#traffic_generator = DragonflyLoadSingleGlobalLinkTrafficGenerator.DragonflyLoadSingleGlobalLinkTrafficGenerator(skewed_expander)
	switch_traffic_matrix = traffic_generator.generate_traffic()

	## generate the traffic by performing bandwidth steering
	block_traffic_matrix = traffic_generator.compute_interblock_traffic_from_switch_traffic(switch_traffic_matrix, skewed_expander.get_block_id_to_switch_ids())
	skewed_expander.design_full_topology(block_traffic_matrix) ## need to feed in the interblock traffic
	## generate the directories
	base_directory = "/Users/minyee/src/jocn_reconf_expander/routing"

	if not os.path.exists(base_directory + "/" + "netbench_simulations"):
		os.mkdir(base_directory + "/" + "netbench_simulations")
	if not os.path.exists(base_directory + "/netbench_simulations/{}".format(skewed_expander_name_str)):
		os.mkdir(base_directory + "/netbench_simulations/{}".format(skewed_expander_name_str))
	#os.chdir(base_directory + "/netbench_simulations/{}".format(skewed_expander_name_str))
	if not os.path.exists(base_directory + "/netbench_simulations/{}/{}".format(skewed_expander_name_str, traffic_generator.to_string())):
		os.mkdir(base_directory + "/netbench_simulations/{}/{}".format(skewed_expander_name_str, traffic_generator.to_string()))

	
	skewed_expander_adj_list = skewed_expander.get_adjacency_list();
	print("Printing the interblock connectivity:\n{}\n".format(skewed_expander.get_interblock_topology()))
	## write the topology file
	topology_adj_list_filename = base_directory + "/netbench_simulations/{}/".format(skewed_expander_name_str) + "topology_description.topology"
	util.write_topology_file(topology_adj_list_filename, skewed_expander_adj_list)

	## then write the switch to block ID file
	switch_to_block_map_filename = base_directory + "/netbench_simulations/{}/".format(skewed_expander_name_str) + "switch_to_block_file.txt"
	util.write_switch_to_block_map(switch_to_block_map_filename, skewed_expander.get_switch_id_to_block_id_map())

	## Generate the traffic files
	traffic_filename = base_directory + "/netbench_simulations/{}/{}/".format(skewed_expander_name_str, traffic_generator.to_string()) + "traffic_filename.txt"
	util.write_traffic_probability_file(traffic_filename, switch_traffic_matrix, skewed_expander.get_total_num_switches())

	## Traffic aware source routing (start cracking the routing weights)
	tolerance_fairness = 0.00
	adaptive_router = AdaptiveRouting(tolerance_fairness, max_intrablock_distance=3)
	routing_weights = adaptive_router.route(skewed_expander.get_adjacency_list(), skewed_expander.get_switch_id_to_block_id_map(), switch_traffic_matrix)
	routing_weights_filename = base_directory + "/netbench_simulations/{}/{}/".format(skewed_expander_name_str, traffic_generator.to_string()) + "routing_weights.txt"
	util.write_routing_weights_file(routing_weights_filename, routing_weights)
	
	### Finally, start writing the simulation property file for each routing algorithm, and then run the netbench simulations
	routing_schemes = [util.ROUTING.TRAFFIC_AWARE_SRC, util.ROUTING.ECMP, util.ROUTING.SIMPLE_FORWARDING, util.ROUTING.BLOCK_VALIANT]
	routing_schemes = [util.ROUTING.TRAFFIC_AWARE_SRC, util.ROUTING.ECMP, util.ROUTING.SIMPLE_FORWARDING, util.ROUTING.BLOCK_VALIANT, util.ROUTING.UGAL_G, util.ROUTING.UGAL_L]
	#routing_schemes = [util.ROUTING.TRAFFIC_AWARE_SRC, util.ROUTING.BLOCK_VALIANT]
	#routing_schemes = [util.ROUTING.UGAL_L]
	#routing_schemes = [util.ROUTING.ECMP, util.ROUTING.SIMPLE_FORWARDING, util.ROUTING.BLOCK_VALIANT, util.ROUTING.UGAL_G, util.ROUTING.UGAL_L]
	#routing_schemes = [util.ROUTING.BLOCK_VALIANT]
	#routing_schemes = [util.ROUTING.UGAL_L, util.ROUTING.UGAL_G]
	#routing_schemes = [util.ROUTING.UGAL_G, util.ROUTING.UGAL_L]
	output_directory = base_directory + "/netbench_simulations/{}/{}".format(skewed_expander_name_str, traffic_generator.to_string())
	for routing_scheme in routing_schemes:
		num_total_servers = skewed_expander.get_total_num_switches() * concentration
		for load_level in load_levels:
			per_server_flow_arrival_rate = load_level * injection_link_capacity / average_flow_size_in_gbits
			sim_param_filename = util.write_simulation_properties_file(output_directory,  
																topology_adj_list_filename, 
																switch_to_block_map_filename, 
																traffic_filename, 
																routing_weights_filename, 
																concentration=concentration, 
																network_link_capacity=network_link_capacity, 
																injection_link_capacity=injection_link_capacity,
																load_level=load_level,
																flow_arrival_per_sec=per_server_flow_arrival_rate * num_total_servers,
																routing_class=routing_scheme)
			os.chdir(NETBENCH_DIRECTORY)
			os.system('java -jar -ea NetBench.jar {}/{}'.format(output_directory, sim_param_filename))
			os.chdir(output_directory)

	print("##########################################################################")
	print("Ending Skewed Expander Simulation")
	print("##########################################################################\n")
	return

if __name__ == "__main__":
	print("\n#################################################")
	print("Starting Routing evaluation")
	print("#################################################\n")
	#toy_example_main()
	#uniform_dragonfly_simulation()
	#skewed_dragonfly_simulation()
	#uniform_expander_simulation()
	skewed_expander_simulation()
	print("\n#################################################")
	print("Completed main")
	print("#################################################\n")