#!/bin/bash

# Singlepath over the top path of the demo topology

ovs-ofctl -O OpenFlow13 add-flow s1 in_port=3,priority=10,actions=output:1
ovs-ofctl -O OpenFlow13 add-flow s1 in_port=1,priority=10,actions=output:3

ovs-ofctl -O OpenFlow13 add-flow s2 in_port=1,priority=10,actions=output:2
ovs-ofctl -O OpenFlow13 add-flow s2 in_port=2,priority=10,actions=output:1

ovs-ofctl -O OpenFlow13 add-flow s3 in_port=1,priority=10,actions=output:2
ovs-ofctl -O OpenFlow13 add-flow s3 in_port=2,priority=10,actions=output:1

ovs-ofctl -O OpenFlow13 add-flow s6 in_port=1,priority=10,actions=output:3
ovs-ofctl -O OpenFlow13 add-flow s6 in_port=3,priority=10,actions=output:1
