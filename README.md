https://zenodo.org/badge/268355125.svg

# TAGO

TAGO is a traffic-aware, globally-direct oblivious routing algorithm for reconfigurable HPC networks. 

## Getting Started
#### Software Dependencies
TAGO simulation has the following dependencies that should be installed:
1) Gurobi (https://www.gurobi.com/)
Gurobi is needed to optimize the network topology based on predicted traffic matrix. 

2) TAGO/Netbench (https://github.com/minyee/netbench)
The original Netbench packet-level simulator can be found in (https://github.com/ndal-eth/netbench). TAGO/Netbench is built on top of the Netbench simulator, and it contains more developed modules to support the functionalities required by TAGO. Please follow the steps of setting up TAGO/Netbench, which will be required before proceeding to the next set of instructions.

#### Run
1) Please ensure that TAGO/Netbench is built succesfully before attempting to run the simulations here. 
2) Before running the example simulation, set the environment variable `$NETBENCH_TAGO_DIRECTORY`. This will tell the simulator where TAGO/Netbench can be found.
3) Next, we will run an example simulation based on Facebook's published Hadoop cluster traces from [1].
4) Run `python routing_simulator.py`
5) The output from the Netbench simulator will be dumped into the user-defined directory in routing_simulator.py

### NOTE
Please run the simulator from the root directory of this project, as some of the imports are based on relative paths. Running the simulator from another directory may cause unexpected errors.

## References
[1] Roy, Arjun, et al. "Inside the social network's (datacenter) network." Proceedings of the 2015 ACM Conference on Special Interest Group on Data Communication. 2015. (https://conferences.sigcomm.org/sigcomm/2015/pdf/papers/p123.pdf)