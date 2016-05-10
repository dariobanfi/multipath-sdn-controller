# Multipath SDN Controller

This SDN Controller runs on top of a multipath network and sets up optimal multipath forwarding flow tables to maximize throughput.
It uses Ryu and can be tested on an emulated network such as Mininet.

## Dependencies

The controller requires a modified version of OpenvSwitch in order to run. 
It can be found in the following repositories, togheter with information about its modifications:
https://github.com/dariobanfi/ovs-multipath

## Architecture
The controller therefore has three logic components:
- Topology Discovery Component
This component is used to discover the SDN switches connected to the controller and have knowledge of the paths between them. This can be automatically be done on L2 Topologies through the Link Layer Discovery Protocol (LLDP) but can be more complex over network-layer routing and require a manual con guration (done through REST APIs).
- Multipath Routing Component
It uses the network knowledge to compute multiple paths and push the resulting computation as  ow rules to the SDN switches. The rules can be a simple forward or a multipath forward, which splits the  ow packets over two or more routes. The controller might additionally set up packet reordering rules at a switch that
- Network Measurement Component
This component is used to do real-time measurements of the network. The con- troller keeps an estimate of the latency and bandwidth of the multiple paths that connect the SDN switches of the multipath topology. This data is used by the multipath routing component to compute forwarding tables which maximize the throughput between the nodes.

## Demo 
Check out an visualization of the network benefits over here:
[https://www.youtube.com/watch?v=hkgf7l9Lshw&feature=youtu.be]()


