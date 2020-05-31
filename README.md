# TAGO

TAGO is a traffic-aware, globally-direct oblivious routing algorithm for reconfigurable HPC networks. 

##Getting Started
#### Software Dependencies
TAGO simulation has the following dependencies that should be installed:
1) Gurobi (https://www.gurobi.com/)
Gurobi is needed to optimize the network topology based on predicted traffic matrix. 

2) TAGO/Netbench (https://github.com/minyee/netbench)
The original Netbench packet-level simulator can be found in (https://github.com/ndal-eth/netbench). TAGO/Netbench is built on top of the Netbench simulator, and it contains more developed modules to support the functionalities required by TAGO. Please follow the steps of setting up TAGO/Netbench, which will be required before proceeding to the next set of instructions.

#### Run
