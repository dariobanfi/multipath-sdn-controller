#!/bin/bash

ovs-ofctl -O OpenFlow13 del-flows s1
ovs-ofctl -O OpenFlow13 del-flows s2
ovs-ofctl -O OpenFlow13 del-flows s3
ovs-ofctl -O OpenFlow13 del-flows s4
ovs-ofctl -O OpenFlow13 del-flows s5
ovs-ofctl -O OpenFlow13 del-flows s6

ovs-ofctl -O OpenFlow13 del-groups s1
ovs-ofctl -O OpenFlow13 del-groups s2
ovs-ofctl -O OpenFlow13 del-groups s3
ovs-ofctl -O OpenFlow13 del-groups s4
ovs-ofctl -O OpenFlow13 del-groups s5
ovs-ofctl -O OpenFlow13 del-groups s6
