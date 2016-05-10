#!/bin/bash

ovs-ofctl -O OpenFlow13 add-group s1 group_id=4292967296,type=select,bucket=weight:2,output:1,bucket=weight:2,output:2
ovs-ofctl -O OpenFlow13 add-flow s1 in_port=3,priority=10,actions=group:4292967296
ovs-ofctl -O OpenFlow13 add-flow s1 in_port=1,priority=10,actions=output:3

ovs-ofctl -O OpenFlow13 add-flow s2 in_port=1,priority=10,actions=output:2
ovs-ofctl -O OpenFlow13 add-flow s2 in_port=2,priority=10,actions=output:1

ovs-ofctl -O OpenFlow13 add-flow s3 in_port=1,priority=10,actions=output:2
ovs-ofctl -O OpenFlow13 add-flow s3 in_port=2,priority=10,actions=output:1

ovs-ofctl -O OpenFlow13 add-flow s4 "arp,in_port=3,arp_spa=10.0.0.3,arp_tpa=10.0.0.2, actions=output:2"
ovs-ofctl -O OpenFlow13 add-flow s4 "arp,in_port=3,arp_spa=10.0.0.3,arp_tpa=10.0.0.4, actions=output:2"
ovs-ofctl -O OpenFlow13 add-flow s4 "ip,in_port=1,nw_src=10.0.0.1,nw_dst=10.0.0.4, actions=output:2"
ovs-ofctl -O OpenFlow13 add-flow s4 "ip,in_port=2,nw_src=10.0.0.4,nw_dst=10.0.0.3, actions=output:3"
ovs-ofctl -O OpenFlow13 add-flow s4 "arp,in_port=2,arp_spa=10.0.0.4,arp_tpa=10.0.0.3, actions=output:3"
ovs-ofctl -O OpenFlow13 add-flow s4 "ip,in_port=2,nw_src=10.0.0.2,nw_dst=10.0.0.3, actions=output:3"
ovs-ofctl -O OpenFlow13 add-flow s4 "arp,in_port=2,arp_spa=10.0.0.2,arp_tpa=10.0.0.3, actions=output:3"
ovs-ofctl -O OpenFlow13 add-flow s4 "arp,in_port=1,arp_spa=10.0.0.1,arp_tpa=10.0.0.4, actions=output:2"
ovs-ofctl -O OpenFlow13 add-flow s4 "ip,in_port=2,nw_src=10.0.0.2,nw_dst=10.0.0.1, actions=output:1"
ovs-ofctl -O OpenFlow13 add-flow s4 "arp,in_port=1,arp_spa=10.0.0.1,arp_tpa=10.0.0.2, actions=output:2"
ovs-ofctl -O OpenFlow13 add-flow s4 "ip,in_port=3,nw_src=10.0.0.3,nw_dst=10.0.0.4, actions=output:2"
ovs-ofctl -O OpenFlow13 add-flow s4 "ip,in_port=3,nw_src=10.0.0.3,nw_dst=10.0.0.2, actions=output:2"
ovs-ofctl -O OpenFlow13 add-flow s4 "ip,in_port=2,nw_src=10.0.0.4,nw_dst=10.0.0.1, actions=output:1"
ovs-ofctl -O OpenFlow13 add-flow s4 "arp,in_port=2,arp_spa=10.0.0.4,arp_tpa=10.0.0.1, actions=output:1"
ovs-ofctl -O OpenFlow13 add-flow s4 "arp,in_port=3,arp_spa=10.0.0.3,arp_tpa=10.0.0.1, actions=output:1"
ovs-ofctl -O OpenFlow13 add-flow s4 "ip,in_port=3,nw_src=10.0.0.3,nw_dst=10.0.0.1, actions=output:1"
ovs-ofctl -O OpenFlow13 add-flow s4 "ip,in_port=1,nw_src=10.0.0.1,nw_dst=10.0.0.2, actions=output:2"
ovs-ofctl -O OpenFlow13 add-flow s4 "arp,in_port=1,arp_spa=10.0.0.1,arp_tpa=10.0.0.3, actions=output:3"

ovs-ofctl -O OpenFlow13 add-flow s5  "arp,in_port=2,arp_spa=10.0.0.2,arp_tpa=10.0.0.1 ,actions=output:1"
ovs-ofctl -O OpenFlow13 add-flow s5  "arp,in_port=1,arp_spa=10.0.0.3,arp_tpa=10.0.0.4 ,actions=output:3"
ovs-ofctl -O OpenFlow13 add-flow s5  "ip,in_port=2,nw_src=10.0.0.2,nw_dst=10.0.0.4 ,actions=output:3"
ovs-ofctl -O OpenFlow13 add-flow s5  "ip,in_port=1,nw_src=10.0.0.1,nw_dst=10.0.0.4 ,actions=output:3"
ovs-ofctl -O OpenFlow13 add-flow s5  "ip,in_port=2,nw_src=10.0.0.2,nw_dst=10.0.0.3 ,actions=output:1"
ovs-ofctl -O OpenFlow13 add-flow s5  "ip,in_port=3,nw_src=10.0.0.4,nw_dst=10.0.0.1 ,actions=output:1"
ovs-ofctl -O OpenFlow13 add-flow s5  "arp,in_port=3,arp_spa=10.0.0.4,arp_tpa=10.0.0.1 ,actions=output:1"
ovs-ofctl -O OpenFlow13 add-flow s5  "arp,in_port=2,arp_spa=10.0.0.2,arp_tpa=10.0.0.3 ,actions=output:1"
ovs-ofctl -O OpenFlow13 add-flow s5  "arp,in_port=1,arp_spa=10.0.0.1,arp_tpa=10.0.0.4 ,actions=output:3"
ovs-ofctl -O OpenFlow13 add-flow s5  "ip,in_port=2,nw_src=10.0.0.2,nw_dst=10.0.0.1 ,actions=output:1"
ovs-ofctl -O OpenFlow13 add-flow s5  "arp,in_port=1,arp_spa=10.0.0.3,arp_tpa=10.0.0.2 ,actions=output:2"
ovs-ofctl -O OpenFlow13 add-flow s5  "arp,in_port=1,arp_spa=10.0.0.1,arp_tpa=10.0.0.2 ,actions=output:2"
ovs-ofctl -O OpenFlow13 add-flow s5  "ip,in_port=3,nw_src=10.0.0.4,nw_dst=10.0.0.3 ,actions=output:1"
ovs-ofctl -O OpenFlow13 add-flow s5  "ip,in_port=3,nw_src=10.0.0.4,nw_dst=10.0.0.2 ,actions=output:2"
ovs-ofctl -O OpenFlow13 add-flow s5  "arp,in_port=3,arp_spa=10.0.0.4,arp_tpa=10.0.0.3 ,actions=output:1"
ovs-ofctl -O OpenFlow13 add-flow s5  "arp,in_port=2,arp_spa=10.0.0.2,arp_tpa=10.0.0.4 ,actions=output:3"
ovs-ofctl -O OpenFlow13 add-flow s5  "ip,in_port=1,nw_src=10.0.0.3,nw_dst=10.0.0.2 ,actions=output:2"
ovs-ofctl -O OpenFlow13 add-flow s5  "arp,in_port=3,arp_spa=10.0.0.4,arp_tpa=10.0.0.2 ,actions=output:2"
ovs-ofctl -O OpenFlow13 add-flow s5  "ip,in_port=1,nw_src=10.0.0.1,nw_dst=10.0.0.2 ,actions=output:2"
ovs-ofctl -O OpenFlow13 add-flow s5  "ip,in_port=1,nw_src=10.0.0.3,nw_dst=10.0.0.4 ,actions=output:3"

ovs-ofctl -O OpenFlow13 add-flow s6 in_port=1,priority=10,actions=output:3
ovs-ofctl -O OpenFlow13 add-flow s6 in_port=2,priority=10,actions=output:3
ovs-ofctl -O OpenFlow13 add-flow s6 in_port=3,priority=10,actions=output:1
